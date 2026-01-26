import os
import json
import boto3
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
from langchain_aws import ChatBedrock
from langchain_core.messages import HumanMessage
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory

app = FastAPI(
    title="Knowledge Base User API",
    description="Knowledge Base 조회 및 질의응답 API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def _get_kb_file_path():
    """KB 파일 경로를 안전하게 계산"""
    current_file = os.path.abspath(__file__)
    current_dir = os.path.dirname(current_file)
    parent_dir = os.path.dirname(current_dir)
    project_root = os.path.dirname(parent_dir)
    return os.path.join(project_root, 'kbs.json')

KB_FILE_PATH = _get_kb_file_path()

def _ensure_kb_file_exists():
    """KB 파일이 없으면 생성"""
    if not os.path.exists(KB_FILE_PATH):
        os.makedirs(os.path.dirname(KB_FILE_PATH), exist_ok=True)
        with open(KB_FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump({"kbs": []}, f, ensure_ascii=False, indent=4)

def load_kbs():
    """모든 KB 조회"""
    if os.path.exists(KB_FILE_PATH):
        try:
            with open(KB_FILE_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
                kbs = data.get("kbs", [])
                for kb in kbs:
                    for key in ['name', 'kb_id', 'ds_id', 'bucket', 'prefix']:
                        if key in kb and isinstance(kb[key], str):
                            kb[key] = kb[key].strip()
                return kbs
        except (json.JSONDecodeError, IOError):
            return []
    
    _ensure_kb_file_exists()
    return []

AWS_REGION = "us-east-1"

def get_bedrock_runtime_client():
    return boto3.client("bedrock-runtime", region_name=AWS_REGION)

def get_bedrock_agent_runtime_client():
    return boto3.client("bedrock-agent-runtime", region_name=AWS_REGION)

# Pydantic 모델
class ApiResponse(BaseModel):
    status: str
    message: str
    data: Optional[Dict] = None

class ChatRequest(BaseModel):
    query: str
    session_id: str
    kb_ids: Optional[List[str]] = None

class Source(BaseModel):
    content: str
    page: Optional[int] = None
    document_title: Optional[str] = None
    score: Optional[float] = None
    location: Optional[Dict] = None

class ChatResponse(BaseModel):
    response: str
    sources: List[Source]

# RAG 챗봇 클래스
class KBChatbot:
    def __init__(self):
        self.bedrock_runtime = get_bedrock_runtime_client()
        self.bedrock_agent_runtime = get_bedrock_agent_runtime_client()
        self.llm = ChatBedrock(
            client=self.bedrock_runtime,
            model="anthropic.claude-3-haiku-20240307-v1:0",
            model_kwargs={
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 4000,
                "temperature": 0.1
            }
        )
        self.chat_histories = {}

    def get_session_history(self, session_id):
        if session_id not in self.chat_histories:
            self.chat_histories[session_id] = InMemoryChatMessageHistory()
        return self.chat_histories[session_id]

    def retrieve_from_kb(self, query: str, kb_ids: List[str], k: int = 3) -> List[Dict]:
        """KB에서 검색 결과 가져오기"""
        all_results = []
        
        for kb_id in kb_ids:
            if not kb_id:
                continue
            
            try:
                response = self.bedrock_agent_runtime.retrieve(
                    knowledgeBaseId=kb_id,
                    retrievalConfiguration={
                        'vectorSearchConfiguration': {
                            'numberOfResults': k,
                            'overrideSearchType': 'SEMANTIC'
                        }
                    },
                    retrievalQuery={'text': query}
                )
                all_results.extend(response.get('retrievalResults', []))
            except Exception:
                continue
        
        return all_results

    def generate_response(self, query: str, kb_ids: List[str], session_id: str) -> tuple:
        """KB 검색 후 답변 생성"""
        retrieval_results = self.retrieve_from_kb(query, kb_ids)
        sources = []
        context_parts = []
        
        for result in retrieval_results:
            content_text = result.get('content', {}).get('text', '')
            if content_text:
                context_parts.append(content_text)
            
            metadata = result.get('metadata', {})
            page = metadata.get('page') if isinstance(metadata, dict) else None
            document_title = (metadata.get('filename') or metadata.get('title')) if isinstance(metadata, dict) else None
            
            sources.append(Source(
                content=content_text[:200] if content_text else "",
                page=page,
                document_title=document_title,
                score=result.get('score', 0.0),
                location=result.get('location', {})
            ))
        
        context = "\n\n".join(context_parts)
        conversation = RunnableWithMessageHistory(
            self.llm,
            self.get_session_history,
            max_history=3
        ).with_config(configurable={"session_id": session_id})
        
        prompt_content = f"""문서 내용을 바탕으로 질문에 답하세요.

질문: {query}

관련 문서 내용:
{context}

위 내용을 참고하여 질문에 대해 명확하고 친절하게 답변해주세요. 문서에 없는 내용은 언급하지 말고, 확실한 정보만 답변에 포함해주세요."""
        
        prompt = HumanMessage(content=prompt_content)
        response = conversation.invoke(
            [prompt],
            config={"configurable": {"session_id": session_id}}
        )
        
        response_text = response.content if isinstance(response.content, str) else str(response.content)
        return response_text, sources

kb_chatbot = KBChatbot()

# API 엔드포인트
@app.get("/api/admin/kbs", response_model=ApiResponse)
async def get_kbs():
    """KB 목록 조회"""
    kbs = load_kbs()
    return ApiResponse(
        status="success",
        message="KB 목록 조회 성공",
        data={"kbs": kbs}
    )

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """KB로 질문하여 답변 받기"""
    if not request.kb_ids or len(request.kb_ids) == 0:
        raise HTTPException(status_code=400, detail="KB를 선택해주세요.")
    
    response, sources = kb_chatbot.generate_response(
        request.query,
        request.kb_ids,
        request.session_id
    )
    
    return ChatResponse(
        response=response,
        sources=sources
    )

@app.delete("/api/chat-history/{session_id}")
async def clear_chat_history(session_id: str):
    """대화 기록 초기화"""
    if session_id in kb_chatbot.chat_histories:
        kb_chatbot.chat_histories[session_id].clear()
    return ApiResponse(
        status="success",
        message="대화 기록이 초기화되었습니다."
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
