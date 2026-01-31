import React, { useState } from 'react';
import './MultiFileDiffViewer.css';

function MultiFileDiffViewer({ diffs, fileDiffs, onClose, onApply }) {
  const [selectedFiles, setSelectedFiles] = useState(new Set(fileDiffs.map(fd => fd.file)));
  const [expandedFiles, setExpandedFiles] = useState(new Set(fileDiffs.map(fd => fd.file)));

  const parseDiff = (diffText) => {
    const lines = diffText.split('\n');
    const files = [];
    let currentFile = null;
    let currentHunk = null;

    lines.forEach((line) => {
      if (line.startsWith('---')) {
        // Save previous file
        if (currentFile) {
          files.push(currentFile);
        }
        const oldPath = line.substring(4).trim();
        currentFile = {
          oldPath: oldPath,
          newPath: oldPath,
          hunks: []
        };
      } else if (line.startsWith('+++')) {
        if (currentFile) {
          currentFile.newPath = line.substring(4).trim();
        }
      } else if (line.startsWith('@@')) {
        if (currentFile && currentHunk) {
          currentFile.hunks.push(currentHunk);
        }
        if (currentFile) {
          currentHunk = {
            header: line,
            lines: []
          };
        }
      } else if (currentHunk) {
        currentHunk.lines.push({
          type: line[0] === '+' ? 'add' : line[0] === '-' ? 'remove' : 'context',
          content: line.substring(1),
          original: line
        });
      }
    });

    // Save last file and hunk
    if (currentHunk && currentFile) {
      currentFile.hunks.push(currentHunk);
    }
    if (currentFile) {
      files.push(currentFile);
    }

    return files;
  };

  const allDiffs = diffs.map(diff => parseDiff(diff)).flat();
  const fileMap = {};
  allDiffs.forEach(file => {
    const key = file.newPath || file.oldPath;
    if (!fileMap[key]) {
      fileMap[key] = file;
    } else {
      // Merge hunks if same file appears multiple times
      fileMap[key].hunks.push(...file.hunks);
    }
  });

  const handleToggleFile = (filePath) => {
    const newSet = new Set(selectedFiles);
    if (newSet.has(filePath)) {
      newSet.delete(filePath);
    } else {
      newSet.add(filePath);
    }
    setSelectedFiles(newSet);
  };

  const handleToggleExpand = (filePath) => {
    const newSet = new Set(expandedFiles);
    if (newSet.has(filePath)) {
      newSet.delete(filePath);
    } else {
      newSet.add(filePath);
    }
    setExpandedFiles(newSet);
  };

  const handleApplySelected = async () => {
    // Combine all selected file diffs
    const selectedDiffs = allDiffs.filter(file => {
      const key = file.newPath || file.oldPath;
      return selectedFiles.has(key);
    });

    if (selectedDiffs.length === 0) {
      alert('Please select at least one file to apply changes');
      return;
    }

    // Reconstruct diff text for selected files
    let combinedDiff = '';
    selectedDiffs.forEach(file => {
      combinedDiff += `--- a/${file.oldPath}\n+++ b/${file.newPath}\n`;
      file.hunks.forEach(hunk => {
        combinedDiff += hunk.header + '\n';
        hunk.lines.forEach(line => {
          combinedDiff += line.original + '\n';
        });
      });
    });

    if (onApply) {
      await onApply(combinedDiff, Array.from(selectedFiles));
    }
  };

  const handleSelectAll = () => {
    setSelectedFiles(new Set(fileDiffs.map(fd => fd.file)));
  };

  const handleDeselectAll = () => {
    setSelectedFiles(new Set());
  };

  return (
    <div className="multi-diff-overlay" onClick={onClose}>
      <div className="multi-diff-viewer" onClick={(e) => e.stopPropagation()}>
        <div className="multi-diff-header">
          <h3>📋 Multi-File Diff Preview</h3>
          <div className="multi-diff-actions">
            <button className="btn-select-all" onClick={handleSelectAll}>
              Select All
            </button>
            <button className="btn-deselect-all" onClick={handleDeselectAll}>
              Deselect All
            </button>
            <button
              className="btn-apply"
              onClick={handleApplySelected}
              disabled={selectedFiles.size === 0}
            >
              ✅ Apply Selected ({selectedFiles.size})
            </button>
            <button className="btn-close" onClick={onClose}>
              ✕ Close
            </button>
          </div>
        </div>

        <div className="multi-diff-content">
          <div className="multi-diff-summary">
            <strong>{fileDiffs.length}</strong> file(s) will be modified
          </div>

          {fileDiffs.map((fileInfo, idx) => {
            const filePath = fileInfo.file;
            const file = fileMap[filePath];
            const isSelected = selectedFiles.has(filePath);
            const isExpanded = expandedFiles.has(filePath);

            if (!file) return null;

            return (
              <div key={idx} className="multi-diff-file">
                <div className="file-header">
                  <label className="file-checkbox">
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => handleToggleFile(filePath)}
                    />
                    <span className="file-name">{filePath}</span>
                    <span className="file-stats">
                      ({fileInfo.hunks} hunk{fileInfo.hunks !== 1 ? 's' : ''})
                    </span>
                  </label>
                  <button
                    className="btn-expand"
                    onClick={() => handleToggleExpand(filePath)}
                  >
                    {isExpanded ? '▼' : '▶'}
                  </button>
                </div>

                {isExpanded && (
                  <div className="file-diff-content">
                    {file.hunks.map((hunk, hunkIdx) => (
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
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

export default MultiFileDiffViewer;






