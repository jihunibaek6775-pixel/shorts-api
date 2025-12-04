FROM python:3.12-slim

WORKDIR /app

# PostgreSQL 클라이언트와 curl 설치
# - postgresql-client: DB 연결용
# - curl: healthcheck용
RUN apt-get update && apt-get install -y \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 앱 코드 복사
COPY . .

# S3 사용으로 로컬 업로드 폴더는 선택사항이지만 개발/테스트용으로 유지
RUN mkdir -p uploads/videos

# 포트 노출
EXPOSE 8000

# 서버 실행 (python -m 추가로 모듈 경로 문제 해결)
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]