import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';

const ErrorToastContext = createContext(null);

const TOAST_AUTO_DISMISS_MS = 6000;

export function ErrorToastProvider({ children }) {
  const [message, setMessage] = useState('');
  const [visible, setVisible] = useState(false);

  const showError = useCallback((msg) => {
    if (!msg) return;
    setMessage(String(msg));
    setVisible(true);
  }, []);

  const hideError = useCallback(() => {
    setVisible(false);
    setMessage('');
  }, []);

  useEffect(() => {
    if (!visible || !message) return;
    const t = setTimeout(() => {
      setVisible(false);
      setMessage('');
    }, TOAST_AUTO_DISMISS_MS);
    return () => clearTimeout(t);
  }, [visible, message]);

  return (
    <ErrorToastContext.Provider value={{ showError, hideError }}>
      {children}
      {visible && message && (
        <div
          className="error-toast"
          role="alert"
          aria-live="assertive"
        >
          <p className="error-toast-message">{message}</p>
          <button
            type="button"
            className="error-toast-dismiss"
            onClick={hideError}
            aria-label="Dismiss"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
              <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z" />
            </svg>
          </button>
        </div>
      )}
    </ErrorToastContext.Provider>
  );
}

export function useErrorToast() {
  const ctx = useContext(ErrorToastContext);
  return ctx || { showError: () => {}, hideError: () => {} };
}
