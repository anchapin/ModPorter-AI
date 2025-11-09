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
  Box,
  Typography,
  Stack,
  Grid,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Chip,
  Snackbar
} from '@mui/material';
import { 
  SearchOutlined,
  Add,
  VisibilityOutlined,
  EditOutlined
} from '@mui/icons-material';
import * as d3 from 'd3';
import { debounce } from 'lodash';
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
  x?: number;
  y?: number;
  fx?: number;
  fy?: number;
}

interface GraphRelationship {
  id: string;
  source: string;
  target: string;
  relationship_type: string;
  confidence_score: number;
  properties: Record<string, any>;
  expert_validated: boolean;
  community_votes: number;
}

interface GraphData {
  nodes: GraphNode[];
  relationships: GraphRelationship[];
}

interface KnowledgeGraphViewerProps {
  width?: number;
  height?: number;
  minecraftVersion?: string;
}

export const KnowledgeGraphViewer: React.FC<KnowledgeGraphViewerProps> = ({
  width = 800,
  height = 600,
  minecraftVersion = 'latest'
}) => {
  const [loading, setLoading] = useState(false);
  const [graphData, setGraphData] = useState<GraphData>({ nodes: [], relationships: [] });
  const [searchTerm, setSearchTerm] = useState('');
  const [nodeTypeFilter, setNodeTypeFilter] = useState<string>('');
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [showNodeModal, setShowNodeModal] = useState(false);
  const [showContributionModal, setShowContributionModal] = useState(false);
  const [conversionPaths, setConversionPaths] = useState<any[]>([]);
  const [showPathsModal, setShowPathsModal] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [showError, setShowError] = useState(false);
  
  const svgRef = useRef<SVGSVGElement>(null);
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
      
      const relationshipsResponse = await api.get('/api/v1/knowledge-graph/relationships');
      
      setGraphData({
        nodes: response.data || [],
        relationships: relationshipsResponse.data?.relationships || []
      });
    } catch (error) {
      setErrorMessage('Failed to load knowledge graph data');
      setShowError(true);
      console.error('Graph fetch error:', error);
    } finally {
      setLoading(false);
    }
  }, [minecraftVersion, nodeTypeFilter, searchTerm, api]);

  // Debounced search
  const debouncedSearch = useCallback(
    debounce((term: string) => {
      setSearchTerm(term);
    }, 500),
    []
  );

  // Draw graph using D3.js
  useEffect(() => {
    if (!svgRef.current || graphData.nodes.length === 0) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    // Create force simulation
    const simulation = d3.forceSimulation(graphData.nodes as any)
      .force('link', d3.forceLink(graphData.relationships)
        .id((d: any) => d.id)
        .strength(0.5)
      )
      .force('charge', d3.forceManyBody().strength(-300))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide().radius(30));

    // Create container for zoom
    const container = svg.append('g');

    // Add zoom behavior
    const zoom = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.1, 4])
      .on('zoom', (event) => {
        container.attr('transform', event.transform);
      });

    svg.call(zoom);

    // Create relationship lines
    const link = container.append('g')
      .selectAll('line')
      .data(graphData.relationships)
      .enter().append('line')
      .attr('stroke', '#999')
      .attr('stroke-opacity', (d: GraphRelationship) => d.confidence_score)
      .attr('stroke-width', (d: GraphRelationship) => Math.max(1, d.confidence_score * 5))
      .attr('marker-end', 'url(#arrowhead)');

    // Create arrowhead marker
    svg.append('defs').append('marker')
      .attr('id', 'arrowhead')
      .attr('viewBox', '0 -5 10 10')
      .attr('refX', 20)
      .attr('refY', 0)
      .attr('markerWidth', 8)
      .attr('markerHeight', 8)
      .attr('orient', 'auto')
      .append('path')
      .attr('d', 'M0,-5L10,0L0,5')
      .attr('fill', '#999');

    // Create node groups
    const node = container.append('g')
      .selectAll('g')
      .data(graphData.nodes)
      .enter().append('g')
      .call(d3.drag<SVGGElement, GraphNode>()
        .on('start', dragstarted)
        .on('drag', dragged)
        .on('end', dragended) as any
      )
      .on('click', handleNodeClick);

    // Add circles for nodes
    node.append('circle')
      .attr('r', (d: GraphNode) => 15 + (d.community_rating * 5))
      .attr('fill', (d: GraphNode) => getNodeColor(d))
      .attr('stroke', '#fff')
      .attr('stroke-width', 2)
      .on('mouseover', handleNodeMouseOver)
      .on('mouseout', handleNodeMouseOut);

    // Add labels
    node.append('text')
      .text((d: GraphNode) => d.name)
      .attr('x', 0)
      .attr('y', -25)
      .attr('text-anchor', 'middle')
      .attr('font-size', '12px')
      .attr('font-weight', 'bold');

    // Add node type badges
    node.append('text')
      .text((d: GraphNode) => d.node_type)
      .attr('x', 0)
      .attr('y', 30)
      .attr('text-anchor', 'middle')
      .attr('font-size', '10px')
      .attr('fill', '#666');

    // Update positions on tick
    simulation.on('tick', () => {
      link
        .attr('x1', (d: any) => d.source.x)
        .attr('y1', (d: any) => d.source.y)
        .attr('x2', (d: any) => d.target.x)
        .attr('y2', (d: any) => d.target.y);

      node
        .attr('transform', (d: any) => `translate(${d.x},${d.y})`);
    });

    // Helper functions
    function getNodeColor(node: GraphNode): string {
      if (node.platform === 'java') return '#4CAF50';
      if (node.platform === 'bedrock') return '#2196F3';
      return '#FF9800'; // Both
    }

    function handleNodeClick(event: MouseEvent, d: GraphNode) {
      setSelectedNode(d);
      setShowNodeModal(true);
    }

    function handleNodeMouseOver(event: MouseEvent) {
      d3.select(event.currentTarget as SVGCircleElement)
        .attr('stroke-width', 4)
        .attr('stroke', '#ff0');
    }

    function handleNodeMouseOut(event: MouseEvent) {
      d3.select(event.currentTarget as SVGCircleElement)
        .attr('stroke-width', 2)
        .attr('stroke', '#fff');
    }

    function dragstarted(event: any, d: GraphNode) {
      if (!event.active) simulation.alphaTarget(0.3).restart();
      d.fx = d.x;
      d.fy = d.y;
    }

    function dragged(event: any, d: GraphNode) {
      d.fx = event.x;
      d.fy = event.y;
    }

    function dragended(event: any, d: GraphNode) {
      if (!event.active) simulation.alphaTarget(0);
      d.fx = null;
      d.fy = null;
    }

  }, [graphData, width, height]);

  // Find conversion paths for selected node
  const findConversionPaths = async (node: GraphNode) => {
    if (node.platform !== 'java' && node.platform !== 'both') {
      setErrorMessage('Conversion paths are only available for Java concepts');
      setShowError(true);
      return;
    }

    try {
      const response = await api.get(`/api/v1/knowledge-graph/graph/paths/${node.id}`, {
        params: {
          minecraft_version: minecraftVersion,
          max_depth: 3
        }
      });
      setConversionPaths(response.data?.conversion_paths || []);
      setShowPathsModal(true);
    } catch (error) {
      setErrorMessage('Failed to find conversion paths');
      setShowError(true);
      console.error('Conversion paths error:', error);
    }
  };

  // Initial data fetch
  useEffect(() => {
    fetchGraphData();
  }, [fetchGraphData]);

  return (
    <>
      <Card sx={{ maxWidth: 1200, margin: '0 auto' }} className="knowledge-graph-viewer">
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
                        <SearchOutlined />
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
                  onClick={() => setShowContributionModal(true)}
                  fullWidth
                >
                  Contribute
                </Button>
              </Grid>
              
              <Grid item xs={12} md={3}>
                <Button 
                  variant="outlined" 
                  startIcon={<SearchOutlined />}
                  onClick={fetchGraphData}
                  disabled={loading}
                  fullWidth
                >
                  Refresh
                </Button>
              </Grid>
            </Grid>

            {/* Graph Visualization */}
            <Box sx={{ border: '1px solid #d9d9d9', borderRadius: 1, position: 'relative' }}>
              {loading && (
                <Box sx={{ 
                  position: 'absolute', 
                  top: 0, 
                  left: 0, 
                  right: 0, 
                  bottom: 0, 
                  display: 'flex', 
                  alignItems: 'center', 
                  justifyContent: 'center',
                  backgroundColor: 'rgba(255,255,255,0.7)',
                  zIndex: 1
                }}>
                  <CircularProgress />
                </Box>
              )}
              <svg
                ref={svgRef}
                width={width}
                height={height}
                style={{ display: 'block' }}
              />
            </Box>

            {/* Graph Statistics */}
            <Alert 
              severity="info" 
              action={
                <Stack direction="row" spacing={1}>
                  <Chip label={`Nodes: ${graphData.nodes.length}`} color="primary" size="small" />
                  <Chip label={`Relationships: ${graphData.relationships.length}`} color="success" size="small" />
                  <Chip label={`Expert Validated: ${graphData.nodes.filter(n => n.expert_validated).length}`} color="warning" size="small" />
                </Stack>
              }
            >
              Knowledge Graph Statistics
            </Alert>
          </Stack>
        </CardContent>
      </Card>

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
                  color={
                    selectedNode.platform === 'java' ? 'success' : 
                    selectedNode.platform === 'bedrock' ? 'info' : 
                    'warning'
                  }
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
          <Button 
            startIcon={<VisibilityOutlined />}
            onClick={() => selectedNode && findConversionPaths(selectedNode)}
          >
            Find Conversion Paths
          </Button>
          <Button startIcon={<EditOutlined />}>
            Edit Node
          </Button>
          <Button onClick={() => setShowNodeModal(false)}>
            Close
          </Button>
        </DialogActions>
      </Dialog>

      {/* Conversion Paths Modal */}
      <Dialog
        open={showPathsModal}
        onClose={() => setShowPathsModal(false)}
        maxWidth="lg"
        fullWidth
      >
        <DialogTitle>
          Conversion Paths
        </DialogTitle>
        <DialogContent>
          <Stack spacing={2}>
            {conversionPaths.map((path, index) => (
              <Card key={index} variant="outlined">
                <CardContent>
                  <Typography variant="subtitle1" gutterBottom>
                    Path {index + 1}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Confidence: {(path.confidence * 100).toFixed(1)}%
                  </Typography>
                  <Typography variant="subtitle2" sx={{ mt: 1 }}>
                    Steps:
                  </Typography>
                  <ol>
                    {path.path?.map((step: any, stepIndex: number) => (
                      <li key={stepIndex}>
                        {step.name} ({step.node_type})
                      </li>
                    ))}
                  </ol>
                </CardContent>
              </Card>
            ))}
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowPathsModal(false)}>
            Close
          </Button>
        </DialogActions>
      </Dialog>

      {/* Community Contribution Modal */}
      <Dialog
        open={showContributionModal}
        onClose={() => setShowContributionModal(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>
          Contribute Knowledge
        </DialogTitle>
        <DialogContent>
          <Stack spacing={2}>
            <FormControl fullWidth>
              <InputLabel>Contribution Type</InputLabel>
              <Select defaultValue="">
                <MenuItem value="pattern">Conversion Pattern</MenuItem>
                <MenuItem value="node">Knowledge Node</MenuItem>
                <MenuItem value="relationship">Relationship</MenuItem>
                <MenuItem value="correction">Correction</MenuItem>
              </Select>
            </FormControl>
            
            <TextField
              fullWidth
              label="Title"
              variant="outlined"
            />
            
            <TextField
              fullWidth
              label="Description"
              multiline
              rows={4}
              variant="outlined"
            />
            
            <FormControl fullWidth>
              <InputLabel>Minecraft Version</InputLabel>
              <Select defaultValue="latest">
                <MenuItem value="latest">Latest</MenuItem>
                <MenuItem value="1.20">1.20</MenuItem>
                <MenuItem value="1.19">1.19</MenuItem>
                <MenuItem value="1.18">1.18</MenuItem>
              </Select>
            </FormControl>
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowContributionModal(false)}>
            Cancel
          </Button>
          <Button variant="contained" onClick={() => setShowContributionModal(false)}>
            Submit
          </Button>
        </DialogActions>
      </Dialog>

      {/* Error Snackbar */}
      <Snackbar
        open={showError}
        autoHideDuration={6000}
        onClose={() => setShowError(false)}
        message={errorMessage}
      />
    </>
  );
};

export default KnowledgeGraphViewer;
