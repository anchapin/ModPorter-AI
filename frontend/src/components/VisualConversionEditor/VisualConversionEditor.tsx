import React, { useState, useCallback, useRef, useEffect } from 'react';
import Editor, { Monaco, OnMount, DiffEditor } from '@monaco-editor/react';
import type { editor } from 'monaco-editor';
import {
  Box,
  Typography,
  Paper,
  IconButton,
  Button,
  Tooltip,
  Divider,
  Chip,
  Slider,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
} from '@mui/material';
import {
  CompareArrows,
  Edit,
  Save,
  Undo,
  Redo,
  Visibility,
  VisibilityOff,
  Sync,
  Link as LinkIcon,
  LinkOff,
  Check,
  Close,
  Compare,
} from '@mui/icons-material';
import './VisualConversionEditor.css';

export interface CodeMapping {
  javaLine: number;
  bedrockLine: number;
  javaCode: string;
  bedrockCode: string;
}

export interface ConversionFile {
  id: string;
  name: string;
  path: string;
  javaContent: string;
  bedrockContent: string;
  mappings: CodeMapping[];
}

interface VisualConversionEditorProps {
  conversionId: string;
  files: ConversionFile[];
  onSave?: (fileId: string, content: string) => void;
  readOnly?: boolean;
}

type ViewMode = 'split' | 'java' | 'bedrock' | 'diff';
type DiffMode = 'inline' | 'side-by-side';

const VisualConversionEditor: React.FC<VisualConversionEditorProps> = ({
  conversionId,
  files,
  onSave,
  readOnly = false,
}) => {
  const [currentFileIndex, setCurrentFileIndex] = useState(0);
  const [viewMode, setViewMode] = useState<ViewMode>('split');
  const [diffMode, setDiffMode] = useState<DiffMode>('side-by-side');
  const [linkedHighlighting, setLinkedHighlighting] = useState(true);
  const [highlightedJavaLine, setHighlightedJavaLine] = useState<number | null>(null);
  const [highlightedBedrockLine, setHighlightedBedrockLine] = useState<number | null>(null);
  const [bedrockContent, setBedrockContent] = useState('');
  const [hasChanges, setHasChanges] = useState(false);
  const [originalBedrockContent, setOriginalBedrockContent] = useState('');
  const [javaEditor, setJavaEditor] = useState<editor.IStandaloneCodeEditor | null>(null);
  const [bedrockEditor, setBedrockEditor] = useState<editor.IStandaloneCodeEditor | null>(null);
  const [splitRatio, setSplitRatio] = useState(50);
  const [validationErrors, setValidationErrors] = useState<string[]>([]);
  const [changeCount, setChangeCount] = useState(0);
  const [hoveredMapping, setHoveredMapping] = useState<CodeMapping | null>(null);
  const [javaMonaco, setJavaMonaco] = useState<Monaco | null>(null);
  const [bedrockMonaco, setBedrockMonaco] = useState<Monaco | null>(null);
  const isDraggingRef = useRef(false);

  const currentFile = files[currentFileIndex];

  useEffect(() => {
    if (currentFile) {
      setBedrockContent(currentFile.bedrockContent);
      setOriginalBedrockContent(currentFile.bedrockContent);
      setHasChanges(false);
    }
  }, [currentFile]);

  const handleJavaEditorMount: OnMount = (editor, monaco) => {
    setJavaEditor(editor);
    setJavaMonaco(monaco);
    
    // Add hover provider for tooltips
    monaco.languages.registerHoverProvider('java', {
      provideHover: (model, position) => {
        if (!currentFile) return null;
        const lineNumber = position.lineNumber;
        const mapping = currentFile.mappings.find(m => m.javaLine === lineNumber);
        if (mapping) {
          return {
            range: new monaco.Range(lineNumber, 1, lineNumber, model.getLineMaxColumn(lineNumber)),
            contents: [
              { value: `**Bedrock Line ${mapping.bedrockLine}:**` },
              { value: '```javascript\n' + mapping.bedrockCode + '\n```' }
            ]
          };
        }
        return null;
      }
    });

    // Add mouse hover listener
    editor.onMouseMove((e) => {
      if (e.target.position) {
        const lineNumber = e.target.position.lineNumber;
        const mapping = currentFile?.mappings.find(m => m.javaLine === lineNumber);
        setHoveredMapping(mapping || null);
      } else {
        setHoveredMapping(null);
      }
    });
    
    editor.onMouseDown((e) => {
      if (e.target.position) {
        const lineNumber = e.target.position.lineNumber;
        setHighlightedJavaLine(lineNumber);
        
        if (linkedHighlighting && currentFile) {
          const mapping = currentFile.mappings.find(m => m.javaLine === lineNumber);
          if (mapping) {
            setHighlightedBedrockLine(mapping.bedrockLine);
            bedrockEditor?.revealLineInCenter(mapping.bedrockLine);
          }
        }
      }
    });

    // Configure Java syntax highlighting
    monaco.languages.register({ id: 'java' });
  };

  const handleBedrockEditorMount: OnMount = (editor, monaco) => {
    setBedrockEditor(editor);
    setBedrockMonaco(monaco);

    // Add JavaScript validation
    const handleValidation = () => {
      const model = editor.getModel();
      if (!model) return;
      
      const markers: editor.IMarkerData[] = [];
      const code = model.getValue();
      
      // Basic JavaScript syntax validation
      try {
        // Check for common syntax issues
        const lines = code.split('\n');
        lines.forEach((line, index) => {
          const lineNum = index + 1;
          // Check for unmatched brackets
          const openBrackets = (line.match(/[{[(]/g) || []).length;
          const closeBrackets = (line.match(/[}\])]/g) || []).length;
          
          // Check for missing semicolons (simplified check)
          const trimmed = line.trim();
          if (trimmed && 
              !trimmed.endsWith(';') && 
              !trimmed.endsWith('{') && 
              !trimmed.endsWith('}') &&
              !trimmed.endsWith(',') &&
              !trimmed.startsWith('//') &&
              !trimmed.startsWith('*') &&
              !trimmed.startsWith('/*') &&
              trimmed.length > 0) {
            // Only warn for complete statements (not inside blocks)
            const blockOpen = (code.substring(0, model.getOffsetAt({ lineNumber: lineNum, column: 1 })).match(/\{/g) || []).length;
            const blockClose = (code.substring(0, model.getOffsetAt({ lineNumber: lineNum, column: 1 })).match(/\}/g) || []).length;
            if (blockOpen === blockClose && !line.includes('=>')) {
              markers.push({
                severity: monaco.MarkerSeverity.Warning,
                message: 'Missing semicolon',
                startLineNumber: lineNum,
                startColumn: line.length + 1,
                endLineNumber: lineNum,
                endColumn: line.length + 1,
              });
            }
          }
        });
      } catch (e) {
        console.error('Validation error:', e);
      }
      
      monaco.editor.setModelMarkers(model, 'javascript-validator', markers);
      setValidationErrors(markers.map(m => m.message));
    };

    // Run validation on content change
    editor.onDidChangeModelContent(() => {
      handleValidation();
    });

    // Run initial validation
    handleValidation();
    
    editor.onMouseDown((e) => {
      if (e.target.position) {
        const lineNumber = e.target.position.lineNumber;
        setHighlightedBedrockLine(lineNumber);
        
        if (linkedHighlighting && currentFile) {
          const mapping = currentFile.mappings.find(m => m.bedrockLine === lineNumber);
          if (mapping) {
            setHighlightedJavaLine(mapping.javaLine);
            javaEditor?.revealLineInCenter(mapping.javaLine);
          }
        }
      }
    });

    // Configure JavaScript syntax highlighting
    monaco.languages.register({ id: 'javascript' });
  };

  const handleBedrockChange = useCallback((value: string | undefined) => {
    if (value !== undefined && value !== currentFile?.bedrockContent) {
      setBedrockContent(value);
      const hasChangesNow = value !== originalBedrockContent;
      setHasChanges(hasChangesNow);
      
      // Calculate change count (simple line-by-line diff)
      if (hasChangesNow) {
        const oldLines = originalBedrockContent.split('\n');
        const newLines = value.split('\n');
        let changes = 0;
        const maxLen = Math.max(oldLines.length, newLines.length);
        for (let i = 0; i < maxLen; i++) {
          if (oldLines[i] !== newLines[i]) changes++;
        }
        setChangeCount(changes);
      } else {
        setChangeCount(0);
      }
    }
  }, [originalBedrockContent, currentFile]);

  const handleSave = useCallback(() => {
    if (onSave && currentFile && hasChanges) {
      onSave(currentFile.id, bedrockContent);
      setOriginalBedrockContent(bedrockContent);
      setHasChanges(false);
    }
  }, [onSave, currentFile, bedrockContent, hasChanges]);

  const handleRevert = useCallback(() => {
    setBedrockContent(originalBedrockContent);
    setHasChanges(false);
  }, [originalBedrockContent]);

  const handleAcceptChanges = useCallback(() => {
    handleSave();
    setChangeCount(0);
  }, [handleSave]);

  const handleRejectChanges = useCallback(() => {
    handleRevert();
    setChangeCount(0);
  }, [handleRevert]);

  // Effect to update change count when original changes
  useEffect(() => {
    if (originalBedrockContent && bedrockContent) {
      const oldLines = originalBedrockContent.split('\n');
      const newLines = bedrockContent.split('\n');
      let changes = 0;
      const maxLen = Math.max(oldLines.length, newLines.length);
      for (let i = 0; i < maxLen; i++) {
        if (oldLines[i] !== newLines[i]) changes++;
      }
      setChangeCount(changes);
    }
  }, [originalBedrockContent, bedrockContent]);

  // Effect to handle line decorations for linked highlighting
  useEffect(() => {
    if (!javaEditor || !bedrockEditor || !javaMonaco || !bedrockMonaco) return;

    // Clear existing decorations
    const javaDecorations = javaEditor.getModel()?.getAllDecorations() || [];
    const bedrockDecorations = bedrockEditor.getModel()?.getAllDecorations() || [];
    
    const oldJavaDecorations = javaDecorations
      .filter(d => d.options.className?.includes('linked-highlight'))
      .map(d => d.id);
    const oldBedrockDecorations = bedrockDecorations
      .filter(d => d.options.className?.includes('linked-highlight'))
      .map(d => d.id);

    let newJavaDecorations: editor.IModelDeltaDecoration[] = [];
    let newBedrockDecorations: editor.IModelDeltaDecoration[] = [];

    // Highlight clicked Java line
    if (highlightedJavaLine !== null && linkedHighlighting) {
      newJavaDecorations.push({
        range: new javaMonaco.Range(highlightedJavaLine, 1, highlightedJavaLine, 1),
        options: {
          isWholeLine: true,
          className: 'linked-highlight-java',
          glyphMarginClassName: 'linked-highlight-glyph',
        }
      });
    }

    // Highlight corresponding Bedrock line
    if (highlightedBedrockLine !== null && linkedHighlighting) {
      newBedrockDecorations.push({
        range: new bedrockMonaco.Range(highlightedBedrockLine, 1, highlightedBedrockLine, 1),
        options: {
          isWholeLine: true,
          className: 'linked-highlight-bedrock',
          glyphMarginClassName: 'linked-highlight-glyph',
        }
      });
    }

    // Apply decorations
    javaEditor.deltaDecorations(oldJavaDecorations, newJavaDecorations);
    bedrockEditor.deltaDecorations(oldBedrockDecorations, newBedrockDecorations);

  }, [highlightedJavaLine, highlightedBedrockLine, linkedHighlighting, javaEditor, bedrockEditor, javaMonaco, bedrockMonaco]);

  const handlePreviousFile = useCallback(() => {
    setCurrentFileIndex((prev) => Math.max(0, prev - 1));
  }, []);

  const handleNextFile = useCallback(() => {
    setCurrentFileIndex((prev) => Math.min(files.length - 1, prev + 1));
  }, [files.length]);

  const handleSplitDrag = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    isDraggingRef.current = true;
    
    const handleMouseMove = (moveEvent: MouseEvent) => {
      if (isDraggingRef.current && moveEvent.target instanceof Element) {
        const container = moveEvent.target.closest('.visual-editor-split-container');
        if (container) {
          const rect = container.getBoundingClientRect();
          const ratio = ((moveEvent.clientX - rect.left) / rect.width) * 100;
          setSplitRatio(Math.min(80, Math.max(20, ratio)));
        }
      }
    };
    
    const handleMouseUp = () => {
      isDraggingRef.current = false;
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
    
    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
  }, []);

  const renderJavaEditor = () => (
    <Box className="editor-pane java-pane">
      <Box className="pane-header">
        <Typography variant="subtitle2" className="pane-title">
          Java (Source)
        </Typography>
        <Chip 
          label="Read Only" 
          size="small" 
          color="default" 
          variant="outlined"
          className="readonly-chip"
        />
      </Box>
      <Box className="editor-content">
        <Editor
          height="100%"
          language="java"
          value={currentFile?.javaContent || ''}
          onMount={handleJavaEditorMount}
          options={{
            readOnly: true,
            minimap: { enabled: false },
            lineNumbers: 'on',
            scrollBeyondLastLine: false,
            fontSize: 13,
            renderLineHighlight: 'line',
            automaticLayout: true,
          }}
        />
      </Box>
    </Box>
  );

  const renderBedrockEditor = () => (
    <Box className="editor-pane bedrock-pane">
      <Box className="pane-header">
        <Typography variant="subtitle2" className="pane-title">
          Bedrock (Target)
        </Typography>
        {!readOnly && (
          <Chip 
            label="Editable" 
            size="small" 
            color="primary" 
            variant="outlined"
            className="editable-chip"
          />
        )}
        {hasChanges && (
          <Chip 
            label="Modified" 
            size="small" 
            color="warning" 
            variant="outlined"
            className="modified-chip"
          />
        )}
      </Box>
      <Box className="editor-content">
        <Editor
          height="100%"
          language="javascript"
          value={bedrockContent}
          onChange={handleBedrockChange}
          onMount={handleBedrockEditorMount}
          options={{
            readOnly: readOnly,
            minimap: { enabled: false },
            lineNumbers: 'on',
            scrollBeyondLastLine: false,
            fontSize: 13,
            renderLineHighlight: 'line',
            automaticLayout: true,
          }}
        />
      </Box>
    </Box>
  );

  const renderDiffView = () => {
    if (diffMode === 'side-by-side') {
      return (
        <Box className="visual-editor-split-container diff-side-by-side">
          <Box className="editor-pane original-pane">
            <Box className="pane-header">
              <Typography variant="subtitle2" className="pane-title">
                Original
              </Typography>
              <Chip 
                label={`${originalBedrockContent.split('\n').length} lines`}
                size="small" 
                color="default" 
                variant="outlined"
                className="line-count-chip"
              />
            </Box>
            <Box className="editor-content">
              <Editor
                height="100%"
                language="javascript"
                value={originalBedrockContent}
                options={{
                  readOnly: true,
                  minimap: { enabled: false },
                  lineNumbers: 'on',
                  fontSize: 13,
                  automaticLayout: true,
                }}
              />
            </Box>
          </Box>
          <Box className="diff-divider" />
          <Box className="editor-pane modified-pane">
            <Box className="pane-header">
              <Typography variant="subtitle2" className="pane-title">
                Modified
              </Typography>
              {hasChanges && (
                <Chip 
                  label={`${changeCount} changes`}
                  size="small" 
                  color="warning" 
                  variant="outlined"
                  className="changes-chip"
                />
              )}
            </Box>
            <Box className="editor-content">
              <Editor
                height="100%"
                language="javascript"
                value={bedrockContent}
                onChange={handleBedrockChange}
                options={{
                  readOnly: readOnly,
                  minimap: { enabled: false },
                  lineNumbers: 'on',
                  fontSize: 13,
                  automaticLayout: true,
                }}
              />
            </Box>
          </Box>
          {/* Accept/Reject buttons */}
          {hasChanges && !readOnly && (
            <Box className="diff-actions">
              <Tooltip title="Accept Changes">
                <IconButton 
                  onClick={handleAcceptChanges}
                  color="success"
                  className="accept-btn"
                >
                  <Check />
                </IconButton>
              </Tooltip>
              <Tooltip title="Reject Changes">
                <IconButton 
                  onClick={handleRejectChanges}
                  color="error"
                  className="reject-btn"
                >
                  <Close />
                </IconButton>
              </Tooltip>
            </Box>
          )}
        </Box>
      );
    }

    // Inline diff using Monaco DiffEditor
    return (
      <Box className="editor-pane diff-inline-pane">
        <Box className="diff-inline-header">
          <Typography variant="subtitle2" className="pane-title">
            Diff View (Inline)
          </Typography>
          {hasChanges && (
            <Chip 
              label={`${changeCount} changes`}
              size="small" 
              color="warning" 
              variant="outlined"
              className="changes-chip"
            />
          )}
        </Box>
        <Box className="editor-content">
          <DiffEditor
            height="100%"
            language="javascript"
            original={originalBedrockContent}
            modified={bedrockContent}
            options={{
              readOnly: readOnly,
              minimap: { enabled: false },
              fontSize: 13,
              renderSideBySide: false,
              automaticLayout: true,
              enableSplitViewResizing: false,
            }}
          />
        </Box>
        {/* Accept/Reject buttons for inline mode */}
        {hasChanges && !readOnly && (
          <Box className="diff-actions-inline">
            <Tooltip title="Accept All Changes">
              <Button 
                onClick={handleAcceptChanges}
                color="success"
                variant="contained"
                startIcon={<Check />}
                size="small"
              >
                Accept All
              </Button>
            </Tooltip>
            <Tooltip title="Reject All Changes">
              <Button 
                onClick={handleRejectChanges}
                color="error"
                variant="outlined"
                startIcon={<Close />}
                size="small"
              >
                Reject All
              </Button>
            </Tooltip>
          </Box>
        )}
      </Box>
    );
  };

  if (!currentFile) {
    return (
      <Box className="visual-editor-empty">
        <Typography variant="h6">No files to display</Typography>
        <Typography variant="body2" color="text.secondary">
          Upload a mod to see the conversion comparison
        </Typography>
      </Box>
    );
  }

  return (
    <Box className="visual-conversion-editor">
      {/* Toolbar */}
      <Paper className="editor-toolbar" elevation={1}>
        <Box className="toolbar-section file-navigation">
          <Tooltip title="Previous file">
            <span>
              <IconButton 
                onClick={handlePreviousFile} 
                disabled={currentFileIndex === 0}
                size="small"
              >
                <Sync className="rotate-180" />
              </IconButton>
            </span>
          </Tooltip>
          <FormControl size="small" className="file-select">
            <Select
              value={currentFileIndex}
              onChange={(e) => setCurrentFileIndex(Number(e.target.value))}
              displayEmpty
            >
              {files.map((file, index) => (
                <MenuItem key={file.id} value={index}>
                  {file.name}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <Tooltip title="Next file">
            <span>
              <IconButton 
                onClick={handleNextFile} 
                disabled={currentFileIndex === files.length - 1}
                size="small"
              >
                <Sync />
              </IconButton>
            </span>
          </Tooltip>
        </Box>

        <Divider orientation="vertical" flexItem className="toolbar-divider" />

        <Box className="toolbar-section view-controls">
          <Tooltip title="Split View">
            <IconButton 
              onClick={() => setViewMode('split')}
              className={viewMode === 'split' ? 'active' : ''}
              size="small"
            >
              <CompareArrows />
            </IconButton>
          </Tooltip>
          <Tooltip title="Java Only">
            <IconButton 
              onClick={() => setViewMode('java')}
              className={viewMode === 'java' ? 'active' : ''}
              size="small"
            >
              <Visibility />
            </IconButton>
          </Tooltip>
          <Tooltip title="Bedrock Only">
            <IconButton 
              onClick={() => setViewMode('bedrock')}
              className={viewMode === 'bedrock' ? 'active' : ''}
              size="small"
            >
              <VisibilityOff />
            </IconButton>
          </Tooltip>
          <Tooltip title="Diff View">
            <IconButton 
              onClick={() => setViewMode('diff')}
              className={viewMode === 'diff' ? 'active' : ''}
              size="small"
            >
              <Compare />
            </IconButton>
          </Tooltip>
        </Box>

        {viewMode === 'diff' && (
          <Box className="toolbar-section diff-mode-controls">
            <FormControl size="small">
              <InputLabel>Diff Mode</InputLabel>
              <Select
                value={diffMode}
                label="Diff Mode"
                onChange={(e) => setDiffMode(e.target.value as DiffMode)}
              >
                <MenuItem value="side-by-side">Side by Side</MenuItem>
                <MenuItem value="inline">Inline</MenuItem>
              </Select>
            </FormControl>
          </Box>
        )}

        <Divider orientation="vertical" flexItem className="toolbar-divider" />

        <Box className="toolbar-section link-controls">
          <Tooltip title={linkedHighlighting ? 'Disable Linked Highlighting' : 'Enable Linked Highlighting'}>
            <IconButton 
              onClick={() => setLinkedHighlighting(!linkedHighlighting)}
              className={linkedHighlighting ? 'active' : ''}
              size="small"
            >
              {linkedHighlighting ? <LinkIcon /> : <LinkOff />}
            </IconButton>
          </Tooltip>
        </Box>

        <Box className="toolbar-section split-slider">
          <Typography variant="caption" className="slider-label">
            Split:
          </Typography>
          <Slider
            value={splitRatio}
            onChange={(_, value) => setSplitRatio(value as number)}
            min={20}
            max={80}
            size="small"
            className="split-slider-control"
          />
        </Box>

        <Box className="toolbar-section actions">
          {!readOnly && (
            <>
              <Tooltip title="Revert Changes">
                <span>
                  <IconButton 
                    onClick={handleRevert} 
                    disabled={!hasChanges}
                    size="small"
                  >
                    <Undo />
                  </IconButton>
                </span>
              </Tooltip>
              <Tooltip title="Save Changes">
                <span>
                  <IconButton 
                    onClick={handleSave} 
                    disabled={!hasChanges}
                    size="small"
                    color="primary"
                  >
                    <Save />
                  </IconButton>
                </span>
              </Tooltip>
            </>
          )}
        </Box>
      </Paper>

      {/* Editor Area */}
      <Box className="editor-area">
        {viewMode === 'split' && (
          <Box className="visual-editor-split-container">
            <Box 
              className="java-pane-wrapper"
              style={{ width: `${splitRatio}%` }}
            >
              {renderJavaEditor()}
            </Box>
            <Box 
              className="split-handle"
              onMouseDown={handleSplitDrag}
            >
              <Box className="split-handle-line" />
            </Box>
            <Box 
              className="bedrock-pane-wrapper"
              style={{ width: `${100 - splitRatio}%` }}
            >
              {renderBedrockEditor()}
            </Box>
          </Box>
        )}

        {viewMode === 'java' && renderJavaEditor()}
        
        {viewMode === 'bedrock' && renderBedrockEditor()}

        {viewMode === 'diff' && renderDiffView()}
      </Box>

      {/* Status Bar */}
      <Paper className="editor-status-bar" elevation={2}>
        <Box className="status-section">
          <Typography variant="caption">
            File: {currentFile.path}
          </Typography>
        </Box>
        <Box className="status-section">
          <Typography variant="caption">
            Mappings: {currentFile.mappings.length}
          </Typography>
        </Box>
        {highlightedJavaLine && (
          <Box className="status-section highlight-info">
            <Typography variant="caption">
              Java Line: {highlightedJavaLine} → Bedrock Line: {highlightedBedrockLine || 'N/A'}
            </Typography>
          </Box>
        )}
        {hasChanges && (
          <Box className="status-section changes-indicator">
            <Typography variant="caption" color="warning.main">
              Unsaved changes
            </Typography>
          </Box>
        )}
      </Paper>
    </Box>
  );
};

export default VisualConversionEditor;
