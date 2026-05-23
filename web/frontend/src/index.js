import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';
import { API_URL } from './config';

// In dev, CRA's package.json `proxy` forwards /api/* to localhost:8010.
// In prod (Vercel), no proxy runs — relative /api/* calls would hit the
// Vercel domain. Prefix relative /api/* URLs with API_URL so every
// existing fetch('/api/...') call in components just works in both
// environments without touching the call site.
if (API_URL && typeof window !== 'undefined') {
  const originalFetch = window.fetch.bind(window);
  window.fetch = (input, init) => {
    if (typeof input === 'string' && input.startsWith('/api/')) {
      return originalFetch(`${API_URL}${input}`, init);
    }
    if (input instanceof Request && input.url.startsWith('/api/')) {
      const rewritten = new Request(`${API_URL}${input.url}`, input);
      return originalFetch(rewritten, init);
    }
    return originalFetch(input, init);
  };
}

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
