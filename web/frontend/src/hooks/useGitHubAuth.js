/**
 * useGitHubAuth
 *
 * Drives the "Sign in with GitHub" UI. Three responsibilities:
 *
 *   1. Pick up the JWT from the OAuth callback URL fragment
 *      (#access_token=...) on first render, persist it to
 *      localStorage, and clean the fragment out of the URL.
 *   2. Fetch the current user from /api/auth/me using whatever
 *      access_token is in localStorage; clear the token on 401.
 *   3. Query /api/auth/github/status once on mount so the button
 *      can self-hide when the backend has no OAuth client configured.
 *
 * Exposes:
 *   { user, loading, oauthEnabled, signIn, signOut }
 *
 * user           - { id, username, email, role } or null when signed out
 * loading        - true during the initial /me check
 * oauthEnabled   - false until /api/auth/github/status answers
 * signIn()       - navigates to the backend /api/auth/github/login route
 * signOut()      - clears localStorage and reloads the page
 */

import { useCallback, useEffect, useState } from 'react';
import { API_URL } from '../config';

const TOKEN_STORAGE_KEY = 'access_token';

function consumeFragmentToken() {
  if (typeof window === 'undefined') return null;
  const hash = window.location.hash || '';
  if (!hash.startsWith('#')) return null;
  const params = new URLSearchParams(hash.slice(1));
  const token = params.get('access_token');
  if (!token) return null;
  // Strip the fragment so refresh doesn't keep replaying the token
  // (and so it's not visible in the URL bar for shoulder-surfers).
  const cleanUrl = window.location.pathname + window.location.search;
  window.history.replaceState({}, document.title, cleanUrl);
  return token;
}

export function useGitHubAuth() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [oauthEnabled, setOauthEnabled] = useState(false);

  // Effect 1: capture token from OAuth callback fragment on mount.
  useEffect(() => {
    const fragmentToken = consumeFragmentToken();
    if (fragmentToken) {
      try {
        localStorage.setItem(TOKEN_STORAGE_KEY, fragmentToken);
      } catch (_e) {
        // localStorage unavailable (private mode); token will live
        // only for this page lifetime — user can re-sign-in if they
        // refresh.
      }
    }
  }, []);

  // Effect 2: probe /api/auth/me with whatever token is stored.
  useEffect(() => {
    let cancelled = false;
    const token = (() => {
      try {
        return localStorage.getItem(TOKEN_STORAGE_KEY);
      } catch (_e) {
        return null;
      }
    })();

    if (!token) {
      setLoading(false);
      return;
    }

    fetch(`${API_URL}/api/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then((u) => {
        if (!cancelled) setUser(u);
      })
      .catch((status) => {
        if (status === 401) {
          try {
            localStorage.removeItem(TOKEN_STORAGE_KEY);
          } catch (_e) {}
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  // Effect 3: ask the backend whether OAuth is wired up.
  useEffect(() => {
    let cancelled = false;
    fetch(`${API_URL}/api/auth/github/status`)
      .then((r) => (r.ok ? r.json() : { enabled: false }))
      .then((body) => {
        if (!cancelled) setOauthEnabled(Boolean(body.enabled));
      })
      .catch(() => {
        if (!cancelled) setOauthEnabled(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const signIn = useCallback(() => {
    // Full-page navigation; we lose React state, but on return the
    // OAuth-callback fragment effect (1) re-establishes the session.
    window.location.href = `${API_URL}/api/auth/github/login`;
  }, []);

  const signOut = useCallback(() => {
    try {
      localStorage.removeItem(TOKEN_STORAGE_KEY);
    } catch (_e) {}
    // Reload so any WS / chat state that captured the old token is
    // dropped — cheaper than threading a sign-out signal everywhere.
    window.location.reload();
  }, []);

  return { user, loading, oauthEnabled, signIn, signOut };
}
