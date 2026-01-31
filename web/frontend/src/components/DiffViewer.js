import React, { useState, useEffect } from 'react';
import './DiffViewer.css';
import ValidationPanel from './ValidationPanel';

function DiffViewer({ diff, onClose, onApply, onFileClick }) {
  const [viewMode, setViewMode] = useState('unified'); // 'unified' or 'side-by-side'
  const [validationResults, setValidationResults] = useState(null);
  const [validating, setValidating] = useState(false);
  const [filePath, setFilePath] = useState(null);
  
  const parseDiff = (diffText) => {
    const lines = diffText.split('\n');
    const hunks = [];
    let currentHunk = null;
    let currentFile = null;
    let oldFile = null;
    let newFile = null;

    lines.forEach((line, idx) => {
      if (line.startsWith('---')) {
        oldFile = line.substring(4).trim();
        if (oldFile.startsWith('a/')) oldFile = oldFile.substring(2);
        if (oldFile === '/dev/null') oldFile = null;
      } else if (line.startsWith('+++')) {
        newFile = line.substring(4).trim();
        if (newFile.startsWith('b/')) newFile = newFile.substring(2);
        currentFile = newFile || oldFile;
      } else if (line.startsWith('@@')) {
        if (currentHunk) {
          hunks.push(currentHunk);
        }
        // Parse hunk header for line numbers
        const match = line.match(/@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@/);
        currentHunk = {
          header: line,
          oldStart: match ? parseInt(match[1]) : 0,
          oldCount: match ? parseInt(match[2] || '1') : 0,
          newStart: match ? parseInt(match[3]) : 0,
          newCount: match ? parseInt(match[4] || '1') : 0,
          lines: []
        };
      } else if (currentHunk) {
        currentHunk.lines.push({
          type: line[0] === '+' ? 'add' : line[0] === '-' ? 'remove' : 'context',
          content: line.substring(1),
          original: line
        });
      }
    });

    if (currentHunk) {
      hunks.push(currentHunk);
    }

    return { file: currentFile, oldFile, newFile, hunks };
  };

  const renderSideBySide = (parsed) => {
    const leftLines = [];
    const rightLines = [];
    let leftLineNum = 0;
    let rightLineNum = 0;

    parsed.hunks.forEach((hunk) => {
      leftLineNum = hunk.oldStart;
      rightLineNum = hunk.newStart;

      hunk.lines.forEach((line) => {
        if (line.type === 'remove') {
          leftLines.push({
            lineNum: leftLineNum++,
            content: line.content,
            type: 'remove'
          });
          rightLines.push({
            lineNum: null,
            content: '',
            type: 'empty'
          });
        } else if (line.type === 'add') {
          leftLines.push({
            lineNum: null,
            content: '',
            type: 'empty'
          });
          rightLines.push({
            lineNum: rightLineNum++,
            content: line.content,
            type: 'add'
          });
        } else {
          // Context line
          leftLines.push({
            lineNum: leftLineNum++,
            content: line.content,
            type: 'context'
          });
          rightLines.push({
            lineNum: rightLineNum++,
            content: line.content,
            type: 'context'
          });
        }
      });
    });

    return { leftLines, rightLines };
  };

  const parsed = parseDiff(diff);

  // Extract file path from diff
  useEffect(() => {
    if (parsed.file) {
      setFilePath(parsed.file);
    }
  }, [parsed.file]);

  // Validate diff when it changes
  useEffect(() => {
    if (diff && filePath) {
      validateDiff();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [diff, filePath]);

  const validateDiff = async () => {
    setValidating(true);
    try {
      const response = await fetch('/api/diff/validate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          diff_text: diff,
          file_path: filePath
        })
      });
      const data = await response.json();
      if (data.validation_results) {
        setValidationResults(data.validation_results);
      }
    } catch (error) {
      console.error('Validation error:', error);
    } finally {
      setValidating(false);
    }
  };

  const handleFileClick = (filePath, lineNumber) => {
    if (onFileClick) {
      onFileClick(filePath, lineNumber);
    }
  };

  const handleApplyAnyway = () => {
    if (onApply) {
      onApply();
    }
  };

  const handleCancel = () => {
    if (onClose) {
      onClose();
    }
  };

  return (
    <div className="diff-viewer-overlay" onClick={onClose}>
      <div className="diff-viewer" onClick={(e) => e.stopPropagation()}>
        <div className="diff-header">
          <h3>📋 Diff Preview</h3>
          <div className="diff-header-controls">
            <div className="diff-view-toggle">
              <button
                className={viewMode === 'unified' ? 'active' : ''}
                onClick={() => setViewMode('unified')}
              >
                Unified
              </button>
              <button
                className={viewMode === 'side-by-side' ? 'active' : ''}
                onClick={() => setViewMode('side-by-side')}
              >
                Side-by-Side
              </button>
            </div>
            <div className="diff-actions">
              {validationResults && Object.values(validationResults).some(
                r => r.issues && r.issues.some(i => i.severity === 'error')
              ) ? (
                <button className="btn-apply" onClick={onApply} disabled title="Fix errors before applying">
                  ⚠️ Apply Changes (Errors Found)
                </button>
              ) : (
                <button className="btn-apply" onClick={onApply}>
                  ✅ Apply Changes
                </button>
              )}
              <button className="btn-close" onClick={onClose}>
                ✕ Close
              </button>
            </div>
          </div>
        </div>
        <div className="diff-content">
          {validating && (
            <div className="validation-loading">
              Validating code...
            </div>
          )}
          
          {validationResults && (
            <ValidationPanel
              validationResults={validationResults}
              onFileClick={handleFileClick}
              onApplyAnyway={handleApplyAnyway}
              onCancel={handleCancel}
            />
          )}

          {parsed.file && (
            <div className="diff-file-header">
              {parsed.oldFile && parsed.newFile && parsed.oldFile !== parsed.newFile ? (
                <>
                  <span className="file-old">{parsed.oldFile}</span>
                  <span className="file-arrow">→</span>
                  <span className="file-new">{parsed.newFile}</span>
                </>
              ) : (
                <span>File: {parsed.file}</span>
              )}
            </div>
          )}
          {viewMode === 'unified' ? (
            parsed.hunks.map((hunk, hunkIdx) => (
              <div key={hunkIdx} className="diff-hunk">
                <div className="hunk-header">{hunk.header}</div>
                <div className="hunk-lines">
                  {hunk.lines.map((line, lineIdx) => (
                    <div
                      key={lineIdx}
                      className={`diff-line ${line.type}`}
                    >
                      <span className="line-marker">
                        {line.type === 'add' ? '+' : line.type === 'remove' ? '-' : ' '}
                      </span>
                      <span className="line-content">{line.content}</span>
                    </div>
                  ))}
                </div>
              </div>
            ))
          ) : (
            (() => {
              const { leftLines, rightLines } = renderSideBySide(parsed);
              return (
                <div className="diff-side-by-side">
                  <div className="diff-side diff-side-left">
                    <div className="diff-side-header">
                      {parsed.oldFile || '/dev/null'}
                    </div>
                    <div className="diff-side-content">
                      {leftLines.map((line, idx) => (
                        <div key={idx} className={`diff-side-line ${line.type}`}>
                          <span className="line-number">
                            {line.lineNum !== null ? line.lineNum : ''}
                          </span>
                          <span className="line-content">{line.content}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                  <div className="diff-side diff-side-right">
                    <div className="diff-side-header">
                      {parsed.newFile || 'new file'}
                    </div>
                    <div className="diff-side-content">
                      {rightLines.map((line, idx) => (
                        <div key={idx} className={`diff-side-line ${line.type}`}>
                          <span className="line-number">
                            {line.lineNum !== null ? line.lineNum : ''}
                          </span>
                          <span className="line-content">{line.content}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              );
            })()
          )}
        </div>
      </div>
    </div>
  );
}

export default DiffViewer;
