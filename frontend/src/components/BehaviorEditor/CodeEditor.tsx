import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Editor } from '@monaco-editor/react';
import type { editor } from 'monaco-editor';
import './CodeEditor.css';

interface BehaviorFile {
  id: string;
  conversion_id: string;
  file_path: string;
  file_type: string;
  content: string;
  created_at: string;
  updated_at: string;
}

interface CodeEditorProps {
  fileId: string | null;
  filePath: string;
  fileType: string;
  onContentChange?: (content: string) => void;
  onSave?: (fileId: string, content: string) => Promise<void>;
  readOnly?: boolean;
}

export const CodeEditor: React.FC<CodeEditorProps> = ({
  fileId,
  filePath,
  fileType,
  onContentChange,
  onSave,
  readOnly = false
}) => {
  const [content, setContent] = useState<string>('');
  const [originalContent, setOriginalContent] = useState<string>('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [lastSaved, setLastSaved] = useState<Date | null>(null);
  const editorRef = useRef<editor.IStandaloneCodeEditor | null>(null);

  // Check if content has unsaved changes
  const hasUnsavedChanges = content !== originalContent;

  // Determine the Monaco language based on file type and extension
  const getEditorLanguage = (fileType: string, filePath: string): string => {
    const extension = filePath.split('.').pop()?.toLowerCase();
    
    if (extension === 'json') return 'json';
    if (extension === 'js') return 'javascript';
    if (extension === 'ts') return 'typescript';
    if (extension === 'mcfunction') return 'plaintext'; // Custom Minecraft function files
    
    // Fallback based on behavior file type
    if (fileType === 'entity_behavior' || fileType === 'block_behavior' || fileType === 'recipe') {
      return 'json'; // Most behavior files are JSON
    }
    if (fileType === 'script') {
      return 'javascript';
    }
    
    return 'plaintext';
  };

  // Load file content when fileId changes
  useEffect(() => {
    const loadFileContent = async () => {
      if (!fileId) {
        setContent('');
        setOriginalContent('');
        setError(null);
        return;
      }

      setIsLoading(true);
      setError(null);

      try {
        const response = await fetch(`/api/v1/behaviors/${fileId}`);
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const fileData: BehaviorFile = await response.json();
        setContent(fileData.content);
        setOriginalContent(fileData.content);
        setLastSaved(new Date(fileData.updated_at));
      } catch (err) {
        console.error('Error loading file:', err);
        setError(err instanceof Error ? err.message : 'Failed to load file');
        setContent('');
        setOriginalContent('');
      } finally {
        setIsLoading(false);
      }
    };

    loadFileContent();
  }, [fileId]);

  // Handle content changes
  const handleContentChange = (value: string | undefined) => {
    const newContent = value || '';
    setContent(newContent);
    setSaveError(null);
    onContentChange?.(newContent);
  };

  // Save file content
  const handleSave = useCallback(async () => {
    if (!fileId || !hasUnsavedChanges || isSaving) return;

    setIsSaving(true);
    setSaveError(null);

    try {
      const response = await fetch(`/api/v1/behaviors/${fileId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ content }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const updatedFile: BehaviorFile = await response.json();
      setOriginalContent(content);
      setLastSaved(new Date(updatedFile.updated_at));
      
      if (onSave) {
        await onSave(fileId, content);
      }
    } catch (err) {
      console.error('Error saving file:', err);
      setSaveError(err instanceof Error ? err.message : 'Failed to save file');
    } finally {
      setIsSaving(false);
    }
  }, [fileId, hasUnsavedChanges, isSaving, content, onSave]);

  // Handle Ctrl+S keyboard shortcut
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key === 's') {
        event.preventDefault();
        handleSave();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [handleSave]);

  // Configure Monaco editor
  const handleEditorDidMount = (editor: editor.IStandaloneCodeEditor) => {
    editorRef.current = editor;
    
    // Configure editor options
    editor.updateOptions({
      minimap: { enabled: false },
      lineNumbers: 'on',
      renderWhitespace: 'selection',
      wordWrap: 'on',
      automaticLayout: true,
      scrollBeyondLastLine: false,
      fontSize: 14,
      fontFamily: '"Fira Code", "JetBrains Mono", "Monaco", "Menlo", "Ubuntu Mono", monospace',
      tabSize: 2,
      insertSpaces: true,
    });
  };

  // Show empty state when no file is selected
  if (!fileId) {
    return (
      <div className="code-editor">
        <div className="editor-header">
          <div className="file-info">
            <span className="file-name">No file selected</span>
          </div>
        </div>
        <div className="editor-empty">
          <div className="empty-content">
            <span className="empty-icon">📝</span>
            <h3>Select a file to start editing</h3>
            <p>Choose a behavior file from the tree on the left to view and edit its content.</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="code-editor">
      <div className="editor-header">
        <div className="file-info">
          <span className={`file-name ${hasUnsavedChanges ? 'modified' : ''}`}>
            {filePath}
            {hasUnsavedChanges && ' •'}
          </span>
          <span className="file-type-badge">{fileType}</span>
        </div>
        
        <div className="editor-actions">
          {lastSaved && (
            <span className="last-saved">
              Saved {lastSaved.toLocaleTimeString()}
            </span>
          )}
          
          {hasUnsavedChanges && !readOnly && (
            <button
              className="save-button"
              onClick={handleSave}
              disabled={isSaving}
              title="Save (Ctrl+S)"
            >
              {isSaving ? 'Saving...' : 'Save'}
            </button>
          )}
        </div>
      </div>

      {saveError && (
        <div className="save-error">
          <span className="error-icon">⚠️</span>
          <span>Failed to save: {saveError}</span>
          <button onClick={handleSave} disabled={isSaving}>
            Retry
          </button>
        </div>
      )}

      <div className="editor-content">
        {isLoading ? (
          <div className="editor-loading">
            <div className="loading-spinner"></div>
            <span>Loading file content...</span>
          </div>
        ) : error ? (
          <div className="editor-error">
            <span className="error-icon">❌</span>
            <h3>Failed to load file</h3>
            <p>{error}</p>
            <button onClick={() => window.location.reload()}>
              Retry
            </button>
          </div>
        ) : (
          <Editor
            height="100%"
            language={getEditorLanguage(fileType, filePath)}
            value={content}
            onChange={handleContentChange}
            onMount={handleEditorDidMount}
            options={{
              readOnly,
              theme: 'vs-dark',
            }}
            loading={
              <div className="editor-loading">
                <div className="loading-spinner"></div>
                <span>Loading editor...</span>
              </div>
            }
          />
        )}
      </div>

      {hasUnsavedChanges && !readOnly && (
        <div className="unsaved-indicator">
          <span className="indicator-dot"></span>
          <span>You have unsaved changes</span>
        </div>
      )}
    </div>
  );
};