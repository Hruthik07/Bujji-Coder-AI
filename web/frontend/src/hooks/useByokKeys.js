/**
 * useByokKeys
 *
 * BYOK ("Bring Your Own Key") credential hook.
 *
 * The deployed Bujji backend does not hold LLM API keys. Visitors paste
 * their own Anthropic / OpenAI / DeepSeek keys into the Settings modal;
 * those keys are persisted in this browser's localStorage and sent on
 * every chat request — as headers for REST calls and as query params
 * for the WebSocket handshake (browsers can't set arbitrary headers on
 * a WS handshake).
 *
 * Note: WebSocket connections snapshot the keys at open-time. If the
 * user updates keys after a chat is already streaming, the change
 * applies on next page reload (or the next time ChatPanel reopens its
 * WS). The Settings modal surfaces that note explicitly.
 */

import { useCallback, useMemo, useState } from 'react';

const STORAGE_KEY = 'bujji.byok.keys.v1';

const EMPTY = { anthropic: '', openai: '', deepseek: '' };

function readFromStorage() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return { ...EMPTY };
    const parsed = JSON.parse(raw);
    return {
      anthropic: parsed.anthropic || '',
      openai: parsed.openai || '',
      deepseek: parsed.deepseek || '',
    };
  } catch (_e) {
    return { ...EMPTY };
  }
}

export function useByokKeys() {
  const [keys, setKeys] = useState(readFromStorage);

  const saveKeys = useCallback((next) => {
    const normalized = {
      anthropic: (next.anthropic || '').trim(),
      openai: (next.openai || '').trim(),
      deepseek: (next.deepseek || '').trim(),
    };
    setKeys(normalized);
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(normalized));
    } catch (_e) {
      // localStorage may be unavailable (private mode, quota); silently continue.
    }
  }, []);

  const clearKeys = useCallback(() => {
    setKeys({ ...EMPTY });
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch (_e) {
      // ignore
    }
  }, []);

  const hasAny = !!(keys.anthropic || keys.openai || keys.deepseek);

  // Headers for REST calls (only present keys are sent).
  const headers = useMemo(() => {
    const h = {};
    if (keys.anthropic) h['X-Anthropic-Key'] = keys.anthropic;
    if (keys.openai) h['X-OpenAI-Key'] = keys.openai;
    if (keys.deepseek) h['X-DeepSeek-Key'] = keys.deepseek;
    return h;
  }, [keys]);

  // Query-string fragment for the WebSocket handshake URL.
  const wsParams = useMemo(() => {
    const p = new URLSearchParams();
    if (keys.anthropic) p.set('anthropic_key', keys.anthropic);
    if (keys.openai) p.set('openai_key', keys.openai);
    if (keys.deepseek) p.set('deepseek_key', keys.deepseek);
    return p.toString();
  }, [keys]);

  return { keys, saveKeys, clearKeys, hasAny, headers, wsParams };
}
