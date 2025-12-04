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
from app.schemas import Video as VideoSchema,VideoUpdate , VideoListResponse# 스키마 임포트
from app.models import Video,Comments,Like
from app.s3_client import upload_file_to_s3, delete_file_from_s3, s3_client, BUCKET_NAME
from urllib.parse import quote

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

@router.get("/search")
async def search_videos(
    q: str,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """동영상 검색 - 문자열 포함 검색"""
    
    videos = db.query(Video).filter(
        Video.original_filename.ilike(f"%{q}%")  # ilike = 대소문자 무시
    ).offset(skip).limit(limit).all()
    
    total = db.query(Video).filter(
        Video.original_filename.ilike(f"%{q}%")
    ).count()
    
    # dict로 변환 (JSON 직렬화를 위해)
    video_list = []
    for video in videos:
        video_list.append({
            "id": video.id,
            "filename": video.filename,
            "original_filename": video.original_filename,
            "file_path": video.file_path,
            "file_size": video.file_size,
            "content_type": video.content_type,
            "uploaded_at": video.uploaded_at.isoformat() if video.uploaded_at else None,
            "updated_at": video.updated_at.isoformat() if video.updated_at else None
        })
    
    return {
        "total": total,
        "videos": video_list
    }

@router.post("/upload", status_code=status.HTTP_201_CREATED, response_model=VideoSchema)
async def upload_video(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """동영상 업로드"""
    
    # 1. 파일 확장자 검증 (동일)
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"허용되지 않는 파일 형식입니다."
        )
    
    # 2. 고유 파일명 생성 (동일)
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    
    # 3. 파일 내용 읽기 (메모리에서 처리)
    try:
        file_content = await file.read()
        file_size = len(file_content)
        
        # 파일 크기 검증
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"파일 크기가 너무 큽니다."
            )
        
        # 4. S3에 업로드 ⭐
        s3_url = upload_file_to_s3(
            file_content=file_content,
            filename=unique_filename,
            content_type=file.content_type
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"파일 업로드 실패: {str(e)}"
        )
    
    # 5. DB에 S3 URL 저장 ⭐
    db_video = Video(
        filename=unique_filename,
        original_filename=file.filename,
        file_path=s3_url,  # S3 URL로 저장!
        file_size=file_size,
        content_type=file.content_type
    )
    
    db.add(db_video)
    db.commit()
    db.refresh(db_video)
    
    return db_video


@router.get("/", response_model=VideoListResponse) # 👈 응답 모델 수정
async def get_videos(skip : int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
    ): # 👈 DB 의존성 주입

    """동영상 목록 조회"""

    videos = db.query(Video).order_by(Video.id.desc()).offset(skip).limit(limit).all()
    # Pydantic이 ORM_MODE=True 덕분에 SQLAlchemy 객체 리스트를 스키마 리스트로 변환함
    total = db.query(Video).count()

    return {
        "total": total,
        "videos": videos
    }


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


from app.s3_client import s3_client, BUCKET_NAME

@router.get("/{video_id}/stream")
async def stream_video(video_id: int, request: Request, db: Session = Depends(get_db)):
    """동영상 스트리밍 (Range Request 지원)"""

    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="동영상을 찾을 수 없습니다.")

    # Range 헤더 확인
    range_header = request.headers.get("range")
    
    # Range 요청 없으면 전체 파일
    if not range_header:
        try:
            # S3에서 파일 가져오기 ⭐
            s3_response = s3_client.get_object(
                Bucket=BUCKET_NAME,
                Key=video.filename
            )
            
            return StreamingResponse(
                s3_response['Body'].iter_chunks(),
                media_type=video.content_type,
                headers={
                    "Accept-Ranges": "bytes",
                    "Content-Length": str(video.file_size),
                }
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"스트리밍 실패: {str(e)}")
    
    # Range 헤더 파싱
    range_str = range_header.replace("bytes=", "")
    start, end = range_str.split("-")
    
    start = int(start)
    end = int(end) if end else video.file_size - 1
    
    # 범위 검증
    if start >= video.file_size or end >= video.file_size:
        raise HTTPException(status_code=416, detail="유효하지 않은 범위")
    
    chunk_size = end - start + 1
    
    try:
        # S3 Range Request ⭐
        s3_response = s3_client.get_object(
            Bucket=BUCKET_NAME,
            Key=video.filename,
            Range=f"bytes={start}-{end}"
        )
        
        return StreamingResponse(
            s3_response['Body'].iter_chunks(),
            status_code=206,
            media_type=video.content_type,
            headers={
                "Content-Range": f"bytes {start}-{end}/{video.file_size}",
                "Accept-Ranges": "bytes",
                "Content-Length": str(chunk_size),
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"스트리밍 실패: {str(e)}")


@router.get("/{video_id}/download")
async def download_video(video_id: int, db: Session = Depends(get_db)):
    """동영상 다운로드"""
    
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="동영상을 찾을 수 없습니다.")
    
    try:
        # S3에서 파일 가져오기 ⭐
        s3_response = s3_client.get_object(
            Bucket=BUCKET_NAME,
            Key=video.filename
        )
        
        # 파일명 처리
        file_ext = Path(video.filename).suffix
        download_filename = video.original_filename if video.original_filename.endswith(file_ext) else f"{video.original_filename}{file_ext}"
        
        encoded_filename = quote(download_filename)

        return StreamingResponse(
            s3_response['Body'].iter_chunks(),
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"다운로드 실패: {str(e)}")
    




@router.delete("/{video_id}", status_code=status.HTTP_200_OK)
async def delete_video(video_id: int, db: Session = Depends(get_db)):
    """동영상 삭제"""
    
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="동영상을 찾을 수 없습니다.")
    
    # DB에서 먼저 삭제
    try:
        db.delete(video)
        db.commit()
        logger.info(f"✅ DB 삭제 완료: video_id={video_id}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="DB 삭제 실패")
    
    # S3에서 파일 삭제 ⭐
    file_deleted = False
    try:
        delete_file_from_s3(video.filename)
        logger.info(f"✅ S3 파일 삭제 성공: {video.filename}")
        file_deleted = True
    except Exception as e:
        logger.error(f"S3 파일 삭제 오류: {e}")
        # 파일 삭제 실패해도 DB는 이미 삭제됨
    
    return {
        "success": True,
        "message": "삭제 완료",
        "file_deleted": file_deleted
    }

@router.put("/{video_id}", response_model=VideoSchema)
async def update_video(
    video_id: int,
    file: UploadFile = File(None),  # 선택사항
    original_filename: str = Form(None),  # 선택사항
    db: Session = Depends(get_db)
):
    """
    동영상 정보 수정
    - original_filename만 제공: 이름만 변경
    - file만 제공: 파일만 교체
    - 둘 다 제공: 파일 교체 + 이름 변경
    """
    
    # 1. 비디오 찾기
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="동영상을 찾을 수 없습니다."
        )
    
    # 2. 수정할 내용이 있는지 확인
    if not file and not original_filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="수정할 내용이 없습니다. (파일 또는 파일명을 제공하세요)"
        )
    
    old_filename = video.filename  # S3 삭제용
    
    # 3. 파일 교체 (file이 제공된 경우)
    if file:
        # 파일 확장자 검증
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"허용되지 않는 파일 형식입니다. 허용: {', '.join(ALLOWED_EXTENSIONS)}"
            )
        
        # 새 고유 파일명 생성
        new_unique_filename = f"{uuid.uuid4()}{file_ext}"
        
        try:
            # 파일 내용 읽기
            file_content = await file.read()
            new_file_size = len(file_content)
            
            # 파일 크기 검증
            if new_file_size > MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"파일 크기가 너무 큽니다. 최대: {MAX_FILE_SIZE / 1024 / 1024}MB"
                )
            
            # S3에 새 파일 업로드
            new_s3_url = upload_file_to_s3(
                file_content=file_content,
                filename=new_unique_filename,
                content_type=file.content_type
            )
            
            # DB 필드 업데이트
            video.filename = new_unique_filename
            video.file_path = new_s3_url
            video.file_size = new_file_size
            video.content_type = file.content_type
            
            logger.info(f"✅ S3 파일 업로드 성공: {new_unique_filename}")
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"파일 업로드 실패: {str(e)}"
            )
    
    # 4. 파일명 변경 (original_filename이 제공된 경우)
    if original_filename:
        video.original_filename = original_filename
        logger.info(f"✅ 파일명 변경: {original_filename}")
    
    # 5. DB 커밋
    try:
        db.commit()
        db.refresh(video)
        logger.info(f"✅ DB 업데이트 완료: video_id={video_id}")
        
        # 6. 파일 교체 성공 시 기존 S3 파일 삭제
        if file and old_filename != video.filename:
            try:
                delete_file_from_s3(old_filename)
                logger.info(f"✅ 기존 S3 파일 삭제 성공: {old_filename}")
            except Exception as e:
                # 기존 파일 삭제 실패해도 무시 (새 파일은 이미 업로드됨)
                logger.warning(f"⚠️ 기존 S3 파일 삭제 실패: {e}")
        
        return video
        
    except SQLAlchemyError as e:
        db.rollback()
        
        # DB 업데이트 실패 시: 새로 업로드한 S3 파일 삭제
        if file:
            try:
                delete_file_from_s3(video.filename)
                logger.info(f"🔄 롤백: 새 S3 파일 삭제")
            except Exception:
                pass
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"DB 업데이트 실패: {str(e)}"
        )
    

        new_original_name = Path(file.filename).stem
        new_s3_filename = f"{new_original_name}_{uuid.uuid4()}{file_ext}"
        asd = {uuid.uuid4()}
        