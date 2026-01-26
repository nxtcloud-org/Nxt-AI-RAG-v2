import { useState, useEffect } from 'react';
import { Document, DocumentUploadRequest } from '../types';
import { DocumentUpload } from '../components/DocumentUpload';
import { DocumentList } from '../components/DocumentList';
import { apiClient } from '../services/api';
import '../styles/AdminPage.css';

export const AdminPage: React.FC = () => {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    loadDocuments();
  }, []);

  const loadDocuments = async (silent = false) => {
    try {
      if (!silent) setIsLoading(true);
      const docs = await apiClient.getAdminDocuments();
      setDocuments(docs);
    } catch (error) {
      console.error('Failed to load documents:', error);
      setDocuments([]);
    } finally {
      if (!silent) setIsLoading(false);
    }
  };

  const handleUpload = async (data: DocumentUploadRequest) => {
    try {
      setIsLoading(true);
      const response = await apiClient.uploadDocument(data);
      if (response.status === 'success') {
        // 사용자 요청에 따른 10초 인위적 딜레이 (업로드 처리 및 인덱싱 대기 연출)
        await new Promise(resolve => setTimeout(resolve, 10000));
        await loadDocuments(true); // 이미 isLoading이 true이므로 silent 모드로 호출
      }
    } catch (error) {
      console.error('Failed to upload document:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDelete = async (docId: number) => {
    try {
      setIsLoading(true);
      // 사용자 요청에 따른 5초 인위적 딜레이 (자연스러운 로딩 연출)
      await new Promise(resolve => setTimeout(resolve, 5000));
      const response = await apiClient.deleteDocument(docId);
      if (response.status === 'success') {
        await loadDocuments(true); // 이미 isLoading이 true이므로 silent 모드로 호출
      }
    } catch (error) {
      console.error('Failed to delete document:', error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="admin-page">
      <header className="page-header">
        <h1>문서 관리 시스템</h1>
        <p>RAG 모델을 위한 지식 베이스를 관리하세요.</p>
      </header>

      <div className="stats-grid">
        <div className="stat-card">
          <span className="stat-label">전체 문서</span>
          <span className="stat-value">{documents.length}</span>
        </div>
        <div className="stat-card">
          <span className="stat-label">총 청크 수</span>
          <span className="stat-value">
            {documents.reduce((acc, doc) => acc + doc.chunk_count, 0)}
          </span>
        </div>
        <div className="stat-card">
          <span className="stat-label">최근 업데이트</span>
          <span className="stat-value">
            {documents.length > 0 
              ? new Date(Math.max(...documents.map(d => new Date(d.created_at || 0).getTime()))).toLocaleDateString('ko-KR')
              : '-'}
          </span>
        </div>
      </div>

      <div className="admin-grid">
        <div className="upload-container">
          <DocumentUpload onUpload={handleUpload} isLoading={isLoading} />
        </div>
        <div className="list-container">
          <DocumentList
            documents={documents}
            onDelete={handleDelete}
            isLoading={isLoading}
          />
        </div>
      </div>
    </div>
  );
};
