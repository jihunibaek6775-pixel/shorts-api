# Shorts API - 동영상 플랫폼 백엔드

FastAPI 기반의 유튜브 숏폼 클론 프로젝트 백엔드 API 서버입니다.

## 기술 스택

### 프레임워크 & 언어
- Python 3.12
- FastAPI 0.104.1
- Uvicorn (ASGI 서버)

### 데이터베이스
- PostgreSQL 15
- SQLAlchemy 2.0.23 (ORM)
- Alembic 1.13.0 (마이그레이션)

### 파일 저장소
- AWS S3 (동영상 파일 저장)
- boto3 1.34.0

### 인프라
- Docker & Docker Compose
- Nginx Proxy Manager (리버스 프록시 & SSL)
- GitHub Actions (CI/CD)

## 주요 기능

### 1. 동영상 관리
- **업로드**: 동영상 파일을 S3에 업로드하고 메타데이터를 DB에 저장
- **조회**: 동영상 목록 및 상세 정보 조회
- **스트리밍**: Range Request를 지원하는 동영상 스트리밍
- **다운로드**: 원본 파일명으로 동영상 다운로드
- **수정**: 동영상 파일 및 메타데이터 수정
- **삭제**: 동영상 및 관련 데이터 삭제 (좋아요, 댓글 포함)
- **검색**: 동영상 제목으로 검색

### 2. 좋아요 기능
- 좋아요 토글 (추가/취소)
- 좋아요 상태 조회 (개수 및 사용자 좋아요 여부)
- 좋아요 취소

### 3. 댓글 기능
- 댓글 작성
- 댓글 목록 조회 (페이지네이션)
- 댓글 수정
- 댓글 삭제

## API 엔드포인트

### Videos
```
GET    /api/videos/              - 동영상 목록 조회
GET    /api/videos/search        - 동영상 검색
GET    /api/videos/{id}          - 동영상 상세 조회
GET    /api/videos/{id}/stream   - 동영상 스트리밍
GET    /api/videos/{id}/download - 동영상 다운로드
POST   /api/videos/upload        - 동영상 업로드
PUT    /api/videos/{id}          - 동영상 수정
DELETE /api/videos/{id}          - 동영상 삭제
```

### Likes
```
POST   /api/videos/{id}/like     - 좋아요 토글
GET    /api/videos/{id}/like     - 좋아요 상태 조회
DELETE /api/videos/{id}/like     - 좋아요 취소
```

### Comments
```
GET    /api/videos/{id}/comments             - 댓글 목록 조회
POST   /api/videos/{id}/comments             - 댓글 작성
PATCH  /api/videos/{id}/comments/{comment_id} - 댓글 수정
DELETE /api/videos/{id}/comments/{comment_id} - 댓글 삭제
```

## 데이터베이스 스키마

### Videos
```python
- id: Integer (PK)
- filename: String (고유 파일명)
- original_filename: String (원본 파일명)
- file_path: String (S3 URL)
- file_size: BigInteger
- content_type: String
- uploaded_at: DateTime
- updated_at: DateTime
```

### Likes
```python
- id: Integer (PK)
- video_id: Integer (FK -> videos.id)
- user_identifier: String (사용자 IP, 추후 user_id로 변경 예정)
- created_at: DateTime
```

### Comments
```python
- id: Integer (PK)
- video_id: Integer (FK -> videos.id)
- user_identifier: String (사용자 ID)
- content: Text
- created_at: DateTime
- updated_at: DateTime
```

## 환경 변수 설정

`.env` 파일을 생성하고 다음 환경 변수를 설정하세요:

```bash
# PostgreSQL 설정
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
POSTGRES_DB=shortsapi
DATABASE_URL=postgresql://postgres:your_password@db:5432/shortsapi

# AWS S3 설정
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=ap-northeast-2
AWS_BUCKET_NAME=your_bucket_name
```

## 로컬 개발 환경 설정

### 1. Python 가상 환경 설정
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. 환경 변수 설정
```bash
cp .env.example .env
# .env 파일 편집하여 필요한 값 입력
```

### 3. 서버 실행
```bash
uvicorn app.main:app --reload
```

API 문서: http://localhost:8000/docs

## Docker를 사용한 배포

### 1. Docker Compose로 실행
```bash
docker-compose up -d
```

이 명령어는 다음 서비스들을 시작합니다:
- PostgreSQL 데이터베이스 (포트 5432)
- FastAPI 서버 (포트 8000)
- Nginx Proxy Manager (포트 80, 443, 81)

### 2. 로그 확인
```bash
docker-compose logs -f api
```

### 3. 서비스 중지
```bash
docker-compose down
```

## 배포 (GitHub Actions)

`main` 브랜치에 푸시하면 GitHub Actions가 자동으로 EC2 서버에 배포합니다.

필요한 GitHub Secrets:
- `EC2_HOST`: EC2 인스턴스 IP 주소
- `EC2_USER`: SSH 사용자명 (예: ubuntu)
- `EC2_SSH_KEY`: SSH 프라이빗 키

## 프로젝트 구조

```
shorts-api/
├── app/
│   ├── __init__.py
│   ├── main.py           # FastAPI 앱 진입점
│   ├── database.py       # DB 연결 설정
│   ├── models.py         # SQLAlchemy 모델
│   ├── schemas.py        # Pydantic 스키마
│   ├── s3_client.py      # S3 클라이언트
│   └── routers/
│       ├── videos.py     # 동영상 라우터
│       ├── likes.py      # 좋아요 라우터
│       └── comments.py   # 댓글 라우터
├── uploads/              # 로컬 임시 저장소 (개발용)
├── .github/
│   └── workflows/
│       └── deploy.yml    # CI/CD 설정
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

## 주요 특징

### 1. Range Request 지원
동영상 스트리밍 시 Range Request를 지원하여 부분 다운로드 및 시크(seek) 기능을 제공합니다.

### 2. S3 스토리지
동영상 파일은 AWS S3에 저장되어 확장성과 안정성을 보장합니다.

### 3. 관계형 데이터 관리
SQLAlchemy의 관계(relationship)와 캐스케이드 삭제를 통해 데이터 무결성을 유지합니다.

### 4. CORS 설정
프론트엔드와의 연동을 위한 CORS 설정이 적용되어 있습니다.

### 5. 헬스 체크
Docker 컨테이너의 상태를 모니터링하기 위한 헬스 체크 엔드포인트(`/health`)를 제공합니다.

## API 문서

서버 실행 후 다음 URL에서 자동 생성된 API 문서를 확인할 수 있습니다:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 라이센스

이 프로젝트는 MIT 라이센스를 따릅니다.

## 배포 주소

- API: https://artlion.p-e.kr
- API 문서: https://artlion.p-e.kr/docs
