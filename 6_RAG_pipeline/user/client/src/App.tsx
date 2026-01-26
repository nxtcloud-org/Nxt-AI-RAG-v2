import React from 'react';
import { ThemeProvider } from './contexts/ThemeContext';
import { LayoutProvider } from './contexts/LayoutContext';
import { UserPage } from './pages/UserPage';
import Sidebar from './components/Sidebar';
import './styles/globals.css';

const AppContent: React.FC = () => {
  return (
    <div className="app-layout">
      <Sidebar />
      <main className="app-main-content">
        <UserPage />
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
