import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useLocation } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import {
  getConversation,
  sendMessage as sendMessageApi,
  createConversation,
} from '../api/conversations';
import { useErrorToast } from '../context/ErrorToastContext';

const bgImage = `${process.env.PUBLIC_URL || ''}/bg-image.avif`;

function ChatPage() {
  const messagesEndRef = useRef(null);
  const location = useLocation();
  const [message, setMessage] = useState('');
  const [messages, setMessages] = useState([]);
  const [activeConversationId, setActiveConversationId] = useState(
    () => (typeof window !== 'undefined' ? localStorage.getItem('active_conversation_id') : null)
  );
  const [loading, setLoading] = useState(false);
  const [sendLoading, setSendLoading] = useState(false);
  const { showError: showErrorToast } = useErrorToast();
  const isArchived = location.pathname === '/chat/archived';
  const isLibrary = location.pathname === '/chat/library';
  const showChatUI = !isArchived && !isLibrary;
  const userId = typeof window !== 'undefined' ? localStorage.getItem('user_id') : null;

  const loadConversation = useCallback(async (conversationId) => {
    if (!conversationId) {
      setMessages([]);
      return;
    }
    setLoading(true);
    try {
      const data = await getConversation(conversationId);
      setMessages(Array.isArray(data?.messages) ? data.messages : []);
    } catch (e) {
      showErrorToast(e.message || 'Failed to load conversation');
      setMessages([]);
    } finally {
      setLoading(false);
    }
  }, [showErrorToast]);

  useEffect(() => {
    if (!showChatUI) return;
    loadConversation(activeConversationId);
  }, [showChatUI, activeConversationId, loadConversation]);

  useEffect(() => {
    if (!showChatUI) return;
    const onChanged = (e) => {
      const id = e.detail?.id ?? null;
      setActiveConversationId(id);
      if (id) loadConversation(id);
      else setMessages([]);
    };
    const onDeleted = (e) => {
      if (e.detail?.id === activeConversationId) {
        setActiveConversationId(null);
        setMessages([]);
      }
    };
    window.addEventListener('active-conversation-changed', onChanged);
    window.addEventListener('active-conversation-deleted', onDeleted);
    return () => {
      window.removeEventListener('active-conversation-changed', onChanged);
      window.removeEventListener('active-conversation-deleted', onDeleted);
    };
  }, [showChatUI, activeConversationId, loadConversation]);

  const handleSend = async (e) => {
    e.preventDefault();
    const trimmed = message.trim();
    if (!trimmed || sendLoading) return;

    let conversationId = activeConversationId;
    if (!conversationId && userId) {
      try {
        const created = await createConversation(userId);
        conversationId = created?.conversation_id ?? null;
        if (conversationId) {
          localStorage.setItem('active_conversation_id', conversationId);
          setActiveConversationId(conversationId);
          window.dispatchEvent(new CustomEvent('active-conversation-changed', { detail: { id: conversationId } }));
        }
      } catch (err) {
        showErrorToast(err.message || 'Failed to create conversation');
        return;
      }
    }

    if (!conversationId) {
      showErrorToast('No conversation selected. Create one from the sidebar.');
      return;
    }

    setMessage('');
    const optimisticUserMessage = {
      message_id: `temp-${Date.now()}`,
      role: 'user',
      content: trimmed,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, optimisticUserMessage]);
    setSendLoading(true);
    try {
      const data = await sendMessageApi(conversationId, trimmed);
      setMessages(Array.isArray(data?.messages) ? data.messages : []);
    } catch (err) {
      showErrorToast(err.message || 'Failed to send message');
      setMessages((prev) => prev.filter((m) => m.message_id !== optimisticUserMessage.message_id));
    } finally {
      setSendLoading(false);
    }
  };

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [messages, sendLoading]);

  return (
    <div
      className="main-page-content chat-page-content"
      style={{
        flex: 1,
        backgroundImage: `url(${bgImage})`,
        backgroundRepeat: 'no-repeat',
        backgroundPosition: 'center',
        backgroundSize: 'cover',
      }}
    >
      <div className="chat-page-overlay" aria-hidden="true" />

      <main className="chat-page-main">
        {loading ? (
          <div className="chat-page-loading" role="status" aria-label="Loading">
            <img
              src={`${process.env.PUBLIC_URL || ''}/loading-gif.gif`}
              alt=""
              className="chat-page-loading-gif"
              aria-hidden="true"
            />
            {/* <span className="chat-page-loading-text">Loading…</span> */}
          </div>
        ) : messages.length > 0 || sendLoading ? (
          <div className="chat-page-messages" role="log" aria-live="polite">
            {messages.map((m) => (
              <article
                key={m.message_id || `${m.role}-${m.content?.slice(0, 30)}`}
                className={`chat-page-msg chat-page-msg--${m.role}`}
                aria-label={m.role === 'user' ? 'Your message' : 'Assistant reply'}
              >
                <span className="chat-page-msg-label">{m.role === 'user' ? 'You' : 'Assistant'}</span>
                <div className="chat-page-msg-content">
                  {m.role === 'assistant' ? (
                    <ReactMarkdown>{m.content || ''}</ReactMarkdown>
                  ) : (
                    <p className="chat-page-msg-plain">{m.content || ''}</p>
                  )}
                </div>
              </article>
            ))}
            {sendLoading && (
              <article
                className="chat-page-msg chat-page-msg--assistant chat-page-msg--thinking"
                aria-live="polite"
                aria-label="Assistant thinking"
              >
                <span className="chat-page-msg-label">Assistant</span>
                <div className="chat-page-msg-content chat-page-thinking">
                  <span className="chat-page-thinking-text">Thinking</span>
                  <span className="chat-page-thinking-dots" aria-hidden="true">
                    <span className="chat-page-thinking-dot" />
                    <span className="chat-page-thinking-dot" />
                    <span className="chat-page-thinking-dot" />
                  </span>
                </div>
              </article>
            )}
            <div ref={messagesEndRef} aria-hidden="true" />
          </div>
        ) : (
          <div className="chat-page-welcome">
            <h1 className="chat-page-title">Welcome to <em>DCT AI Agent</em></h1>
            <p className="chat-page-subtitle">Ask me anything about your vehicle</p>
          </div>
        )}
      </main>

      
        <form className="chat-page-composer" onSubmit={handleSend}>
          <div className="chat-page-composer-inner">
            <input
              className="chat-page-input"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="Ask Anything..."
              aria-label="Message"
              disabled={sendLoading}
            />
            <button className="chat-page-send" type="submit" aria-label="Send" disabled={sendLoading}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                <path d="M12 4l-1.41 1.41L15.17 10H4v2h11.17l-4.58 4.59L12 18l8-8z" />
              </svg>
            </button>
          </div>
        </form>
      
    </div>
  );
}

export default ChatPage;
