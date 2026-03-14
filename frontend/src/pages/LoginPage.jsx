import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { validateLogin } from '../api/auth';
import { useTransition } from '../context/TransitionContext';

function LoginPage() {
  const navigate = useNavigate();
  const { setShowHeaderDuringTransition } = useTransition();
  const [userName, setUserName] = useState('');
  const [password, setPassword] = useState('');
  const [slideUpDone, setSlideUpDone] = useState(false);
  const [splitDone, setSplitDone] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [transitioningToLanding, setTransitioningToLanding] = useState(false);

  useEffect(() => {
    const t1 = setTimeout(() => setSlideUpDone(true), 400);
    const t2 = setTimeout(() => setSplitDone(true), 1800);
    return () => { clearTimeout(t1); clearTimeout(t2); };
  }, []);

  useEffect(() => {
    if (!transitioningToLanding) setShowHeaderDuringTransition(false);
  }, [transitioningToLanding, setShowHeaderDuringTransition]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const data = await validateLogin(userName.trim(), password);
      // Success: { status: "success", user_id, username }
      if (data.status === true || data.status === 'success') {
        if (data.user_id) localStorage.setItem('user_id', data.user_id);
        if (data.username) localStorage.setItem('username', data.username);
        setTransitioningToLanding(true);
        setShowHeaderDuringTransition(true);
        setTimeout(() => navigate('/', { state: { fromLogin: true } }), 1200);
        return;
      }
      // Failed: { status: "failed", detail: "Invalid username or credentials." }
      setError(data.detail || 'Login failed');
    } catch (err) {
      setError(err.message || 'Unable to reach server');
    } finally {
      setLoading(false);
    }
  };

  const bgImage = `${process.env.PUBLIC_URL || ''}/bg-image.avif`;

  return (
    <div
      className={`login-page-layout ${slideUpDone ? 'slide-up-done' : ''} ${splitDone ? 'split-done' : ''} ${transitioningToLanding ? 'transition-to-landing' : ''}`}
    >
      {/* Left section: form (visible after split) */}
      <section className="login-page-left">
        <div className="login-page-form">
          <h1 className="login-page-form-title">Welcome <em>back</em></h1>
          <p className="login-page-form-subtitle">Please enter your details to continue to chat</p>
          <form onSubmit={handleSubmit} className="login-page-form-fields">
            <div className="login-page-form-group">
              <label htmlFor="userName">User Name</label>
              <input
                id="userName"
                type="text"
                value={userName}
                onChange={(e) => setUserName(e.target.value)}
                required
                placeholder="Enter your user name"
              />
            </div>
            <div className="login-page-form-group">
              <label htmlFor="password">Password</label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                placeholder="••••••••"
              />
            </div>
            {error && (
              <p className="login-page-form-error" role="alert">
                {error}
              </p>
            )}
            <button
              type="submit"
              className="login-page-form-cta"
              disabled={loading}
            >
              <span>{loading ? 'Checking…' : 'Continue to chat'}</span>
              {!loading && (
                <span className="login-page-form-cta-arrow" aria-hidden="true">→</span>
              )}
            </button>
          </form>
        </div>
        <p className="login-page-copyright">© 2026 </p>
        <p className="login-page-copyleft">aXtrLabs</p>
      </section>


      {/* Right section: slide from bottom; inner box has bg image */}
      <section className="login-page-right">
        <div className="login-page-right-slide">
          <div
            className="login-page-right-inner-circle"
            aria-hidden="true"
            style={{ backgroundImage: `url(${bgImage})` }}
          />
        </div>
      </section>

      {/* Box: centered until split, then moves to right section */}
      <div className="login-page-object-wrapper">
        <div className="login-page-object" aria-hidden="false">
          <h2 className="login-page-object-title">Automotive <em>Intelligence</em></h2>
          <p className="login-page-object-text">
            Transform vehicle fault codes into actionable repair intelligence.
          </p>
          <p className="login-page-object-text">
            Powered by aXtrLabs
          </p>
        </div>
      </div>
    </div>
  );
}

export default LoginPage;
