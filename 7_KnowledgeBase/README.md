# Knowledge Base 시스템

AWS Bedrock을 활용한 지식 베이스 관리 및 챗봇 시스템입니다.

## 프로젝트 구조

```
7_KnowledgeBase/
├── server/            # FastAPI 백엔드 (KB 관리 + 챗봇 API)
├── client/            # React 프론트엔드 (KB 관리 + 챗봇 UI)
├── data/              # 샘플 문서 데이터
├── kbs.json           # Knowledge Base 설정 파일
└── requirements.txt   # Python 의존성 패키지
```

## 주요 기능

### KB 관리
- Knowledge Base 등록 및 삭제
- 문서 업로드 및 S3 동기화
- Ingestion 상태 조회
- 문서 목록 조회

### 챗봇
- Knowledge Base 기반 RAG 질의응답
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

4. 서버 실행
```bash
cd server
uvicorn main:app --reload --port 8000
```

### Client 설정

1. 의존성 설치
```bash
cd client
npm install
```

2. 개발 서버 실행
```bash
npm start
```

### 실행 포트

| 서비스 | 포트 |
|--------|------|
| Server (FastAPI) | 8000 |
| Client (React Dev) | 3000 |

## API 엔드포인트 (포트 8000)

### KB 관리
- `GET /api/admin/kbs` - KB 목록 조회
- `POST /api/admin/kbs` - KB 등록
- `DELETE /api/admin/kbs/{kb_id}` - KB 삭제
- `POST /api/admin/upload-and-sync` - 문서 업로드 및 동기화
- `GET /api/admin/ingest-status/{kb_id}/{ds_id}/{job_id}` - Ingestion 상태 조회
- `GET /api/admin/documents/{ds_id}` - 문서 목록 조회

### 챗봇
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

`data/` 폴더에는 샘플 문서 세트가 두 벌 들어 있습니다. 교육 대상에 맞는 세트를 골라 S3에 업로드합니다.

### `data/academic/` — 학사 데이터 (학생 대상)

- `univ-data.pdf` — 학사 행정 정보 (휴학·복학·졸업 등)
- `club-guid.md`, `club-guid.pdf` — 동아리 회칙 및 가이드
- `campus-facilities.md`, `campus-facilities.pdf` — 캠퍼스 시설 및 학생 서비스

### `data/admin/` — 대학행정 데이터 (교직원 대상)

- `univ-admin-manual.md`, `univ-admin-manual.pdf` — 대학행정 업무 편람 (규정)
- `portal-manual.md`, `portal-manual.pdf` — 업무포털 사용 매뉴얼 (절차)
- `annual-calendar.md`, `annual-calendar.pdf` — 연간 행정 업무 일정 (시점)

두 세트 모두 **같은 주제를 서로 다른 층위로 다루는 문서 3종**으로 구성되어 있어, 질문에 따라 어느 문서에서 답을 가져오는지(출처 추적)를 확인할 수 있습니다.
