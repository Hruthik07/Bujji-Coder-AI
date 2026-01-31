import React, { useState, useEffect, useRef } from 'react';
import Editor, { useMonaco } from '@monaco-editor/react';
import './CodeEditor.css';

function CodeEditor({ filePath, content, onSave, language, scrollToLine, onScrollComplete }) {
  const [editorContent, setEditorContent] = useState(content);
  const [isDirty, setIsDirty] = useState(false);
  const editorRef = useRef(null);
  const completionProviderRef = useRef(null);

  useEffect(() => {
    setEditorContent(content);
    setIsDirty(false);
  }, [content, filePath]);

  // Scroll to line when scrollToLine prop changes
  useEffect(() => {
    if (scrollToLine !== null && editorRef.current) {
      const editor = editorRef.current;
      const lineNumber = Math.max(1, Math.min(scrollToLine, editor.getModel()?.getLineCount() || 1));
      editor.revealLineInCenter(lineNumber);
      editor.setPosition({ lineNumber, column: 1 });
      if (onScrollComplete) {
        onScrollComplete();
      }
    }
  }, [scrollToLine, onScrollComplete]);

  const handleEditorChange = (value) => {
    setEditorContent(value || '');
    setIsDirty(true);
  };

  const handleSave = () => {
    if (onSave && isDirty) {
      onSave(editorContent);
      setIsDirty(false);
    }
  };

  const getLanguage = () => {
    if (!filePath) return 'plaintext';
    const ext = filePath.split('.').pop();
    const langMap = {
      'py': 'python',
      'js': 'javascript',
      'jsx': 'javascript',
      'ts': 'typescript',
      'tsx': 'typescript',
      'html': 'html',
      'css': 'css',
      'json': 'json',
      'md': 'markdown',
      'yaml': 'yaml',
      'yml': 'yaml'
    };
    return langMap[ext] || language || 'plaintext';
  };

  const setupAutocomplete = (editor, monaco) => {
    if (!filePath || !editor || !monaco) return;

    const lang = getLanguage();
    if (lang === 'plaintext') return;

    // Remove existing provider if any
    if (completionProviderRef.current) {
      completionProviderRef.current.dispose();
      completionProviderRef.current = null;
    }

    // Map our completion kinds to Monaco kinds
    const kindMap = {
      'function': monaco.languages.CompletionItemKind.Function,
      'class': monaco.languages.CompletionItemKind.Class,
      'variable': monaco.languages.CompletionItemKind.Variable,
      'keyword': monaco.languages.CompletionItemKind.Keyword,
      'snippet': monaco.languages.CompletionItemKind.Snippet,
      'text': monaco.languages.CompletionItemKind.Text
    };

    // Create completion provider
    const completionProvider = {
      provideCompletionItems: async (model, position) => {
        try {
          // Call completion API
          const response = await fetch('/api/completion', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              file_path: filePath,
              file_content: model.getValue(),
              cursor_line: position.lineNumber - 1, // 0-indexed
              cursor_column: position.column - 1,  // 0-indexed
              language: lang
            })
          });

          const data = await response.json();
          
          if (data.success && data.completions) {
            // Convert to Monaco format
            const word = model.getWordUntilPosition(position);
            const range = {
              startLineNumber: position.lineNumber,
              startColumn: word.startColumn,
              endLineNumber: position.lineNumber,
              endColumn: word.endColumn
            };

            const suggestions = data.completions.map(comp => ({
              label: comp.label,
              kind: kindMap[comp.kind] || monaco.languages.CompletionItemKind.Text,
              detail: comp.detail,
              documentation: comp.documentation ? { value: comp.documentation } : undefined,
              insertText: comp.insertText,
              range: range
            }));

            return { suggestions };
          }
        } catch (error) {
          console.error('Completion error:', error);
        }

        return { suggestions: [] };
      },
      triggerCharacters: ['.', '(', ' ', '\n']
    };

    // Register provider
    completionProviderRef.current = monaco.languages.registerCompletionItemProvider(
      lang,
      completionProvider
    );
  };

  const handleEditorDidMount = (editor, monaco) => {
    editorRef.current = editor;
    setupAutocomplete(editor, monaco);
  };

  return (
    <div className="code-editor-container">
      <div className="editor-header">
        <div className="editor-title">
          {filePath ? (
            <>
              <span className="file-icon">📄</span>
              <span className="file-name">{filePath}</span>
            </>
          ) : (
            <span className="no-file">No file selected</span>
          )}
        </div>
        {isDirty && filePath && (
          <button className="save-button" onClick={handleSave}>
            💾 Save
          </button>
        )}
      </div>
      <div className="editor-wrapper">
        <Editor
          height="100%"
          language={getLanguage()}
          value={editorContent}
          onChange={handleEditorChange}
          onMount={handleEditorDidMount}
          theme="vs-dark"
          options={{
            minimap: { enabled: true },
            fontSize: 14,
            wordWrap: 'on',
            automaticLayout: true,
            scrollBeyondLastLine: false,
            readOnly: !filePath,
            quickSuggestions: true,
            suggestOnTriggerCharacters: true,
            acceptSuggestionOnEnter: 'on',
            tabCompletion: 'on',
            wordBasedSuggestions: 'allDocuments'
          }}
        />
      </div>
    </div>
  );
}

export default CodeEditor;
