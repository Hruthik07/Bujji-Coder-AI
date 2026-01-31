import React, { useState } from 'react';
import './Composer.css';

function Composer({ onClose, onDiffsGenerated }) {
  const [query, setQuery] = useState('');
  const [files, setFiles] = useState('');
  const [context, setContext] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!query.trim() || isProcessing) return;

    setIsProcessing(true);
    setError(null);

    try {
      const response = await fetch('/api/composer', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: query.trim(),
          files: files.trim() ? files.split(',').map(f => f.trim()) : null,
          context: context.trim() || null
        })
      });

      const data = await response.json();

      if (data.success) {
        // Pass diffs to parent
        if (onDiffsGenerated) {
          onDiffsGenerated(data.diffs, data.file_diffs, data.response);
        }
        onClose();
      } else {
        setError(data.error || 'Failed to generate edits');
      }
    } catch (err) {
      setError(err.message || 'Network error');
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="composer-overlay" onClick={onClose}>
      <div className="composer-panel" onClick={(e) => e.stopPropagation()}>
        <div className="composer-header">
          <h2>✏️ Composer - Multi-File Editor</h2>
          <button className="composer-close" onClick={onClose}>✕</button>
        </div>

        <form onSubmit={handleSubmit} className="composer-form">
          <div className="composer-section">
            <label htmlFor="query">
              <strong>What would you like to change?</strong>
            </label>
            <textarea
              id="query"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g., Add error handling to all API endpoints, or Refactor the authentication system..."
              rows={4}
              required
              disabled={isProcessing}
            />
          </div>

          <div className="composer-section">
            <label htmlFor="files">
              <strong>Specific files (optional)</strong>
              <span className="hint">Comma-separated file paths. Leave empty to let AI decide.</span>
            </label>
            <input
              id="files"
              type="text"
              value={files}
              onChange={(e) => setFiles(e.target.value)}
              placeholder="e.g., app.py, utils.py, config.py"
              disabled={isProcessing}
            />
          </div>

          <div className="composer-section">
            <label htmlFor="context">
              <strong>Additional context (optional)</strong>
            </label>
            <textarea
              id="context"
              value={context}
              onChange={(e) => setContext(e.target.value)}
              placeholder="Any additional information that might help..."
              rows={3}
              disabled={isProcessing}
            />
          </div>

          {error && (
            <div className="composer-error">
              ⚠️ {error}
            </div>
          )}

          <div className="composer-actions">
            <button
              type="button"
              className="btn-cancel"
              onClick={onClose}
              disabled={isProcessing}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn-submit"
              disabled={isProcessing || !query.trim()}
            >
              {isProcessing ? '🔄 Generating...' : '✨ Generate Changes'}
            </button>
          </div>
        </form>

        <div className="composer-hints">
          <h4>💡 Tips:</h4>
          <ul>
            <li>Be specific about what you want to change</li>
            <li>Mention file names if you know them</li>
            <li>The AI will generate diffs for all affected files</li>
            <li>You can review and accept/reject changes per file</li>
          </ul>
        </div>
      </div>
    </div>
  );
}

export default Composer;






