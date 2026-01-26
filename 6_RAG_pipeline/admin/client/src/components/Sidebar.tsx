import React from 'react';
import { useTheme } from '../contexts/ThemeContext';
import '../styles/Sidebar.css';

const Sidebar: React.FC = () => {
  const { theme, toggleTheme } = useTheme();

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="logo">
          <span className="logo-icon">📚</span>
          <span className="logo-text">RAG Admin</span>
        </div>
      </div>

      <nav className="sidebar-nav">
        <ul>
          <li className="active">
            <a href="#dashboard">
              <span className="nav-text">main</span>
            </a>
          </li>
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