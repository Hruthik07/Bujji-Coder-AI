import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';
import Landing from './components/Landing';
import ErrorBoundary from './components/ErrorBoundary';
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

// Route at the entrypoint: root path "/" gets the marketing landing
// page, every other path (e.g. /app) drops into the editor/chat shell.
// Lifting this above <App /> avoids breaking the rules-of-hooks (an
// early-return inside App would shift hook order if path changed).
const path = typeof window !== 'undefined' ? window.location.pathname : '';
const isLandingRoute = path === '/' || path === '';
const RootComponent = isLandingRoute ? Landing : App;

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <ErrorBoundary>
      <RootComponent />
    </ErrorBoundary>
  </React.StrictMode>
);
