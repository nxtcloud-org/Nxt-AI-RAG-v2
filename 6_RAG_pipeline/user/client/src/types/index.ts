// 문서 타입 정의
export interface Document {
  id: number;
  title: string;
  chunk_count: number;
  created_at?: string;
}

// 채팅 메시지 타입
export interface Message {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  sources?: Source[];
}

// 참고 문서 출처
export interface Source {
  content: string;
  page: number;
  document_id?: number;
  document_title?: string;
}

// 채팅 요청/응답
export interface ChatRequest {
  query: string;
  session_id: string;
}

export interface ChatResponse {
  response: string;
  sources: Source[];
}



// API 응답 래퍼
export interface ApiResponse<T> {
  status: 'success' | 'error';
  data?: T;
  message?: string;
}

// 세션 정보
export interface Session {
  id: string;
  created_at: Date;
  last_activity: Date;
}
