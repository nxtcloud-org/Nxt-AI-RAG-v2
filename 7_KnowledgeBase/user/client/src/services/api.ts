import axios, { AxiosInstance } from 'axios';
import {
  KnowledgeBase,
  ChatRequest,
  ChatResponse,
  ApiResponse
} from '../types';

const getBaseUrl = () => {
  const apiUrl = process.env.REACT_APP_API_URL;
  if (apiUrl && apiUrl.trim() !== '') {
    const trimmedUrl = apiUrl.trim();
    if (trimmedUrl.includes('/api')) {
      return trimmedUrl.endsWith('/') ? trimmedUrl.slice(0, -1) : trimmedUrl;
    }
    const baseUrl = trimmedUrl.endsWith('/') ? trimmedUrl.slice(0, -1) : trimmedUrl;
    return `${baseUrl}/api`;
  }
  
  if (typeof window !== 'undefined') {
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
      baseURL: API_BASE_URL,
      timeout: 30000
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

  async chat(request: ChatRequest): Promise<ChatResponse> {
    const response = await this.client.post<ChatResponse>('/chat', request);
    return response.data;
  }

  async clearChatHistory(sessionId: string): Promise<void> {
    await this.client.delete(`/chat-history/${sessionId}`);
  }
}

export const apiClient = new ApiClient();
