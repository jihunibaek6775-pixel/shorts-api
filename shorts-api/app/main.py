from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import videos , likes , comments
from .database import Base, engine , init_db
from . import models
import os
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# 데이터베이스 테이블 생성


# FastAPI 앱 생성
app = FastAPI(
    title="Shorts API",
    description="유튜브 숏폼 클론 - 동영상 업로드/재생",
    version="0.2.0"
)

@app.on_event("startup")
def startup_event():
    """서버가 시작될 때 단 한 번 실행되어 테이블을 생성합니다."""
    print("데이터베이스 테이블 초기화 시작...")
    # Base.metadata는 models.py 임포트로 이미 모든 테이블 정보를 갖고 있습니다.
    init_db(engine, Base.metadata)
    print("데이터베이스 초기화 완료.")

# CORS 설정 (프론트엔드 연동용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5174",
        "http://localhost:5173",
        "http://localhost:3000",
        "http://43.200.134.109:5173/",
        "https://www.artlion.p-e.kr",
        "https://artlion.p-e.kr",
    ],  # 개발 중에 필요한 origin들만 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(videos.router)
app.include_router(likes.router) 
app.include_router(comments.router)

# 루트 엔드포인트
@app.get("/")
async def root():
    return {
        "message": "Shorts API 서버",
        "version": "0.2.0",
        "endpoints": {
            "docs": "/docs",
            "upload": "/api/videos/upload",
            "list": "/api/videos/",
            "stream": "/api/videos/{id}/stream"
        }
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

