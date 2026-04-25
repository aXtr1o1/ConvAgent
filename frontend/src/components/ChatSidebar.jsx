import React, { useState, useEffect, useCallback, useRef } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { createConversation, listConversations, deleteConversation } from '../api/conversations';
import { useErrorToast } from '../context/ErrorToastContext';

function ChatSidebar({ visible, exiting }) {
  const location = useLocation();
  const isChatView = location.pathname.startsWith('/chat');
  const isArchivedView = location.pathname === '/chat/archived';
  const isLibraryView = location.pathname === '/chat/library';
  const [animateIn, setAnimateIn] = useState(false);
  const [notImplemented, setNotImplemented] = useState('');
  const [conversations, setConversations] = useState([]);
  const [activeConversationId, setActiveConversationId] = useState(
    typeof window !== 'undefined' ? localStorage.getItem('active_conversation_id') : null
  );
 
  const { showError: showErrorToast } = useErrorToast();
  const userId = typeof window !== 'undefined' ? localStorage.getItem('user_id') : null;
  const refreshSeqRef = useRef(0);

  const refreshConversations = useCallback(async () => {
    if (!userId) {
      setConversations([]);
      return;
    }
    const seq = ++refreshSeqRef.current;
    
    try {
      const data = await listConversations(userId);
      if (seq !== refreshSeqRef.current) return;
      const list = Array.isArray(data.conversations) ? data.conversations : [];
      list.sort(
        (a, b) =>
          new Date(b.updated_at || b.created_at || 0) - new Date(a.updated_at || a.created_at || 0)
      );
      setConversations(list);
    } catch (e) {
      if (seq !== refreshSeqRef.current) return;
      showErrorToast(e.message || 'Failed to load conversations');
    }
  }, [userId, showErrorToast]);

  useEffect(() => {
    if (visible && !exiting) {
      const id = requestAnimationFrame(() => {
        requestAnimationFrame(() => setAnimateIn(true));
      });
      return () => cancelAnimationFrame(id);
    }
    if (!visible) setAnimateIn(false);
  }, [visible, exiting]);

  // Always ensure conversations load when we are on /chat
  useEffect(() => {
    if (!isChatView) return;
    refreshConversations();
  }, [isChatView, refreshConversations]);

  // Reload when sidebar becomes visible (e.g., after animation)
  useEffect(() => {
    if (!visible || exiting || !isChatView) return;
    refreshConversations();
  }, [visible, exiting, isChatView, refreshConversations]);

  // When a conversation is updated (new message), smoothly move it to the top
  useEffect(() => {
    if (!isChatView) return;
    const handleUpdated = (e) => {
      const id = e.detail?.id;
      if (!id) return;
      // Reorder locally so the updated conversation moves to the top without reloading.
      // If we don't have it yet (e.g. newly created from ChatPage), refresh from server.
      let found = false;
      setConversations((prev) => {
        const idx = prev.findIndex((c) => c.conversation_id === id);
        found = idx !== -1;
        if (idx <= 0) return prev;
        const next = [...prev];
        const [item] = next.splice(idx, 1);
        next.unshift(item);
        return next;
      });
      if (!found) {
        refreshConversations();
      } else {
        // Also refresh in background so title/updated_at stay in sync with backend.
        refreshConversations();
      }
    };
    window.addEventListener('conversation-updated', handleUpdated);
    return () => {
      window.removeEventListener('conversation-updated', handleUpdated);
    };
  }, [isChatView, refreshConversations]);

  // If ChatPage creates a conversation (first message), it dispatches active-conversation-changed.
  // Make sure the sidebar list updates immediately without requiring a reload.
  useEffect(() => {
    if (!isChatView) return;
    const onChanged = (e) => {
      const id = e.detail?.id ?? null;
      setActiveConversationId(id);
      refreshConversations();
    };
    window.addEventListener('active-conversation-changed', onChanged);
    return () => window.removeEventListener('active-conversation-changed', onChanged);
  }, [isChatView, refreshConversations]);

  useEffect(() => {
    if (!notImplemented) return;
    const t = setTimeout(() => setNotImplemented(''), 2200);
    return () => clearTimeout(t);
  }, [notImplemented]);

  const className = [
    'chat-sidebar',
    animateIn && visible && !exiting && 'chat-sidebar-visible',
    exiting && 'chat-sidebar-exiting',
  ]
    .filter(Boolean)
    .join(' ');

  const handleNewChat = async () => {
    try {
      const created = await createConversation(userId);
      const newId = created.conversation_id;
      if (newId) {
        localStorage.setItem('active_conversation_id', newId);
        setActiveConversationId(newId);
        if (typeof window !== 'undefined') {
          window.dispatchEvent(
            new CustomEvent('active-conversation-changed', { detail: { id: newId } })
          );
        }
      }
      await refreshConversations();
    } catch (e) {
      showErrorToast(e.message || 'Failed to create conversation');
    }
  };

  const handleSelectConversation = (id) => {
    localStorage.setItem('active_conversation_id', id);
    setActiveConversationId(id);
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent('active-conversation-changed', { detail: { id } }));
    }
  };

  const handleDeleteConversation = async (e, conversationId) => {
    e.preventDefault();
    e.stopPropagation();
    try {
      await deleteConversation(conversationId);
      if (conversationId === activeConversationId) {
        localStorage.removeItem('active_conversation_id');
        setActiveConversationId(null);
        if (typeof window !== 'undefined') {
          window.dispatchEvent(
            new CustomEvent('active-conversation-deleted', { detail: { id: conversationId } })
          );
        }
      }
      await refreshConversations();
    } catch (err) {
      showErrorToast(err.message || 'Failed to delete');
    }
  };

  return (
    <aside className={className} aria-label="Chat sidebar">
      <div className="chat-sidebar-inner">
        <div className="chat-sidebar-new-chat-wrap">
          <button type="button" className="chat-sidebar-new-chat" onClick={handleNewChat}>
            <svg
              className="chat-sidebar-new-chat-bubble"
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="currentColor"
            >
              <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z" />
            </svg>
            <span>New Chat</span>
          </button>
        </div>

        <div className="chat-sidebar-features">
          <div className="chat-sidebar-features-label">FEATURES</div>
          <nav className="chat-sidebar-nav">
            <NavLink
              to="/chat"
              className={({ isActive }) => `chat-sidebar-nav-item ${isActive ? 'active' : ''}`}
              end
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z" />
              </svg>
              <span>Chat</span>
            </NavLink>
            <NavLink
              to="/chat/archived"
              className={({ isActive }) => `chat-sidebar-nav-item ${isActive ? 'active' : ''}`}
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                <path d="M20.54 5.23l-1.39-1.68C18.88 3.21 18.47 3 18 3H6c-.47 0-.88.21-1.16.55L3.46 5.23C3.17 5.57 3 6.02 3 6.5V19c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V6.5c0-.48-.17-.93-.46-1.27zM12 17.5L6.5 12H10v-2h4v2h3.5L12 17.5zM5.12 5l.81-1h12l.94 1H5.12z" />
              </svg>
              <span>Archived</span>
            </NavLink>
            <NavLink
              to="/chat/library"
              className={({ isActive }) => `chat-sidebar-nav-item ${isActive ? 'active' : ''}`}
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                <path d="M3 18h18v-2H3v2zm0-5h18v-2H3v2zm0-7v2h18V6H3z" />
              </svg>
              <span>Library</span>
            </NavLink>
          </nav>
        </div>

        <div className="chat-sidebar-conversations">
          <div className="chat-sidebar-conversations-inner">
            {isArchivedView ? (
              <div className="chat-sidebar-placeholder-card" role="status">
                <span className="chat-sidebar-placeholder-title">Archived</span>
                <span className="chat-sidebar-placeholder-text">Yet to be implemented</span>
              </div>
            ) : isLibraryView ? (
              <div className="chat-sidebar-placeholder-card" role="status">
                <span className="chat-sidebar-placeholder-title">Library</span>
                <span className="chat-sidebar-placeholder-text">Yet to be implemented</span>
              </div>
            ) : !isChatView ? (
              <p className="chat-sidebar-no-conversations">Select Chat to see conversations</p>
            ) : (
              <>
                {notImplemented && (
                  <div className="chat-sidebar-not-impl" role="status">
                    {notImplemented}
                  </div>
                )}

                

                {conversations.length === 0 ? (
                  <p className="chat-sidebar-no-conversations">No conversations yet</p>
                ) : (
                  <div className="chat-sidebar-conv-list" role="list">
                    {conversations.map((c) => (
                      <div
                        key={c.conversation_id}
                        role="listitem"
                        className={`chat-sidebar-conv-item ${
                          activeConversationId === c.conversation_id ? 'active' : ''
                        }`}
                        onClick={() => handleSelectConversation(c.conversation_id)}
                        title={c.title}
                      >
                        <span className="chat-sidebar-conv-title">
                          {c.title || 'New Conversation'}
                        </span>
                        <button
                          type="button"
                          className="chat-sidebar-conv-delete"
                          onClick={(e) => handleDeleteConversation(e, c.conversation_id)}
                          aria-label={`Delete ${c.title || 'conversation'}`}
                        >
                          <svg
                            width="16"
                            height="16"
                            viewBox="0 0 24 24"
                            fill="currentColor"
                            aria-hidden="true"
                          >
                            <path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z" />
                          </svg>
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </>
            )}
          </div>
        </div>

        <div className="chat-sidebar-beta">
          <svg
            className="chat-sidebar-beta-icon"
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="currentColor"
          >
            <path d="M1 21h22L12 2 1 21zm12-3h-2v-2h2v2zm0-4h-2v-4h2v4z" />
          </svg>
          <div className="chat-sidebar-beta-text">
            <strong>BETA VERSION</strong>
            <p>
              CortexForge Diagnostics is in beta - AI-generated guidance should be verified with
              official service procedures.
            </p>
          </div>
        </div>
      </div>
    </aside>
  );
}

export default ChatSidebar;