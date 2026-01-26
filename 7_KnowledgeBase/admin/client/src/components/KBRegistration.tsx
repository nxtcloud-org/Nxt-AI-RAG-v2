import { useState } from 'react';
import { KBRegistrationRequest } from '../types';
import '../styles/DocumentUpload.css';

interface KBRegistrationProps {
  onRegister: (data: KBRegistrationRequest) => Promise<void>;
  isLoading: boolean;
}

export const KBRegistration: React.FC<KBRegistrationProps> = ({
  onRegister,
  isLoading
}) => {
  const [formData, setFormData] = useState<KBRegistrationRequest>({
    name: '',
    kb_id: '',
    ds_id: '',
    bucket: ''
  });
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.name || !formData.kb_id || !formData.ds_id || !formData.bucket) {
      setMessage({ text: '필수 필드를 모두 입력해주세요', type: 'error' });
      return;
    }

    try {
      await onRegister(formData);
      setMessage({ text: '✅ 등록 성공!', type: 'success' });
      setFormData({
        name: '',
        kb_id: '',
        ds_id: '',
        bucket: ''
      });
      setTimeout(() => setMessage(null), 3000);
    } catch {
      setMessage({ text: '❌ 등록 실패', type: 'error' });
      setTimeout(() => setMessage(null), 3000);
    }
  };

  return (
    <div className="document-upload">
      <h3>새로운 Knowledge Base 등록</h3>
      <form onSubmit={handleSubmit} className="upload-form">
        <div className="form-group">
          <label>KB 이름 (별칭)</label>
          <input
            type="text"
            name="name"
            value={formData.name}
            onChange={handleChange}
            placeholder="예: 마케팅 가이드라인"
            disabled={isLoading}
            className="form-input"
          />
        </div>
        <div className="form-group">
          <label>Knowledge Base ID</label>
          <input
            type="text"
            name="kb_id"
            value={formData.kb_id}
            onChange={handleChange}
            placeholder="AWS Bedrock KB ID"
            disabled={isLoading}
            className="form-input"
          />
        </div>
        <div className="form-group">
          <label>Data Source ID</label>
          <input
            type="text"
            name="ds_id"
            value={formData.ds_id}
            onChange={handleChange}
            placeholder="AWS Bedrock DS ID"
            disabled={isLoading}
            className="form-input"
          />
        </div>
        <div className="form-group">
          <label>S3 버킷 이름</label>
          <input
            type="text"
            name="bucket"
            value={formData.bucket}
            onChange={handleChange}
            placeholder="s3-bucket-name"
            disabled={isLoading}
            className="form-input"
          />
        </div>

        <button type="submit" disabled={isLoading} className="btn-upload">
          {isLoading ? (
            <span className="btn-loading-content">
              <span className="spinner-small"></span>
              등록 중...
            </span>
          ) : (
            'KB 등록하기'
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
