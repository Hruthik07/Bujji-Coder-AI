import React, { useState } from 'react';
import './ValidationPanel.css';

function ValidationPanel({ validationResults, onFileClick, onApplyAnyway, onCancel }) {
  const [expandedFiles, setExpandedFiles] = useState({});

  if (!validationResults || Object.keys(validationResults).length === 0) {
    return null;
  }

  const toggleFile = (filePath) => {
    setExpandedFiles(prev => ({
      ...prev,
      [filePath]: !prev[filePath]
    }));
  };

  const getSeverityCounts = (issues) => {
    const counts = { error: 0, warning: 0, info: 0 };
    issues.forEach(issue => {
      if (counts[issue.severity] !== undefined) {
        counts[issue.severity]++;
      }
    });
    return counts;
  };

  const hasErrors = Object.values(validationResults).some(
    result => result.issues && result.issues.some(issue => issue.severity === 'error')
  );

  const hasWarnings = Object.values(validationResults).some(
    result => result.issues && result.issues.some(issue => issue.severity === 'warning')
  );

  return (
    <div className="validation-panel">
      <div className="validation-header">
        <h3>⚠️ Validation Results</h3>
        <div className="validation-summary">
          {hasErrors && (
            <span className="summary-badge error">
              {Object.values(validationResults).reduce((sum, r) => 
                sum + (r.issues?.filter(i => i.severity === 'error').length || 0), 0
              )} Error(s)
            </span>
          )}
          {hasWarnings && (
            <span className="summary-badge warning">
              {Object.values(validationResults).reduce((sum, r) => 
                sum + (r.issues?.filter(i => i.severity === 'warning').length || 0), 0
              )} Warning(s)
            </span>
          )}
        </div>
      </div>

      <div className="validation-content">
        {Object.entries(validationResults).map(([filePath, result]) => {
          const issues = result.issues || [];
          const counts = getSeverityCounts(issues);
          const isExpanded = expandedFiles[filePath];

          return (
            <div key={filePath} className="validation-file">
              <div 
                className="validation-file-header"
                onClick={() => toggleFile(filePath)}
              >
                <span className="file-icon">{isExpanded ? '▼' : '▶'}</span>
                <span className="file-path">{filePath}</span>
                <div className="file-status">
                  {result.syntax_valid === false && (
                    <span className="status-badge error">Syntax Error</span>
                  )}
                  {result.type_check_passed === false && (
                    <span className="status-badge error">Type Error</span>
                  )}
                  {result.linter_passed === false && (
                    <span className="status-badge warning">Linter Issues</span>
                  )}
                  {counts.error > 0 && (
                    <span className="status-badge error">{counts.error} Error(s)</span>
                  )}
                  {counts.warning > 0 && (
                    <span className="status-badge warning">{counts.warning} Warning(s)</span>
                  )}
                  {counts.error === 0 && counts.warning === 0 && result.syntax_valid && (
                    <span className="status-badge success">✓ Valid</span>
                  )}
                </div>
              </div>

              {isExpanded && issues.length > 0 && (
                <div className="validation-issues">
                  {issues.map((issue, idx) => (
                    <div 
                      key={idx} 
                      className={`validation-issue ${issue.severity}`}
                      onClick={() => {
                        if (onFileClick && issue.line_number) {
                          onFileClick(filePath, issue.line_number);
                        }
                      }}
                    >
                      <div className="issue-header">
                        <span className={`issue-severity ${issue.severity}`}>
                          {issue.severity === 'error' ? '❌' : issue.severity === 'warning' ? '⚠️' : 'ℹ️'}
                        </span>
                        <span className="issue-location">
                          Line {issue.line_number}
                          {issue.column && `, Column ${issue.column}`}
                        </span>
                        {issue.rule && (
                          <span className="issue-rule">{issue.rule}</span>
                        )}
                      </div>
                      <div className="issue-message">{issue.message}</div>
                      {issue.fix_suggestion && (
                        <div className="issue-fix">
                          <strong>Fix:</strong> {issue.fix_suggestion}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>

      <div className="validation-actions">
        {hasErrors ? (
          <>
            <button className="btn-cancel" onClick={onCancel}>
              Cancel
            </button>
            <div className="validation-warning">
              ⚠️ Critical errors found. Please fix them before applying.
            </div>
          </>
        ) : hasWarnings ? (
          <>
            <button className="btn-apply-anyway" onClick={onApplyAnyway}>
              Apply Anyway
            </button>
            <button className="btn-cancel" onClick={onCancel}>
              Cancel
            </button>
          </>
        ) : (
          <button className="btn-apply" onClick={onApplyAnyway}>
            Apply Changes
          </button>
        )}
      </div>
    </div>
  );
}

export default ValidationPanel;
