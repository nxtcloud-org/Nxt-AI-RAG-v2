import { useState, useEffect } from 'react';
import { KnowledgeBase, KBRegistrationRequest, KBUploadRequest } from '../types';
import { KBRegistration } from '../components/KBRegistration';
import { KBList } from '../components/KBList';
import { KBUpload } from '../components/KBUpload';
import { apiClient } from '../services/api';
import '../styles/AdminPage.css';

export const AdminPage: React.FC = () => {
  const [kbs, setKbs] = useState<KnowledgeBase[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<'list' | 'register' | 'upload'>('list');

  useEffect(() => {
    loadKBs();
  }, []);

  const loadKBs = async (silent = false) => {
    try {
      if (!silent) setIsLoading(true);
      const data = await apiClient.getKBs();
      setKbs(data);
    } catch (error) {
      console.error('Failed to load KBs:', error);
      setKbs([]);
    } finally {
      if (!silent) setIsLoading(false);
    }
  };

  const handleRegister = async (data: KBRegistrationRequest) => {
    try {
      setIsLoading(true);
      const response = await apiClient.registerKB(data);
      if (response.status === 'success') {
        await loadKBs(true);
      } else {
        throw new Error(response.message);
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleDelete = async (kbId: string) => {
    try {
      setIsLoading(true);
      const response = await apiClient.deleteKB(kbId);
      if (response.status === 'success') {
        await loadKBs(true);
      } else {
        throw new Error(response.message);
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleUpload = async (data: KBUploadRequest) => {
    const response = await apiClient.uploadAndSync(data);
    if (response.status === 'success' && response.data) {
      return response.data;
    }
    throw new Error(response.message || '업로드 실패');
  };

  const checkIngestStatus = async (kbId: string, dsId: string, jobId: string) => {
    return await apiClient.getIngestStatus(kbId, dsId, jobId);
  };

  return (
    <div className="admin-page">
      <header className="page-header">
        <h1>Knowledge Base 관리</h1>
        <p>AWS Bedrock 지식 기반을 등록하고 문서를 동기화하세요.</p>
      </header>

      <div className="stats-grid">
        <div className="stat-card">
          <span className="stat-label">등록된 KB</span>
          <span className="stat-value">{kbs.length}</span>
        </div>
        <div className="stat-card">
          <span className="stat-label">활성 리전</span>
          <span className="stat-value">us-east-1</span>
        </div>
        <div className="stat-card">
          <span className="stat-label">시스템 상태</span>
          <span className="stat-value">정상</span>
        </div>
      </div>

      <div className="admin-tabs">
        <button 
          className={`tab-btn ${activeTab === 'list' ? 'active' : ''}`}
          onClick={() => setActiveTab('list')}
        >
          KB 목록
        </button>
        <button 
          className={`tab-btn ${activeTab === 'register' ? 'active' : ''}`}
          onClick={() => setActiveTab('register')}
        >
          KB 등록
        </button>
        <button 
          className={`tab-btn ${activeTab === 'upload' ? 'active' : ''}`}
          onClick={() => setActiveTab('upload')}
        >
          문서 업로드
        </button>
      </div>

      <div className="tab-content">
        {activeTab === 'list' && (
          <div className="list-container full-width">
            <KBList
              kbs={kbs}
              onDelete={handleDelete}
              isLoading={isLoading}
            />
          </div>
        )}
        
        {activeTab === 'register' && (
          <div className="upload-container centered">
            <KBRegistration
              onRegister={handleRegister}
              isLoading={isLoading}
            />
          </div>
        )}

        {activeTab === 'upload' && (
          <div className="upload-container centered">
            <KBUpload
              kbs={kbs}
              onUpload={handleUpload}
              checkStatus={checkIngestStatus}
              isLoading={isLoading}
            />
          </div>
        )}
      </div>
    </div>
  );
};
