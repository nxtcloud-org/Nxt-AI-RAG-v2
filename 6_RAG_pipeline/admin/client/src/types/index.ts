export type DocumentStatus = 'pending' | 'processed' | 'error';

export type MessageType = 'user' | 'assistant';

export interface Document {
  readonly id: number;
  readonly title: string;
  readonly s3_key: string;
  readonly chunk_count: number;
  readonly created_at?: string;
  readonly status?: DocumentStatus;
  readonly queryable_topics?: string[];
  readonly example_questions?: string[];
}

export interface Source {
  content: string;
  page: number;
  document_id?: number;
  document_title?: string;
}

export interface Message {
  id: string;
  type: MessageType;
  content: string;
  timestamp: Date;
  sources?: Source[];
}

export interface Session {
  readonly id: string;
  readonly created_at: Date;
  readonly last_activity: Date;
}

export interface ChatRequest {
  query: string;
  session_id: string;
}

export interface ChatResponse {
  response: string;
  sources: Source[];
}

export interface DocumentUploadRequest {
  file: File;
  title: string;
  description?: string;
  category?: string;
  queryable_topics?: string[];
  example_questions?: string[];
}

export interface DocumentUploadResponse {
  status: 'success' | 'error';
  document_id?: number;
  message: string;
}

export type ApiStatus = 'success' | 'error';

export interface ApiResponse<T = unknown> {
  status: ApiStatus;
  data?: T;
  message?: string;
}
