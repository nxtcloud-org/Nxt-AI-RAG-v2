import React, { useState } from 'react';
import { ThemeProvider } from './contexts/ThemeContext';
import { LayoutProvider } from './contexts/LayoutContext';
import { UserPage } from './pages/UserPage';
import Sidebar from './components/Sidebar';
import './styles/globals.css';

const AppContent: React.FC = () => {
  const [selectedKBIds, setSelectedKBIds] = useState<string[]>([]);

  return (
    <div className="app-layout">
      <Sidebar selectedKBIds={selectedKBIds} onKBSelect={setSelectedKBIds} />
      <main className="app-main-content">
        <UserPage selectedKBIds={selectedKBIds} />
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
