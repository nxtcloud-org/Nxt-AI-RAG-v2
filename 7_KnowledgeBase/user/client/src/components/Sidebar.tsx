import React, { useEffect, useState } from 'react';
import { useTheme } from '../contexts/ThemeContext';
import { apiClient } from '../services/api';
import { KnowledgeBase } from '../types';
import '../styles/Sidebar.css';

interface SidebarProps {
  selectedKBIds: string[];
  onKBSelect: (kbIds: string[]) => void;
}

const Sidebar: React.FC<SidebarProps> = ({ selectedKBIds, onKBSelect }) => {
  const { theme, toggleTheme } = useTheme();
  const [kbs, setKBs] = useState<KnowledgeBase[]>([]);

  useEffect(() => {
    const loadKBs = async () => {
      try {
        const kbList = await apiClient.getKBs();
        setKBs(Array.isArray(kbList) ? kbList : []);
      } catch {
        setKBs([]);
      }
    };
    loadKBs();
  }, []);

  const handleKBToggle = (kbId: string) => {
    if (selectedKBIds.includes(kbId)) {
      onKBSelect(selectedKBIds.filter(id => id !== kbId));
    } else {
      onKBSelect([...selectedKBIds, kbId]);
    }
  };

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="logo">
          <span className="logo-icon">📚</span>
          <span className="logo-text">KB User</span>
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
          <span className="section-title">Knowledge Bases</span>
        </div>
        
        <ul className="document-list">
          {kbs.length === 0 ? (
            <li className="no-docs">
              <span className="nav-text">No KBs available</span>
            </li>
          ) : (
            kbs.map((kb) => (
              <li key={kb.kb_id}>
                <a 
                  href="#" 
                  onClick={(e) => {
                    e.preventDefault();
                    handleKBToggle(kb.kb_id);
                  }}
                  className={selectedKBIds.includes(kb.kb_id) ? 'selected' : ''}
                  title={kb.name}
                >
                  <span className="nav-icon">
                    {selectedKBIds.includes(kb.kb_id) ? '✅' : '📄'}
                  </span>
                  <span className="nav-text">{kb.name}</span>
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
