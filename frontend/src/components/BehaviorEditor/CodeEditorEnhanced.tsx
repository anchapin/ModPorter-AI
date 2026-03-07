import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Editor } from '@monaco-editor/react';
import type { editor } from 'monaco-editor';
import {
  Box,
  IconButton,
  Tooltip,
  Menu,
  MenuItem,
  ListItemIcon,
  ListItemText
} from '@mui/material';
import {
  Undo,
  Redo,
  Save,
  MoreVert,
  FileCopy,
  FileDownload,
  FileUpload
} from '@mui/icons-material';
import { useUndoRedo } from '../../hooks/useUndoRedo';
import { bedrockSchemaLoader } from '../../services/BedrockSchemaLoader';
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

interface CodeEditorEnhancedProps {
  fileId: string | null;
  filePath: string;
  fileType: string;
  onContentChange?: (content: string) => void;
  onSave?: (fileId: string, content: string) => Promise<void>;
  readOnly?: boolean;
}

export const CodeEditorEnhanced: React.FC<CodeEditorEnhancedProps> = ({
  fileId,
  filePath,
  fileType,
  onContentChange,
  onSave,
  readOnly = false
}) => {
  // Use undo/redo hook
  const {
    state: content,
    updateState: setEditorContent,
    undo,
    redo,
    canUndo,
    canRedo,
    clearHistory,
    cleanup
  } = useUndoRedo<string>('', {
    maxHistory: 100,
    enableDebounce: false // Let Monaco handle its own history
  });

  const [originalContent, setOriginalContent] = useState<string>('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [lastSaved, setLastSaved] = useState<Date | null>(null);
  const [cursorPosition, setCursorPosition] = useState({ line: 1, column: 1 });
  const [validationErrors, setValidationErrors] = useState<editor.IMarkerData[]>([]);
  const [menuAnchor, setMenuAnchor] = useState<null | HTMLElement>(null);

  const editorRef = useRef<editor.IStandaloneCodeEditor | null>(null);
  const monacoRef = useRef<typeof import('monaco-editor') | null>(null);

  // Check if content has unsaved changes
  const hasUnsavedChanges = content !== originalContent;

  // Determine Monaco language based on file type and extension
  const getEditorLanguage = (fileType: string, filePath: string): string => {
    const extension = filePath.split('.').pop()?.toLowerCase();

    if (extension === 'json') return 'json';
    if (extension === 'js') return 'javascript';
    if (extension === 'ts') return 'typescript';
    if (extension === 'mcfunction') return 'plaintext';

    if (['entity_behavior', 'block_behavior', 'recipe', 'loot_table'].includes(fileType)) {
      return 'json';
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
        setEditorContent('', 'Load empty state');
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
        setEditorContent(fileData.content, 'Load file content');
        setOriginalContent(fileData.content);
        setLastSaved(new Date(fileData.updated_at));
        clearHistory(); // Clear undo/redo history on file load
      } catch (err) {
        console.error('Error loading file:', err);
        setError(err instanceof Error ? err.message : 'Failed to load file');
        setEditorContent('', 'Error state');
        setOriginalContent('');
      } finally {
        setIsLoading(false);
      }
    };

    loadFileContent();
  }, [fileId, setEditorContent, clearHistory]);

  // Handle content changes
  const handleContentChange = useCallback((value: string | undefined) => {
    const newContent = value || '';
    setEditorContent(newContent, 'Content change');
    setSaveError(null);
    onContentChange?.(newContent);
  }, [setEditorContent, onContentChange]);

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

  // Undo/Redo handlers
  const handleUndo = useCallback(() => {
    undo();
  }, [undo]);

  const handleRedo = useCallback(() => {
    redo();
  }, [redo]);

  // Copy content to clipboard
  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(content);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  }, [content]);

  // Download content as file
  const handleDownload = useCallback(() => {
    const blob = new Blob([content], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filePath.split('/').pop() || 'file.json';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, [content, filePath]);

  // Upload file content
  const handleUpload = useCallback(() => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json,.js,.ts,.mcfunction';
    input.onchange = (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (file) {
        const reader = new FileReader();
        reader.onload = (e) => {
          const content = e.target?.result as string;
          setEditorContent(content, 'File upload');
        };
        reader.readAsText(file);
      }
    };
    input.click();
  }, [setEditorContent]);

  // Handle keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      // Ctrl+S / Cmd+S: Save
      if ((event.ctrlKey || event.metaKey) && event.key === 's') {
        event.preventDefault();
        handleSave();
      }
      // Ctrl+Z / Cmd+Z: Undo
      if ((event.ctrlKey || event.metaKey) && event.key === 'z' && !event.shiftKey) {
        event.preventDefault();
        handleUndo();
      }
      // Ctrl+Y / Cmd+Y / Ctrl+Shift+Z: Redo
      if (
        ((event.ctrlKey || event.metaKey) && event.key === 'y') ||
        ((event.ctrlKey || event.metaKey) && event.key === 'z' && event.shiftKey)
      ) {
        event.preventDefault();
        handleRedo();
      }
      // Ctrl+C / Cmd+C: Copy (if no selection in editor)
      if ((event.ctrlKey || event.metaKey) && event.key === 'c') {
        const selection = editorRef.current?.getSelection();
        if (!selection || selection.isEmpty()) {
          event.preventDefault();
          handleCopy();
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [handleSave, handleUndo, handleRedo, handleCopy]);

  // Configure Monaco editor
  const handleEditorWillMount = useCallback((monaco: typeof import('monaco-editor')) => {
    monacoRef.current = monaco;

    // Setup Bedrock schema loader
    bedrockSchemaLoader.setupAutoCompletion(monaco);

    // Configure JSON defaults
    monaco.languages.json.jsonDefaults.setDiagnosticsOptions({
      validate: true,
      allowComments: false,
      enableSchemaRequest: true,
      format: true,
      trailingCommas: 'error'
    });
  }, []);

  const handleEditorDidMount = useCallback((editor: editor.IStandaloneCodeEditor, monaco: typeof import('monaco-editor')) => {
    editorRef.current = editor;

    // Configure editor options
    editor.updateOptions({
      minimap: { enabled: true },
      lineNumbers: 'on',
      renderWhitespace: 'selection',
      wordWrap: 'on',
      automaticLayout: true,
      scrollBeyondLastLine: false,
      fontSize: 14,
      fontFamily: '"Fira Code", "JetBrains Mono", "Monaco", "Menlo", "Ubuntu Mono", monospace',
      tabSize: 2,
      insertSpaces: true,
      formatOnPaste: true,
      formatOnType: true,
      autoIndent: 'full',
      suggestOnTriggerCharacters: true,
      quickSuggestions: true,
      parameterHints: { enabled: true },
      folding: true,
      bracketPairColorization: { enabled: true }
    });

    // Track cursor position
    const cursorListener = editor.onDidChangeCursorPosition((e) => {
      setCursorPosition({
        line: e.position.lineNumber,
        column: e.position.column
      });
    });

    // JSON validation for Bedrock files
    const jsonExtension = filePath.split('.').pop()?.toLowerCase();
    if (jsonExtension === 'json') {
      const disposable = editor.onDidChangeModelContent(() => {
        // Use Monaco's JSON language features for validation
        const model = editor.getModel();
        if (model) {
          const markers = monaco.editor.getModelMarkers({ resource: model.uri });
          const jsonMarkers = markers.filter(m => m.source === 'json');
          setValidationErrors(jsonMarkers);
        }
      });

      validationDisposablesRef.current.push(disposable);
    }

    // Cleanup on unmount
    return () => {
      cursorListener.dispose();
    };
  }, [filePath]);

  const validationDisposablesRef = useRef<editor.IEditorDisposable[]>([]);

  // Cleanup disposables on unmount
  useEffect(() => {
    return () => {
      validationDisposablesRef.current.forEach(disposable => {
        disposable.dispose();
      });
      cleanup();
    };
  }, [cleanup]);

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
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            {validationErrors.length > 0 && (
              <Tooltip title={`${validationErrors.length} validation error(s)`}>
                <span className="validation-error-count">{validationErrors.length}</span>
              </Tooltip>
            )}

            {lastSaved && (
              <Tooltip title="Last saved time">
                <span className="last-saved">
                  Saved {lastSaved.toLocaleTimeString()}
                </span>
              </Tooltip>
            )}

            <Tooltip title="Undo (Ctrl+Z)">
              <span>
                <IconButton
                  size="small"
                  onClick={handleUndo}
                  disabled={!canUndo || readOnly}
                >
                  <Undo fontSize="small" />
                </IconButton>
              </span>
            </Tooltip>

            <Tooltip title="Redo (Ctrl+Y)">
              <IconButton
                size="small"
                onClick={handleRedo}
                disabled={!canRedo || readOnly}
              >
                <Redo fontSize="small" />
              </IconButton>
            </Tooltip>

            <Tooltip title="More options">
              <IconButton
                size="small"
                onClick={(e) => setMenuAnchor(e.currentTarget)}
              >
                <MoreVert fontSize="small" />
              </IconButton>
            </Tooltip>

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
          </Box>
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
            beforeMount={handleEditorWillMount}
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

      {/* Context Menu */}
      <Menu
        anchorEl={menuAnchor}
        open={Boolean(menuAnchor)}
        onClose={() => setMenuAnchor(null)}
      >
        <MenuItem onClick={() => { handleCopy(); setMenuAnchor(null); }} disabled={readOnly}>
          <ListItemIcon><FileCopy fontSize="small" /></ListItemIcon>
          <ListItemText>Copy All</ListItemText>
        </MenuItem>
        <MenuItem onClick={() => { handleDownload(); setMenuAnchor(null); }}>
          <ListItemIcon><FileDownload fontSize="small" /></ListItemIcon>
          <ListItemText>Download</ListItemText>
        </MenuItem>
        <MenuItem onClick={() => { handleUpload(); setMenuAnchor(null); }} disabled={readOnly}>
          <ListItemIcon><FileUpload fontSize="small" /></ListItemIcon>
          <ListItemText>Upload File</ListItemText>
        </MenuItem>
        <MenuItem onClick={() => { handleSave(); setMenuAnchor(null); }} disabled={!hasUnsavedChanges || readOnly}>
          <ListItemIcon><Save fontSize="small" /></ListItemIcon>
          <ListItemText>Save</ListItemText>
        </MenuItem>
      </Menu>

      {/* Status Bar */}
      <div className="editor-status-bar">
        <span>Ln {cursorPosition.line}, Col {cursorPosition.column}</span>
        <span>{content.length} characters</span>
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
