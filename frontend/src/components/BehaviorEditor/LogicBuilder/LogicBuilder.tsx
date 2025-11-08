import React, { useState, useCallback, useRef } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  Alert,
  Menu,
  MenuItem as MenuItemComponent,
  Card,
  CardContent,
  ListItemIcon,
  ListItemText,
  Divider
} from '@mui/material';
import {
  Add,
  PlayArrow,
  Save,
  CompareArrows,
  AccountTree,
  DataObject,
  Settings,
  Functions,
  Hub
} from '@mui/icons-material';

// Node and connection interfaces
export interface LogicNode {
  id: string;
  type: 'trigger' | 'condition' | 'action' | 'variable' | 'function';
  name: string;
  category: string;
  position: { x: number; y: number };
  inputs: NodePort[];
  outputs: NodePort[];
  parameters: Record<string, any>;
  config?: NodeConfig;
}

export interface NodePort {
  id: string;
  name: string;
  type: 'flow' | 'data';
  dataType?: 'string' | 'number' | 'boolean' | 'object' | 'any';
  required?: boolean;
  multiple?: boolean;
}

export interface NodeConnection {
  id: string;
  sourceNodeId: string;
  sourcePortId: string;
  targetNodeId: string;
  targetPortId: string;
}

export interface NodeConfig {
  description?: string;
  icon?: React.ReactNode;
  color?: string;
  template?: Record<string, any>;
}

export interface LogicFlow {
  id: string;
  name: string;
  description: string;
  nodes: LogicNode[];
  connections: NodeConnection[];
  variables: LogicVariable[];
  triggers: string[]; // Node IDs that act as entry points
}

export interface LogicVariable {
  id: string;
  name: string;
  type: 'string' | 'number' | 'boolean' | 'object';
  defaultValue: any;
  scope: 'local' | 'global';
  description?: string;
}

// Node templates
const nodeTemplates: Record<string, NodeConfig> = {
  // Triggers
  'on_block_break': {
    description: 'Triggered when a block is broken',
    icon: <AccountTree />,
    color: '#4CAF50'
  },
  'on_entity_spawn': {
    description: 'Triggered when an entity spawns',
    icon: <AccountTree />,
    color: '#4CAF50'
  },
  'on_player_interact': {
    description: 'Triggered when a player interacts',
    icon: <AccountTree />,
    color: '#4CAF50'
  },
  
  // Conditions
  'if_condition': {
    description: 'Conditional logic branch',
    icon: <CompareArrows />,
    color: '#2196F3'
  },
  'check_block_type': {
    description: 'Check if block matches type',
    icon: <DataObject />,
    color: '#2196F3'
  },
  'check_entity_type': {
    description: 'Check if entity matches type',
    icon: <DataObject />,
    color: '#2196F3'
  },
  
  // Actions
  'set_block': {
    description: 'Set a block at position',
    icon: <Settings />,
    color: '#FF9800'
  },
  'spawn_entity': {
    description: 'Spawn an entity',
    icon: <Settings />,
    color: '#FF9800'
  },
  'give_item': {
    description: 'Give item to player',
    icon: <Settings />,
    color: '#FF9800'
  },
  'play_sound': {
    description: 'Play a sound',
    icon: <Settings />,
    color: '#FF9800'
  },
  
  // Functions
  'math_operation': {
    description: 'Perform mathematical operation',
    icon: <Functions />,
    color: '#9C27B0'
  },
  'string_operation': {
    description: 'Perform string operation',
    icon: <Functions />,
    color: '#9C27B0'
  },
  'get_world_time': {
    description: 'Get current world time',
    icon: <Functions />,
    color: '#9C27B0'
  }
};

interface LogicBuilderProps {
  flow?: LogicFlow;
  onFlowChange?: (flow: LogicFlow) => void;
  onSave?: (flow: LogicFlow) => void;
  onTest?: (flow: LogicFlow) => void;
  readOnly?: boolean;
}

export const LogicBuilder: React.FC<LogicBuilderProps> = ({
  flow: initialFlow,
  onFlowChange,
  onSave,
  onTest,
  readOnly = false
}) => {
  // Generate unique ID using counter instead of Date.now() for purity
  const idCounter = useRef(0);
  const generateId = useCallback((prefix: string) => `${prefix}_${++idCounter.current}`, []);
  
  const [flow, setFlow] = useState<LogicFlow>(() => 
    initialFlow || {
      id: `flow_${Date.now()}`,
      name: 'New Logic Flow',
      description: '',
      nodes: [],
      connections: [],
      variables: [],
      triggers: []
    }
  );
  const [selectedNode, setSelectedNode] = useState<LogicNode | null>(null);
  const [nodeMenuAnchor, setNodeMenuAnchor] = useState<null | HTMLElement>(null);
  const [connecting, setConnecting] = useState<{ nodeId: string; portId: string; type: 'source' | 'target' } | null>(null);
  
  const canvasRef = useRef<HTMLDivElement>(null);
  const [draggingNode, setDraggingNode] = useState<string | null>(null);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });

  // Update flow and notify parent
  const updateFlow = useCallback((newFlow: LogicFlow) => {
    setFlow(newFlow);
    onFlowChange?.(newFlow);
  }, [onFlowChange]);

  // Add new node
  const addNode = useCallback((templateKey: string, position: { x: number; y: number }) => {
    const template = nodeTemplates[templateKey];
    const newNode: LogicNode = {
      id: generateId('node'),
      type: templateKey.includes('on_') ? 'trigger' : 
            templateKey.includes('if_') || templateKey.includes('check_') ? 'condition' : 
            templateKey.includes('math_') || templateKey.includes('string_') || templateKey.includes('get_') ? 'function' : 'action',
      name: templateKey.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
      category: templateKey.split('_')[0],
      position,
      inputs: templateKey.includes('on_') ? [] : [{ id: 'input_1', name: 'input', type: 'flow' }],
      outputs: [{ id: 'output_1', name: 'output', type: 'flow' }],
      parameters: template.template || {},
      config: template
    };

    const updatedFlow = {
      ...flow,
      nodes: [...flow.nodes, newNode]
    };

    // Add to triggers if it's a trigger node
    if (newNode.type === 'trigger') {
      updatedFlow.triggers.push(newNode.id);
    }

    updateFlow(updatedFlow);
    setNodeMenuAnchor(null);
  }, [flow, updateFlow, generateId]);



  // Update node
  const updateNode = useCallback((nodeId: string, updates: Partial<LogicNode>) => {
    updateFlow({
      ...flow,
      nodes: flow.nodes.map(n => n.id === nodeId ? { ...n, ...updates } : n)
    });
  }, [flow, updateFlow]);

  // Add connection
  const addConnection = useCallback((sourceNodeId: string, sourcePortId: string, targetNodeId: string, targetPortId: string) => {
    const newConnection: NodeConnection = {
      id: generateId('conn'),
      sourceNodeId,
      sourcePortId,
      targetNodeId,
      targetPortId
    };
    updateFlow({
      ...flow,
      connections: [...flow.connections, newConnection]
    });
  }, [flow, updateFlow, generateId]);



  // Handle canvas mouse events for dragging
  const handleCanvasMouseDown = useCallback((e: React.MouseEvent) => {
    if (e.target === canvasRef.current) {
      setSelectedNode(null);
    }
  }, []);

  const handleNodeMouseDown = useCallback((e: React.MouseEvent, nodeId: string) => {
    e.stopPropagation();
    const node = flow.nodes.find(n => n.id === nodeId);
    if (!node) return;

    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return;

    setDraggingNode(nodeId);
    setDragOffset({
      x: e.clientX - rect.left - node.position.x,
      y: e.clientY - rect.top - node.position.y
    });
    setSelectedNode(node);
  }, [flow.nodes]);

  const handleCanvasMouseMove = useCallback((e: React.MouseEvent) => {
    if (!draggingNode || !canvasRef.current) return;

    const rect = canvasRef.current.getBoundingClientRect();
    const newPosition = {
      x: e.clientX - rect.left - dragOffset.x,
      y: e.clientY - rect.top - dragOffset.y
    };

    updateNode(draggingNode, { position: newPosition });
  }, [draggingNode, dragOffset, updateNode]);

  const handleCanvasMouseUp = useCallback(() => {
    setDraggingNode(null);
  }, []);

  // Handle port connections
  const handlePortClick = useCallback((nodeId: string, portId: string, type: 'input' | 'output') => {
    if (!connecting) {
      // Start connection
      setConnecting({ nodeId, portId, type: type === 'output' ? 'source' : 'target' });
    } else {
      // Complete connection
      if (connecting.type === 'source' && type === 'input') {
        addConnection(connecting.nodeId, connecting.portId, nodeId, portId);
      } else if (connecting.type === 'target' && type === 'output') {
        addConnection(nodeId, portId, connecting.nodeId, connecting.portId);
      }
      setConnecting(null);
    }
  }, [connecting, addConnection]);

  // Get node templates grouped by category
  const getNodeTemplatesByCategory = useCallback(() => {
    const categories: Record<string, Array<{ key: string; config: NodeConfig }>> = {};
    
    Object.entries(nodeTemplates).forEach(([key, config]) => {
      const category = key.split('_')[0];
      if (!categories[category]) {
        categories[category] = [];
      }
      categories[category].push({ key, config });
    });

    return categories;
  }, []);

  const nodeCategories = getNodeTemplatesByCategory();

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <Paper sx={{ p: 2, mb: 2, zIndex: 1 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="h6">Logic Builder - Visual Programming</Typography>
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Button
              variant="outlined"
              startIcon={<PlayArrow />}
              onClick={() => onTest?.(flow)}
              disabled={flow.nodes.length === 0}
            >
              Test
            </Button>
            <Button
              variant="outlined"
              startIcon={<Save />}
              onClick={() => onSave?.(flow)}
            >
              Save
            </Button>
          </Box>
        </Box>
      </Paper>

      {/* Info Alert */}
      <Alert severity="info" sx={{ mb: 2 }}>
        This is a placeholder implementation for the Logic Builder. Full functionality including:
        visual node connections, parameter editing, and flow execution will be implemented in the next phase.
      </Alert>

      {/* Canvas */}
      <Paper sx={{ flex: 1, position: 'relative', overflow: 'hidden', bgcolor: '#f5f5f5' }}>
        <Box
          ref={canvasRef}
          sx={{ width: '100%', height: '100%', position: 'relative' }}
          onMouseDown={handleCanvasMouseDown}
          onMouseMove={handleCanvasMouseMove}
          onMouseUp={handleCanvasMouseUp}
          onMouseLeave={handleCanvasMouseUp}
        >
          {/* Grid background */}
          <Box sx={{
            position: 'absolute',
            inset: 0,
            backgroundImage: 'radial-gradient(circle, #ddd 1px, transparent 1px)',
            backgroundSize: '20px 20px',
            opacity: 0.5
          }} />

          {/* Add Node Button */}
          <Button
            variant="contained"
            startIcon={<Add />}
            onClick={(e) => setNodeMenuAnchor(e.currentTarget)}
            disabled={readOnly}
            sx={{ position: 'absolute', top: 16, left: 16, zIndex: 10 }}
          >
            Add Node
          </Button>

          {/* Nodes */}
          {flow.nodes.map(node => (
            <Card
              key={node.id}
              sx={{
                position: 'absolute',
                left: node.position.x,
                top: node.position.y,
                width: 180,
                cursor: draggingNode === node.id ? 'grabbing' : 'grab',
                border: selectedNode?.id === node.id ? '2px solid #1976d2' : '1px solid #ddd',
                bgcolor: node.config?.color ? `${node.config.color}20` : 'white',
                '&:hover': {
                  boxShadow: 3
                }
              }}
              onMouseDown={(e) => handleNodeMouseDown(e, node.id)}
            >
              <CardContent sx={{ p: 1.5 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  {node.config?.icon}
                  <Typography variant="subtitle2" sx={{ ml: 1, fontSize: '0.75rem' }}>
                    {node.name}
                  </Typography>
                </Box>
                <Typography variant="caption" color="text.secondary">
                  {node.config?.description}
                </Typography>
              </CardContent>
              
              {/* Input/Output Ports */}
              <Box sx={{ display: 'flex', justifyContent: 'space-between', p: 0.5 }}>
                {/* Input Ports */}
                <Box>
                  {node.inputs.map(port => (
                    <Box
                      key={port.id}
                      sx={{
                        width: 12,
                        height: 12,
                        borderRadius: '50%',
                        bgcolor: port.type === 'flow' ? '#4CAF50' : '#2196F3',
                        border: '2px solid white',
                        cursor: 'pointer',
                        mb: 0.5
                      }}
                      onClick={(e) => {
                        e.stopPropagation();
                        handlePortClick(node.id, port.id, 'input');
                      }}
                    />
                  ))}
                </Box>
                
                {/* Output Ports */}
                <Box>
                  {node.outputs.map(port => (
                    <Box
                      key={port.id}
                      sx={{
                        width: 12,
                        height: 12,
                        borderRadius: '50%',
                        bgcolor: port.type === 'flow' ? '#4CAF50' : '#2196F3',
                        border: '2px solid white',
                        cursor: 'pointer',
                        mb: 0.5
                      }}
                      onClick={(e) => {
                        e.stopPropagation();
                        handlePortClick(node.id, port.id, 'output');
                      }}
                    />
                  ))}
                </Box>
              </Box>
            </Card>
          ))}

          {/* Connections (placeholder - would need SVG implementation) */}
          {flow.connections.map(connection => {
            const sourceNode = flow.nodes.find(n => n.id === connection.sourceNodeId);
            const targetNode = flow.nodes.find(n => n.id === connection.targetNodeId);
            if (!sourceNode || !targetNode) return null;

            return (
              <Box
                key={connection.id}
                sx={{
                  position: 'absolute',
                  left: Math.min(sourceNode.position.x + 180, targetNode.position.x),
                  top: Math.min(sourceNode.position.y + 30, targetNode.position.y + 30),
                  width: Math.abs(targetNode.position.x - sourceNode.position.x - 180),
                  height: Math.abs(targetNode.position.y - sourceNode.position.y),
                  borderBottom: '2px solid #666',
                  zIndex: -1
                }}
              />
            );
          })}
        </Box>
      </Paper>

      {/* Node Menu */}
      <Menu
        anchorEl={nodeMenuAnchor}
        open={Boolean(nodeMenuAnchor)}
        onClose={() => setNodeMenuAnchor(null)}
        PaperProps={{ sx: { maxHeight: 400, width: 300 } }}
      >
        {Object.entries(nodeCategories).map(([category, templates]) => (
          <Box key={category}>
            <Typography variant="subtitle2" sx={{ px: 2, py: 1, textTransform: 'capitalize' }}>
              {category}
            </Typography>
            {templates.map(({ key, config }) => (
              <MenuItemComponent
                key={key}
                onClick={() => addNode(key, { x: 100, y: 100 })}
              >
                <ListItemIcon>{config.icon}</ListItemIcon>
                <ListItemText 
                  primary={key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                  secondary={config.description}
                  secondaryTypographyProps={{ variant: 'caption' }}
                />
              </MenuItemComponent>
            ))}
            <Divider />
          </Box>
        ))}
      </Menu>

      {/* Empty State */}
      {flow.nodes.length === 0 && (
        <Box sx={{
          position: 'absolute',
          inset: 0,
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          pointerEvents: 'none'
        }}>
          <Hub sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
          <Typography variant="h6" color="text.secondary" gutterBottom>
            No Logic Nodes
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Click "Add Node" to start building your logic flow
          </Typography>
        </Box>
      )}
    </Box>
  );
};
