import React, { useEffect, useState } from 'react';
import { useTheme } from '../contexts/ThemeContext';
import { apiClient } from '../services/api';
import { Document } from '../types';
import '../styles/Sidebar.css';

const Sidebar: React.FC = () => {
  const { theme, toggleTheme } = useTheme();
  const [documents, setDocuments] = useState<Document[]>([]);

  useEffect(() => {
    const loadDocuments = async () => {
      try {
        const docs = await apiClient.getDocuments();
        setDocuments(Array.isArray(docs) ? docs : []);
      } catch (error) {
        console.error('Failed to load documents:', error);
        setDocuments([]);
      }
    };
    loadDocuments();
  }, []);

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="logo">
          <span className="logo-icon">📚</span>
          <span className="logo-text">RAG User</span>
        </div>
      </div>

      <nav className="sidebar-nav">
        <ul>
          <li className="active">
            <a href="#chat">
              <span className="nav-icon">💬</span>
              <span className="nav-text">Chat</span>
            </a>
          </li>
        </ul>
        
        <div className="nav-divider"></div>
        
        <div className="nav-section-header">
          <span className="section-title">Documents</span>
        </div>
        
        <ul className="document-list">
          {documents.length === 0 ? (
            <li className="no-docs">
              <span className="nav-text">No documents</span>
            </li>
          ) : (
            documents.map((doc) => (
              <li key={doc.id}>
                <a href="#" onClick={(e) => e.preventDefault()} title={doc.title}>
                  <span className="nav-icon">📄</span>
                  <span className="nav-text">{doc.title}</span>
                </a>
              </li>
            ))
          )}
        </ul>
      </nav>

      <div className="sidebar-footer">
        <button
          className="theme-toggle-btn"
          onClick={toggleTheme}
          title={`Switch to ${theme === 'light' ? 'Dark' : 'Light'} Mode`}
        >
          {theme === 'light' ? '🌙' : '☀️'}
          <span className="theme-text">{theme === 'light' ? '다크 모드' : '라이트 모드'}</span>
        </button>
      </div>
    </aside>
  );
}

export default Sidebar;
