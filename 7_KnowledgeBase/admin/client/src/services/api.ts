import axios, { AxiosInstance } from 'axios';
import {
  KnowledgeBase,
  KBRegistrationRequest,
  KBUploadRequest,
  KBUploadResponse,
  IngestStatusResponse,
  ApiResponse,
  ChatRequest,
  ChatResponse
} from '../types';

const getBaseUrl = () => {
  // 환경 변수에서 API URL 가져오기
  const apiUrl = process.env.REACT_APP_API_URL;
  if (apiUrl) {
    // 이미 /api가 포함되어 있으면 그대로 사용, 없으면 추가
    return apiUrl.includes('/api') ? apiUrl : `${apiUrl.replace(/\/$/, '')}/api`;
  }
  
  if (typeof window !== 'undefined') {
    // 8001(admin) 또는 8002(user) 포트에서 실행 중이면 해당 origin 사용
    // npm start(3000) 등에서 실행 중이면 proxy 설정을 타도록 상대 경로만 반환
    if (window.location.port === '8001' || window.location.port === '8002') {
      return `${window.location.origin}/api`;
    }
  }
  return '/api';
};

const API_BASE_URL = getBaseUrl();

class ApiClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL
    });

    this.client.interceptors.request.use((config) => {
      if (config.data instanceof FormData) {
        config.headers['Content-Type'] = 'multipart/form-data';
      } else if (!config.headers['Content-Type']) {
        config.headers['Content-Type'] = 'application/json';
      }
      return config;
    });
  }

  async getKBs(): Promise<KnowledgeBase[]> {
    const response = await this.client.get<ApiResponse<any>>('/admin/kbs');
    const data = response.data.data?.kbs;
    return Array.isArray(data) ? data : [];
  }

  async registerKB(data: KBRegistrationRequest): Promise<ApiResponse<null>> {
    const response = await this.client.post<ApiResponse<null>>('/admin/kbs', data);
    return response.data;
  }

  async deleteKB(kbId: string): Promise<ApiResponse<null>> {
    const response = await this.client.delete<ApiResponse<null>>(`/admin/kbs/${kbId}`);
    return response.data;
  }

  async uploadAndSync(data: KBUploadRequest): Promise<ApiResponse<KBUploadResponse>> {
    const formData = new FormData();
    formData.append('kb_id', data.kb_id);
    formData.append('ds_id', data.ds_id);
    formData.append('bucket', data.bucket);
    formData.append('file', data.file);

    const response = await this.client.post<ApiResponse<KBUploadResponse>>(
      '/admin/upload-and-sync',
      formData
    );
    return response.data;
  }

  async getIngestStatus(kbId: string, dsId: string, jobId: string): Promise<IngestStatusResponse> {
    const response = await this.client.get<ApiResponse<IngestStatusResponse>>(
      `/admin/ingest-status/${kbId}/${dsId}/${jobId}`
    );
    return response.data.data || { status: 'ERROR' };
  }

  async getDocumentsByDsId(dsId: string): Promise<any> {
    try {
      const response = await this.client.get<ApiResponse<any>>(`/admin/documents/${dsId}`);
      return response.data.data || { documents: [] };
    } catch (error) {
      return { documents: [], error: String(error) };
    }
  }

  async chat(request: ChatRequest): Promise<ChatResponse> {
    const response = await this.client.post<ChatResponse>('/chat', request);
    return response.data;
  }

  async clearChatHistory(sessionId: string): Promise<void> {
    await this.client.delete(`/chat-history/${sessionId}`);
  }
}

export const apiClient = new ApiClient();
