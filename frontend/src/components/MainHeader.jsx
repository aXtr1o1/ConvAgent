import React, { useState, useRef, useEffect } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';

function UserIcon() {
  return (
    <svg className="main-profile-icon-svg" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z" />
    </svg>
  );
}

export default function MainHeader() {
  const navigate = useNavigate();
  const [popoverOpen, setPopoverOpen] = useState(false);
  const popoverRef = useRef(null);
  const username = typeof window !== 'undefined' ? localStorage.getItem('username') : null;
  const userId = typeof window !== 'undefined' ? localStorage.getItem('user_id') : null;
  const avatarUrl = null;

  useEffect(() => {
    function handleClickOutside(e) {
      if (popoverRef.current && !popoverRef.current.contains(e.target)) {
        setPopoverOpen(false);
      }
    }
    if (popoverOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [popoverOpen]);

  const handleSignOut = () => {
    localStorage.removeItem('user_id');
    localStorage.removeItem('username');
    setPopoverOpen(false);
    navigate('/login');
  };

  return (
    <header className="main-top-nav main-top-nav-transition" aria-label="Main">
      <nav className="main-top-nav-links">
        <NavLink to="/" className={({ isActive }) => isActive ? 'main-nav-link active' : 'main-nav-link'}>
          Home
        </NavLink>
        <NavLink to="/chat" className={({ isActive }) => isActive ? 'main-nav-link active' : 'main-nav-link'}>
          Chat
        </NavLink>
        <NavLink to="/about" className={({ isActive }) => isActive ? 'main-nav-link active' : 'main-nav-link'}>
          About
        </NavLink>
      </nav>
      <div className="main-profile-wrap" ref={popoverRef}>
        <button
          type="button"
          className="main-profile-btn"
          aria-label="Profile"
          aria-expanded={popoverOpen}
          onClick={() => setPopoverOpen((o) => !o)}
        >
          <span className="main-profile-avatar">
            {avatarUrl ? (
              <img src={avatarUrl} alt="" className="main-profile-avatar-img" />
            ) : username ? (
              <span className="main-profile-initials">{username.charAt(0).toUpperCase()}</span>
            ) : (
              <UserIcon />
            )}
          </span>
        </button>
        {popoverOpen && (
          <div className="main-profile-popover" role="dialog" aria-label="Profile menu">
            <div className="main-profile-popover-header">
              <span className="main-profile-popover-name">{username || 'User'}</span>
              {userId && (
                <span className="main-profile-popover-info">Signed in</span>
              )}
            </div>
            <button type="button" className="main-profile-signout" onClick={handleSignOut}>
              Sign out
            </button>
          </div>
        )}
      </div>
    </header>
  );
}
