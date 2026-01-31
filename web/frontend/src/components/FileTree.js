import React, { useState, useEffect } from 'react';
import './FileTree.css';

function FileTree({ files, onFileSelect, selectedFile, onRefresh }) {
  const [expanded, setExpanded] = useState({});
  const [gitStatus, setGitStatus] = useState(null);

  useEffect(() => {
    loadGitStatus();
    // Poll for git status updates every 5 seconds
    const interval = setInterval(loadGitStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  const loadGitStatus = async () => {
    try {
      const response = await fetch('/api/git/status');
      const data = await response.json();
      if (data.is_repo) {
        setGitStatus(data);
      }
    } catch (err) {
      // Silently fail if git is not available
      setGitStatus(null);
    }
  };

  const getGitStatusForFile = (filePath) => {
    if (!gitStatus) return null;
    
    // Check staged files
    const staged = gitStatus.staged.find(f => f.path === filePath);
    if (staged) return { status: staged.status, type: 'staged' };
    
    // Check unstaged files
    const unstaged = gitStatus.unstaged.find(f => f.path === filePath);
    if (unstaged) return { status: unstaged.status, type: 'unstaged' };
    
    // Check untracked files
    const untracked = gitStatus.untracked.find(f => f.path === filePath);
    if (untracked) return { status: untracked.status, type: 'untracked' };
    
    return null;
  };

  const getGitStatusIcon = (fileStatus) => {
    if (!fileStatus) return null;
    
    const icons = {
      'M': '✏️',
      'A': '➕',
      'D': '➖',
      'R': '🔄',
      'C': '📋',
      'U': '❓'
    };
    
    const icon = icons[fileStatus.status] || '📄';
    const color = fileStatus.type === 'staged' ? '#10b981' : 
                  fileStatus.type === 'unstaged' ? '#fbbf24' : '#6b7280';
    
    return (
      <span 
        className="git-status-icon" 
        style={{ color, marginLeft: '4px' }}
        title={`${fileStatus.type}: ${fileStatus.status}`}
      >
        {icon}
      </span>
    );
  };

  const toggleExpand = (path) => {
    setExpanded(prev => ({
      ...prev,
      [path]: !prev[path]
    }));
  };

  const getFileIcon = (item) => {
    if (item.type === 'directory') {
      return expanded[item.path] ? '📂' : '📁';
    }
    const ext = item.name.split('.').pop();
    const iconMap = {
      'py': '🐍',
      'js': '📜',
      'jsx': '⚛️',
      'ts': '📘',
      'tsx': '⚛️',
      'html': '🌐',
      'css': '🎨',
      'json': '📋',
      'md': '📝',
      'txt': '📄'
    };
    return iconMap[ext] || '📄';
  };

  const renderItem = (item, level = 0) => {
    const isSelected = selectedFile === item.path;
    const isExpanded = expanded[item.path];
    const hasChildren = item.type === 'directory';

    return (
      <div key={item.path}>
        <div
          className={`tree-item ${isSelected ? 'selected' : ''}`}
          style={{ paddingLeft: `${level * 20 + 10}px` }}
          onClick={() => {
            if (hasChildren) {
              toggleExpand(item.path);
            } else {
              onFileSelect(item.path);
            }
          }}
        >
          <span className="tree-icon">
            {hasChildren ? (isExpanded ? '▼' : '▶') : ''}
          </span>
          <span className="file-icon">{getFileIcon(item)}</span>
          <span className="file-name">{item.name}</span>
          {!hasChildren && getGitStatusIcon(getGitStatusForFile(item.path))}
        </div>
        {hasChildren && isExpanded && (
          <div className="tree-children">
            {files
              .filter(f => f.path.startsWith(item.path + '/') && f.path.split('/').length === item.path.split('/').length + 1)
              .map(child => renderItem(child, level + 1))}
          </div>
        )}
      </div>
    );
  };

  const rootItems = files.filter(item => {
    const parts = item.path.split('/');
    return parts.length === 1 || (parts.length === 2 && parts[0] === '.');
  });

  return (
    <div className="file-tree">
      <div className="tree-header">
        <h3>📁 Files</h3>
        <button className="refresh-button" onClick={onRefresh} title="Refresh">
          🔄
        </button>
      </div>
      <div className="tree-content">
        {rootItems.length === 0 ? (
          <div className="tree-empty">No files found</div>
        ) : (
          rootItems.map(item => renderItem(item))
        )}
      </div>
    </div>
  );
}

export default FileTree;
