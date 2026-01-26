import os
import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional
import boto3
import psycopg2
from pathlib import Path
from dotenv import load_dotenv

# 환경 설정
# 경로: /user/server/main.py -> /user -> / (6_RAG_pipeline_v2)
env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

# FastAPI 애플리케이션 생성
app = FastAPI(
    title="RAG User API",
    description="사용자용 질의응답 API",
    version="2.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================
# Pydantic 모델
# ============================================

class ChatRequest(BaseModel):
    """채팅 요청 모델"""
    query: str
    session_id: str


class Source(BaseModel):
    """참고 문서 출처 모델"""
    content: str
    page: int
    document_title: Optional[str] = None


class ChatResponse(BaseModel):
    """채팅 응답 모델"""
    response: str
    sources: List[Source]


class ApiResponse(BaseModel):
    """API 응답 래퍼 모델"""
    status: str
    message: str
    data: Optional[dict] = None


# ============================================
# 데이터베이스 연결
# ============================================

def get_db_connection():
    """PostgreSQL 데이터베이스 연결"""
    return psycopg2.connect(
        host=os.getenv('DB_HOST'),
        database=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD')
    )


# ============================================
# API 엔드포인트
# ============================================

@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    return {"status": "ok", "message": "User API is running"}


@app.get("/api/documents", response_model=ApiResponse)
async def get_documents():
    """
    문서 목록 조회
    
    Returns:
        ApiResponse: 문서 목록이 포함된 응답
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        conn.autocommit = True
        cursor = conn.cursor()
        
        # 데이터베이스에서 문서 목록 조회
        cursor.execute("""
            SELECT DISTINCT 
                metadata->>'filename' as filename,
                metadata->>'document_file_id' as document_file_id,
                COUNT(*) as chunk_count,
                MAX(created_at) as latest_created_at
            FROM documents
            GROUP BY metadata->>'filename', metadata->>'document_file_id'
            ORDER BY MAX(created_at) DESC
        """)
        rows = cursor.fetchall()
        
        # 결과를 문서 객체로 변환
        documents = []
        for r in rows:
            try:
                doc_id = int(r[1]) if r[1] and str(r[1]).strip() else None
            except (ValueError, TypeError):
                doc_id = None
            
            documents.append({
                "id": doc_id,
                "title": r[0] or "Untitled",
                "chunk_count": r[2],
                "created_at": r[3].isoformat() if r[3] else None
            })
        
        return ApiResponse(
            status="success",
            message="Documents retrieved",
            data={"documents": documents}
        )
    
    except Exception as e:
        import traceback
        error_msg = f"{str(e)}\n{traceback.format_exc()}"
        print(f"Error in get_documents: {error_msg}")
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    사용자 질문에 대한 답변 반환
    
    1. 질문을 임베딩으로 변환
    2. 유사한 문서 검색
    3. LLM을 통해 답변 생성
    
    Args:
        request: ChatRequest (query, session_id)
        
    Returns:
        ChatResponse: 답변 및 참고 문서
    """
    conn = None
    cursor = None
    try:
        from langchain_aws import ChatBedrock, BedrockEmbeddings
        from langchain_core.messages import HumanMessage
        
        # AWS Bedrock 클라이언트 초기화
        bedrock_client = boto3.client(
            "bedrock-runtime",
            region_name="us-east-1"
        )
        
        # ============================================
        # 1단계: 질문 임베딩 생성
        # ============================================
        embeddings = BedrockEmbeddings(
            client=bedrock_client,
            model_id="amazon.titan-embed-text-v1"
        )
        query_embedding = embeddings.embed_query(request.query)
        embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"
        
        # ============================================
        # 2단계: 유사한 문서 검색 (상위 3개)
        # ============================================
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT content, metadata FROM documents
            ORDER BY embedding <=> %s::vector LIMIT 3
        """, (embedding_str,))
        
        results = cursor.fetchall()
        
        # ============================================
        # 3단계: 참고 문서 처리
        # ============================================
        context_text = "\n".join([r[0] or "" for r in results])
        sources = []
        
        for r in results:
            content, metadata = r
            
            # 메타데이터 파싱
            if metadata:
                try:
                    meta_dict = json.loads(metadata) if isinstance(metadata, str) else metadata
                    page = meta_dict.get("page", 0)
                    doc_title = meta_dict.get("filename", meta_dict.get("title", "Unknown"))
                except (json.JSONDecodeError, AttributeError, TypeError):
                    page = 0
                    doc_title = "Unknown"
            else:
                page = 0
                doc_title = "Unknown"
            
            # Source 객체 생성
            sources.append(Source(
                content=(content or "")[:200],
                page=page,
                document_title=doc_title
            ))
        
        # ============================================
        # 4단계: LLM을 통해 답변 생성
        # ============================================
        llm = ChatBedrock(
            client=bedrock_client,
            model_id="anthropic.claude-3-haiku-20240307-v1:0",
            model_kwargs={
                "max_tokens": 2000,
                "temperature": 0.1
            }
        )
        
        # 프롬프트 구성
        prompt = f"문서 내용:\n{context_text}\n\n질문: {request.query}\n\n답변:"
        
        # LLM 호출
        response = llm.invoke([HumanMessage(content=prompt)])
        response_text = response.content if isinstance(response.content, str) else str(response.content)
        
        return ChatResponse(response=response_text, sources=sources)
    
    except Exception as e:
        import traceback
        error_msg = f"{str(e)}\n{traceback.format_exc()}"
        print(f"Error in chat: {error_msg}")
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@app.delete("/api/chat-history/{session_id}")
async def clear_history(session_id: str):
    """
    채팅 기록 초기화 (현재는 클라이언트 측에서 처리)
    
    Args:
        session_id: 세션 ID
        
    Returns:
        dict: 성공 응답
    """
    return {"status": "success"}


# ============================================
# 정적 파일 마운트
# ============================================

# 클라이언트 빌드 디렉토리가 있으면 마운트
build_dir = os.path.join(os.path.dirname(__file__), "../client/build")
if os.path.exists(build_dir):
    app.mount("/", StaticFiles(directory=build_dir, html=True), name="static")


# ============================================
# 메인
# ============================================

if __name__ == "__main__":
    import uvicorn
    host = os.getenv("SERVER_HOST", "0.0.0.0")
    port = int(os.getenv("SERVER_PORT", "8002"))
    uvicorn.run(app, host=host, port=port)
