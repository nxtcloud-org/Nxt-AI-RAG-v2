import { useState } from 'react';
import { KnowledgeBase, KBUploadRequest, IngestStatusResponse } from '../types';
import '../styles/DocumentUpload.css';

interface KBUploadProps {
  kbs: KnowledgeBase[];
  onUpload: (data: KBUploadRequest) => Promise<{ job_id: string; kb_id: string; ds_id: string }>;
  checkStatus: (kbId: string, dsId: string, jobId: string) => Promise<IngestStatusResponse>;
  isLoading: boolean;
}

export const KBUpload: React.FC<KBUploadProps> = ({
  kbs,
  onUpload,
  checkStatus,
  isLoading
}) => {
  const [selectedKBId, setSelectedKBId] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [ingestStatus, setIngestStatus] = useState<IngestStatusResponse['status'] | null>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  const selectedKB = kbs.find(kb => kb.kb_id === selectedKBId);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      setFile(selectedFile);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedKB || !file) {
      setMessage({ text: 'KB와 파일을 선택해주세요', type: 'error' });
      return;
    }

    try {
      setMessage({ text: 'S3 업로드 및 동기화 요청 중...', type: 'info' });
      const { job_id, kb_id, ds_id } = await onUpload({
        kb_id: selectedKB.kb_id,
        ds_id: selectedKB.ds_id,
        bucket: selectedKB.bucket,
        file
      });

      setIngestStatus('STARTING');
      pollStatus(kb_id, ds_id, job_id);
    } catch {
      setMessage({ text: '❌ 요청 실패', type: 'error' });
    }
  };

  const pollStatus = async (kbId: string, dsId: string, jobId: string) => {
    const interval = setInterval(async () => {
      try {
        const { status } = await checkStatus(kbId, dsId, jobId);
        setIngestStatus(status);
        
        if (status === 'COMPLETE') {
          setMessage({ text: '🎉 동기화 완료!', type: 'success' });
          clearInterval(interval);
          setFile(null);
        } else if (status === 'FAILED' || status === 'ERROR') {
          setMessage({ text: `❌ 동기화 실패: ${status}`, type: 'error' });
          clearInterval(interval);
        }
      } catch {
        setIngestStatus('ERROR');
        clearInterval(interval);
      }
    }, 3000);
  };

  return (
    <div className="document-upload">
      <h3>문서 업로드 및 동기화</h3>
      <form onSubmit={handleSubmit} className="upload-form">
        <div className="form-group">
          <label>대상 지식 기반 선택</label>
          <select 
            className="form-input" 
            value={selectedKBId} 
            onChange={(e) => setSelectedKBId(e.target.value)}
            disabled={isLoading || ingestStatus === 'IN_PROGRESS'}
          >
            <option value="">KB를 선택하세요</option>
            {kbs.map(kb => (
              <option key={kb.kb_id} value={kb.kb_id}>{kb.name}</option>
            ))}
          </select>
        </div>

        {selectedKB && (
          <div className="kb-info-box">
            <p><strong>Bucket:</strong> {selectedKB.bucket}</p>
            <p><strong>DS ID:</strong> {selectedKB.ds_id}</p>
          </div>
        )}

        <div
          className={`file-drop-zone ${file ? 'has-file' : ''}`}
          onClick={() => !isLoading && document.getElementById('file-input-kb')?.click()}
        >
          <input
            type="file"
            accept=".pdf"
            onChange={handleFileChange}
            disabled={isLoading || (ingestStatus !== null && ingestStatus !== 'COMPLETE' && ingestStatus !== 'FAILED' && ingestStatus !== 'ERROR')}
            id="file-input-kb"
            hidden
          />
          <span className="drop-zone-icon">{file ? '✅' : '📄'}</span>
          <span className="drop-zone-text">
            {file ? file.name : 'PDF 파일을 선택하세요'}
          </span>
        </div>

        {ingestStatus && (
          <div className="status-indicator">
            <span className={`status-badge status-${ingestStatus.toLowerCase()}`}>
              상태: {ingestStatus}
            </span>
          </div>
        )}

        <button type="submit" disabled={isLoading || !file || !selectedKBId || (ingestStatus !== null && ingestStatus !== 'COMPLETE' && ingestStatus !== 'FAILED' && ingestStatus !== 'ERROR')} className="btn-upload">
          {isLoading ? (
            <span className="btn-loading-content">
              <span className="spinner-small"></span>
              처리 중...
            </span>
          ) : (
            '업로드 및 데이터 동기화'
          )}
        </button>

        {message && (
          <div className={`upload-message ${message.type}`}>
            {message.text}
          </div>
        )}
      </form>
    </div>
  );
};
