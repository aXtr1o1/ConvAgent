import React, { useState, useEffect } from 'react';
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
  const [loadingConversations, setLoadingConversations] = useState(false);
  const { showError: showErrorToast } = useErrorToast();
  const userId = typeof window !== 'undefined' ? localStorage.getItem('user_id') : null;

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
    let cancelled = false;
    async function initialLoad() {
      setLoadingConversations(true);
      try {
        const data = await listConversations(userId);
        if (!cancelled) {
          const list = Array.isArray(data.conversations) ? data.conversations : [];
          list.sort(
            (a, b) =>
              new Date(b.updated_at || b.created_at || 0) -
              new Date(a.updated_at || a.created_at || 0)
          );
          setConversations(list);
        }
      } catch (e) {
        if (!cancelled) showErrorToast(e.message || 'Failed to load conversations');
      } finally {
        if (!cancelled) setLoadingConversations(false);
      }
    }
    initialLoad();
    return () => {
      cancelled = true;
    };
  }, [isChatView, userId, showErrorToast]);

  // Reload when sidebar becomes visible (e.g., after animation)
  useEffect(() => {
    if (!visible || exiting || !isChatView) return;
    let cancelled = false;
    async function load() {
      setLoadingConversations(true);
      try {
        const data = await listConversations(userId);
        if (!cancelled) {
          const list = Array.isArray(data.conversations) ? data.conversations : [];
          list.sort(
            (a, b) =>
              new Date(b.updated_at || b.created_at || 0) -
              new Date(a.updated_at || a.created_at || 0)
          );
          setConversations(list);
        }
      } catch (e) {
        if (!cancelled) showErrorToast(e.message || 'Failed to load conversations');
      } finally {
        if (!cancelled) setLoadingConversations(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [visible, exiting, isChatView, userId, showErrorToast]);

  // When a conversation is updated (new message), smoothly move it to the top
  useEffect(() => {
    if (!isChatView) return;
    const handleUpdated = (e) => {
      const id = e.detail?.id;
      if (!id) return;
      // Reorder locally so the updated conversation moves to the top without reloading
      setConversations((prev) => {
        const idx = prev.findIndex((c) => c.conversation_id === id);
        if (idx <= 0) return prev;
        const next = [...prev];
        const [item] = next.splice(idx, 1);
        next.unshift(item);
        return next;
      });
    };
    window.addEventListener('conversation-updated', handleUpdated);
    return () => {
      window.removeEventListener('conversation-updated', handleUpdated);
    };
  }, [isChatView, userId, showErrorToast]);

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
      const data = await listConversations(userId);
      const list = Array.isArray(data.conversations) ? data.conversations : [];
      list.sort(
        (a, b) =>
          new Date(b.updated_at || b.created_at || 0) -
          new Date(a.updated_at || a.created_at || 0)
      );
      setConversations(list);
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
      const data = await listConversations(userId);
      const list = Array.isArray(data.conversations) ? data.conversations : [];
      list.sort(
        (a, b) =>
          new Date(b.updated_at || b.created_at || 0) -
          new Date(a.updated_at || a.created_at || 0)
      );
      setConversations(list);
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

                {loadingConversations ? (
                  <p className="chat-sidebar-no-conversations">Loading…</p>
                ) : conversations.length === 0 ? (
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