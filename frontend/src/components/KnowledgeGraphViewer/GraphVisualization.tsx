import React, { useEffect, useRef, useState } from 'react';
import mermaid from 'mermaid';
import { Box, Button, Paper, Typography, Tabs, Tab } from '@mui/material';
import { 
  ZoomIn, 
  ZoomOut, 
  Fullscreen, 
  Download,
  Share 
} from '@mui/icons-material';

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

interface GraphRelationship {
  id: string;
  source: string;
  target: string;
  relationship_type: string;
  confidence: number;
  properties: Record<string, any>;
}

interface GraphVisualizationProps {
  nodes: GraphNode[];
  relationships: GraphRelationship[];
  title?: string;
  height?: string;
  onNodeClick?: (node: GraphNode) => void;
  onRelationshipClick?: (relationship: GraphRelationship) => void;
}

const GraphVisualization: React.FC<GraphVisualizationProps> = ({
  nodes,
  relationships,
  title = 'Knowledge Graph',
  height = '600px',
  onNodeClick,
  onRelationshipClick
}) => {
  const mermaidRef = useRef<HTMLDivElement>(null);
  const diagramCounterRef = useRef(0);
  const [selectedTab, setSelectedTab] = useState(0);
  const [zoom, setZoom] = useState(1);
  const [fullscreen, setFullscreen] = useState(false);

  // Initialize Mermaid
  useEffect(() => {
    mermaid.initialize({
      startOnLoad: true,
      theme: 'default',
      securityLevel: 'loose',
      fontFamily: 'monospace',
      fontSize: 16,
      flowchart: {
        useMaxWidth: true,
        htmlLabels: true,
        curve: 'basis'
      }
    });
  }, []);

  // Update graph when data changes
  useEffect(() => {
    if (nodes.length === 0 && relationships.length === 0) {
      return;
    }
    
    // Directly render here instead of using useCallback to avoid circular dependencies
    const render = async () => {
      if (!mermaidRef.current) return;

      try {
        // Clear previous content
        mermaidRef.current.innerHTML = '';

        // Generate unique ID for this diagram using a counter
        diagramCounterRef.current += 1;
        const diagramId = `mermaid-diagram-${diagramCounterRef.current}`;

        // Helper functions defined inline to avoid hoisting issues
        const getNodeShape = (node: GraphNode): string => {
          if (node.node_type === 'entity') return '{' + '}';
          if (node.node_type === 'pattern') return '[(' + ')]';
          if (node.node_type === 'behavior') return '[/' + '/]';
          if (node.platform === 'java') return '((' + '))';
          if (node.platform === 'bedrock') return '(' + ')';
          return '[' + ']';
        };

        const getNodeStyle = (node: GraphNode): string => {
          const styles = [];
          
          if (node.expert_validated) {
            styles.push('stroke:#4caf50,stroke-width:2px');
          }
          
          if (node.community_rating >= 0.8) {
            styles.push('fill:#e8f5e8');
          } else if (node.community_rating >= 0.5) {
            styles.push('fill:#fff3e0');
          } else {
            styles.push('fill:#ffebee');
          }
          
          if (node.platform === 'java') {
            styles.push('color:#1976d2');
          } else if (node.platform === 'bedrock') {
            styles.push('color:#d32f2f');
          }
          
          return styles.length > 0 ? `:::style${styles.join(',')}` : '';
        };

        const getRelationshipArrow = (relationship: GraphRelationship): string => {
          if (relationship.confidence >= 0.8) return '>';
          if (relationship.confidence >= 0.5) return '>>';
          return '>';
        };

        const getRelationshipStyle = (relationship: GraphRelationship): string => {
          const styles = [];
          
          if (relationship.confidence >= 0.8) {
            styles.push('stroke:#4caf50,stroke-width:2px');
          } else if (relationship.confidence >= 0.5) {
            styles.push('stroke:#ff9800,stroke-width:2px');
          } else {
            styles.push('stroke:#f44336,stroke-width:2px');
          }
          
          return styles.length > 0 ? `:::style${styles.join(',')}` : '';
        };

        // Create node definitions
        const nodeDefinitions = nodes.map(node => {
          const shape = getNodeShape(node);
          const style = getNodeStyle(node);
          return `  ${node.id}["${node.name}"]${shape}${style}`;
        }).join('\n');

        // Create relationship definitions
        const relationshipDefinitions = relationships.map(rel => {
          const arrow = getRelationshipArrow(rel);
          const style = getRelationshipStyle(rel);
          return `  ${rel.source} -->|${rel.relationship_type}|${arrow} ${rel.target}${style}`;
        }).join('\n');

        const mermaidCode = `
flowchart TD
${nodeDefinitions}
${relationshipDefinitions}
        `.trim();

        // Render diagram
        const { svg } = await mermaid.render(diagramId, mermaidCode);
        
        if (svg) {
          mermaidRef.current.appendChild(svg);
          
          // Add click handlers if provided
          if (onNodeClick || onRelationshipClick) {
            // Add click handlers to nodes
            svg.querySelectorAll('.node').forEach(nodeElement => {
              const nodeId = nodeElement.getAttribute('id');
              if (nodeId) {
                nodeElement.style.cursor = 'pointer';
                nodeElement.addEventListener('click', () => {
                  const node = nodes.find(n => n.id === nodeId);
                  if (node && onNodeClick) {
                    onNodeClick(node);
                  }
                });
              }
            });

            // Add click handlers to relationships
            svg.querySelectorAll('.edgeLabel').forEach(edgeElement => {
              edgeElement.style.cursor = 'pointer';
              edgeElement.addEventListener('click', () => {
                // Find corresponding relationship
                const label = edgeElement.textContent;
                const relationship = relationships.find(r => 
                  r.relationship_type === label || 
                  r.confidence.toString() === label
                );
                if (relationship && onRelationshipClick) {
                  onRelationshipClick(relationship);
                }
              });
            });
          }
        }
      } catch (error) {
        console.error('Error rendering Mermaid diagram:', error);
        
        // Show error message
        if (mermaidRef.current) {
          mermaidRef.current.innerHTML = `
            <div style="padding: 20px; text-align: center; color: #666;">
              <p>Unable to render graph visualization</p>
              <p style="font-size: 0.9em;">${error instanceof Error ? error.message : 'Unknown error'}</p>
            </div>
          `;
        }
      }
    };

    render();
  }, [nodes, relationships, onNodeClick, onRelationshipClick]);

  const handleZoomIn = () => {
    setZoom(prev => Math.min(prev + 0.1, 2));
  };

  const handleZoomOut = () => {
    setZoom(prev => Math.max(prev - 0.1, 0.5));
  };

  const handleFullscreen = () => {
    setFullscreen(!fullscreen);
  };

  const handleDownload = () => {
    if (mermaidRef.current) {
      const svg = mermaidRef.current.querySelector('svg');
      if (svg) {
        const svgData = new XMLSerializer().serializeToString(svg);
        const blob = new Blob([svgData], { type: 'image/svg+xml' });
        const url = URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = `knowledge-graph-${Date.now()}.svg`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      }
    }
  };

  const handleShare = () => {
    const shareData = {
      title: 'Knowledge Graph Visualization',
      text: `Check out this knowledge graph with ${nodes.length} nodes and ${relationships.length} relationships`,
      url: window.location.href
    };

    if (navigator.share) {
      navigator.share(shareData);
    } else {
      // Fallback - copy to clipboard
      navigator.clipboard.writeText(window.location.href);
      // Show toast or notification
    }
  };

  return (
    <Paper elevation={2} sx={{ p: 2, height: fullscreen ? '100vh' : height }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
        <Typography variant="h6">{title}</Typography>
        
        <Box display="flex" gap={1}>
          <Button size="small" onClick={handleZoomOut} disabled={zoom <= 0.5}>
            <ZoomOut />
          </Button>
          <Button size="small" onClick={handleZoomIn} disabled={zoom >= 2}>
            <ZoomIn />
          </Button>
          <Button size="small" onClick={handleFullscreen}>
            <Fullscreen />
          </Button>
          <Button size="small" onClick={handleDownload}>
            <Download />
          </Button>
          <Button size="small" onClick={handleShare}>
            <Share />
          </Button>
        </Box>
      </Box>

      <Tabs value={selectedTab} onChange={(_, newValue) => setSelectedTab(newValue)} mb={2}>
        <Tab label="Graph View" />
        <Tab label="Data View" />
      </Tabs>

      {selectedTab === 0 && (
        <Box
          ref={mermaidRef}
          sx={{
            width: '100%',
            height: '100%',
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            overflow: 'auto',
            transform: `scale(${zoom})`,
            transformOrigin: 'top left'
          }}
        />
      )}

      {selectedTab === 1 && (
        <Box sx={{ maxHeight: '500px', overflow: 'auto' }}>
          <Typography variant="subtitle1" gutterBottom>Nodes ({nodes.length})</Typography>
          {nodes.map(node => (
            <Box key={node.id} sx={{ mb: 2, p: 1, border: '1px solid #eee', borderRadius: 1 }}>
              <Typography variant="subtitle2">{node.name}</Typography>
              <Typography variant="body2" color="textSecondary">
                Type: {node.node_type} | Platform: {node.platform}
              </Typography>
              {node.expert_validated && (
                <Typography variant="body2" color="success.main">Expert Validated</Typography>
              )}
              <Typography variant="body2">
                Community Rating: {(node.community_rating * 100).toFixed(1)}%
              </Typography>
            </Box>
          ))}

          <Typography variant="subtitle1" gutterBottom sx={{ mt: 3 }}>
            Relationships ({relationships.length})
          </Typography>
          {relationships.map(rel => (
            <Box key={rel.id} sx={{ mb: 2, p: 1, border: '1px solid #eee', borderRadius: 1 }}>
              <Typography variant="body2">
                {rel.source} → {rel.target}
              </Typography>
              <Typography variant="body2" color="textSecondary">
                Type: {rel.relationship_type} | Confidence: {(rel.confidence * 100).toFixed(1)}%
              </Typography>
            </Box>
          ))}
        </Box>
      )}
    </Paper>
  );
};

export default GraphVisualization;
