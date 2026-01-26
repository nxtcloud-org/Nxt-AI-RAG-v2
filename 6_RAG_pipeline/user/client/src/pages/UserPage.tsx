import React, { useState } from 'react';
import { Message } from '../types';
import { ChatInterface } from '../components/ChatInterface';
import { apiClient } from '../services/api';
import '../styles/UserPage.css';

export const UserPage: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId] = useState(`user_${Date.now()}`);

  const handleSendMessage = async (query: string) => {
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
        session_id: sessionId
      });

      const assistantMessage: Message = {
        id: `msg_${Date.now()}_assistant`,
        type: 'assistant',
        content: response.response,
        timestamp: new Date(),
        sources: response.sources
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Chat error:', error);
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
    try {
      await apiClient.clearChatHistory(sessionId);
      setMessages([]);
    } catch (error) {
      console.error('Clear history error:', error);
    }
  };

  return (
    <div className="user-page">
      <main className="chat-layout">
        <header className="chat-header">
          <div className="header-content">
            <h1>RAG Chat Assistant</h1>
            <span className="status-badge">Online</span>
          </div>
          <p className="subtitle">문서 기반 질의응답 시스템</p>
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
