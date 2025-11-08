import React, { useState, useCallback, useEffect } from 'react';
import {
  Box,
  Tabs,
  Tab,
  Typography,
  Button,
  IconButton,
  Tooltip,
  LinearProgress,
  Alert,
  Snackbar,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Divider,
  Chip,
} from '@mui/material';
import {
  ViewCode,
  ViewQuilt,
  Settings,
  Download,
  Save,
  Refresh,
  Add,
  CheckCircle,
  Error as ErrorIcon,
} from '@mui/icons-material';
import { BehaviorFileTree } from './BehaviorFileTree';
import { CodeEditor } from './CodeEditor';
import { BlockPropertyEditor } from './BlockEditor';
import { RecipeBuilder } from './RecipeBuilder';
import { LootTableEditor } from './LootTableEditor';
import { LogicBuilder } from './LogicBuilder';
import { TemplateSelector } from './TemplateSelector/TemplateSelector';
import { behaviorExportAPI } from '../../services/api';
import { BehaviorTemplate } from '../../services/api';
import {
  useApplyBehaviorTemplate,
} from '../../hooks/useBehaviorQueries';
import { ErrorBoundary } from '../common/ErrorBoundary';
import { LoadingWrapper, SaveLoading } from '../common/LoadingWrapper';
import { useUIState, useAsyncOperation } from '../../hooks/useUIState';
import ExportManager from '../ExportManager/ExportManager';
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
  
  // Loading and error states
  const [isLoading, setIsLoading] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  
  // Template integration state
  const [showTemplateDialog, setShowTemplateDialog] = useState(false);
  const [templateDialogTab, setTemplateDialogTab] = useState(0);
  const [currentTemplate, setCurrentTemplate] = useState<BehaviorTemplate | null>(null);
  
  // State management
  const [showExportDialog, setShowExportDialog] = useState(false);
  
  // Enhanced UI state hooks
  const { loading, error: uiError, setError: setUIError, clearError: clearUIError, toast } = useUIState();
  
  // React Query hooks
  const applyTemplateMutation = useApplyBehaviorTemplate();

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

  // Handle successful save with loading states
  const handleSave = useCallback(async (fileId: string, content: string) => {
    setIsLoading(true);
    setLocalError(null);
    
    try {
      // Here you would typically save to backend API
      console.log(`File ${fileId} saved successfully`);
      setSuccessMessage('File saved successfully');
      
      // Auto-hide success message after 3 seconds
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to save file';
      setLocalError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Handle content changes with debounced auto-save
  const handleContentChange = useCallback((content: string) => {
    // Optional: Add debounced auto-save logic here
    console.log('Content changed:', content.length, 'characters');
    // For now, we just track changes
  }, []);

  // Toggle file tree collapse
  const toggleTreeCollapse = () => {
    setIsTreeCollapsed(!isTreeCollapsed);
  };

  // Handle visual editor changes with API integration
  const handleBlockPropertiesChange = useCallback(async (properties: any) => {
    setIsLoading(true);
    setLocalError(null);
    
    try {
      // Here you would save to backend API
      console.log('Block properties changed:', properties);
      setSuccessMessage('Block properties updated');
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to save block properties';
      setLocalError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const handleRecipeChange = useCallback(async (recipe: any) => {
    setIsLoading(true);
    setLocalError(null);
    
    try {
      // Here you would save to backend API
      console.log('Recipe changed:', recipe);
      setSuccessMessage('Recipe updated');
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to save recipe';
      setLocalError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Template handlers
  const handleTemplateSelect = useCallback((template: BehaviorTemplate) => {
    setCurrentTemplate(template);
  }, []);

  const handleTemplateApply = useCallback((template: BehaviorTemplate) => {
    if (!selectedFile) {
      setError('Please select a file before applying a template');
      return;
    }

    applyTemplateMutation.mutate({
      template_id: template.id,
      conversion_id: conversionId,
      file_path: selectedFile.path,
    }, {
      onSuccess: () => {
        setSuccessMessage(`Template "${template.name}" applied successfully`);
        setShowTemplateDialog(false);
        setTimeout(() => setSuccessMessage(null), 3000);
      },
      onError: (err) => {
        const errorMessage = err instanceof Error ? err.message : 'Failed to apply template';
        setLocalError(errorMessage);
      },
    });
  }, [selectedFile, conversionId, applyTemplateMutation]);

  // Export handlers using React Query
  const handleExportPreview = useCallback(() => {
    // Trigger the preview query
    // exportPreviewQuery.refetch().then((result) => {
      if (!result.error) {
        setShowExportDialog(true);
      } else {
        const errorMessage = result.error instanceof Error ? result.error.message : 'Failed to preview export';
        setLocalError(errorMessage);
      }
    });
  }, [exportPreviewQuery]);

  const handleExportDownload = useCallback((format: string = 'mcaddon') => {
    // downloadPackMutation.mutate({
      conversionId,
      format,
    }, {
      onSuccess: ({ filename }) => {
        setSuccessMessage(`Export downloaded as ${filename}`);
        setTimeout(() => setSuccessMessage(null), 3000);
        setShowExportDialog(false);
      },
      onError: (err) => {
        const errorMessage = err instanceof Error ? err.message : 'Failed to download export';
        setLocalError(errorMessage);
      },
    });
  }, [conversionId, downloadPackMutation]);

  const handleExport = useCallback((format: string = 'mcaddon', includeTemplates: boolean = true) => {
    // exportPackMutation.mutate({
      conversion_id: conversionId,
      file_types: [], // Empty means all files
      include_templates,
      export_format: format as 'mcaddon' | 'zip' | 'json',
    }, {
      onSuccess: (exportResult) => {
        // Download immediately after export
        // handleExportDownload(format);
        setSuccessMessage(`Export completed: ${exportResult.file_count} files, ${exportResult.export_size} bytes`);
        setTimeout(() => setSuccessMessage(null), 5000);
      },
      onError: (err) => {
        const errorMessage = err instanceof Error ? err.message : 'Failed to export behavior pack';
        setLocalError(errorMessage);
      },
    });
  }, [conversionId, exportPackMutation, handleExportDownload]);

  // Clear error handler
  const clearLocalError = useCallback(() => {
    setLocalError(null);
  }, []);

  // Clear success message handler
  const clearSuccess = useCallback(() => {
    setSuccessMessage(null);
  }, []);

  // Clear all errors handler
  const clearLocalError = useCallback(() => {
    // Using the enhanced UI state clear function
    Object.keys(error).forEach(key => {
      setError(key, null);
    });
  }, [error, setError]);

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
    <ErrorBoundary
      onError={(error, errorInfo) => {
        console.error('BehaviorEditor error:', error, errorInfo);
        toast.error('An error occurred in the editor. Please try again.');
      }}
    >
      <div className={`behavior-editor ${className}`}>
      {/* Loading Progress */}
      {(isLoading || applyTemplateMutation.isPending || false || false || false) && (
        <LinearProgress sx={{ position: 'absolute', top: 0, left: 0, right: 0, zIndex: 1000 }} />
      )}

      {/* Error Alert */}
      {(localError || uiError) && (
        <Alert 
          severity="error" 
          sx={{ mb: 2 }} 
          onClose={clearLocalError}
          action={
            <IconButton size="small" onClick={clearLocalError}>
              <ErrorIcon />
            </IconButton>
          }
        >
          {localError || uiError}
        </Alert>
      )}

      {/* Editor Mode Header */}
      <div className="editor-mode-header">
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6">
            {selectedFile ? `Editing: ${selectedFile.path}` : 'Behavior Editor'}
          </Typography>
          
          {/* Action Buttons */}
          <Box sx={{ display: 'flex', gap: 1 }}>
            {selectedFile && (
              <Button
                variant="outlined"
                startIcon={<Add />}
                onClick={() => setShowTemplateDialog(true)}
                size="small"
              >
                Templates
              </Button>
            )}
            <Button
              variant="outlined"
              startIcon={<Download />}
              onClick={handleExportClick}
              size="small"
              disabled={isLoading}
            >
              Export
            </Button>
            <Button
              variant="outlined"
              startIcon={<Refresh />}
              size="small"
              onClick={() => window.location.reload()}
            >
              Refresh
            </Button>
          </Box>
        </Box>
        
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
                        <LootTableEditor
                          onLootTableChange={(lootTable) => console.log('Loot table changed:', lootTable)}
                          onPreview={(lootTable) => console.log('Preview loot table:', lootTable)}
                          onSave={(lootTable) => console.log('Save loot table:', lootTable)}
                          readOnly={false}
                        />
                      )}
                      
                      {editorTab === 3 && (
                        <LogicBuilder
                          onFlowChange={(flow) => console.log('Logic flow changed:', flow)}
                          onSave={(flow) => console.log('Save logic flow:', flow)}
                          onTest={(flow) => console.log('Test logic flow:', flow)}
                          readOnly={false}
                        />
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

      {/* Template Dialog */}
      <Dialog
        open={showTemplateDialog}
        onClose={() => setShowTemplateDialog(false)}
        maxWidth="lg"
        fullWidth
        PaperProps={{
          sx: { height: '80vh' }
        }}
      >
        <DialogTitle>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Typography variant="h6">Behavior Templates</Typography>
            <IconButton onClick={() => setShowTemplateDialog(false)}>
              <Close />
            </IconButton>
          </Box>
        </DialogTitle>
        <DialogContent sx={{ pb: 0 }}>
          <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 2 }}>
            <Tabs 
              value={templateDialogTab} 
              onChange={(_, newValue) => setTemplateDialogTab(newValue)}
            >
              <Tab label="Browse Templates" />
              <Tab label="My Templates" />
              <Tab label="Create New" />
            </Tabs>
          </Box>
          
          {templateDialogTab === 0 && (
            <TemplateSelector
              onTemplateSelect={handleTemplateSelect}
              onTemplateApply={handleTemplateApply}
              category={selectedFile?.type}
              showApplyButton={true}
              disabled={isLoading}
            />
          )}
          
          {templateDialogTab === 1 && (
            <Box>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Your custom templates will appear here.
              </Typography>
              <Typography variant="body2" color="text.secondary">
                This feature is coming soon! You'll be able to save your own templates for reuse.
              </Typography>
            </Box>
          )}
          
          {templateDialogTab === 2 && (
            <Box>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Create custom templates from your current work.
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Template creation tools are coming soon! You'll be able to save configurations as reusable templates.
              </Typography>
            </Box>
          )}
        </DialogContent>
      </Dialog>

      {/* Export Manager Dialog */}
      <ExportManager
        conversionId={conversionId}
        open={showExportDialog}
        onClose={() => setShowExportDialog(false)}
      />

      {/* Success Snackbar */}
      <Snackbar
        open={!!successMessage}
        autoHideDuration={3000}
        onClose={clearSuccess}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert 
          onClose={clearSuccess} 
          severity="success" 
          sx={{ width: '100%' }}
          icon={<CheckCircle />}
        >
          {successMessage}
        </Alert>
      </Snackbar>
      </div>
    </ErrorBoundary>
  );
};
