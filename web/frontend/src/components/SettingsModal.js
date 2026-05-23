import React, { useState } from 'react';
import { useByokKeys } from '../hooks/useByokKeys';
import './SettingsModal.css';

const PROVIDERS = [
  {
    id: 'anthropic',
    label: 'Anthropic (Claude)',
    placeholder: 'sk-ant-...',
    helpUrl: 'https://console.anthropic.com/settings/keys',
  },
  {
    id: 'openai',
    label: 'OpenAI',
    placeholder: 'sk-...',
    helpUrl: 'https://platform.openai.com/api-keys',
  },
  {
    id: 'deepseek',
    label: 'DeepSeek',
    placeholder: 'sk-...',
    helpUrl: 'https://platform.deepseek.com/api_keys',
  },
];

function SettingsModal({ onClose }) {
  const { keys, saveKeys, clearKeys, hasAny } = useByokKeys();
  const [draft, setDraft] = useState(keys);
  const [revealed, setRevealed] = useState({});
  const [savedNotice, setSavedNotice] = useState(false);

  const updateField = (provider) => (e) => {
    setDraft({ ...draft, [provider]: e.target.value });
  };

  const toggleReveal = (provider) => {
    setRevealed({ ...revealed, [provider]: !revealed[provider] });
  };

  const handleSave = () => {
    saveKeys(draft);
    setSavedNotice(true);
  };

  const handleClear = () => {
    if (window.confirm('Remove all stored API keys from this browser?')) {
      clearKeys();
      setDraft({ anthropic: '', openai: '', deepseek: '' });
      setSavedNotice(false);
    }
  };

  return (
    <div className="settings-overlay" onClick={onClose}>
      <div
        className="settings-modal"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="settings-title"
      >
        <div className="settings-header">
          <h2 id="settings-title">API Key Settings</h2>
          <button
            className="settings-close"
            onClick={onClose}
            aria-label="Close settings"
          >
            ×
          </button>
        </div>

        <p className="settings-explainer">
          Bujji uses your own LLM API keys. They are stored only in your
          browser's localStorage and sent with each chat request. They are
          never logged or stored on our server. Add at least one provider
          to start chatting.
        </p>

        {PROVIDERS.map(({ id, label, placeholder, helpUrl }) => (
          <div className="settings-field" key={id}>
            <label htmlFor={`byok-${id}`}>
              {label}{' '}
              <a
                href={helpUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="settings-help-link"
              >
                Get key
              </a>
            </label>
            <div className="settings-input-row">
              <input
                id={`byok-${id}`}
                type={revealed[id] ? 'text' : 'password'}
                value={draft[id] || ''}
                onChange={updateField(id)}
                placeholder={placeholder}
                autoComplete="off"
                spellCheck="false"
              />
              <button
                type="button"
                className="settings-reveal"
                onClick={() => toggleReveal(id)}
              >
                {revealed[id] ? 'Hide' : 'Show'}
              </button>
            </div>
          </div>
        ))}

        {savedNotice && (
          <div className="settings-saved-notice">
            Saved. Reload the page (or close + reopen this tab) for the
            chat WebSocket to pick up the new keys.
          </div>
        )}

        <div className="settings-actions">
          <button
            className="settings-clear"
            onClick={handleClear}
            disabled={!hasAny}
          >
            Clear all
          </button>
          <button className="settings-save" onClick={handleSave}>
            Save
          </button>
        </div>
      </div>
    </div>
  );
}

export default SettingsModal;
