import React, { useState, useEffect, useRef } from 'react';
import {
  IconButton,
  TextField,
  InputAdornment,
  Menu,
  MenuItem,
  ListItemIcon,
  ListItemText,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Tooltip,
  Chip
} from '@mui/material';
import {
  Search,
  FolderOpen,
  Folder,
  InsertDriveFile,
  Add,
  Delete,
  Rename,
  Download,
  Copy,
  Folder as FolderIcon
} from '@mui/icons-material';
import './BehaviorFileTree.css';

export interface BehaviorFileTreeNode {
  id: string;
  name: string;
  path: string;
  type: 'file' | 'directory';
  file_type: string;
  children: BehaviorFileTreeNode[];
}

interface BehaviorFileTreeEnhancedProps {
  conversionId: string;
  onFileSelect: (fileId: string, filePath: string, fileType: string) => void;
  selectedFileId?: string;
  readOnly?: boolean;
}

export const BehaviorFileTreeEnhanced: React.FC<BehaviorFileTreeEnhancedProps> = ({
  conversionId,
  onFileSelect,
  selectedFileId,
  readOnly = false
}) => {
  const [treeData, setTreeData] = useState<BehaviorFileTreeNode[]>([]);
  const [filteredTreeData, setFilteredTreeData] = useState<BehaviorFileTreeNode[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedFolders, setExpandedFolders] = useState<Set<string>>(new Set());
  const [searchQuery, setSearchQuery] = useState('');
  const [contextMenu, setContextMenu] = useState<{
    node: BehaviorFileTreeNode;
    anchorEl: HTMLElement | null;
  }>({ node: {} as BehaviorFileTreeNode, anchorEl: null });

  const [renameDialog, setRenameDialog] = useState<{
    open: boolean;
    node: BehaviorFileTreeNode | null;
    newName: string;
  }>({ open: false, node: null, newName: '' });

  const [createDialog, setCreateDialog] = useState<{
    open: boolean;
    parentNode: BehaviorFileTreeNode | null;
    type: 'file' | 'directory';
    name: string;
  }>({ open: false, parentNode: null, type: 'file', name: '' });

  const draggedNodeRef = useRef<BehaviorFileTreeNode | null>(null);

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
        setFilteredTreeData(data);

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

  // Search/filter functionality
  useEffect(() => {
    if (!searchQuery.trim()) {
      setFilteredTreeData(treeData);
      // Restore expanded folders
      const rootDirs = treeData.filter(node => node.type === 'directory').map(node => node.path);
      setExpandedFolders(new Set(rootDirs));
      return;
    }

    const filterTree = (nodes: BehaviorFileTreeNode[]): BehaviorFileTreeNode[] => {
      const filtered: BehaviorFileTreeNode[] = [];

      for (const node of nodes) {
        if (node.type === 'file') {
          if (node.name.toLowerCase().includes(searchQuery.toLowerCase())) {
            filtered.push({ ...node });
          }
        } else if (node.type === 'directory') {
          const filteredChildren = filterTree(node.children);
          if (filteredChildren.length > 0) {
            filtered.push({ ...node, children: filteredChildren });
          } else if (node.name.toLowerCase().includes(searchQuery.toLowerCase())) {
            filtered.push({ ...node });
          }
        }
      }

      return filtered;
    };

    const result = filterTree(treeData);
    setFilteredTreeData(result);

    // Expand all folders that contain matches
    const expandMatches = (nodes: BehaviorFileTreeNode[]) => {
      const newExpanded = new Set(expandedFolders);

      const expandNode = (node: BehaviorFileTreeNode) => {
        if (node.type === 'directory') {
          const hasMatch = node.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
            node.children.some(child =>
              child.name.toLowerCase().includes(searchQuery.toLowerCase())
            );

          if (hasMatch) {
            newExpanded.add(node.path);
          }

          node.children.forEach(expandNode);
        }
      };

      nodes.forEach(expandNode);
      setExpandedFolders(newExpanded);
    };

    expandMatches(treeData);
  }, [searchQuery, treeData, expandedFolders]);

  const toggleFolder = (folderPath: string) => {
    const newExpanded = new Set(expandedFolders);
    if (newExpanded.has(folderPath)) {
      newExpanded.delete(folderPath);
    } else {
      newExpanded.add(folderPath);
    }
    setExpandedFolders(newExpanded);
  };

  const handleContextMenu = (event: React.MouseEvent, node: BehaviorFileTreeNode) => {
    event.preventDefault();
    event.stopPropagation();

    setContextMenu({
      node,
      anchorEl: event.currentTarget as HTMLElement
    });
  };

  const handleCloseContextMenu = () => {
    setContextMenu({ node: {} as BehaviorFileTreeNode, anchorEl: null });
  };

  const handleRename = (node: BehaviorFileTreeNode) => {
    setRenameDialog({ open: true, node, newName: node.name });
    handleCloseContextMenu();
  };

  const handleRenameConfirm = async () => {
    if (!renameDialog.node) return;

    try {
      const response = await fetch(`/api/v1/behaviors/${renameDialog.node.id}/rename`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ new_name: renameDialog.newName })
      });

      if (!response.ok) throw new Error('Failed to rename');

      // Refresh tree
      const response2 = await fetch(`/api/v1/conversions/${conversionId}/behaviors`);
      const data = await response2.json();
      setTreeData(data);
      setFilteredTreeData(data);
    } catch (err) {
      console.error('Error renaming:', err);
    } finally {
      setRenameDialog({ open: false, node: null, newName: '' });
    }
  };

  const handleDelete = async (node: BehaviorFileTreeNode) => {
    if (!confirm(`Are you sure you want to delete ${node.name}?`)) return;

    try {
      const response = await fetch(`/api/v1/behaviors/${node.id}`, {
        method: 'DELETE'
      });

      if (!response.ok) throw new Error('Failed to delete');

      // Refresh tree
      const response2 = await fetch(`/api/v1/conversions/${conversionId}/behaviors`);
      const data = await response2.json();
      setTreeData(data);
      setFilteredTreeData(data);
    } catch (err) {
      console.error('Error deleting:', err);
    } finally {
      handleCloseContextMenu();
    }
  };

  const handleDownload = async (node: BehaviorFileTreeNode) => {
    try {
      const response = await fetch(`/api/v1/behaviors/${node.id}`);
      if (!response.ok) throw new Error('Failed to download');

      const data = await response.json();
      const blob = new Blob([data.content], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = node.name;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Error downloading:', err);
    } finally {
      handleCloseContextMenu();
    }
  };

  const handleCreate = (parentNode: BehaviorFileTreeNode | null, type: 'file' | 'directory') => {
    setCreateDialog({ open: true, parentNode, type, name: '' });
    handleCloseContextMenu();
  };

  const handleCreateConfirm = async () => {
    try {
      const parentPath = createDialog.parentNode?.path || '';
      const response = await fetch(`/api/v1/conversions/${conversionId}/behaviors`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: createDialog.name,
          type: createDialog.type,
          parent_path: parentPath
        })
      });

      if (!response.ok) throw new Error('Failed to create');

      // Refresh tree
      const response2 = await fetch(`/api/v1/conversions/${conversionId}/behaviors`);
      const data = await response2.json();
      setTreeData(data);
      setFilteredTreeData(data);

      // Expand parent folder
      if (parentPath) {
        setExpandedFolders(new Set([...expandedFolders, parentPath]));
      }
    } catch (err) {
      console.error('Error creating:', err);
    } finally {
      setCreateDialog({ open: false, parentNode: null, type: 'file', name: '' });
    }
  };

  // Drag and drop handlers
  const handleDragStart = (event: React.DragEvent, node: BehaviorFileTreeNode) => {
    draggedNodeRef.current = node;
    event.dataTransfer.effectAllowed = 'move';
    event.dataTransfer.setData('text/plain', node.path);
  };

  const handleDragOver = (event: React.DragEvent, _node: BehaviorFileTreeNode) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  };

  const handleDrop = async (event: React.DragEvent, targetNode: BehaviorFileTreeNode) => {
    event.preventDefault();
    const draggedNode = draggedNodeRef.current;
    if (!draggedNode || draggedNode.id === targetNode.id) return;
    if (targetNode.type !== 'directory') return;

    try {
      const response = await fetch(`/api/v1/behaviors/${draggedNode.id}/move`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target_path: targetNode.path })
      });

      if (!response.ok) throw new Error('Failed to move');

      // Refresh tree
      const response2 = await fetch(`/api/v1/conversions/${conversionId}/behaviors`);
      const data = await response2.json();
      setTreeData(data);
      setFilteredTreeData(data);

      // Expand target folder
      setExpandedFolders(new Set([...expandedFolders, targetNode.path]));
    } catch (err) {
      console.error('Error moving:', err);
    } finally {
      draggedNodeRef.current = null;
    }
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
            onContextMenu={(e) => handleContextMenu(e, node)}
            draggable={!readOnly}
            onDragStart={(e) => handleDragStart(e, node)}
            onDragOver={(e) => handleDragOver(e, node)}
            onDrop={(e) => handleDrop(e, node)}
          >
            <span className={`folder-icon ${isExpanded ? 'expanded' : ''}`}>
              {isExpanded ? <FolderOpen fontSize="small" /> : <Folder fontSize="small" />}
            </span>
            <span className="node-name">{node.name}</span>
            <Chip
              label={`${node.children.length}`}
              size="small"
              variant="outlined"
              sx={{ ml: 1, fontSize: '0.7rem', height: 18 }}
            />
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
            onContextMenu={(e) => handleContextMenu(e, node)}
            draggable={!readOnly}
            onDragStart={(e) => handleDragStart(e, node)}
          >
            <span className="file-icon">{getFileIcon(node.file_type, node.name)}</span>
            <span className="node-name">{node.name}</span>
            <span className="file-type-badge">{node.file_type}</span>
          </div>
        </div>
      );
    }
  };

  const getFileIcon = (fileType: string, fileName: string): React.ReactNode => {
    if (fileName.endsWith('.json')) return <InsertDriveFile fontSize="small" sx={{ color: '#f57c00' }} />;
    if (fileName.endsWith('.js') || fileName.endsWith('.ts')) return <InsertDriveFile fontSize="small" sx={{ color: '#ffca28' }} />;
    if (fileType === 'entity_behavior') return <InsertDriveFile fontSize="small" sx={{ color: '#7e57c2' }} />;
    if (fileType === 'block_behavior') return <InsertDriveFile fontSize="small" sx={{ color: '#8d6e63' }} />;
    if (fileType === 'script') return <InsertDriveFile fontSize="small" sx={{ color: '#42a5f5' }} />;
    if (fileType === 'recipe') return <InsertDriveFile fontSize="small" sx={{ color: '#66bb6a' }} />;
    return <InsertDriveFile fontSize="small" sx={{ color: '#78909c' }} />;
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
          <Button onClick={() => window.location.reload()}>Retry</Button>
        </div>
      </div>
    );
  }

  return (
    <div className="behavior-file-tree">
      <div className="tree-header">
        <h3>Behavior Files</h3>
        <Tooltip title="Create new file or folder">
          <IconButton
            size="small"
            onClick={(e) => handleContextMenu(e, { id: 'root', name: '', path: '', type: 'directory', file_type: '', children: [] })}
            disabled={readOnly}
          >
            <Add fontSize="small" />
          </IconButton>
        </Tooltip>
      </div>

      {/* Search Bar */}
      <div className="tree-search">
        <TextField
          fullWidth
          size="small"
          placeholder="Search files..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <Search fontSize="small" />
              </InputAdornment>
            ),
            endAdornment: searchQuery && (
              <InputAdornment position="end">
                <IconButton
                  size="small"
                  onClick={() => setSearchQuery('')}
                >
                  ✕
                </IconButton>
              </InputAdornment>
            )
          }}
        />
      </div>

      <div className="tree-content">
        {filteredTreeData.length === 0 ? (
          <div className="tree-empty">
            {searchQuery ? (
              <p>No files match "{searchQuery}"</p>
            ) : (
              <>
                <p>No behavior files found for this conversion.</p>
                <p>Files will appear here after conversion generates editable behaviors.</p>
              </>
            )}
          </div>
        ) : (
          filteredTreeData.map(node => renderTreeNode(node))
        )}
      </div>

      {/* Context Menu */}
      <Menu
        anchorEl={contextMenu.anchorEl}
        open={Boolean(contextMenu.anchorEl)}
        onClose={handleCloseContextMenu}
      >
        {contextMenu.node.type === 'file' && (
          <>
            <MenuItem onClick={() => onFileSelect(contextMenu.node.id, contextMenu.node.path, contextMenu.node.file_type)}>
              <ListItemIcon><InsertDriveFile fontSize="small" /></ListItemIcon>
              <ListItemText>Open</ListItemText>
            </MenuItem>
            <MenuItem onClick={() => handleRename(contextMenu.node)} disabled={readOnly}>
              <ListItemIcon><Rename fontSize="small" /></ListItemIcon>
              <ListItemText>Rename</ListItemText>
            </MenuItem>
            <MenuItem onClick={() => handleDownload(contextMenu.node)}>
              <ListItemIcon><Download fontSize="small" /></ListItemIcon>
              <ListItemText>Download</ListItemText>
            </MenuItem>
            <MenuItem onClick={() => handleDownload(contextMenu.node)}>
              <ListItemIcon><Copy fontSize="small" /></ListItemIcon>
              <ListItemText>Copy Path</ListItemText>
            </MenuItem>
            <MenuItem onClick={() => handleDelete(contextMenu.node)} disabled={readOnly}>
              <ListItemIcon><Delete fontSize="small" /></ListItemIcon>
              <ListItemText>Delete</ListItemText>
            </MenuItem>
          </>
        )}
        {contextMenu.node.type === 'directory' && (
          <>
            <MenuItem onClick={() => handleCreate(contextMenu.node, 'file')} disabled={readOnly}>
              <ListItemIcon><InsertDriveFile fontSize="small" /></ListItemIcon>
              <ListItemText>New File</ListItemText>
            </MenuItem>
            <MenuItem onClick={() => handleCreate(contextMenu.node, 'directory')} disabled={readOnly}>
              <ListItemIcon><FolderIcon fontSize="small" /></ListItemIcon>
              <ListItemText>New Folder</ListItemText>
            </MenuItem>
            <MenuItem onClick={() => handleRename(contextMenu.node)} disabled={readOnly}>
              <ListItemIcon><Rename fontSize="small" /></ListItemIcon>
              <ListItemText>Rename</ListItemText>
            </MenuItem>
            <MenuItem onClick={() => handleDelete(contextMenu.node)} disabled={readOnly}>
              <ListItemIcon><Delete fontSize="small" /></ListItemIcon>
              <ListItemText>Delete</ListItemText>
            </MenuItem>
          </>
        )}
        {contextMenu.node.id === 'root' && (
          <>
            <MenuItem onClick={() => handleCreate(null, 'file')} disabled={readOnly}>
              <ListItemIcon><InsertDriveFile fontSize="small" /></ListItemIcon>
              <ListItemText>New File</ListItemText>
            </MenuItem>
            <MenuItem onClick={() => handleCreate(null, 'directory')} disabled={readOnly}>
              <ListItemIcon><FolderIcon fontSize="small" /></ListItemIcon>
              <ListItemText>New Folder</ListItemText>
            </MenuItem>
          </>
        )}
      </Menu>

      {/* Rename Dialog */}
      <Dialog open={renameDialog.open} onClose={() => setRenameDialog({ ...renameDialog, open: false })}>
        <DialogTitle>Rename {renameDialog.node?.type}</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            fullWidth
            label="New Name"
            value={renameDialog.newName}
            onChange={(e) => setRenameDialog({ ...renameDialog, newName: e.target.value })}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRenameDialog({ ...renameDialog, open: false })}>Cancel</Button>
          <Button onClick={handleRenameConfirm} variant="contained">Rename</Button>
        </DialogActions>
      </Dialog>

      {/* Create Dialog */}
      <Dialog open={createDialog.open} onClose={() => setCreateDialog({ ...createDialog, open: false })}>
        <DialogTitle>Create New {createDialog.type === 'file' ? 'File' : 'Folder'}</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            fullWidth
            label={`${createDialog.type === 'file' ? 'File' : 'Folder'} Name`}
            value={createDialog.name}
            onChange={(e) => setCreateDialog({ ...createDialog, name: e.target.value })}
            helperText={createDialog.type === 'file' ? 'Include .json extension if needed' : 'Folder name without extension'}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateDialog({ ...createDialog, open: false })}>Cancel</Button>
          <Button onClick={handleCreateConfirm} variant="contained">Create</Button>
        </DialogActions>
      </Dialog>
    </div>
  );
};
