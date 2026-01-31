import React, { useState, useEffect } from 'react';
import './GitPanel.css';

function GitPanel({ onClose }) {
  const [status, setStatus] = useState(null);
  const [branches, setBranches] = useState(null);
  const [commitMessage, setCommitMessage] = useState('');
  const [isGeneratingMessage, setIsGeneratingMessage] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState({ staged: [], unstaged: [], untracked: [] });
  const [commitHistory, setCommitHistory] = useState([]);
  const [selectedDiffFile, setSelectedDiffFile] = useState(null);
  const [diffContent, setDiffContent] = useState('');
  const [newBranchName, setNewBranchName] = useState('');
  const [isCreatingBranch, setIsCreatingBranch] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadGitStatus();
    loadBranches();
    loadCommitHistory();
    
    // Poll for status updates every 3 seconds
    const interval = setInterval(() => {
      loadGitStatus();
    }, 3000);
    
    return () => clearInterval(interval);
  }, []);

  const loadGitStatus = async () => {
    try {
      const response = await fetch('/api/git/status');
      const data = await response.json();
      setStatus(data);
      setError(null);
    } catch (err) {
      setError('Failed to load git status');
      console.error('Error loading git status:', err);
    }
  };

  const loadBranches = async () => {
    try {
      const response = await fetch('/api/git/branches');
      const data = await response.json();
      setBranches(data);
    } catch (err) {
      console.error('Error loading branches:', err);
    }
  };

  const loadCommitHistory = async () => {
    try {
      const response = await fetch('/api/git/history?limit=10');
      const data = await response.json();
      setCommitHistory(data.commits || []);
    } catch (err) {
      console.error('Error loading commit history:', err);
    }
  };

  const handleStage = async (filePath) => {
    try {
      const response = await fetch('/api/git/stage', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ files: [filePath] })
      });
      const data = await response.json();
      if (data.success) {
        loadGitStatus();
      } else {
        setError(data.message || 'Failed to stage file');
      }
    } catch (err) {
      setError('Failed to stage file');
    }
  };

  const handleUnstage = async (filePath) => {
    try {
      const response = await fetch('/api/git/unstage', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ files: [filePath] })
      });
      const data = await response.json();
      if (data.success) {
        loadGitStatus();
      } else {
        setError(data.message || 'Failed to unstage file');
      }
    } catch (err) {
      setError('Failed to unstage file');
    }
  };

  const handleGenerateMessage = async () => {
    if (!status || status.staged.length === 0) {
      setError('No staged files to generate commit message for');
      return;
    }

    setIsGeneratingMessage(true);
    setError(null);

    try {
      const stagedFiles = status.staged.map(f => f.path);
      const response = await fetch('/api/git/commit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: '',
          generate_message: true,
          files: stagedFiles
        })
      });

      const data = await response.json();
      if (data.message) {
        setCommitMessage(data.message);
      } else {
        setError('Failed to generate commit message');
      }
    } catch (err) {
      setError('Failed to generate commit message');
    } finally {
      setIsGeneratingMessage(false);
    }
  };

  const handleCommit = async () => {
    if (!commitMessage.trim()) {
      setError('Commit message is required');
      return;
    }

    if (!status || status.staged.length === 0) {
      setError('No staged files to commit');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const stagedFiles = status.staged.map(f => f.path);
      const response = await fetch('/api/git/commit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: commitMessage.trim(),
          files: stagedFiles
        })
      });

      const data = await response.json();
      if (data.success) {
        setCommitMessage('');
        loadGitStatus();
        loadCommitHistory();
        setError(null);
      } else {
        setError(data.message || 'Failed to create commit');
      }
    } catch (err) {
      setError('Failed to create commit');
    } finally {
      setLoading(false);
    }
  };

  const handleSwitchBranch = async (branchName) => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/git/branch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          branch: branchName,
          create: false
        })
      });

      const data = await response.json();
      if (data.success) {
        loadGitStatus();
        loadBranches();
        setError(null);
      } else {
        setError(data.message || 'Failed to switch branch');
      }
    } catch (err) {
      setError('Failed to switch branch');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateBranch = async () => {
    if (!newBranchName.trim()) {
      setError('Branch name is required');
      return;
    }

    setIsCreatingBranch(true);
    setError(null);

    try {
      const response = await fetch('/api/git/branch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          branch: newBranchName.trim(),
          create: true
        })
      });

      const data = await response.json();
      if (data.success) {
        setNewBranchName('');
        loadGitStatus();
        loadBranches();
        setError(null);
      } else {
        setError(data.message || 'Failed to create branch');
      }
    } catch (err) {
      setError('Failed to create branch');
    } finally {
      setIsCreatingBranch(false);
    }
  };

  const handleViewDiff = async (filePath, isStaged) => {
    try {
      const response = await fetch(`/api/git/diff?file_path=${encodeURIComponent(filePath)}&staged=${isStaged}`);
      const data = await response.json();
      if (data.diff) {
        setSelectedDiffFile(filePath);
        setDiffContent(data.diff);
      }
    } catch (err) {
      console.error('Error loading diff:', err);
    }
  };

  const getStatusIcon = (statusCode) => {
    const icons = {
      'M': '✏️',
      'A': '➕',
      'D': '➖',
      'R': '🔄',
      'C': '📋',
      'U': '❓'
    };
    return icons[statusCode] || '📄';
  };

  const getStatusColor = (statusCode) => {
    const colors = {
      'M': '#fbbf24',
      'A': '#10b981',
      'D': '#ef4444',
      'R': '#3b82f6',
      'C': '#8b5cf6',
      'U': '#6b7280'
    };
    return colors[statusCode] || '#6b7280';
  };

  if (!status) {
    return (
      <div className="git-panel-overlay" onClick={onClose}>
        <div className="git-panel" onClick={(e) => e.stopPropagation()}>
          <div className="git-panel-header">
            <h2>Git</h2>
            <button className="git-panel-close" onClick={onClose}>×</button>
          </div>
          <div className="git-panel-content">
            <p>Loading git status...</p>
          </div>
        </div>
      </div>
    );
  }

  if (!status.is_repo) {
    return (
      <div className="git-panel-overlay" onClick={onClose}>
        <div className="git-panel" onClick={(e) => e.stopPropagation()}>
          <div className="git-panel-header">
            <h2>Git</h2>
            <button className="git-panel-close" onClick={onClose}>×</button>
          </div>
          <div className="git-panel-content">
            <p className="git-not-repo">Not a git repository</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="git-panel-overlay" onClick={onClose}>
      <div className="git-panel" onClick={(e) => e.stopPropagation()}>
        <div className="git-panel-header">
          <h2>Git</h2>
          <button className="git-panel-close" onClick={onClose}>×</button>
        </div>

        {error && (
          <div className="git-error">
            {error}
          </div>
        )}

        <div className="git-panel-content">
          {/* Branch Section */}
          <div className="git-section">
            <h3>Branch</h3>
            <div className="git-branch-controls">
              <select
                value={status.branch || ''}
                onChange={(e) => handleSwitchBranch(e.target.value)}
                className="git-branch-select"
                disabled={loading}
              >
                {branches && branches.branches.map(branch => (
                  <option key={branch.name} value={branch.name}>
                    {branch.name} {branch.is_current ? '(current)' : ''}
                  </option>
                ))}
              </select>
              <div className="git-create-branch">
                <input
                  type="text"
                  placeholder="New branch name"
                  value={newBranchName}
                  onChange={(e) => setNewBranchName(e.target.value)}
                  className="git-branch-input"
                />
                <button
                  onClick={handleCreateBranch}
                  disabled={isCreatingBranch || !newBranchName.trim()}
                  className="git-btn git-btn-primary"
                >
                  {isCreatingBranch ? 'Creating...' : 'Create'}
                </button>
              </div>
            </div>
          </div>

          {/* Status Section */}
          <div className="git-section">
            <h3>Changes</h3>
            
            {/* Staged Files */}
            {status.staged.length > 0 && (
              <div className="git-file-group">
                <h4>Staged Changes</h4>
                {status.staged.map((file, idx) => (
                  <div key={idx} className="git-file-item">
                    <span className="git-file-status" style={{ color: getStatusColor(file.status) }}>
                      {getStatusIcon(file.status)} {file.status}
                    </span>
                    <span className="git-file-path">{file.path}</span>
                    <div className="git-file-actions">
                      <button
                        onClick={() => handleViewDiff(file.path, true)}
                        className="git-btn git-btn-small"
                      >
                        View Diff
                      </button>
                      <button
                        onClick={() => handleUnstage(file.path)}
                        className="git-btn git-btn-small git-btn-danger"
                      >
                        Unstage
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Unstaged Files */}
            {status.unstaged.length > 0 && (
              <div className="git-file-group">
                <h4>Unstaged Changes</h4>
                {status.unstaged.map((file, idx) => (
                  <div key={idx} className="git-file-item">
                    <span className="git-file-status" style={{ color: getStatusColor(file.status) }}>
                      {getStatusIcon(file.status)} {file.status}
                    </span>
                    <span className="git-file-path">{file.path}</span>
                    <div className="git-file-actions">
                      <button
                        onClick={() => handleViewDiff(file.path, false)}
                        className="git-btn git-btn-small"
                      >
                        View Diff
                      </button>
                      <button
                        onClick={() => handleStage(file.path)}
                        className="git-btn git-btn-small git-btn-primary"
                      >
                        Stage
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Untracked Files */}
            {status.untracked.length > 0 && (
              <div className="git-file-group">
                <h4>Untracked Files</h4>
                {status.untracked.map((file, idx) => (
                  <div key={idx} className="git-file-item">
                    <span className="git-file-status" style={{ color: getStatusColor(file.status) }}>
                      {getStatusIcon(file.status)} {file.status}
                    </span>
                    <span className="git-file-path">{file.path}</span>
                    <div className="git-file-actions">
                      <button
                        onClick={() => handleStage(file.path)}
                        className="git-btn git-btn-small git-btn-primary"
                      >
                        Stage
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {status.staged.length === 0 && status.unstaged.length === 0 && status.untracked.length === 0 && (
              <p className="git-no-changes">No changes</p>
            )}
          </div>

          {/* Commit Section */}
          <div className="git-section">
            <h3>Commit</h3>
            <div className="git-commit-controls">
              <textarea
                value={commitMessage}
                onChange={(e) => setCommitMessage(e.target.value)}
                placeholder="Commit message..."
                className="git-commit-message"
                rows="3"
              />
              <div className="git-commit-buttons">
                <button
                  onClick={handleGenerateMessage}
                  disabled={isGeneratingMessage || status.staged.length === 0}
                  className="git-btn git-btn-secondary"
                >
                  {isGeneratingMessage ? 'Generating...' : 'Generate Message'}
                </button>
                <button
                  onClick={handleCommit}
                  disabled={loading || !commitMessage.trim() || status.staged.length === 0}
                  className="git-btn git-btn-primary"
                >
                  {loading ? 'Committing...' : 'Commit'}
                </button>
              </div>
            </div>
          </div>

          {/* Diff Preview */}
          {selectedDiffFile && diffContent && (
            <div className="git-section">
              <h3>Diff: {selectedDiffFile}</h3>
              <div className="git-diff-preview">
                <pre>{diffContent}</pre>
              </div>
              <button
                onClick={() => {
                  setSelectedDiffFile(null);
                  setDiffContent('');
                }}
                className="git-btn git-btn-small"
              >
                Close Diff
              </button>
            </div>
          )}

          {/* Commit History */}
          {commitHistory.length > 0 && (
            <div className="git-section">
              <h3>Recent Commits</h3>
              <div className="git-commit-history">
                {commitHistory.map((commit, idx) => (
                  <div key={idx} className="git-commit-item">
                    <div className="git-commit-hash">{commit.hash}</div>
                    <div className="git-commit-message-text">{commit.summary}</div>
                    <div className="git-commit-meta">
                      {commit.author} • {new Date(commit.date).toLocaleDateString()}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default GitPanel;
