import React, { useState, useCallback } from 'react';
import { BehaviorFileTree } from './BehaviorFileTree';
import { CodeEditor } from './CodeEditor';
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

  // Handle file selection from the tree
  const handleFileSelect = useCallback((fileId: string, filePath: string, fileType: string) => {
    setSelectedFile({ id: fileId, path: filePath, type: fileType });
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

  return (
    <div className={`behavior-editor ${className}`}>
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

        {/* Code Editor */}
        <div className="code-editor-area">
          <CodeEditor
            fileId={selectedFile?.id || null}
            filePath={selectedFile?.path || ''}
            fileType={selectedFile?.type || ''}
            onContentChange={handleContentChange}
            onSave={handleSave}
          />
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
        </div>
      </div>
    </div>
  );
};