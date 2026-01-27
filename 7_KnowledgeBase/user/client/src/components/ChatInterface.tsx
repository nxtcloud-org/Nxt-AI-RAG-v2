import React, { useState, useRef, useEffect } from 'react';
import { Message } from '../types';
import '../styles/ChatInterface.css';

interface ChatInterfaceProps {
  messages: Message[];
  isLoading: boolean;
  onSendMessage: (message: string) => void;
  onClearHistory: () => void;
}

export const ChatInterface: React.FC<ChatInterfaceProps> = ({
  messages,
  isLoading,
  onSendMessage,
  onClearHistory
}) => {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = () => {
    if (input.trim()) {
      onSendMessage(input);
      setInput('');
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="chat-interface">
      <div className="messages-container">
        {messages.length === 0 ? (
          <div className="empty-state">
            <p>💬 대화를 시작해보세요</p>
            <p className="hint">Knowledge Base에 대한 질문을 입력하면 답변을 얻을 수 있습니다</p>
          </div>
        ) : (
          messages.map((msg) => (
            <div
              key={msg.id}
              className={`message ${msg.type === 'user' ? 'user-message' : 'assistant-message'}`}
            >
              <div className="message-content">
                <p>{msg.content}</p>
                {msg.sources && msg.sources.length > 0 && (
                  <div className="sources">
                    <p className="sources-label">📚 참고 문서:</p>
                    {msg.sources.map((source, idx) => (
                      <div key={idx} className="source-item">
                        <span className="page-number">
                          {source.document_title ? `${source.document_title} • ` : ''}
                          {source.page ? `${source.page}페이지` : ''}
                          {source.score ? ` • 점수: ${source.score.toFixed(4)}` : ''}
                        </span>
                        <p className="source-text">{source.content}</p>
                        {source.location?.s3Location?.uri && (
                          <p className="source-uri" style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
                            {source.location.s3Location.uri}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
              <span className="timestamp">
                {msg.timestamp.toLocaleTimeString('ko-KR', {
                  hour: '2-digit',
                  minute: '2-digit'
                })}
              </span>
            </div>
          ))
        )}
        {isLoading && (
          <div className="message assistant-message">
            <div className="loading-container">
              <span className="dot"></span>
              <span className="dot"></span>
              <span className="dot"></span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="input-area">
        <div className="input-wrapper">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyPress}
            placeholder="질문을 입력하세요..."
            disabled={isLoading}
            className="message-input"
          />
          <button
            onClick={handleSend}
            disabled={isLoading || !input.trim()}
            className="send-button"
          >
            보내기
          </button>
        </div>
        <button onClick={onClearHistory} className="clear-button">
          🗑️ 대화 초기화
        </button>
      </div>
    </div>
  );
};
