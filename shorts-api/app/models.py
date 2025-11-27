from sqlalchemy import Column, Integer, String, BigInteger, DateTime
from .database import Base
from datetime import datetime

class Video(Base):
    __tablename__ = "videos"
    
    # DB에서 사용할 고유 ID (Primary Key)
    id = Column(Integer, primary_key=True, index=True)
    
    # 업로드 시 생성된 고유 파일명 (실제 저장된 파일 이름)
    filename = Column(String, unique=True, index=True, nullable=False)
    
    # 사용자가 업로드한 원본 파일 이름
    original_filename = Column(String, nullable=False)
    
    # 실제 파일 시스템에서의 경로
    file_path = Column(String, nullable=False)
    
    # 파일 크기 (바이트)
    file_size = Column(BigInteger, nullable=False)
    
    # MIME 타입 (예: video/mp4)
    content_type = Column(String)
    
    # 업로드 시각
    uploaded_at = Column(DateTime, default=datetime.now)
