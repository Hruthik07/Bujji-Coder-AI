import React, { useState, useEffect } from 'react';
import './RulesEditor.css';

function RulesEditor({ onClose }) {
  const [rulesContent, setRulesContent] = useState('');
  const [originalContent, setOriginalContent] = useState('');
  const [rulesInfo, setRulesInfo] = useState(null);
  const [preview, setPreview] = useState(null);
  const [validation, setValidation] = useState(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [showPreview, setShowPreview] = useState(false);

  useEffect(() => {
    loadRules();
  }, []);

  const loadRules = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch('/api/rules');
      const data = await response.json();
      setRulesContent(data.content || '');
      setOriginalContent(data.content || '');
      setRulesInfo(data.info);
    } catch (err) {
      setError('Failed to load rules');
      console.error('Error loading rules:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    try {
      const response = await fetch('/api/rules', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: rulesContent })
      });
      const data = await response.json();
      if (data.success) {
        setOriginalContent(rulesContent);
        setError(null);
        // Reload info
        loadRules();
      } else {
        setError(data.message || 'Failed to save rules');
      }
    } catch (err) {
      setError('Failed to save rules');
    } finally {
      setSaving(false);
    }
  };

  const handleValidate = async () => {
    setError(null);
    try {
      const response = await fetch('/api/rules/validate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: rulesContent })
      });
      const data = await response.json();
      setValidation(data);
      if (!data.valid) {
        setError(`Validation failed: ${data.errors.join(', ')}`);
      }
    } catch (err) {
      setError('Failed to validate rules');
    }
  };

  const handlePreview = async () => {
    setError(null);
    try {
      const response = await fetch('/api/rules/preview');
      const data = await response.json();
      setPreview(data);
      setShowPreview(true);
    } catch (err) {
      setError('Failed to load preview');
    }
  };

  const hasChanges = rulesContent !== originalContent;

  return (
    <div className="rules-editor-overlay" onClick={onClose}>
      <div className="rules-editor" onClick={(e) => e.stopPropagation()}>
        <div className="rules-editor-header">
          <h2>.cursorrules Editor</h2>
          <button className="rules-editor-close" onClick={onClose}>×</button>
        </div>

        {error && (
          <div className="rules-error">
            {error}
          </div>
        )}

        {validation && validation.warnings && validation.warnings.length > 0 && (
          <div className="rules-warning">
            <strong>Warnings:</strong>
            <ul>
              {validation.warnings.map((warning, idx) => (
                <li key={idx}>{warning}</li>
              ))}
            </ul>
          </div>
        )}

        <div className="rules-editor-content">
          {loading ? (
            <div className="rules-loading">Loading rules...</div>
          ) : (
            <>
              <div className="rules-info">
                {rulesInfo && (
                  <div className="rules-info-item">
                    <span>Status:</span>
                    <span>{rulesInfo.exists ? '✓ File exists' : '✗ File does not exist'}</span>
                  </div>
                )}
                {rulesInfo && rulesInfo.exists && (
                  <>
                    <div className="rules-info-item">
                      <span>Size:</span>
                      <span>{rulesInfo.size} bytes</span>
                    </div>
                    <div className="rules-info-item">
                      <span>Lines:</span>
                      <span>{rulesInfo.line_count}</span>
                    </div>
                  </>
                )}
              </div>

              <div className="rules-editor-section">
                <div className="rules-editor-toolbar">
                  <h3>Rules Content</h3>
                  <div className="rules-toolbar-actions">
                    <button
                      onClick={handleValidate}
                      className="rules-btn rules-btn-secondary"
                    >
                      Validate
                    </button>
                    <button
                      onClick={handlePreview}
                      className="rules-btn rules-btn-secondary"
                    >
                      Preview Prompt
                    </button>
                    <button
                      onClick={handleSave}
                      disabled={saving || !hasChanges}
                      className="rules-btn rules-btn-primary"
                    >
                      {saving ? 'Saving...' : 'Save'}
                    </button>
                  </div>
                </div>
                <textarea
                  value={rulesContent}
                  onChange={(e) => setRulesContent(e.target.value)}
                  className="rules-textarea"
                  placeholder="Enter your project-specific rules and guidelines here...

Example:
- Use TypeScript for all new files
- Follow ESLint configuration
- Use functional components in React
- Add JSDoc comments to all functions
- Use async/await instead of promises
..."
                  rows={20}
                />
                {hasChanges && (
                  <div className="rules-unsaved">
                    You have unsaved changes
                  </div>
                )}
              </div>

              {showPreview && preview && (
                <div className="rules-editor-section">
                  <div className="rules-editor-toolbar">
                    <h3>Prompt Preview</h3>
                    <button
                      onClick={() => setShowPreview(false)}
                      className="rules-btn rules-btn-small"
                    >
                      Close
                    </button>
                  </div>
                  <div className="rules-preview">
                    <div className="rules-preview-section">
                      <h4>Base Prompt</h4>
                      <pre>{preview.base_prompt}</pre>
                    </div>
                    {preview.has_rules && (
                      <div className="rules-preview-section">
                        <h4>Merged Prompt (with rules)</h4>
                        <pre>{preview.merged_prompt}</pre>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default RulesEditor;
