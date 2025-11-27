# schemas.py

from pydantic import BaseModel
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