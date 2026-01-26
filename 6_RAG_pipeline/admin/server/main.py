import os
import json
import uuid
import boto3
import psycopg2
import numpy as np
from fastapi import FastAPI, File, UploadFile, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, Dict
from pathlib import Path
from dotenv import load_dotenv
from langchain_aws import ChatBedrock, BedrockEmbeddings
from langchain_core.messages import HumanMessage
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory

env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

app = FastAPI(
    title="RAG Admin API",
    description="관리자용 문서 관리 및 RAG 챗봇 API",
    version="2.0.1"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 공통 유틸리티 함수
def get_db_connection():
    """데이터베이스 연결 생성"""
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST'),
        database=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD')
    )
    conn.autocommit = True
    return conn

def get_s3_client():
    """S3 클라이언트 생성"""
    return boto3.client('s3', region_name=os.getenv('AWS_REGION', 'us-east-1'))

def get_bedrock_client():
    """Bedrock 클라이언트 생성"""
    return boto3.client("bedrock-runtime", region_name="us-east-1")

# 임베딩 및 유사도 검색 함수
def get_embedding(text, bedrock_client=None):
    """텍스트 임베딩 생성"""
    if not bedrock_client:
        bedrock_client = get_bedrock_client()
    
    embeddings = BedrockEmbeddings(
        client=bedrock_client,
        model_id="amazon.titan-embed-text-v1"
    )
    return embeddings.embed_query(text)

def find_similar_chunks(query_embedding, k=3):
    """유사도 기반 문서 검색"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT content, metadata,
                   embedding as doc_embedding
            FROM documents
            ORDER BY embedding <=> %s::vector
            LIMIT %s;
        """, (query_embedding, k))
        
        results = cursor.fetchall()
        
        def calculate_cosine_similarity(qe, e):
            qe_array = np.array(qe, dtype=float)
            e_array = np.array(e, dtype=float)
            return np.dot(qe_array, e_array) / (np.linalg.norm(qe_array) * np.linalg.norm(e_array))
        
        return [(row[0], row[1], calculate_cosine_similarity(query_embedding, row[2])) for row in results]
    finally:
        cursor.close()
        conn.close()

# Pydantic 모델
class ApiResponse(BaseModel):
    status: str
    message: str
    data: Optional[Dict] = None

class ChatRequest(BaseModel):
    query: str
    session_id: Optional[str] = "default"

class DocumentUploadResponse(BaseModel):
    s3_key: str
    document_id: Optional[int] = None

# RAG 챗봇 엔드포인트
class RAGChatbot:
    def __init__(self):
        self.bedrock_client = get_bedrock_client()
        self.llm = ChatBedrock(
            client=self.bedrock_client,
            model="anthropic.claude-3-haiku-20240307-v1:0",
            model_kwargs={
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 4000,
                "temperature": 0.1
            },
            streaming=True
        )
        self.chat_histories = {}

    def get_session_history(self, session_id):
        if session_id not in self.chat_histories:
            self.chat_histories[session_id] = InMemoryChatMessageHistory()
        return self.chat_histories[session_id]

    def generate_response(self, query: str, session_id: Optional[str] = None):
        session_id = session_id or "default"
        
        conversation = RunnableWithMessageHistory(
            self.llm,
            self.get_session_history,
            max_history=3
        ).with_config(configurable={"session_id": session_id})

        query_embedding = get_embedding(query, self.bedrock_client)
        similar_chunks = find_similar_chunks(query_embedding)
        context = "\n\n".join([chunk[0] for chunk in similar_chunks])

        prompt = HumanMessage(content=f"""이전 대화 기록과 문서 내용을 참고하여 답변해주세요.
        
        질문: {query}
        
        관련 문서 내용:
        {context}
        
        위 내용과 이전 대화 맥락을 바탕으로 질문에 대해 명확하고 친절하게 답변해주세요. 
        문서에 없는 내용은 언급하지 말고, 확실한 정보만 답변에 포함해주세요.""")

        response = conversation.invoke([prompt], config={"configurable": {"session_id": session_id}})
        return response.content, similar_chunks

rag_chatbot = RAGChatbot()

# 엔드포인트 정의
@app.post("/api/chat", response_model=ApiResponse)
async def chat_endpoint(request: ChatRequest):
    try:
        response, chunks = rag_chatbot.generate_response(request.query, request.session_id)
        return ApiResponse(
            status="success", 
            message="답변 생성 완료", 
            data={
                "response": response, 
                "references": [{"content": chunk[0], "metadata": chunk[1]} for chunk in chunks]
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            query = data.get('query', '')
            session_id = data.get('session_id', 'default')
            
            try:
                response, chunks = rag_chatbot.generate_response(query, session_id)
                await websocket.send_json({
                    "status": "success",
                    "response": response,
                    "references": [{"content": chunk[0], "metadata": chunk[1]} for chunk in chunks]
                })
            except Exception as e:
                await websocket.send_json({
                    "status": "error",
                    "message": str(e)
                })
    except WebSocketDisconnect:
        print("WebSocket disconnected")

@app.get("/api/admin/documents")
async def get_admin_documents():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                metadata->>'filename' as filename,
                metadata->>'s3_key' as s3_key,
                metadata->>'document_file_id' as document_file_id,
                COUNT(*) as chunk_count,
                MAX(created_at) as latest_created_at
            FROM documents
            WHERE metadata->>'filename' IS NOT NULL
            GROUP BY metadata->>'filename', metadata->>'s3_key', metadata->>'document_file_id'
            ORDER BY latest_created_at DESC
        """)
        
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        
        documents = []
        for row in rows:
            try:
                filename, s3_key, document_file_id, chunk_count, created_at = row
                doc_id = None
                if document_file_id:
                    try:
                        doc_id = int(document_file_id)
                    except (ValueError, TypeError):
                        doc_id = None
                doc = {
                    "id": doc_id,
                    "title": filename or "Untitled",
                    "s3_key": s3_key,
                    "chunk_count": int(chunk_count) if chunk_count else 0,
                    "created_at": created_at.isoformat() if created_at else None
                }
                documents.append(doc)
            except (ValueError, AttributeError, TypeError) as row_error:
                print(f"Warning: Error processing row {row}: {row_error}")
                continue
        
        return {
            "status": "success",
            "message": "Admin documents retrieved successfully",
            "data": {"documents": documents}
        }
    except Exception as e:
        import traceback
        print(f"Error in get_admin_documents: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/admin/documents", response_model=DocumentUploadResponse)
async def upload_document(file: UploadFile = File(...)):
    try:
        s3_client = get_s3_client()
        bucket_name = os.getenv('BUCKET_NAME')
        
        if not bucket_name:
            raise ValueError("BUCKET_NAME environment variable is not set")
        
        file_content = await file.read()
        file_key = f"documents/{uuid.uuid4()}_{file.filename}"
        
        s3_client.put_object(
            Bucket=bucket_name,
            Key=file_key,
            Body=file_content,
            ContentType="application/pdf"
        )
        
        return DocumentUploadResponse(
            s3_key=file_key
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 문서 삭제
@app.delete("/api/admin/documents/{doc_id}", response_model=ApiResponse)
async def delete_document(doc_id: int):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            DELETE FROM documents 
            WHERE metadata->>'document_file_id' = %s
        """, (str(doc_id),))
        
        deleted_count = cursor.rowcount
        cursor.close()
        conn.close()
        
        return ApiResponse(
            status="success",
            message=f"Document and {deleted_count} chunks deleted successfully",
            data={"deleted_chunks": deleted_count}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 정적 파일 서빙 (기존과 동일)
build_dir = os.path.join(os.path.dirname(__file__), "../client/build")
if os.path.exists(build_dir):
    app.mount("/", StaticFiles(directory=build_dir, html=True), name="static")

# 메인 실행
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)