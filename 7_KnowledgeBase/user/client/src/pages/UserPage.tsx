import React, { useState } from 'react';
import { Message } from '../types';
import { ChatInterface } from '../components/ChatInterface';
import { apiClient } from '../services/api';
import '../styles/UserPage.css';

interface UserPageProps {
  selectedKBIds: string[];
}

export const UserPage: React.FC<UserPageProps> = ({ selectedKBIds }) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId] = useState(`user_${Date.now()}`);

  const handleSendMessage = async (query: string) => {
    if (selectedKBIds.length === 0) {
      const errorMessage: Message = {
        id: `msg_${Date.now()}_error`,
        type: 'assistant',
        content: '검색할 Knowledge Base를 선택해주세요.',
        timestamp: new Date()
      };
      setMessages((prev) => [...prev, errorMessage]);
      return;
    }

    const userMessage: Message = {
      id: `msg_${Date.now()}_user`,
      type: 'user',
      content: query,
      timestamp: new Date()
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    try {
      const response = await apiClient.chat({
        query,
        session_id: sessionId,
        kb_ids: selectedKBIds
      });

      const assistantMessage: Message = {
        id: `msg_${Date.now()}_assistant`,
        type: 'assistant',
        content: response.response,
        timestamp: new Date(),
        sources: response.sources
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch {
      const errorMessage: Message = {
        id: `msg_${Date.now()}_error`,
        type: 'assistant',
        content: '죄송합니다. 질문 처리 중 오류가 발생했습니다.',
        timestamp: new Date()
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleClearHistory = async () => {
    await apiClient.clearChatHistory(sessionId);
    setMessages([]);
  };

  return (
    <div className="user-page">
      <main className="chat-layout">
        <header className="chat-header">
          <div className="header-content">
            <h1>Knowledge Base Chat Assistant</h1>
            <span className="status-badge">Online</span>
          </div>
          <p className="subtitle">
            {selectedKBIds.length > 0 
              ? `${selectedKBIds.length}개 KB 선택됨` 
              : 'Knowledge Base를 선택해주세요'}
          </p>
        </header>

        <div className="chat-container-wrapper">
          <ChatInterface
            messages={messages}
            isLoading={isLoading}
            onSendMessage={handleSendMessage}
            onClearHistory={handleClearHistory}
          />
        </div>
      </main>
    </div>
  );
};
