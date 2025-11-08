import React, { useState, useCallback, useEffect } from 'react';
import {
  Box,
  Tabs,
  Tab,
  Typography,
  Button,
  IconButton,
  Tooltip
} from '@mui/material';
import {
  ViewCode,
  ViewQuilt,
  Settings
} from '@mui/icons-material';
import { BehaviorFileTree } from './BehaviorFileTree';
import { CodeEditor } from './CodeEditor';
import { BlockPropertyEditor } from './BlockEditor';
import { RecipeBuilder } from './RecipeBuilder';
import './BehaviorEditor.css';

interface BehaviorEditorProps {
  conversionId: string;
  className?: string;
}

interface SelectedFile {
  id: string;
  path: string;
  type: string;
}

export const BehaviorEditor: React.FC<BehaviorEditorProps> = ({
  conversionId,
  className = ''
}) => {
  const [selectedFile, setSelectedFile] = useState<SelectedFile | null>(null);
  const [isTreeCollapsed, setIsTreeCollapsed] = useState(false);
  const [editorMode, setEditorMode] = useState<'code' | 'visual'>('code');
  const [editorTab, setEditorTab] = useState(0);

  // Handle file selection from the tree
  const handleFileSelect = useCallback((fileId: string, filePath: string, fileType: string) => {
    setSelectedFile({ id: fileId, path: filePath, type: fileType });
    
    // Auto-detect editor mode based on file type
    if (fileType === 'block_behavior') {
      setEditorMode('visual');
      setEditorTab(0); // Block Properties tab
    } else if (fileType === 'recipe') {
      setEditorMode('visual');
      setEditorTab(1); // Recipe Builder tab
    } else {
      setEditorMode('code');
    }
  }, []);

  // Handle successful save
  const handleSave = useCallback(async (fileId: string, _content: string) => {
    // Optional: Add any post-save logic here
    console.log(`File ${fileId} saved successfully`);
    // Avoid unused variable warning
    void _content;
  }, []);

  // Handle content changes (for potential auto-save or change tracking)
  const handleContentChange = useCallback((_content: string) => {
    // Optional: Add change tracking logic here
    // console.log('Content changed:', _content.length, 'characters');
    // Avoid unused variable warning
    void _content;
  }, []);

  // Toggle file tree collapse
  const toggleTreeCollapse = () => {
    setIsTreeCollapsed(!isTreeCollapsed);
  };

  // Handle visual editor changes
  const handleBlockPropertiesChange = useCallback((properties: any) => {
    console.log('Block properties changed:', properties);
    // Here you would typically save to backend
  }, []);

  const handleRecipeChange = useCallback((recipe: any) => {
    console.log('Recipe changed:', recipe);
    // Here you would typically save to backend
  }, []);

  // Determine if visual editing is available for current file
  const isVisualEditingAvailable = () => {
    if (!selectedFile) return false;
    return ['block_behavior', 'recipe', 'loot_table'].includes(selectedFile.type);
  };

  // Mock data for recipe builder (in real app, this would come from API)
  const mockAvailableItems = [
    { id: 'minecraft:oak_planks', type: 'minecraft:item', name: 'Oak Planks', count: 1 },
    { id: 'minecraft:stick', type: 'minecraft:item', name: 'Stick', count: 1 },
    { id: 'minecraft:iron_ingot', type: 'minecraft:item', name: 'Iron Ingot', count: 1 },
    { id: 'minecraft:diamond', type: 'minecraft:item', name: 'Diamond', count: 1 },
  ];

  return (
    <div className={`behavior-editor ${className}`}>
      {/* Editor Mode Header */}
      <div className="editor-mode-header">
        <Typography variant="h6" sx={{ mb: 2 }}>
          {selectedFile ? `Editing: ${selectedFile.path}` : 'Behavior Editor'}
        </Typography>
        
        {selectedFile && isVisualEditingAvailable() && (
          <Box className="mode-toggle-buttons">
            <Button
              variant={editorMode === 'code' ? 'contained' : 'outlined'}
              startIcon={<ViewCode />}
              onClick={() => setEditorMode('code')}
              size="small"
            >
              Code Editor
            </Button>
            <Button
              variant={editorMode === 'visual' ? 'contained' : 'outlined'}
              startIcon={<ViewQuilt />}
              onClick={() => setEditorMode('visual')}
              size="small"
            >
              Visual Editor
            </Button>
          </Box>
        )}
      </div>

      <div className="behavior-editor-container">
        {/* File Tree Sidebar */}
        <div className={`file-tree-sidebar ${isTreeCollapsed ? 'collapsed' : ''}`}>
          <BehaviorFileTree
            conversionId={conversionId}
            onFileSelect={handleFileSelect}
            selectedFileId={selectedFile?.id}
          />
        </div>

        {/* Splitter/Toggle Button */}
        <div className="splitter">
          <button
            className="tree-toggle-button"
            onClick={toggleTreeCollapse}
            title={isTreeCollapsed ? 'Show file tree' : 'Hide file tree'}
          >
            {isTreeCollapsed ? '▶' : '◀'}
          </button>
        </div>

        {/* Editor Content */}
        <div className="editor-content-area">
          {selectedFile ? (
            <>
              {editorMode === 'code' ? (
                // Code Editor View
                <div className="code-editor-area">
                  <CodeEditor
                    fileId={selectedFile?.id || null}
                    filePath={selectedFile?.path || ''}
                    fileType={selectedFile?.type || ''}
                    onContentChange={handleContentChange}
                    onSave={handleSave}
                  />
                </div>
              ) : (
                // Visual Editor View
                <div className="visual-editor-area">
                  <Box sx={{ width: '100%', height: '100%' }}>
                    <Tabs 
                      value={editorTab} 
                      onChange={(_, newValue) => setEditorTab(newValue)}
                      sx={{ borderBottom: 1, borderColor: 'divider' }}
                    >
                      <Tab label="Block Properties" disabled={selectedFile.type !== 'block_behavior'} />
                      <Tab label="Recipe Builder" disabled={selectedFile.type !== 'recipe'} />
                      <Tab label="Loot Tables" disabled={selectedFile.type !== 'loot_table'} />
                      <Tab label="Event Editor" disabled />
                    </Tabs>
                    
                    {/* Tab Panels */}
                    <Box sx={{ py: 2, height: 'calc(100% - 48px)', overflow: 'auto' }}>
                      {editorTab === 0 && selectedFile.type === 'block_behavior' && (
                        <BlockPropertyEditor
                          onPropertiesChange={handleBlockPropertiesChange}
                          readOnly={false}
                        />
                      )}
                      
                      {editorTab === 1 && selectedFile.type === 'recipe' && (
                        <RecipeBuilder
                          availableItems={mockAvailableItems}
                          onRecipeChange={handleRecipeChange}
                        />
                      )}
                      
                      {editorTab === 2 && selectedFile.type === 'loot_table' && (
                        <Box sx={{ p: 2, textAlign: 'center' }}>
                          <Typography variant="body2" color="text.secondary">
                            Loot Table Editor coming soon...
                          </Typography>
                        </Box>
                      )}
                      
                      {editorTab === 3 && (
                        <Box sx={{ p: 2, textAlign: 'center' }}>
                          <Typography variant="body2" color="text.secondary">
                            Event Editor coming soon...
                          </Typography>
                        </Box>
                      )}
                    </Box>
                  </Box>
                </div>
              )}
            </>
          ) : (
            // No file selected
            <div className="no-file-selected">
              <Typography variant="h6" color="text.secondary" gutterBottom>
                No File Selected
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Select a file from the tree to start editing
              </Typography>
            </div>
          )}
        </div>
      </div>

      {/* Status Bar */}
      <div className="behavior-editor-status">
        <div className="status-left">
          {selectedFile ? (
            <>
              <span className="status-file-path">{selectedFile.path}</span>
              <span className="status-separator">•</span>
              <span className="status-file-type">{selectedFile.type}</span>
              <span className="status-separator">•</span>
              <span className="status-mode">{editorMode} mode</span>
            </>
          ) : (
            <span className="status-no-file">No file selected</span>
          )}
        </div>
        
        <div className="status-right">
          <span className="status-conversion-id">
            <span className="status-label">Conversion:</span>
            <span className="status-value">{conversionId}</span>
          </span>
          {isVisualEditingAvailable() && (
            <span className="status-visual-hint">
              <Tooltip title="Visual editing available for this file type">
                <IconButton size="small">
                  <ViewQuilt fontSize="small" />
                </IconButton>
              </Tooltip>
            </span>
          )}
        </div>
      </div>
    </div>
  );
};