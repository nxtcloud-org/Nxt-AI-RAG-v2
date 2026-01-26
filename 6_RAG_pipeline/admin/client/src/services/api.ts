import axios, { AxiosInstance } from 'axios';
import {
  Document,
  ChatRequest,
  ChatResponse,
  DocumentUploadRequest,
  DocumentUploadResponse,
  ApiResponse
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

    // FormData 자동 처리를 위한 인터셉터
    this.client.interceptors.request.use((config) => {
      if (config.data instanceof FormData) {
        config.headers['Content-Type'] = 'multipart/form-data';
      } else if (!config.headers['Content-Type']) {
        config.headers['Content-Type'] = 'application/json';
      }
      return config;
    });
  }

  async getDocuments(): Promise<Document[]> {
    try {
      const response = await this.client.get<ApiResponse<any>>('/documents');
      const data = response.data.data?.documents;
      return Array.isArray(data) ? data : [];
    } catch (error) {
      console.error('Error fetching documents:', error);
      throw error;
    }
  }

  async chat(request: ChatRequest): Promise<ChatResponse> {
    try {
      const response = await this.client.post<ChatResponse>('/chat', request);
      return response.data;
    } catch (error) {
      console.error('Error sending chat message:', error);
      throw error;
    }
  }

  async clearChatHistory(sessionId: string): Promise<void> {
    try {
      await this.client.delete(`/chat-history/${sessionId}`);
    } catch (error) {
      console.error('Error clearing chat history:', error);
      throw error;
    }
  }

  async getAdminDocuments(): Promise<Document[]> {
    try {
      const response = await this.client.get<ApiResponse<any>>('/admin/documents');
      const data = response.data.data?.documents;
      return Array.isArray(data) ? data : [];
    } catch (error) {
      console.error('Error fetching admin documents:', error);
      throw error;
    }
  }

  async uploadDocument(data: DocumentUploadRequest): Promise<DocumentUploadResponse> {
    try {
      const formData = new FormData();
      formData.append('file', data.file);

      const response = await axios.post<DocumentUploadResponse>(
        `${API_BASE_URL}/admin/documents`,
        formData
      );
      return response.data;
    } catch (error) {
      console.error('Error uploading document:', error);
      throw error;
    }
  }

  async deleteDocument(docId: number): Promise<ApiResponse<null>> {
    try {
      const response = await this.client.delete<ApiResponse<null>>(
        `/admin/documents/${docId}`
      );
      return response.data;
    } catch (error) {
      console.error('Error deleting document:', error);
      throw error;
    }
  }

}

export const apiClient = new ApiClient();
