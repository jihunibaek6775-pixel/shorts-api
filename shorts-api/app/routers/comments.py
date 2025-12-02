from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import logging
# 로컬 파일에서 필요한 요소들을 가져옵니다.
# FastAPI 프로젝트 구조에 따라 경로는 달라질 수 있습니다.
from app.database import get_db
from app.models import Comments, Video # Comments 모델과 Videos 모델 필요
from app.schemas import CommentCreate, CommentResponse , CommentUpdate , CommentListResponse
from datetime import datetime

# APIRouter 인스턴스 생성
router = APIRouter(prefix="/api/videos", tags=["comments"])

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__) 
# 사용자 식별자 (임시)
# 실제 프로젝트에서는 인증 시스템에서 현재 로그인된 사용자 정보를 가져와야 합니다.
def get_current_user_identifier():
    # 실제로는 JWT 토큰 등을 통해 사용자 ID를 반환해야 합니다.
    return "guest_user_123" 


## 1. 댓글 목록 조회 API (GET)
# GET /videos/{video_id}/comments
@router.get("/{video_id}/comments", response_model=CommentListResponse)
def read_comments(
    video_id: int, 
    skip : int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """
    특정 영상(video_id)에 달린 모든 댓글을 조회합니다.
    """
    
    # 1. 비디오 존재 여부 확인 (댓글을 달 대상이 있는지 확인)
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="동영상을 찾을 수 없습니다."
        )

    # 2. 해당 video_id를 가진 댓글들을 최신순(created_at 내림차순)으로 조회
    comments = db.query(Comments).filter(
        Comments.video_id == video_id
    ).order_by(
        Comments.created_at.desc()
    ).offset(skip).limit(limit).all()
    
    # 댓글 총 개수 
    total = db.query(Comments).filter(
        Comments.video_id == video_id
    ).count()

    return {
        "total": total,
        "comments": comments
    }


## 2. 댓글 작성 API (POST)
# POST /videos/{video_id}/comments
@router.post("/{video_id}/comments", response_model=CommentResponse , status_code=status.HTTP_201_CREATED)
def create_comment(
    video_id: int, 
    comment: CommentCreate, # Pydantic 스키마로 요청 본문 검증
    db: Session = Depends(get_db),
    user_identifier: str = Depends(get_current_user_identifier) # 임시 사용자 ID
):
    """
    특정 영상에 새로운 댓글을 작성합니다.
    """
    
    # 1. 비디오 존재 여부 확인
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="동영상을 찾을 수 없습니다."
        )
    
    # 2. 새 댓글 객체 생성
    db_comment = Comments(
        video_id=video_id,
        user_identifier=user_identifier, # 로그인한 사용자 ID 사용
        content=comment.content          # 요청 본문에서 받은 내용 사용
        # created_at 필드는 models.py에서 server_default=func.now()로 자동 설정됨
    )
    
    # 3. 데이터베이스에 저장
    db.add(db_comment)
    db.commit()
    db.refresh(db_comment) # 데이터베이스에서 자동 생성된 id와 created_at을 가져옴
    
    return db_comment

@router.delete("/{video_id}/comments/{comment_id}", status_code=status.HTTP_200_OK)
async def delete_comments(video_id: int, comment_id: int, db: Session = Depends(get_db)):
    """댓글 삭제"""
    
    # 댓글 찾기 (video_id와 comment_id를 모두 사용)
    comment = db.query(Comments).filter(Comments.id == comment_id, Comments.video_id == video_id).first()
    
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="댓글을 찾을 수 없습니다."
        )

     # DB에서 삭제
    try:
        db.delete(comment)
        db.commit()
        logger.info(f"✅ DB 삭제 완료: comment_id={comment_id}")
    except Exception as e:
        db.rollback()
        logger.error(f"DB 삭제 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="DB 삭제 실패"
        )
    
    return {
        "success": True,
        "message": "삭제 완료",
        "comment_id": comment_id
    }


@router.patch("/{video_id}/comments/{comment_id}", response_model=CommentResponse)
async def update_comments(
    video_id: int,
    comment_id: int,
    comment_update: CommentUpdate, # 명확성을 위해 변수명 변경
    db: Session = Depends(get_db)
):
    """댓글 수정"""
    

    # 댓글 찾기 (video_id와 comment_id를 모두 사용)                                     
    comment = db.query(Comments).filter(Comments.id == comment_id, Comments.video_id == video_id).first()

    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="댓글을 찾을 수 없습니다."
        )
    
    update_data = comment_update.dict(exclude_unset=True)

    if "content" in update_data and update_data["content"]:
        comment.content = update_data["content"]
        comment.updated_at = datetime.now() # 수정 시간 기록
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="수정할 내용이 없습니다."    
        )
    
    try:
        db.commit()
        db.refresh(comment)
        logger.info(f"✅ 댓글 수정 완료: comment_id={comment_id}, content={comment.content}")
    except Exception as e:
        db.rollback()
        logger.error(f"DB 정보 수정 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="DB 정보 수정 실패"
        )
    
    return comment