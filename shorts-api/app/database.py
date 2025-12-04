# # database.py

# from sqlalchemy import create_engine,func
# from sqlalchemy.ext.declarative import declarative_base
# from sqlalchemy.orm import sessionmaker
# from pathlib import Path

# # SQLite 파일 경로 설정
# BASE_DIR = Path(__file__).parent
# SQLITE_FILE = BASE_DIR / "video_metadata.db"

# # 데이터베이스 연결 엔진 생성
# # check_same_thread=False는 FastAPI와 같은 비동기 환경에서 필요
# engine = create_engine(
#     f"sqlite:///{SQLITE_FILE}", 
#     connect_args={"check_same_thread": False}
# )

# # 세션 생성기
# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# # 기본 클래스
# Base = declarative_base()

# # 📝 비디오 메타데이터를 위한 SQLAlchemy 모델

# # 테이블 생성 (파일이 존재하지 않을 경우)
# def create_db_tables():
#     Base.metadata.create_all(bind=engine)

# def init_db(engine, metadata):
#     metadata.create_all(bind=engine)

# # DB 세션을 얻기 위한 의존성 주입 함수 (FastAPI에서 사용)
# def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()

# # 처음 한 번 테이블 생성 호출

# database.py

from sqlalchemy import create_engine, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# PostgreSQL 연결 URL
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/video_platform")

# 데이터베이스 연결 엔진 생성
# PostgreSQL에서는 check_same_thread 옵션 불필요
engine = create_engine(
    DATABASE_URL,
    echo=True,  # 쿼리 로그 보고 싶으면 True, 운영 환경에서는 False
    pool_pre_ping=True  # 연결 끊김 자동 재연결
)

# 세션 생성기
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 기본 클래스
Base = declarative_base()

# 테이블 생성
def create_db_tables():
    Base.metadata.create_all(bind=engine)

def init_db(engine, metadata):
    metadata.create_all(bind=engine)

# DB 세션을 얻기 위한 의존성 주입 함수 (FastAPI에서 사용)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()