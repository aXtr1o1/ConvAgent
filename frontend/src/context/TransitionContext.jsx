import React, { createContext, useContext, useState } from 'react';

const TransitionContext = createContext(null);

export function TransitionProvider({ children }) {
  const [showHeaderDuringTransition, setShowHeaderDuringTransition] = useState(false);
  return (
    <TransitionContext.Provider value={{ showHeaderDuringTransition, setShowHeaderDuringTransition }}>
      {children}
    </TransitionContext.Provider>
  );
}

export function useTransition() {
  const ctx = useContext(TransitionContext);
  return ctx;
}
