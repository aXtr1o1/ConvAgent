import { useEffect, useRef, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { useTransition } from './context/TransitionContext';
import MainHeader from './components/MainHeader';
import ChatSidebar from './components/ChatSidebar';
import LoginPage from './pages/LoginPage';
import MainLayout from './components/MainLayout';
import HomePage from './pages/HomePage';
import ChatPage from './pages/ChatPage';
import AboutPage from './pages/AboutPage';
import { Route, Routes, Navigate } from 'react-router-dom';
import { isLoggedIn } from './api/auth';

const SIDEBAR_EXIT_MS = 400;

export default function AppContent() {
  const location = useLocation();
  const { showHeaderDuringTransition } = useTransition();
  const [sidebarExiting, setSidebarExiting] = useState(false);
  const prevPathRef = useRef(location.pathname);
  const loggedIn = isLoggedIn();

  const isOnChat = location.pathname.startsWith('/chat');
  const wasOnChat = prevPathRef.current.startsWith('/chat');
  const leavingChat = wasOnChat && !isOnChat;
  const showSidebar = loggedIn && (isOnChat || leavingChat || sidebarExiting);
  const sidebarVisible = isOnChat && !sidebarExiting;
  const sidebarIsExiting = (!isOnChat && leavingChat) || sidebarExiting;

  useEffect(() => {
    if (leavingChat) {
      setSidebarExiting(true);
      const t = setTimeout(() => setSidebarExiting(false), SIDEBAR_EXIT_MS);
      return () => clearTimeout(t);
    }
  }, [location.pathname, leavingChat]);

  useEffect(() => {
    prevPathRef.current = location.pathname;
  }, [location.pathname]);

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [location.pathname]);

  const isMainRoute = ['/', '/about'].includes(location.pathname) || location.pathname.startsWith('/chat');
  const showHeader = loggedIn && (isMainRoute || (location.pathname === '/login' && showHeaderDuringTransition));

  return (
    <>
      {showHeader && <MainHeader />}
      {showSidebar && (
        <ChatSidebar visible={sidebarVisible} exiting={sidebarIsExiting} />
      )}
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/" element={loggedIn ? <MainLayout /> : <Navigate to="/login" replace />}>
          <Route index element={<HomePage />} />
          <Route path="chat" element={<ChatPage />} />
          <Route path="chat/archived" element={<ChatPage />} />
          <Route path="chat/library" element={<ChatPage />} />
          <Route path="about" element={<AboutPage />} />
        </Route>
        <Route path="*" element={<Navigate to={loggedIn ? '/' : '/login'} replace />} />
      </Routes>
    </>
  );
}
