import os
import json
import boto3
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
from langchain_aws import ChatBedrock
from langchain_core.messages import HumanMessage
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory

app = FastAPI(
    title="Knowledge Base Admin API",
    description="Knowledge Base 관리를 위한 관리자용 API",
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

# KB 관리 함수
def _ensure_kb_file_exists():
    """KB 파일이 없으면 생성 (기존 파일이 있으면 절대 덮어쓰지 않음)"""
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

def save_kb(name, kb_id, ds_id, bucket, prefix=""):
    """새 KB 등록"""
    kbs = load_kbs()
    if any(kb['kb_id'] == kb_id for kb in kbs):
        return False, "이미 존재하는 Knowledge Base ID입니다."
    
    new_kb = {
        "name": name.strip(),
        "kb_id": kb_id.strip(),
        "ds_id": ds_id.strip(),
        "bucket": bucket.strip(),
        "prefix": prefix.strip() if prefix else ""
    }
    kbs.append(new_kb)
    
    with open(KB_FILE_PATH, 'w', encoding='utf-8') as f:
        json.dump({"kbs": kbs}, f, ensure_ascii=False, indent=4)
    return True, "성공적으로 등록되었습니다."

def delete_kb(kb_id):
    """KB 삭제"""
    kbs = load_kbs()
    new_kbs = [kb for kb in kbs if kb['kb_id'] != kb_id]
    
    if len(kbs) == len(new_kbs):
        return False, "해당 ID를 찾을 수 없습니다."
        
    with open(KB_FILE_PATH, 'w', encoding='utf-8') as f:
        json.dump({"kbs": new_kbs}, f, ensure_ascii=False, indent=4)
    return True, "삭제되었습니다."

# AWS 클라이언트 설정
AWS_REGION = "us-east-1"

def get_s3_client():
    return boto3.client('s3', region_name=AWS_REGION)

def get_bedrock_agent_client():
    return boto3.client('bedrock-agent', region_name=AWS_REGION)

def get_bedrock_runtime_client():
    return boto3.client("bedrock-runtime", region_name=AWS_REGION)

def get_bedrock_agent_runtime_client():
    return boto3.client("bedrock-agent-runtime", region_name=AWS_REGION)

# Pydantic 모델
class ApiResponse(BaseModel):
    status: str
    message: str
    data: Optional[Dict] = None

class KBRegistrationRequest(BaseModel):
    name: str
    kb_id: str
    ds_id: str
    bucket: str
    prefix: Optional[str] = ""

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
        # KB에서 검색
        retrieval_results = self.retrieve_from_kb(query, kb_ids)
        
        # 검색 결과를 Source로 변환
        sources = []
        context_parts = []
        
        for result in retrieval_results:
            content_text = result.get('content', {}).get('text', '')
            if content_text:
                context_parts.append(content_text)
            
            # Source 정보 추출
            location = result.get('location', {})
            score = result.get('score', 0.0)
            
            # 메타데이터에서 페이지 정보 추출
            metadata = result.get('metadata', {})
            page = None
            document_title = None
            
            if isinstance(metadata, dict):
                page = metadata.get('page')
                document_title = metadata.get('filename') or metadata.get('title')
            
            sources.append(Source(
                content=content_text[:200] if content_text else "",
                page=page,
                document_title=document_title,
                score=score,
                location=location
            ))
        
        # 컨텍스트 구성
        context = "\n\n".join(context_parts)
        
        # 대화 기록 관리
        conversation = RunnableWithMessageHistory(
            self.llm,
            self.get_session_history,
            max_history=3
        ).with_config(configurable={"session_id": session_id})
        
        # 프롬프트 구성
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
    try:
        kbs = load_kbs()
        return ApiResponse(
            status="success",
            message="KB 목록 조회 성공",
            data={"kbs": kbs}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/admin/kbs", response_model=ApiResponse)
async def register_kb(request: KBRegistrationRequest):
    """KB 등록"""
    try:
        success, msg = save_kb(
            request.name, 
            request.kb_id, 
            request.ds_id, 
            request.bucket, 
            request.prefix
        )
        if success:
            return ApiResponse(status="success", message=msg)
        else:
            return ApiResponse(status="error", message=msg)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/admin/kbs/{kb_id}", response_model=ApiResponse)
async def delete_kb_endpoint(kb_id: str):
    """KB 삭제"""
    try:
        success, msg = delete_kb(kb_id)
        if success:
            return ApiResponse(status="success", message=msg)
        else:
            return ApiResponse(status="error", message=msg)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/admin/upload-and-sync", response_model=ApiResponse)
async def upload_and_sync(
    kb_id: str = Form(...),
    ds_id: str = Form(...),
    bucket: str = Form(...),
    file: UploadFile = File(...)
):
    """파일 업로드 및 동기화"""
    try:
        s3 = get_s3_client()
        agent_client = get_bedrock_agent_client()
        
        # 1. S3 업로드
        file_content = await file.read()
        target_key = file.filename
        
        s3.put_object(
            Bucket=bucket,
            Key=target_key,
            Body=file_content,
            ContentType="application/pdf"
        )
        
        # 2. Ingestion Job 시작
        response = agent_client.start_ingestion_job(
            knowledgeBaseId=kb_id, 
            dataSourceId=ds_id
        )
        job_id = response['ingestionJob']['ingestionJobId']
        
        return ApiResponse(
            status="success",
            message="파일 업로드 및 동기화 시작됨",
            data={
                "job_id": job_id,
                "kb_id": kb_id,
                "ds_id": ds_id
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/admin/ingest-status/{kb_id}/{ds_id}/{job_id}", response_model=ApiResponse)
async def check_status(kb_id: str, ds_id: str, job_id: str):
    """Ingestion 상태 조회"""
    try:
        client = get_bedrock_agent_client()
        response = client.get_ingestion_job(
            knowledgeBaseId=kb_id, 
            dataSourceId=ds_id, 
            ingestionJobId=job_id
        )
        status = response['ingestionJob']['status']
        return ApiResponse(
            status="success",
            message="상태 조회 성공",
            data={"status": status}
        )
    except Exception as e:
        return ApiResponse(status="error", message=str(e), data={"status": "ERROR"})

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """KB로 질문하여 답변 받기"""
    try:
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
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/chat-history/{session_id}")
async def clear_chat_history(session_id: str):
    """대화 기록 초기화"""
    try:
        if session_id in kb_chatbot.chat_histories:
            kb_chatbot.chat_histories[session_id].clear()
        return ApiResponse(
            status="success",
            message="대화 기록이 초기화되었습니다."
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/admin/documents/{ds_id}", response_model=ApiResponse)
async def get_documents_by_ds_id(ds_id: str):
    """Data Source ID로 문서 목록 조회"""
    try:
        kbs = load_kbs()
        kb_info = next((kb for kb in kbs if kb.get('ds_id') == ds_id), None)
        
        if not kb_info:
            return ApiResponse(
                status="error",
                message="해당 Data Source ID를 찾을 수 없습니다.",
                data={"documents": []}
            )
        
        kb_id = kb_info.get('kb_id')
        agent_client = get_bedrock_agent_client()
        documents = []
        document_identifiers = set()
        has_jobs = False
        has_in_progress = False
        total_jobs = 0
        completed_jobs = 0
        
        try:
            ingestion_jobs_response = agent_client.list_ingestion_jobs(
                knowledgeBaseId=kb_id,
                dataSourceId=ds_id,
                maxResults=100
            )
            
            ingestion_jobs = ingestion_jobs_response.get('ingestionJobs', [])
            total_jobs = len(ingestion_jobs)
            has_jobs = total_jobs > 0
            
            for ingestion_job in ingestion_jobs:
                ingestion_status = ingestion_job.get('status')
                ingestion_job_id = ingestion_job.get('ingestionJobId', '')
                
                if ingestion_status in ('IN_PROGRESS', 'STARTING'):
                    has_in_progress = True
                
                if ingestion_status == 'COMPLETE':
                    completed_jobs += 1
                    try:
                        job_detail = agent_client.get_ingestion_job(
                            knowledgeBaseId=kb_id,
                            dataSourceId=ds_id,
                            ingestionJobId=ingestion_job_id
                        )
                        
                        job_data = job_detail.get('ingestionJob', {})
                        statistics = job_data.get('statistics', {})
                        num_documents = statistics.get('numberOfDocumentsScanned', 0)
                        
                        if num_documents > 0:
                            identifier = f"Job-{ingestion_job_id[:8]}"
                            if identifier not in document_identifiers:
                                document_identifiers.add(identifier)
                                documents.append({
                                    "identifier": identifier,
                                    "job_id": ingestion_job_id,
                                    "status": ingestion_status,
                                    "documents_scanned": num_documents,
                                    "documents_modified": statistics.get('numberOfModifiedDocuments', 0),
                                    "documents_failed": statistics.get('numberOfFailedDocuments', 0),
                                    "started_at": job_data.get('startedAt', ''),
                                    "updated_at": job_data.get('updatedAt', '')
                                })
                    except Exception:
                        statistics = ingestion_job.get('statistics', {})
                        num_documents = statistics.get('numberOfDocumentsScanned', 0)
                        if num_documents > 0:
                            identifier = f"Job-{ingestion_job_id[:8] if ingestion_job_id else 'unknown'}"
                            if identifier not in document_identifiers:
                                document_identifiers.add(identifier)
                                documents.append({
                                    "identifier": identifier,
                                    "job_id": ingestion_job_id,
                                    "status": ingestion_status,
                                    "documents_scanned": num_documents
                                })
            
        except Exception as agent_error:
            return ApiResponse(
                status="error",
                message=f"문서 목록 조회 중 오류가 발생했습니다: {str(agent_error)}",
                data={
                    "documents": [],
                    "has_jobs": False,
                    "has_in_progress": False,
                    "total_jobs": 0,
                    "completed_jobs": 0,
                    "error": str(agent_error)
                }
            )
        
        return ApiResponse(
            status="success",
            message="문서 목록 조회 성공",
            data={
                "documents": documents,
                "has_jobs": has_jobs,
                "has_in_progress": has_in_progress,
                "total_jobs": total_jobs,
                "completed_jobs": completed_jobs
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
