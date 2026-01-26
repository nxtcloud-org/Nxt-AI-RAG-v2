export interface KnowledgeBase {
  readonly name: string;
  readonly kb_id: string;
  readonly ds_id: string;
  readonly bucket: string;
  readonly prefix: string;
}

export interface Message {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  sources?: Source[];
}

export interface Source {
  content: string;
  page?: number;
  document_title?: string;
  score?: number;
  location?: {
    s3Location?: {
      uri?: string;
    };
  };
}

export interface ChatRequest {
  query: string;
  session_id: string;
  kb_ids?: string[];
}

export interface ChatResponse {
  response: string;
  sources: Source[];
}

export interface ApiResponse<T> {
  status: 'success' | 'error';
  data?: T;
  message?: string;
}
