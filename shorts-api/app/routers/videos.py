from fastapi import APIRouter, UploadFile, File, HTTPException, status, Request, Depends , Form
from fastapi.responses import StreamingResponse, FileResponse , JSONResponse
from pathlib import Path
import os
import shutil
import uuid
import logging
import asyncio
from typing import List
from sqlalchemy.orm import Session # 세션 임포트
from sqlalchemy.exc import SQLAlchemyError
from app.database import get_db # DB 관련 임포트
from app.schemas import Video as VideoSchema,VideoUpdate # 스키마 임포트
from app.models import Video

router = APIRouter(prefix="/api/videos", tags=["videos"])

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__) 

# ... (기존 설정: UPLOAD_DIR, ALLOWED_EXTENSIONS, MAX_FILE_SIZE 등 유지) ...

# 업로드 디렉토리 설정
UPLOAD_DIR = Path("uploads/videos")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# 설정
ALLOWED_EXTENSIONS = {".mp4", ".mov", ".avi", ".webm"}
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB

# 🚫 임시 저장소 videos_db 삭제 또는 주석 처리

@router.post("/upload", status_code=status.HTTP_201_CREATED, response_model=VideoSchema)
async def upload_video(file: UploadFile = File(...), db: Session = Depends(get_db)): # 👈 DB 의존성 주입
    """동영상 업로드"""
    
    # 1. 파일 확장자 검증 (기존 코드와 동일)
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"허용되지 않는 파일 형식입니다. 허용: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # 2. 고유 파일명 생성 (기존 코드와 동일)
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = UPLOAD_DIR / unique_filename
    
    # 3. 파일 저장 및 크기 확인 (기존 코드와 동일)
    try:
        # 파일을 임시로 저장하여 크기를 확인
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        file_size = os.path.getsize(file_path)
        
        if file_size > MAX_FILE_SIZE:
            os.remove(file_path) 
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"파일 크기가 너무 큽니다. 최대: {MAX_FILE_SIZE / 1024 / 1024}MB"
            )
        
    except Exception as e:
        if file_path.exists():
            os.remove(file_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"파일 저장 실패: {str(e)}"
        )
    
    # 4. 메타데이터 DB 저장 (기존 videos_db 대체)
    # SQLAlchemy 모델 인스턴스 생성
    db_video = Video(
        filename=unique_filename,
        original_filename=file.filename,
        file_path=str(file_path),
        file_size=file_size,
        content_type=file.content_type
    )
    
    db.add(db_video) # DB 세션에 추가
    db.commit()      # DB에 반영
    db.refresh(db_video) # DB로부터 생성된 ID 등을 포함하여 객체 갱신
    
    # 응답은 Pydantic 스키마(VideoSchema)에 맞춤
    return db_video


@router.get("/", response_model=List[VideoSchema]) # 👈 응답 모델 수정
async def get_videos(db: Session = Depends(get_db)): # 👈 DB 의존성 주입
    """동영상 목록 조회"""
    videos = db.query(Video).all()
    # Pydantic이 ORM_MODE=True 덕분에 SQLAlchemy 객체 리스트를 스키마 리스트로 변환함
    return videos 


@router.get("/{video_id}", response_model=VideoSchema) # 👈 응답 모델 수정
async def get_video(video_id: int, db: Session = Depends(get_db)): # 👈 DB 의존성 주입
    """단일 동영상 정보 조회"""
    
    # DB에서 ID를 사용하여 비디오 찾기
    video = db.query(Video).filter(Video.id == video_id).first()
    
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="동영상을 찾을 수 없습니다."
        )
    
    return video # SQLAlchemy 객체 반환


@router.get("/{video_id}/stream")
async def stream_video(video_id: int, request: Request, db: Session = Depends(get_db)):
    """동영상 스트리밍 (Range Request 지원)"""

    # 비디오 찾기
    video = db.query(Video).filter(Video.id == video_id).first()

    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="동영상을 찾을 수 없습니다."
        )

    file_path = Path(video.file_path)

    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="비디오 파일을 찾을 수 없습니다."
        )

    # 파일 크기
    file_size = os.path.getsize(file_path)

    # Range 헤더 확인
    range_header = request.headers.get("range")

    # Range 요청이 없으면 전체 파일 반환
    if not range_header:
        return FileResponse(
            path=file_path,
            media_type="video/mp4",
            headers={
                "Accept-Ranges": "bytes",
                "Content-Length": str(file_size),
            }
        )

    # Range 헤더 파싱 (예: "bytes=0-1023")
    range_str = range_header.replace("bytes=", "")
    start, end = range_str.split("-")

    start = int(start)
    end = int(end) if end else file_size - 1

    # 범위 검증
    if start >= file_size or end >= file_size:
        raise HTTPException(
            status_code=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE,
            detail="요청한 범위가 유효하지 않습니다."
        )

    # 읽을 크기
    chunk_size = end - start + 1

    # 파일에서 해당 범위 읽기
    def iter_file():
        with open(file_path, "rb") as f:
            f.seek(start)
            remaining = chunk_size
            while remaining > 0:
                read_size = min(8192, remaining)  # 8KB씩 읽기
                data = f.read(read_size)
                if not data:
                    break
                remaining -= len(data)
                yield data

    # 206 Partial Content 응답
    return StreamingResponse(
        iter_file(),
        status_code=206,
        media_type="video/mp4",
        headers={
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(chunk_size),
        }
    )


@router.get("/{video_id}/download")
async def download_video(video_id: int, db: Session = Depends(get_db)):
    """동영상 다운로드 (별도 엔드포인트)"""

    video = db.query(Video).filter(Video.id == video_id).first()

    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="동영상을 찾을 수 없습니다."
        )

    file_path = Path(video.file_path)

    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="비디오 파일을 찾을 수 없습니다."
        )
    
    file_ext = file_path.suffix  # .mp4, .mov, .avi 등
    
    # original_filename에 이미 확장자가 있는지 확인
    if video.original_filename.endswith(file_ext):
        # 이미 확장자 있음 → 그대로 사용
        download_filename = video.original_filename
    else:
        # 확장자 없음 → 자동 추가
        download_filename = f"{video.original_filename}{file_ext}"

    return FileResponse(
        path=file_path,
        media_type="application/octet-stream",
        filename=download_filename,
    )


@router.delete("/{video_id}", status_code=status.HTTP_200_OK)
async def delete_video(video_id: int, db: Session = Depends(get_db)): # 👈 DB 의존성 주입
    """동영상 삭제"""
    
    # 비디오 찾기
    video = db.query(Video).filter(Video.id == video_id).first()
    
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="동영상을 찾을 수 없습니다."
        )
    
    # 1. 파일 삭제
    file_path = Path(video.file_path)

     # DB에서 먼저 삭제
    try:
        db.delete(video)
        db.commit()
        logger.info(f"✅ DB 삭제 완료: video_id={video_id}")
    except Exception as e:
        db.rollback()
        logger.error(f"DB 삭제 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="DB 삭제 실패"
        )
    
    # 파일 삭제 (에러가 나도 무시)
    file_deleted = False
    if file_path.exists():
        for attempt in range(3):
            try:
                if attempt > 0:
                    await asyncio.sleep(0.2)
                
                os.remove(file_path)
                logger.info(f"✅ 파일 삭제 성공: {file_path}")
                file_deleted = True
                break
                
            except PermissionError:
                logger.warning(f"⚠️ 파일 사용 중 (시도 {attempt + 1}/3)")
                # 마지막 시도에도 실패하면 그냥 넘어감
                
            except Exception as e:
                logger.error(f"파일 삭제 오류: {e}")
                break
    
    # 성공 응답 (파일 삭제 실패해도 200 반환)
    return {
        "success": True,
        "message": "삭제 완료",
        "file_deleted": file_deleted
    }
@router.patch("/{video_id}",response_model=VideoSchema)
async def update_video_filename(
    video_id : int,
    video_update : VideoUpdate,
    db : Session = Depends(get_db)
):
    """비디오 원본 파일명(original_filename) 수정"""
    # 비디오 찾기                                     
    video = db.query(Video).filter(Video.id == video_id).first()

    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="동영상을 찾을 수 없습니다."
        )
    update_data = video_update.dict(exclude_unset=True)
    if not update_data : 
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="수정할 내용이 없습니다."    
        )
    
    if "original_filename" in update_data :
        video.original_filename = update_data["original_filename"]
    try :
        db.commit()
        db.refresh(video)
        logger.info(f"✅ 동영상 정보 수정 완료: video_id={video_id}, new_filename={video.original_filename}")
    except Exception as e:
        db.rollback()
        logger.error(f"DB 정보 수정 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="DB 정보 수정 실패"
        )
    
    return video

@router.put("/{video_id}",response_model=VideoSchema)
async def replace_video_file(
    video_id: int, 
    file: UploadFile = File(..., description="교체할 새로운 동영상 파일"),
    # original_filename을 폼 데이터로 받거나, 파일 이름 그대로 사용
    original_filename: str = Form(None), 
    db: Session = Depends(get_db)
):
    #비디오 찾기
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="동영상을 찾을 수 없습니다."
        )
    
    old_file_path = video.file_path
    
    # 2. 새 파일 정보 준비 및 저장
    # 파일명 충돌 방지를 위해 UUID나 고유한 이름 사용
    file_extension = os.path.splitext(file.filename)[1]
    new_filename = f"{os.urandom(16).hex()}{file_extension}"
    new_file_path = os.path.join(UPLOAD_DIR, new_filename)
    
    # 새 파일 임시 저장
    try:
        with open(new_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # 파일 크기 확인
        new_file_size = os.path.getsize(new_file_path)
        
    except Exception as e:
        # 파일 저장 실패 시 500 에러 반환
        raise HTTPException(status_code=500, detail=f"Failed to save new file: {e}")

    # 3. DB 업데이트 시도 (트랜잭션 시작)
    try:
        # DB 필드 업데이트
        video.file_path = new_file_path
        video.file_size = new_file_size
        video.original_filename = original_filename if original_filename else file.filename
        video.content_type = file.content_type
        video.filename = new_filename
        # updated_at은 models.py의 onupdate에 의해 자동으로 갱신됩니다.
        
        db.add(video)
        db.commit()
        db.refresh(video)
        
        # 4. 성공 시: 기존 파일 삭제
        if os.path.exists(old_file_path):
            try:
                os.remove(old_file_path)

            except PermissionError:
            # 파일 사용 중이면 무시 (나중에 수동 삭제)
                logger.warning(f"⚠️ 기존 파일 삭제 실패 (사용 중): {old_file_path}")
            except Exception as e:
                logger.error(f"❌ 파일 삭제 오류: {e}")
        
        return video

    except SQLAlchemyError as e:
        # 5. DB 업데이트 실패 시: 롤백 및 새로 저장한 파일 삭제
        db.rollback()
        if os.path.exists(new_file_path):
            os.remove(new_file_path) # 새로 저장한 파일 삭제 (롤백)
        
        # 500 에러를 반환하여 클라이언트에게 실패 알림
        raise HTTPException(status_code=500, detail=f"Database update failed. Rolled back. Error: {e}")

    except Exception as e:
        # 기타 예상치 못한 오류 발생 시
        db.rollback() # 혹시 모를 트랜잭션 롤백
        if os.path.exists(new_file_path):
            os.remove(new_file_path) # 새로 저장한 파일 삭제
        
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred during replacement: {e}")
