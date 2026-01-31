import React, { useState, useEffect, useRef } from 'react';
import './App.css';
import ChatPanel from './components/ChatPanel';
import CodeEditor from './components/CodeEditor';
import FileTree from './components/FileTree';
import DiffViewer from './components/DiffViewer';
import MultiFileDiffViewer from './components/MultiFileDiffViewer';
import Composer from './components/Composer';
import PerformanceDashboard from './components/PerformanceDashboard';
import GitPanel from './components/GitPanel';
import RulesEditor from './components/RulesEditor';
import Terminal from './components/Terminal';
import StatusBar from './components/StatusBar';

function App() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [fileContent, setFileContent] = useState('');
  const [files, setFiles] = useState([]);
  const [diff, setDiff] = useState(null);
  const [multiFileDiffs, setMultiFileDiffs] = useState(null);
  const [fileDiffs, setFileDiffs] = useState([]);
  const [status, setStatus] = useState({ rag_enabled: false, rag_indexed: false });
  const [showDiff, setShowDiff] = useState(false);
  const [showMultiDiff, setShowMultiDiff] = useState(false);
  const [showComposer, setShowComposer] = useState(false);
  const [showPerformance, setShowPerformance] = useState(false);
  const [showGit, setShowGit] = useState(false);
  const [showRules, setShowRules] = useState(false);
  const [showTerminal, setShowTerminal] = useState(false);
  const [scrollToLine, setScrollToLine] = useState(null);

  useEffect(() => {
    // Load file tree on mount
    loadFiles();
    loadStatus();
  }, []);

  const loadFiles = async () => {
    try {
      const response = await fetch('/api/files?directory=.');
      const data = await response.json();
      if (data.items) {
        setFiles(data.items);
      }
    } catch (error) {
      console.error('Error loading files:', error);
    }
  };

  const loadStatus = async () => {
    try {
      const response = await fetch('/api/status');
      const data = await response.json();
      setStatus(data);
    } catch (error) {
      console.error('Error loading status:', error);
    }
  };

  const handleFileSelect = async (filePath, lineNumber = null) => {
    setSelectedFile(filePath);
    try {
      const response = await fetch('/api/files/read', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ file_path: filePath })
      });
      const data = await response.json();
      if (data.content) {
        setFileContent(data.content);
        // Store line number to scroll to (will be used by CodeEditor)
        if (lineNumber !== null) {
          setScrollToLine(lineNumber);
        }
      }
    } catch (error) {
      console.error('Error reading file:', error);
    }
  };

  const handleSaveFile = async (content) => {
    if (!selectedFile) return;
    
    try {
      const response = await fetch('/api/files/write', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          file_path: selectedFile,
          contents: content
        })
      });
      const data = await response.json();
      if (data.success) {
        setFileContent(content);
        loadFiles(); // Refresh file tree
      }
    } catch (error) {
      console.error('Error saving file:', error);
    }
  };

  const handleDiffGenerated = (diffText) => {
    setDiff(diffText);
    setShowDiff(true);
  };

  const handleApplyDiff = async () => {
    if (!diff) return;
    
    try {
      const response = await fetch('/api/diff/apply', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ diff_text: diff, dry_run: false })
      });
      const data = await response.json();
      if (data.success) {
        setShowDiff(false);
        setDiff(null);
        if (selectedFile) {
          handleFileSelect(selectedFile); // Reload file
        }
        loadFiles(); // Refresh file tree
      }
    } catch (error) {
      console.error('Error applying diff:', error);
    }
  };

  const handleComposerDiffs = (diffs, fileDiffsData, response) => {
    setMultiFileDiffs(diffs);
    setFileDiffs(fileDiffsData);
    setShowMultiDiff(true);
  };

  const handleApplyMultiDiff = async (combinedDiff, selectedFiles) => {
    try {
      const response = await fetch('/api/diff/apply', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ diff_text: combinedDiff, dry_run: false })
      });
      const data = await response.json();
      if (data.success) {
        setShowMultiDiff(false);
        setMultiFileDiffs(null);
        setFileDiffs([]);
        if (selectedFile) {
          handleFileSelect(selectedFile); // Reload file
        }
        loadFiles(); // Refresh file tree
        alert(`Successfully applied changes to ${selectedFiles.length} file(s)`);
      } else {
        alert(`Error applying changes: ${data.error || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('Error applying multi-file diff:', error);
      alert(`Error applying changes: ${error.message}`);
    }
  };

  return (
    <div className="app">
      <div className="app-header">
        <h1>🤖 AI Coding Assistant</h1>
        <div className="header-actions">
          <button
            onClick={() => setShowComposer(true)}
            className="btn-composer"
            title="Open Composer for multi-file editing"
          >
            ✏️ Composer
          </button>
          <button
            onClick={() => setShowGit(true)}
            className="btn-secondary"
            title="Open Git Panel"
          >
            🔀 Git
          </button>
          <button
            onClick={() => setShowRules(true)}
            className="btn-secondary"
            title="Edit .cursorrules"
          >
            📋 Rules
          </button>
          <button
            onClick={() => setShowPerformance(true)}
            className="btn-secondary"
            title="View Performance Dashboard"
          >
            📊 Performance
          </button>
          <button
            onClick={() => setShowTerminal(!showTerminal)}
            className="btn-secondary"
            title="Toggle Terminal"
          >
            💻 Terminal
          </button>
          <button onClick={loadStatus} className="btn-secondary">
            Refresh Status
          </button>
          {!status.rag_indexed && status.rag_enabled && (
            <button
              onClick={async () => {
                try {
                  await fetch('/api/index?force=false', { method: 'POST' });
                  loadStatus();
                } catch (error) {
                  console.error('Error indexing:', error);
                }
              }}
              className="btn-primary"
            >
              Index Codebase
            </button>
          )}
        </div>
      </div>

      <div className="app-body">
        <div className="sidebar">
          <FileTree
            files={files}
            onFileSelect={handleFileSelect}
            selectedFile={selectedFile}
            onRefresh={loadFiles}
          />
        </div>

        <div className="main-content">
          <div className="editor-container">
            <CodeEditor
              filePath={selectedFile}
              content={fileContent}
              onSave={handleSaveFile}
              language={selectedFile?.split('.').pop() || 'plaintext'}
              scrollToLine={scrollToLine}
              onScrollComplete={() => setScrollToLine(null)}
            />
          </div>

          <div className="chat-container">
            <ChatPanel
              onDiffGenerated={handleDiffGenerated}
              onFileRequest={handleFileSelect}
            />
          </div>
        </div>
      </div>

      {showDiff && diff && (
        <DiffViewer
          diff={diff}
          onClose={() => setShowDiff(false)}
          onApply={handleApplyDiff}
          onFileClick={handleFileSelect}
        />
      )}

      {showMultiDiff && multiFileDiffs && fileDiffs.length > 0 && (
        <MultiFileDiffViewer
          diffs={multiFileDiffs}
          fileDiffs={fileDiffs}
          onClose={() => {
            setShowMultiDiff(false);
            setMultiFileDiffs(null);
            setFileDiffs([]);
          }}
          onApply={handleApplyMultiDiff}
        />
      )}

      {showComposer && (
        <Composer
          onClose={() => setShowComposer(false)}
          onDiffsGenerated={handleComposerDiffs}
        />
      )}

      {showPerformance && (
        <PerformanceDashboard
          onClose={() => setShowPerformance(false)}
        />
      )}

      {showGit && (
        <GitPanel
          onClose={() => setShowGit(false)}
        />
      )}

      {showRules && (
        <RulesEditor
          onClose={() => setShowRules(false)}
        />
      )}

      {showTerminal && (
        <div className="terminal-panel-overlay" onClick={() => setShowTerminal(false)}>
          <div className="terminal-panel" onClick={(e) => e.stopPropagation()}>
            <div className="terminal-panel-header">
              <h3>Terminal</h3>
              <button
                className="terminal-close-btn"
                onClick={() => setShowTerminal(false)}
              >
                ✕
              </button>
            </div>
            <div className="terminal-panel-content">
              <Terminal workspacePath="." />
            </div>
          </div>
        </div>
      )}

      <StatusBar status={status} />
    </div>
  );
}

export default App;
