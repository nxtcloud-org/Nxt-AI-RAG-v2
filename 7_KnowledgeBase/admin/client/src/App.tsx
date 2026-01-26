import React from 'react';
import { ThemeProvider } from './contexts/ThemeContext';
import { LayoutProvider, useLayout } from './contexts/LayoutContext';
import { AdminPage } from './pages/AdminPage';
import Sidebar from './components/Sidebar';
import './styles/globals.css';

const AppContent: React.FC = () => {
  const { isSidebarCollapsed } = useLayout();
  
  return (
    <div className={`app-layout ${isSidebarCollapsed ? 'sidebar-collapsed' : ''}`}>
      <Sidebar />
      <main className="app-main-content">
        <AdminPage />
      </main>
    </div>
  );
};

function App() {
  return (
    <ThemeProvider>
      <LayoutProvider>
        <AppContent />
      </LayoutProvider>
    </ThemeProvider>
  );
}

export default App;
