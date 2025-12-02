from fastapi import APIRouter, HTTPException, status, Depends, Request
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..database import get_db
from ..models import Video, Like
from ..schemas import LikeResponse, LikeStatus

router = APIRouter(prefix="/api/videos", tags=["likes"])


def get_user_identifier(request: Request) -> str:
    """
    사용자 식별자 가져오기
    - 임시로 IP 주소 사용
    - 나중에 JWT 인증 시 user_id로 변경
    """
    return request.client.host


@router.post("/{video_id}/like", response_model=LikeStatus, status_code=status.HTTP_200_OK)
async def toggle_like(
    video_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    좋아요 토글
    - 좋아요 안 눌렀으면 → 좋아요
    - 이미 눌렀으면 → 좋아요 취소
    """
    
    # 비디오 존재 확인
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="동영상을 찾을 수 없습니다."
        )
    
    # 사용자 식별자
    user_identifier = get_user_identifier(request)
    
    # 이미 좋아요 눌렀는지 확인
    existing_like = db.query(Like).filter(
        Like.video_id == video_id,
        Like.user_identifier == user_identifier
    ).first()
    
    if existing_like:
        # 좋아요 취소
        db.delete(existing_like)
        db.commit()
        
        is_liked = False
    
    else:
        # 좋아요 추가
        new_like = Like(
            video_id=video_id,
            user_identifier=user_identifier
        )
        db.add(new_like)
        db.commit()
        is_liked = True
        
    # 현재 좋아요 개수
    like_count = db.query(func.count(Like.id)).filter(Like.video_id == video_id).scalar()
    
    return {
        "video_id": video_id,
        "like_count": like_count or 0,
        "is_liked": is_liked
    }


@router.get("/{video_id}/like", response_model=LikeStatus)
async def get_like_status(
    video_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    좋아요 상태 조회
    - 좋아요 개수
    - 현재 사용자가 좋아요 눌렀는지
    """
    
    # 비디오 존재 확인
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="동영상을 찾을 수 없습니다."
        )
    
    # 좋아요 개수
    like_count = db.query(func.count(Like.id)).filter(
        Like.video_id == video_id
    ).scalar()
    
    # 현재 사용자가 좋아요 눌렀는지
    user_identifier = get_user_identifier(request)
    is_liked = db.query(Like).filter(
        Like.video_id == video_id,
        Like.user_identifier == user_identifier
    ).first() is not None
    
    return {
        "video_id": video_id,
        "like_count": like_count or 0,
        "is_liked": is_liked
    }


@router.delete("/{video_id}/like")
async def unlike_video(
    video_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """좋아요 취소 (명시적)"""
    
    # 비디오 존재 확인
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="동영상을 찾을 수 없습니다."
        )
    
    # 사용자 식별자
    user_identifier = get_user_identifier(request)
    
    # 좋아요 찾기
    like = db.query(Like).filter(
        Like.video_id == video_id,
        Like.user_identifier == user_identifier
    ).first()
    
    if not like:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="좋아요를 누르지 않았습니다."
        )
    
    # 삭제
    db.delete(like)
    db.commit()
    
    # 현재 좋아요 개수
    like_count = db.query(func.count(Like.id)).filter(Like.video_id == video_id).scalar()
    
    return {
        "message": "좋아요 취소 완료",
        "like_count": like_count or 0,
        "is_liked": False
    }