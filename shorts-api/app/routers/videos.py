# from fastapi import APIRouter, UploadFile, File, HTTPException, status, Request
# from fastapi.responses import StreamingResponse, FileResponse
# from pathlib import Path
# import os
# import shutil
# from datetime import datetime
# import uuid
# from typing import Optional

# router = APIRouter(prefix="/api/videos", tags=["videos"])

# # 업로드 디렉토리 설정
# UPLOAD_DIR = Path("uploads/videos")
# UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# # 설정
# ALLOWED_EXTENSIONS = {".mp4", ".mov", ".avi", ".webm"}
# MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB

# # 임시 저장소 (나중에 DB로 교체)
# videos_db = []


# @router.post("/upload", status_code=status.HTTP_201_CREATED)
# async def upload_video(file: UploadFile = File(...)):
#     """동영상 업로드"""
    
#     # 1. 파일 확장자 검증
#     file_ext = Path(file.filename).suffix.lower()
#     if file_ext not in ALLOWED_EXTENSIONS:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail=f"허용되지 않는 파일 형식입니다. 허용: {', '.join(ALLOWED_EXTENSIONS)}"
#         )
    
#     # 2. 고유 파일명 생성
#     unique_filename = f"{uuid.uuid4()}{file_ext}"
#     file_path = UPLOAD_DIR / unique_filename
    
#     # 3. 파일 저장
#     try:
#         with open(file_path, "wb") as buffer:
#             shutil.copyfileobj(file.file, buffer)
        
#         # 4. 파일 크기 확인
#         file_size = os.path.getsize(file_path)
        
#         if file_size > MAX_FILE_SIZE:
#             os.remove(file_path)  # 크기 초과 시 삭제
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail=f"파일 크기가 너무 큽니다. 최대: {MAX_FILE_SIZE / 1024 / 1024}MB"
#             )
        
#     except Exception as e:
#         if file_path.exists():
#             os.remove(file_path)
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"파일 저장 실패: {str(e)}"
#         )
    
#     # 5. 메타데이터 저장 (임시 - 나중에 DB)
#     video_data = {
#         "id": len(videos_db) + 1,
#         "filename": unique_filename,
#         "original_filename": file.filename,
#         "file_path": str(file_path),
#         "file_size": file_size,
#         "content_type": file.content_type,
#         "uploaded_at": datetime.now().isoformat()
#     }
    
#     videos_db.append(video_data)
    
#     return {
#         "message": "업로드 성공!",
#         "video": video_data
#     }


# @router.get("/")
# async def get_videos():
#     """동영상 목록 조회"""
#     return {
#         "total": len(videos_db),
#         "videos": videos_db
#     }


# @router.get("/{video_id}")
# async def get_video(video_id: int):
#     """단일 동영상 정보 조회"""
    
#     # 비디오 찾기
#     video = next((v for v in videos_db if v["id"] == video_id), None)
    
#     if not video:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="동영상을 찾을 수 없습니다."
#         )
    
#     return video


# @router.get("/{video_id}/stream")
# async def stream_video(video_id: int, request: Request):
#     """
#     동영상 스트리밍 (Range Request 지원)
#     브라우저에서 <video> 태그로 재생 가능
#     """
    
#     # 비디오 찾기
#     video = next((v for v in videos_db if v["id"] == video_id), None)
    
#     if not video:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="동영상을 찾을 수 없습니다."
#         )
    
#     file_path = Path(video["file_path"])
    
#     if not file_path.exists():
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="비디오 파일을 찾을 수 없습니다."
#         )
    
#     # 파일 크기
#     file_size = os.path.getsize(file_path)
    
#     # Range 헤더 확인
#     range_header = request.headers.get("range")
    
#     # Range 요청이 없으면 전체 파일 반환
#     if not range_header:
#         return FileResponse(
#             path=file_path,
#             media_type="video/mp4",
#             headers={
#                 "Accept-Ranges": "bytes",
#                 "Content-Length": str(file_size),
#             }
#         )
    
#     # Range 헤더 파싱 (예: "bytes=0-1023")
#     range_str = range_header.replace("bytes=", "")
#     start, end = range_str.split("-")
    
#     start = int(start)
#     end = int(end) if end else file_size - 1
    
#     # 범위 검증
#     if start >= file_size or end >= file_size:
#         raise HTTPException(
#             status_code=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE,
#             detail="요청한 범위가 유효하지 않습니다."
#         )
    
#     # 읽을 크기
#     chunk_size = end - start + 1
    
#     # 파일에서 해당 범위 읽기
#     def iter_file():
#         with open(file_path, "rb") as f:
#             f.seek(start)
#             remaining = chunk_size
#             while remaining > 0:
#                 read_size = min(8192, remaining)  # 8KB씩 읽기
#                 data = f.read(read_size)
#                 if not data:
#                     break
#                 remaining -= len(data)
#                 yield data
    
#     # 206 Partial Content 응답
#     return StreamingResponse(
#         iter_file(),
#         status_code=206,
#         media_type="video/mp4",
#         headers={
#             "Content-Range": f"bytes {start}-{end}/{file_size}",
#             "Accept-Ranges": "bytes",
#             "Content-Length": str(chunk_size),
#         }
#     )


# @router.get("/{video_id}/download")
# async def download_video(video_id: int):
#     """동영상 다운로드 (별도 엔드포인트)"""
    
#     video = next((v for v in videos_db if v["id"] == video_id), None)
    
#     if not video:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="동영상을 찾을 수 없습니다."
#         )
    
#     file_path = Path(video["file_path"])
    
#     if not file_path.exists():
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="비디오 파일을 찾을 수 없습니다."
#         )
    
#     return FileResponse(
#         path=file_path,
#         media_type="application/octet-stream",
#         filename=video["original_filename"],
#         headers={
#             "Content-Disposition": f'attachment; filename="{video["original_filename"]}"'
#         }
#     )


# @router.delete("/{video_id}")
# async def delete_video(video_id: int):
#     """동영상 삭제"""
    
#     global videos_db
    
#     # 비디오 찾기
#     video = next((v for v in videos_db if v["id"] == video_id), None)
    
#     if not video:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="동영상을 찾을 수 없습니다."
#         )
    
#     # 파일 삭제
#     file_path = Path(video["file_path"])
#     if file_path.exists():
#         os.remove(file_path)
    
#     # DB에서 제거
#     videos_db = [v for v in videos_db if v["id"] != video_id]
    
#     return {"message": "삭제 완료"}

from fastapi import APIRouter, UploadFile, File, HTTPException, status, Request, Depends
from fastapi.responses import StreamingResponse, FileResponse
from pathlib import Path
import os
import shutil
import uuid
from typing import List
from sqlalchemy.orm import Session # 세션 임포트
from app.database import get_db # DB 관련 임포트
from app.schemas import Video as VideoSchema # 스키마 임포트
from app.models import Video

router = APIRouter(prefix="/api/videos", tags=["videos"])

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
async def stream_video(video_id: int, request: Request, db: Session = Depends(get_db)): # 👈 DB 의존성 주입
    """동영상 스트리밍 (Range Request 지원)"""
    
    # 비디오 찾기
    video = db.query(Video).filter(Video.id == video_id).first()
    
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="동영상을 찾을 수 없습니다."
        )
    
    # ... (Range Header 처리 및 파일 스트리밍 로직은 기존 코드와 거의 동일) ...
    
    file_path = Path(video.file_path) # SQLAlchemy 객체의 속성 접근
    
    # ... (나머지 로직 유지) ...


@router.get("/{video_id}/download")
async def download_video(video_id: int, db: Session = Depends(get_db)): # 👈 DB 의존성 주입
    """동영상 다운로드 (별도 엔드포인트)"""
    
    video = db.query(Video).filter(Video.id == video_id).first()
    
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="동영상을 찾을 수 없습니다."
        )
    
    # ... (나머지 로직 유지) ...

    
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
    if file_path.exists():
        os.remove(file_path) 
    
    # 2. DB에서 제거
    db.delete(video)
    db.commit()
    
    return {"message": "삭제 완료"}