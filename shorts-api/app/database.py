# database.py

from sqlalchemy import create_engine,func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from pathlib import Path

# SQLite 파일 경로 설정
BASE_DIR = Path(__file__).parent
SQLITE_FILE = BASE_DIR / "video_metadata.db"

# 데이터베이스 연결 엔진 생성
# check_same_thread=False는 FastAPI와 같은 비동기 환경에서 필요
engine = create_engine(
    f"sqlite:///{SQLITE_FILE}", 
    connect_args={"check_same_thread": False}
)

# 세션 생성기
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 기본 클래스
Base = declarative_base()

# 📝 비디오 메타데이터를 위한 SQLAlchemy 모델

# 테이블 생성 (파일이 존재하지 않을 경우)
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

# 처음 한 번 테이블 생성 호출
