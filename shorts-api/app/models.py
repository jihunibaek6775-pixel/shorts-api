# #models.py
# from sqlalchemy import Column, Integer, String, BigInteger, DateTime , ForeignKey, Boolean , Text
# from sqlalchemy.orm import relationship
# from sqlalchemy.sql import func
# from .database import Base
# from datetime import datetime

# class Video(Base):
#     __tablename__ = "videos"
    
#     # DB에서 사용할 고유 ID (Primary Key)
#     id = Column(Integer, primary_key=True, index=True)
    
#     # 업로드 시 생성된 고유 파일명 (실제 저장된 파일 이름)
#     filename = Column(String, unique=True, index=True, nullable=False)
    
#     # 사용자가 업로드한 원본 파일 이름
#     original_filename = Column(String, nullable=False)
    
#     # 실제 파일 시스템에서의 경로
#     file_path = Column(String, nullable=False)
    
#     # 파일 크기 (바이트)
#     file_size = Column(BigInteger, nullable=False)
    
#     # MIME 타입 (예: video/mp4)
#     content_type = Column(String)
    
#     # 업로드 시각
#     uploaded_at = Column(DateTime, default=datetime.now)

#     # 수정 시각
#     updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
#     likes = relationship("Like", back_populates="video", cascade="all, delete-orphan")
#     comments = relationship("Comments", back_populates="video", cascade="all, delete-orphan")

# class Like(Base):
#     __tablename__ = "likes"
    
#     id = Column(Integer, primary_key=True, index=True)
#     video_id = Column(Integer, ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, index=True)
#     user_identifier = Column(String, nullable=False, index=True)  # IP 주소 (임시)
#     created_at = Column(DateTime, default=datetime.now)
    
#     # 관계
#     video = relationship("Video", back_populates="likes")


# class Comments(Base):
#     __tablename__ = "comments"

#     id = Column(Integer, primary_key=True, index=True)
#     video_id = Column(Integer, ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, index=True)
#     user_identifier = Column(String, nullable=False, index=True)
#     content = Column(Text, nullable=False)
#     created_at = Column(DateTime, default=datetime.now)
#     updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

#     video = relationship("Video", back_populates="comments")

# models.py
from sqlalchemy import Column, Integer, String, BigInteger, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base
from datetime import datetime

class Video(Base):
    __tablename__ = "videos"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), unique=True, index=True, nullable=False)  # 길이 명시
    original_filename = Column(String(500), nullable=False)  # 길이 명시
    file_path = Column(String(1000), nullable=False)  # 길이 명시 (S3 URL용)
    file_size = Column(BigInteger, nullable=False)
    content_type = Column(String(100))  # 길이 명시
    
    # PostgreSQL에서는 func.now() 권장
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    likes = relationship("Like", back_populates="video", cascade="all, delete-orphan")
    comments = relationship("Comments", back_populates="video", cascade="all, delete-orphan")


class Like(Base):
    __tablename__ = "likes"
    
    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(Integer, ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, index=True)
    user_identifier = Column(String(100), nullable=False, index=True)  # 길이 명시
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    video = relationship("Video", back_populates="likes")


class Comments(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(Integer, ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, index=True)
    user_identifier = Column(String(100), nullable=False, index=True)  # 길이 명시
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    video = relationship("Video", back_populates="comments")