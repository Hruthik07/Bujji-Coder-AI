/**
 * Runtime configuration for the frontend.
 *
 * In local dev (CRA dev server, `npm start`), API_URL is empty so all
 * fetch('/api/...') calls stay relative and CRA's `proxy` setting in
 * package.json forwards them to the backend on :8010.
 *
 * In production (Vercel build), REACT_APP_API_URL must point at the
 * deployed Railway backend (e.g. https://bujji-api.up.railway.app).
 * REACT_APP_WS_URL must use the wss:// scheme matching that backend.
 *
 * See web/frontend/.env.example for the template.
 */

export const API_URL = process.env.REACT_APP_API_URL || '';

export const WS_URL =
  process.env.REACT_APP_WS_URL ||
  (typeof window !== 'undefined'
    ? `ws://${window.location.hostname}:8010`
    : 'ws://localhost:8010');
