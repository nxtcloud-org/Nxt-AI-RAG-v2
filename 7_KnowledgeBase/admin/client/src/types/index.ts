export interface KnowledgeBase {
  readonly name: string;
  readonly kb_id: string;
  readonly ds_id: string;
  readonly bucket: string;
  readonly prefix: string;
}

export interface KBRegistrationRequest {
  name: string;
  kb_id: string;
  ds_id: string;
  bucket: string;
  prefix?: string;
}

export interface KBUploadRequest {
  kb_id: string;
  ds_id: string;
  bucket: string;
  file: File;
}

export interface KBUploadResponse {
  job_id: string;
  kb_id: string;
  ds_id: string;
}

export interface IngestStatusResponse {
  status: 'STARTING' | 'IN_PROGRESS' | 'COMPLETE' | 'FAILED' | 'ERROR';
}

export type ApiStatus = 'success' | 'error';

export interface ApiResponse<T = unknown> {
  status: ApiStatus;
  data?: T;
  message?: string;
}

export interface ChatRequest {
  query: string;
  session_id: string;
  kb_ids?: string[];
}

export interface Source {
  content: string;
  page?: number;
  document_title?: string;
  score?: number;
  location?: Record<string, unknown>;
}

export interface ChatResponse {
  response: string;
  sources: Source[];
}
