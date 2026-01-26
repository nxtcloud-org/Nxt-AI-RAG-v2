# RAG Pipeline v2

AI 문서 검색 및 챗봇 시스템 (Retrieval-Augmented Generation)

## 📋 프로젝트 구조

```
6_RAG_pipeline_v2/
├── admin/                    # 관리자 시스템
│   ├── server/              # 문서 관리 API (FastAPI)
│   │   ├── main.py          # 관리자 API 엔드포인트
│   │   ├── lambda/          # AWS Lambda 함수
│   │   └── db/              # 데이터베이스 관리
│   └── client/              # 관리 페이지 (React/TypeScript)
│
├── user/                     # 사용자 시스템
│   ├── server/              # Q&A API (FastAPI)
│   │   └── main.py          # 질의응답 엔드포인트
│   └── client/              # 사용자 페이지 (React/TypeScript)
│
├── requirements.txt          # Python 의존성
└── .env.example              # 환경 변수 템플릿
```

## 🛠 기술 스택

**Backend**
- FastAPI (API 서버)
- PostgreSQL (데이터 저장)
- AWS S3 (문서 저장)
- AWS Bedrock (LLM, 임베딩)
- LangChain (RAG 구현)

**Frontend**
- React + TypeScript
- Node.js

## 🚀 빠른 시작

### 환경 설정

```bash
# Python 가상환경 생성
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# 환경 변수 설정
cp .env.example .env
# .env 파일에 다음 항목 입력:
# - DB_HOST, DB_NAME, DB_USER, DB_PASSWORD (PostgreSQL)
# - BUCKET_NAME (AWS S3)
```

### 서버 실행

```bash
# 관리자 API (포트 8000)
cd admin/server
uvicorn main:app --reload --port 8000

# 사용자 API (포트 8001)
cd user/server
uvicorn main:app --reload --port 8001
```

### 클라이언트 실행

```bash
# 관리자 페이지
cd admin/client
npm install
npm start

# 사용자 페이지
cd user/client
npm install
npm start
```

## 📚 주요 기능

### 관리자 API
- 문서 업로드 및 관리
- 벡터 DB 관리
- 챗봇 설정
- WebSocket 기반 실시간 스트리밍

### 사용자 API
- RAG 기반 질의응답
- 참고 문서 출처 제공
- 대화 세션 관리
- 스트리밍 응답 지원

## 🔧 API 엔드포인트

### 관리자 API (`/admin/server`)
- `POST /upload` - 문서 업로드
- `GET /documents` - 문서 목록 조회
- `DELETE /documents/{id}` - 문서 삭제

### 사용자 API (`/user/server`)
- `POST /chat` - 질문 및 답변
- `GET /chat/{session_id}` - 대화 이력 조회

## 📝 환경 변수

```
DB_HOST=          # PostgreSQL 호스트
DB_NAME=          # 데이터베이스 이름
DB_USER=          # DB 사용자명
DB_PASSWORD=      # DB 비밀번호
BUCKET_NAME=      # AWS S3 버킷명
```

## 📄 라이선스

MIT
