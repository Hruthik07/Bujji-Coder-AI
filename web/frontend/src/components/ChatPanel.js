import React, { useState, useRef, useEffect } from 'react';
import './ChatPanel.css';
import ModelSelector from './ModelSelector';

function ChatPanel({ onDiffGenerated, onFileRequest }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [ws, setWs] = useState(null);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [showSearch, setShowSearch] = useState(false);
  const [selectedModel, setSelectedModel] = useState('auto');

  useEffect(() => {
    // Connect to WebSocket
    const websocket = new WebSocket(`ws://${window.location.hostname}:8001/ws/chat`);
    
    websocket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      if (data.type === 'typing') {
        setIsTyping(data.status);
      } else if (data.type === 'message') {
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: data.response,
          timestamp: new Date(),
          model: data.model || 'auto'
        }]);
        setIsTyping(false);
        
        // Check if response contains diff
        if (data.response && data.response.includes('```diff')) {
          const diffMatch = data.response.match(/```diff\n([\s\S]*?)```/);
          if (diffMatch) {
            onDiffGenerated(diffMatch[1]);
          }
        }
      } else if (data.type === 'error') {
        setMessages(prev => [...prev, {
          role: 'error',
          content: data.message,
          timestamp: new Date()
        }]);
        setIsTyping(false);
      }
    };
    
    websocket.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
    
    websocket.onclose = () => {
      console.log('WebSocket closed');
    };
    
    setWs(websocket);
    
    return () => {
      websocket.close();
    };
  }, [onDiffGenerated]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || !ws || ws.readyState !== WebSocket.OPEN) return;
    
    const userMessage = input.trim();
    setInput('');
    
    // Add user message with model info
    setMessages(prev => [...prev, {
      role: 'user',
      content: userMessage,
      timestamp: new Date(),
      model: selectedModel !== 'auto' ? selectedModel : undefined
    }]);
    
    // Send via WebSocket with model selection
    ws.send(JSON.stringify({ 
      message: userMessage,
      model: selectedModel !== 'auto' ? selectedModel : undefined
    }));
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Parse code references in message content
  const parseCodeReferences = (text) => {
    // Pattern: file paths like `file.py`, `path/to/file.js`, `file.py:42` (with line number)
    const filePattern = /`([^\s`]+\.(py|js|ts|jsx|tsx|java|go|rs|cpp|c|h|hpp|rb|php|swift|kt|md|json|yaml|yml|xml|html|css))(?::(\d+))?`/g;
    const parts = [];
    let lastIndex = 0;
    let match;

    while ((match = filePattern.exec(text)) !== null) {
      // Add text before match
      if (match.index > lastIndex) {
        parts.push({ type: 'text', content: text.substring(lastIndex, match.index) });
      }
      
      // Add clickable file reference
      const filePath = match[1];
      const lineNumber = match[3] ? parseInt(match[3]) : null;
      parts.push({
        type: 'file',
        content: match[0],
        filePath,
        lineNumber
      });
      
      lastIndex = match.index + match[0].length;
    }
    
    // Add remaining text
    if (lastIndex < text.length) {
      parts.push({ type: 'text', content: text.substring(lastIndex) });
    }
    
    return parts.length > 0 ? parts : [{ type: 'text', content: text }];
  };

  const handleFileClick = (filePath, lineNumber) => {
    if (onFileRequest) {
      onFileRequest(filePath, lineNumber);
    }
  };

  const handleExport = () => {
    const conversationText = messages.map(msg => {
      const role = msg.role === 'user' ? 'User' : msg.role === 'error' ? 'Error' : 'Assistant';
      const time = msg.timestamp.toLocaleString();
      return `[${time}] ${role}:\n${msg.content}\n`;
    }).join('\n---\n\n');
    
    const blob = new Blob([conversationText], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `conversation-${new Date().toISOString().split('T')[0]}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const filteredMessages = searchQuery
    ? messages.filter(msg => 
        msg.content.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : messages;

  return (
    <div className="chat-panel">
      <div className="chat-header">
        <h3>💬 Chat with Assistant</h3>
        <div className="chat-header-actions">
          <button
            onClick={() => setShowSearch(!showSearch)}
            className="chat-action-btn"
            title="Search conversation"
          >
            🔍
          </button>
          <button
            onClick={handleExport}
            className="chat-action-btn"
            title="Export conversation"
            disabled={messages.length === 0}
          >
            💾
          </button>
        </div>
      </div>

      {showSearch && (
        <div className="chat-search">
          <input
            type="text"
            placeholder="Search messages..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="chat-search-input"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="chat-search-clear"
            >
              ×
            </button>
          )}
        </div>
      )}

      <div className="model-selector-container">
        <ModelSelector
          onModelChange={setSelectedModel}
          currentModel={selectedModel}
        />
      </div>
      
      <div className="chat-messages">
        {messages.length === 0 && (
          <div className="chat-welcome">
            <p>👋 Welcome! Ask me anything about your code.</p>
            <p className="hint">Try: "What files are in this directory?" or "Show me the structure of assistant.py"</p>
          </div>
        )}
        
        {filteredMessages.map((msg, idx) => {
          const parts = parseCodeReferences(msg.content);
          return (
            <div key={idx} className={`chat-message ${msg.role}`}>
              <div className="message-content">
                {msg.role === 'user' ? '👤' : msg.role === 'error' ? '❌' : '🤖'}
                <div className="message-text">
                  {msg.model && msg.model !== 'auto' && (
                    <span className="model-indicator" title={`Model: ${msg.model}`}>
                      [{msg.model}]
                    </span>
                  )}
                  {parts.map((part, i) => {
                    if (part.type === 'file') {
                      return (
                        <span
                          key={i}
                          className="code-reference"
                          onClick={() => handleFileClick(part.filePath, part.lineNumber)}
                          title={`Click to open ${part.filePath}${part.lineNumber ? `:${part.lineNumber}` : ''}`}
                        >
                          {part.content}
                        </span>
                      );
                    }
                    // Regular text - split by newlines
                    return part.content.split('\n').map((line, j) => (
                      <React.Fragment key={`${i}-${j}`}>
                        {line}
                        {j < part.content.split('\n').length - 1 && <br />}
                      </React.Fragment>
                    ));
                  })}
                </div>
              </div>
              <div className="message-time">
                {msg.timestamp.toLocaleTimeString()}
              </div>
            </div>
          );
        })}
        
        {isTyping && (
          <div className="chat-message assistant typing">
            <div className="message-content">
              🤖
              <div className="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>
      
      <div className="chat-input-container">
        <textarea
          ref={inputRef}
          className="chat-input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="Ask a question or request code changes..."
          rows={2}
        />
        <button
          className="send-button"
          onClick={handleSend}
          disabled={!input.trim() || isTyping}
        >
          Send
        </button>
      </div>
    </div>
  );
}

export default ChatPanel;
