import { useState } from 'react';
import { KnowledgeBase } from '../types';
import '../styles/DocumentList.css';
import '../styles/Modal.css';

interface KBListProps {
  kbs: KnowledgeBase[];
  onDelete: (kbId: string) => Promise<void>;
  isLoading: boolean;
}

export const KBList: React.FC<KBListProps> = ({
  kbs,
  onDelete,
  isLoading
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

  const filteredKBs = kbs.filter((kb) => {
    return kb.name.toLowerCase().includes(searchTerm.toLowerCase()) || 
           kb.kb_id.toLowerCase().includes(searchTerm.toLowerCase());
  });

  // Data Source ID를 파싱하여 배열로 변환 (쉼표로 구분된 경우 처리)
  const parseDataSourceIds = (dsId: string): string[] => {
    if (!dsId) return [];
    return dsId.split(',').map(id => id.trim()).filter(id => id.length > 0);
  };

  const handleDeleteClick = (kbId: string) => {
    setDeleteConfirm(kbId);
  };

  const handleConfirmDelete = async (kbId: string) => {
    try {
      await onDelete(kbId);
      setMessage({ text: '삭제되었습니다', type: 'success' });
      setDeleteConfirm(null);
      setTimeout(() => setMessage(null), 2000);
    } catch {
      setMessage({ text: '삭제 실패', type: 'error' });
      setTimeout(() => setMessage(null), 2000);
    }
  };

  const handleCancelDelete = () => {
    setDeleteConfirm(null);
  };

  return (
    <div className="document-list">
      <div className="list-header">
        <h3>등록된 Knowledge Base 목록</h3>
        <div className="search-container">
          <span className="search-icon">🔍</span>
          <input
            type="text"
            placeholder="KB 이름 또는 ID로 검색..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
      </div>

      {filteredKBs.length === 0 ? (
        <div className="empty-state">
          <span className="empty-state-icon">📂</span>
          <p className="empty-state-text">등록된 Knowledge Base가 없습니다.</p>
        </div>
      ) : (
        <div className="table-container">
          <table className="modern-table">
            <thead>
              <tr>
                <th>KB 정보</th>
                <th>Data Source ID</th>
                <th>관리</th>
              </tr>
            </thead>
            <tbody>
              {filteredKBs.map((kb) => (
                <tr key={kb.kb_id}>
                  <td>
                    <div className="doc-info">
                      <span className="doc-name">{kb.name}</span>
                      <span className="doc-meta">ID: {kb.kb_id}</span>
                    </div>
                  </td>
                  <td>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', alignItems: 'flex-start' }}>
                      {parseDataSourceIds(kb.ds_id).map((dsId, idx) => (
                        <span 
                          key={idx} 
                          className="chunk-badge" 
                          style={{ 
                            display: 'inline-block', 
                            width: 'auto',
                            maxWidth: '100%',
                            whiteSpace: 'nowrap'
                          }}
                        >
                          {dsId}
                        </span>
                      ))}
                      {parseDataSourceIds(kb.ds_id).length === 0 && (
                        <span 
                          className="chunk-badge" 
                          style={{ 
                            color: '#999', 
                            display: 'inline-block', 
                            width: 'auto',
                            maxWidth: '100%',
                            whiteSpace: 'nowrap'
                          }}
                        >
                          {kb.ds_id || '-'}
                        </span>
                      )}
                    </div>
                  </td>
                  <td>
                    <div className="action-buttons">
                      <button
                        className="btn-icon btn-delete"
                        onClick={() => handleDeleteClick(kb.kb_id)}
                        disabled={isLoading}
                        title="삭제"
                      >
                        🗑️
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {message && (
        <div className={`notification ${message.type}`}>
          {message.text}
        </div>
      )}

      {deleteConfirm !== null && (
        <div className="modal-overlay">
          <div className="modal-card">
            <div className="modal-header">
              <h4>Knowledge Base 삭제</h4>
              <button onClick={handleCancelDelete} className="close-btn">&times;</button>
            </div>
            <div className="modal-body">
              <p>이 Knowledge Base 등록 정보를 삭제하시겠습니까?</p>
              <p className="text-warning text-sm">※ AWS 실제 리소스는 삭제되지 않으며, 등록 정보만 삭제됩니다.</p>
            </div>
            <div className="modal-footer">
              <button
                onClick={handleCancelDelete}
                className="btn-secondary"
                disabled={isLoading}
              >
                취소
              </button>
              <button
                onClick={() => handleConfirmDelete(deleteConfirm)}
                className="btn-danger"
                disabled={isLoading}
              >
                {isLoading ? (
                  <span className="btn-loading-content">
                    <span className="spinner-small"></span>
                    삭제 중...
                  </span>
                ) : (
                  '삭제하기'
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
