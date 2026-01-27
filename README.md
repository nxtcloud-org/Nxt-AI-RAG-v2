# Nxt-AI-RAG

Nxtcloud Technical Training Team의 RAG(Retrieval-Augmented Generation) 실습 교육용 레포지토리입니다.

## 개요

이 레포지토리는 AWS Bedrock 기반 RAG 시스템 구축을 단계별로 학습할 수 있도록 구성되어 있습니다. 기본적인 챗봇 구현부터 프로덕션 수준의 RAG 파이프라인까지 점진적으로 학습합니다.

## 커리큘럼

| 폴더 | 주제 | 설명 |
|------|------|------|
| `1_simple_chatbot` | 기본 챗봇 | AWS Bedrock + Streamlit 기반 간단한 챗봇 구현 |
| `2_context` | 대화 컨텍스트 | LangChain Memory를 활용한 대화 맥락 유지 (Buffer, Window, Summary) |
| `3_embeddings` | 벡터 임베딩 | Amazon Titan Embeddings를 활용한 텍스트 임베딩 이해 |
| `4_chunk_splite` | 문서 분할 | PDF 문서 로딩 및 청크 분할 전략 |
| `5_RAG` | 기본 RAG | ChromaDB를 활용한 로컬 RAG 시스템 구현 |
| `6_RAG_pipeline` | 프로덕션 RAG | PostgreSQL + pgvector 기반 Admin/User 분리 아키텍처 |
| `7_KnowledgeBase` | AWS Knowledge Bases | AWS 관리형 RAG 서비스 활용 |
| `8_evaluation` | RAG 평가 | RAGAS를 활용한 RAG 성능 평가 및 비교 분석 |

## 기술 스택

- **LLM**: AWS Bedrock (Claude 3 Haiku)
- **Embeddings**: Amazon Titan Embeddings
- **Vector DB**: ChromaDB (로컬), PostgreSQL + pgvector (프로덕션)
- **Framework**: LangChain, FastAPI, Streamlit
- **Frontend**: React + TypeScript
- **Infrastructure**: AWS Lambda, S3, Knowledge Bases
- **Evaluation**: RAGAS

## 사전 요구사항

- Python 3.10+
- Node.js 18+ (프론트엔드 실습 시)
- AWS 계정 및 Bedrock 모델 접근 권한
- AWS CLI 설정 완료

## 시작하기

```bash
# 레포지토리 클론
git clone https://github.com/nxtcloud-org/Nxt-AI-RAG-v2.git
cd Nxt-AI-RAG-v2

# 각 폴더별로 의존성 설치 후 실습 진행
cd 1_simple_chatbot
pip install -r requirements.txt
streamlit run simple_chatbot.py
```

## 폴더 구조

```
Nxt-AI-RAG-v2/
├── 1_simple_chatbot/       # 기본 챗봇
├── 2_context/              # 대화 컨텍스트 관리
├── 3_embeddings/           # 벡터 임베딩
├── 4_chunk_splite/         # 문서 분할
├── 5_RAG/                  # 기본 RAG (ChromaDB)
├── 6_RAG_pipeline/         # 프로덕션 RAG
│   ├── admin/              # 관리자 (문서 업로드/관리)
│   │   ├── client/         # React 프론트엔드
│   │   └── server/         # FastAPI 백엔드
│   ├── user/               # 사용자 (질의응답)
│   │   ├── client/
│   │   └── server/
│   └── lambda/             # 문서 처리 Lambda
├── 7_KnowledgeBase/        # AWS Knowledge Bases
│   └── user/
│       ├── client/
│       └── server/
└── 8_evaluation/           # RAG 평가
```

## 라이선스

이 레포지토리는 Nxtcloud Technical Training Team의 교육 목적으로 제작되었습니다.
