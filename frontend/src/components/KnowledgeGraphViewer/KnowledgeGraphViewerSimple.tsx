import React, { useState, useEffect, useCallback, useRef } from 'react';
import { 
  Alert, 
  Button, 
  Card, 
  CardContent,
  TextField, 
  InputAdornment,
  FormControl, 
  InputLabel, 
  Select, 
  MenuItem,
  CircularProgress, 
  Chip,
  Box,
  Typography,
  Stack,
  Grid,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions
} from '@mui/material';
import { 
  Search, 
  Add
} from '@mui/icons-material';
import { } from 'lodash';
import { useApi } from '../../hooks/useApi';

interface GraphNode {
  id: string;
  name: string;
  node_type: string;
  platform: string;
  expert_validated: boolean;
  community_rating: number;
  properties: Record<string, any>;
  minecraft_version: string;
}

interface GraphData {
  nodes: GraphNode[];
  relationships: any[];
}

interface KnowledgeGraphViewerProps {
  minecraftVersion?: string;
}

export const KnowledgeGraphViewer: React.FC<KnowledgeGraphViewerProps> = ({
  minecraftVersion = 'latest'
}) => {
  const [loading, setLoading] = useState(false);
  const [graphData, setGraphData] = useState<GraphData>({ nodes: [], relationships: [] });
  const [searchTerm, setSearchTerm] = useState('');
  const [nodeTypeFilter, setNodeTypeFilter] = useState<string>('');
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [showNodeModal, setShowNodeModal] = useState(false);
  
  const api = useApi();

  // Fetch graph data
  const fetchGraphData = useCallback(async () => {
    setLoading(true);
    try {
      const response = await api.get('/api/v1/knowledge-graph/nodes', {
        params: {
          minecraft_version: minecraftVersion,
          ...(nodeTypeFilter && { node_type: nodeTypeFilter }),
          ...(searchTerm && { search: searchTerm })
        }
      });
      
      setGraphData({
        nodes: response.data || [],
        relationships: [] // Simplified for now
      });
    } catch (error) {
      console.error('Graph fetch error:', error);
    } finally {
      setLoading(false);
    }
  }, [minecraftVersion, nodeTypeFilter, searchTerm, api]);

  // Debounced search - using setTimeout instead of debounce to avoid ESLint warning
  const debouncedSearch = useCallback((term: string) => {
    if (debounceTimer.current) {
      clearTimeout(debounceTimer.current);
    }
    debounceTimer.current = setTimeout(() => {
      setSearchTerm(term);
    }, 500);
  }, [setSearchTerm]);

  // Timer ref for debounce
  const debounceTimer = useRef<number | null>(null);

  // Handle node click
  const handleNodeClick = (node: GraphNode) => {
    setSelectedNode(node);
    setShowNodeModal(true);
  };

  // Get platform color
  const getPlatformColor = (platform: string) => {
    switch (platform) {
      case 'java': return 'success';
      case 'bedrock': return 'info';
      case 'both': return 'warning';
      default: return 'default';
    }
  };

  // Initial data fetch
  useEffect(() => {
    fetchGraphData();
  }, [fetchGraphData]);

  return (
    <Card sx={{ maxWidth: 1200, margin: '0 auto' }}>
      <CardContent>
        <Stack spacing={3}>
          {/* Search and Filters */}
          <Grid container spacing={2} alignItems="center">
            <Grid item xs={12} md={4}>
              <TextField
                fullWidth
                placeholder="Search knowledge nodes..."
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <Search />
                    </InputAdornment>
                  ),
                }}
                onChange={(e) => debouncedSearch(e.target.value)}
              />
            </Grid>
            
            <Grid item xs={12} md={3}>
              <FormControl fullWidth>
                <InputLabel>Filter by node type</InputLabel>
                <Select
                  value={nodeTypeFilter}
                  label="Filter by node type"
                  onChange={(e) => setNodeTypeFilter(e.target.value || '')}
                >
                  <MenuItem value="">All Types</MenuItem>
                  <MenuItem value="java_concept">Java Concept</MenuItem>
                  <MenuItem value="bedrock_concept">Bedrock Concept</MenuItem>
                  <MenuItem value="conversion_pattern">Conversion Pattern</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            
            <Grid item xs={12} md={2}>
              <Button 
                variant="contained" 
                startIcon={<Add />}
                onClick={() => {/* TODO: Implement contribution modal */}}
                fullWidth
              >
                Contribute
              </Button>
            </Grid>
            
            <Grid item xs={12} md={3}>
              <Button 
                variant="outlined" 
                startIcon={<Search />}
                onClick={fetchGraphData}
                disabled={loading}
                fullWidth
              >
                Refresh
              </Button>
            </Grid>
          </Grid>

          {/* Graph Statistics */}
          <Alert 
            severity="info" 
            action={
              <Stack direction="row" spacing={1}>
                <Chip label={`Nodes: ${graphData.nodes.length}`} color="primary" size="small" />
                <Chip label={`Expert Validated: ${graphData.nodes.filter(n => n.expert_validated).length}`} color="success" size="small" />
              </Stack>
            }
          >
            Knowledge Graph Statistics
          </Alert>

          {/* Nodes List */}
          <Box>
            <Typography variant="h6" gutterBottom>
              Knowledge Nodes
            </Typography>
            
            {loading ? (
              <Box display="flex" justifyContent="center" p={3}>
                <CircularProgress />
              </Box>
            ) : (
              <Grid container spacing={2}>
                {graphData.nodes.map((node) => (
                  <Grid item xs={12} sm={6} md={4} key={node.id}>
                    <Card 
                      variant="outlined" 
                      sx={{ cursor: 'pointer', '&:hover': { boxShadow: 4 } }}
                      onClick={() => handleNodeClick(node)}
                    >
                      <CardContent>
                        <Stack spacing={1}>
                          <Typography variant="h6" noWrap>
                            {node.name}
                          </Typography>
                          
                          <Stack direction="row" spacing={1}>
                            <Chip 
                              label={node.node_type} 
                              size="small" 
                              variant="outlined" 
                            />
                            <Chip 
                              label={node.platform} 
                              size="small" 
                              color={getPlatformColor(node.platform) as any}
                            />
                          </Stack>
                          
                          {node.community_rating > 0 && (
                            <Typography variant="caption" color="text.secondary">
                              Rating: {node.community_rating.toFixed(2)}
                            </Typography>
                          )}
                          
                          {node.expert_validated && (
                            <Chip 
                              label="Expert Validated" 
                              size="small" 
                              color="success" 
                            />
                          )}
                          
                          <Typography variant="caption" color="text.secondary">
                            Version: {node.minecraft_version}
                          </Typography>
                        </Stack>
                      </CardContent>
                    </Card>
                  </Grid>
                ))}
              </Grid>
            )}
          </Box>

          {graphData.nodes.length === 0 && !loading && (
            <Box textAlign="center" p={3}>
              <Typography color="text.secondary">
                No knowledge nodes found. Try adjusting your search or filters.
              </Typography>
            </Box>
          )}
        </Stack>
      </CardContent>

      {/* Node Details Modal */}
      <Dialog
        open={showNodeModal}
        onClose={() => setShowNodeModal(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          Knowledge Node Details
        </DialogTitle>
        <DialogContent>
          {selectedNode && (
            <Stack spacing={2}>
              <Typography variant="h6">
                {selectedNode.name}
              </Typography>
              
              <Stack direction="row" spacing={1}>
                <Chip label={selectedNode.node_type} variant="outlined" />
                <Chip 
                  label={selectedNode.platform} 
                  color={getPlatformColor(selectedNode.platform) as any}
                />
                {selectedNode.expert_validated && (
                  <Chip label="Expert Validated" color="success" />
                )}
              </Stack>
              
              <Typography variant="body2">
                <strong>Version:</strong> {selectedNode.minecraft_version}
              </Typography>
              
              <Typography variant="body2">
                <strong>Community Rating:</strong> {selectedNode.community_rating?.toFixed(2) || 'N/A'}
              </Typography>
              
              <Typography variant="body2">
                <strong>Expert Validated:</strong> {selectedNode.expert_validated ? 'Yes' : 'No'}
              </Typography>
              
              {Object.keys(selectedNode.properties).length > 0 && (
                <Box>
                  <Typography variant="body2" gutterBottom>
                    <strong>Properties:</strong>
                  </Typography>
                  <Box 
                    component="pre" 
                    sx={{ 
                      background: '#f5f5f5', 
                      padding: 2, 
                      borderRadius: 1,
                      fontSize: '0.875rem',
                      overflow: 'auto',
                      maxHeight: 200
                    }}
                  >
                    {JSON.stringify(selectedNode.properties, null, 2)}
                  </Box>
                </Box>
              )}
            </Stack>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowNodeModal(false)}>
            Close
          </Button>
        </DialogActions>
      </Dialog>
    </Card>
  );
};

export default KnowledgeGraphViewer;
