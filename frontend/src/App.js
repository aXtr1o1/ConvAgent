import './App.css';
import { BrowserRouter as Router } from 'react-router-dom';
import { TransitionProvider } from './context/TransitionContext';
import { ErrorToastProvider } from './context/ErrorToastContext';
import AppContent from './AppContent';

function App() {
  return (
    <div className="App">
      <Router>
        <ErrorToastProvider>
          <TransitionProvider>
            <AppContent />
          </TransitionProvider>
        </ErrorToastProvider>
      </Router>
    </div>
  );
}

export default App;
