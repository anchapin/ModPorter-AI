import React, { useState, useEffect } from 'react';
import './BehaviorFileTree.css';

export interface BehaviorFileTreeNode {
  id: string;
  name: string;
  path: string;
  type: 'file' | 'directory';
  file_type: string;
  children: BehaviorFileTreeNode[];
}

interface BehaviorFileTreeProps {
  conversionId: string;
  onFileSelect: (fileId: string, filePath: string, fileType: string) => void;
  selectedFileId?: string;
}

export const BehaviorFileTree: React.FC<BehaviorFileTreeProps> = ({
  conversionId,
  onFileSelect,
  selectedFileId
}) => {
  const [treeData, setTreeData] = useState<BehaviorFileTreeNode[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedFolders, setExpandedFolders] = useState<Set<string>>(new Set());

  useEffect(() => {
    const fetchFileTree = async () => {
      setIsLoading(true);
      setError(null);
      
      try {
        const response = await fetch(`/api/v1/conversions/${conversionId}/behaviors`);
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data: BehaviorFileTreeNode[] = await response.json();
        setTreeData(data);
        
        // Auto-expand root level directories
        const rootDirs = data.filter(node => node.type === 'directory').map(node => node.path);
        setExpandedFolders(new Set(rootDirs));
      } catch (err) {
        console.error('Error fetching behavior file tree:', err);
        setError(err instanceof Error ? err.message : 'Failed to load file tree');
      } finally {
        setIsLoading(false);
      }
    };

    if (conversionId) {
      fetchFileTree();
    }
  }, [conversionId]);

  const toggleFolder = (folderPath: string) => {
    const newExpanded = new Set(expandedFolders);
    if (newExpanded.has(folderPath)) {
      newExpanded.delete(folderPath);
    } else {
      newExpanded.add(folderPath);
    }
    setExpandedFolders(newExpanded);
  };

  const renderTreeNode = (node: BehaviorFileTreeNode, level: number = 0): React.ReactNode => {
    const isExpanded = expandedFolders.has(node.path);
    const isSelected = node.id === selectedFileId;
    const indentStyle = { paddingLeft: `${level * 20 + 8}px` };

    if (node.type === 'directory') {
      return (
        <div key={node.path} className="tree-node">
          <div
            className="tree-node-content directory"
            style={indentStyle}
            onClick={() => toggleFolder(node.path)}
          >
            <span className={`folder-icon ${isExpanded ? 'expanded' : ''}`}>
              {isExpanded ? '📂' : '📁'}
            </span>
            <span className="node-name">{node.name}</span>
          </div>
          {isExpanded && (
            <div className="tree-children">
              {node.children.map(child => renderTreeNode(child, level + 1))}
            </div>
          )}
        </div>
      );
    } else {
      return (
        <div key={node.id} className="tree-node">
          <div
            className={`tree-node-content file ${isSelected ? 'selected' : ''}`}
            style={indentStyle}
            onClick={() => onFileSelect(node.id, node.path, node.file_type)}
          >
            <span className="file-icon">
              {getFileIcon(node.file_type, node.name)}
            </span>
            <span className="node-name">{node.name}</span>
            <span className="file-type-badge">{node.file_type}</span>
          </div>
        </div>
      );
    }
  };

  const getFileIcon = (fileType: string, fileName: string): string => {
    if (fileName.endsWith('.json')) return '📄';
    if (fileName.endsWith('.js') || fileName.endsWith('.ts')) return '📜';
    if (fileType === 'entity_behavior') return '🎭';
    if (fileType === 'block_behavior') return '🧱';
    if (fileType === 'script') return '⚙️';
    if (fileType === 'recipe') return '🍳';
    return '📝';
  };

  if (isLoading) {
    return (
      <div className="behavior-file-tree">
        <div className="tree-header">
          <h3>Behavior Files</h3>
        </div>
        <div className="tree-loading">Loading files...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="behavior-file-tree">
        <div className="tree-header">
          <h3>Behavior Files</h3>
        </div>
        <div className="tree-error">
          <p>Error loading files: {error}</p>
          <button onClick={() => window.location.reload()}>Retry</button>
        </div>
      </div>
    );
  }

  if (treeData.length === 0) {
    return (
      <div className="behavior-file-tree">
        <div className="tree-header">
          <h3>Behavior Files</h3>
        </div>
        <div className="tree-empty">
          <p>No behavior files found for this conversion.</p>
          <p>Files will appear here after the conversion generates editable behaviors.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="behavior-file-tree">
      <div className="tree-header">
        <h3>Behavior Files</h3>
        <span className="file-count">{treeData.length} items</span>
      </div>
      <div className="tree-content">
        {treeData.map(node => renderTreeNode(node))}
      </div>
    </div>
  );
};