# Knowledge Base 시스템

AWS Bedrock을 활용한 지식 베이스 관리 및 챗봇 시스템입니다.

## 프로젝트 구조

```
7_KnowledgeBase/
├── admin/              # 관리자용 애플리케이션
│   ├── client/        # React 프론트엔드 (KB 관리 UI)
│   └── server/        # FastAPI 백엔드 (KB 관리 API)
├── user/              # 사용자용 애플리케이션
│   ├── client/        # React 프론트엔드 (챗봇 UI)
│   └── server/        # FastAPI 백엔드 (챗봇 API)
├── data/              # 샘플 문서 데이터
├── kbs.json           # Knowledge Base 설정 파일
└── requirements.txt   # Python 의존성 패키지
```

## 주요 기능

### 관리자 (Admin)
- Knowledge Base 등록 및 관리
- 문서 업로드 및 동기화
- Ingestion 상태 조회
- 문서 목록 조회
- 챗봇 테스트

### 사용자 (User)
- Knowledge Base 기반 챗봇 질의응답
- 채팅 히스토리 관리

## 기술 스택

### Backend
- **FastAPI**: RESTful API 서버
- **LangChain**: LLM 통합 및 RAG 파이프라인
- **AWS Bedrock**: LLM 서비스
- **AWS S3**: 문서 저장소
- **PostgreSQL**: 데이터베이스 (psycopg2-binary)

### Frontend
- **React 18**: UI 프레임워크
- **TypeScript**: 타입 안정성
- **Axios**: HTTP 클라이언트

## 설치 및 실행

### Backend 설정

1. Python 가상환경 생성 및 활성화
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

2. 의존성 설치
```bash
pip install -r requirements.txt
```

3. 환경 변수 설정
- AWS 자격 증명 설정 (AWS CLI 또는 환경 변수)
- 데이터베이스 연결 정보 설정

### Frontend 설정

1. 의존성 설치
```bash
cd admin/client  # 또는 user/client
npm install
```

2. 개발 서버 실행
```bash
npm start
```

### 서버 실행

**관리자 서버:**
```bash
cd admin/server
uvicorn main:app --reload --port 8001
```

**사용자 서버:**
```bash
cd user/server
uvicorn main:app --reload --port 8002
```

## API 엔드포인트

### 관리자 API (포트 8001)
- `GET /api/admin/kbs` - KB 목록 조회
- `POST /api/admin/kbs` - KB 등록
- `DELETE /api/admin/kbs/{kb_id}` - KB 삭제
- `POST /api/admin/upload-and-sync` - 문서 업로드 및 동기화
- `GET /api/admin/ingest-status/{kb_id}/{ds_id}/{job_id}` - Ingestion 상태 조회
- `GET /api/admin/documents/{ds_id}` - 문서 목록 조회
- `POST /api/chat` - 챗봇 질의응답
- `DELETE /api/chat-history/{session_id}` - 채팅 히스토리 삭제

### 사용자 API (포트 8002)
- `GET /api/admin/kbs` - KB 목록 조회
- `POST /api/chat` - 챗봇 질의응답
- `DELETE /api/chat-history/{session_id}` - 채팅 히스토리 삭제

## 설정 파일

### kbs.json
Knowledge Base 메타데이터를 저장하는 JSON 파일입니다.

```json
{
    "kbs": [
        {
            "name": "school",
            "kb_id": "UJD3EEXBQA",
            "ds_id": "IBKHPJTM0O",
            "bucket": "ella-rag-0-kb"
        }
    ]
}
```

## 데이터

`data/` 폴더에는 샘플 문서들이 포함되어 있습니다:
- `campus-facilities.md`, `campus-facilities.pdf`
- `club-guid.md`, `club-guid.pdf`
- `univ-data.pdf`
