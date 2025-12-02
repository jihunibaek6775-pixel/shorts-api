# schemas.py
from typing import List
from pydantic import BaseModel , Field
from datetime import datetime
from typing import Optional

class VideoBase(BaseModel):
    filename: str
    original_filename: str
    file_path: str
    file_size: int
    content_type: str
    uploaded_at: datetime
    # 💡 updated_at 컬럼 추가 (Optional)
    updated_at: Optional[datetime] = None
    
# DB에서 읽어올 때 사용하는 스키마
class Video(VideoBase):
    id: int
    uploaded_at: datetime
    
    class Config:
        # ORM 모드 활성화: SQLAlchemy 모델 객체를 Pydantic 모델로 변환 가능하게 함
        from_attributes = True

# 비디오 정보 수정을 위한 스키마
class VideoUpdate(BaseModel):
    original_filename: Optional[str] = None
    
    class Config:
        from_attributes = True

class VideoResponse(VideoBase):
    """동영상 응답 (좋아요 개수 포함)"""
    id: int
    uploaded_at: datetime
    updated_at: Optional[datetime] = None
    like_count: int = 0  # ← 추가
    
    class Config:
        from_attributes = True

class LikeResponse(BaseModel):
    """좋아요 응답"""
    id: int
    video_id: int
    user_identifier: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class LikeStatus(BaseModel):
    """좋아요 상태 응답"""
    video_id: int
    like_count: int
    is_liked: bool


class CommentCreate(BaseModel):
    # content만 사용자가 입력하며, 나머지 정보(video_id, user_identifier, created_at)는
    # 서버에서 처리되므로 스키마에 포함하지 않습니다.
    content: str = Field(..., min_length=1, max_length=1000) 
    
    # 추가: Pydantic 모델 설정
    class Config:
        # 이 모델은 ORM 객체와 호환되게 설정합니다.
        from_attributes = True

class CommentResponse(CommentCreate):
    # CommentCreate를 상속받아 content 필드를 포함합니다.

    id: int # 댓글 고유 ID
    video_id: int 
    user_identifier: str # 작성자 식별자 (실제 사용자 이름으로 대체될 수도 있음)
    created_at: datetime # 댓글 작성 시각
    
    # 예시: 만약 사용자 이름 정보를 포함해야 한다면, 여기에 추가 필드를 넣을 수 있습니다.
    # author_username: str 
    
    class Config:
        from_attributes = True

class CommentUpdate(BaseModel):
    # 수정이 가능하도록 content만 정의
    content: str = Field(..., min_length=1, max_length=1000)
    
    class Config:
        from_attributes = True

class CommentListResponse(BaseModel):
    total: int
    comments: List[CommentResponse]

    class Config:
        from_attributes = True