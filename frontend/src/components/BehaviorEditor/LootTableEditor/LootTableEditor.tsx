import React, { useState, useCallback } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  IconButton,
  Grid,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Chip,
  Alert,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Switch,
  FormControlLabel
} from '@mui/material';
import {
  Delete,
  Edit,
  ExpandMore,
  Inventory2,
  Save,
  Preview,
  Add
} from '@mui/icons-material';

// Loot table interfaces
export interface LootPool {
  id: string;
  name: string;
  conditions: LootCondition[];
  functions: LootFunction[];
  entries: LootEntry[];
  rolls: {
    min?: number;
    max?: number;
    type: 'exact' | 'range';
    value: number;
  };
  bonus_rolls?: {
    min?: number;
    max?: number;
    type: 'exact' | 'range';
    value: number;
  };
}

export interface LootEntry {
  id: string;
  type: 'item' | 'tag' | 'loot_table' | 'empty';
  name: string;
  weight: number;
  quality?: number;
  conditions: LootCondition[];
  functions: LootFunction[];
  children?: LootEntry[];
}

export interface LootCondition {
  id: string;
  condition: string;
  parameters: Record<string, any>;
}

export interface LootFunction {
  id: string;
  function: string;
  parameters: Record<string, any>;
}

export interface LootTable {
  id: string;
  type: string; // 'entity', 'block', 'gift', 'advancement_reward', etc.
  pools: LootPool[];
  functions?: LootFunction[];
  conditions?: LootCondition[];
}

interface LootTableEditorProps {
  lootTable?: LootTable;
  onLootTableChange?: (lootTable: LootTable) => void;
  onPreview?: (lootTable: LootTable) => void;
  onSave?: (lootTable: LootTable) => void;
  readOnly?: boolean;
}

export const LootTableEditor: React.FC<LootTableEditorProps> = ({
  lootTable: initialLootTable,
  onLootTableChange,
  onPreview,
  onSave,
  readOnly = false
}) => {
  const [lootTable, setLootTable] = useState<LootTable>(
    initialLootTable || {
      id: '',
      type: 'entity',
      pools: []
    }
  );
  const [expandedPool, setExpandedPool] = useState<string | false>(false);
  const [conditionDialogOpen, setConditionDialogOpen] = useState(false);
  const [functionDialogOpen, setFunctionDialogOpen] = useState(false);
  const [previewData, setPreviewData] = useState<any>(null);
  const [previewOpen, setPreviewOpen] = useState(false);





  // Update loot table and notify parent
  const updateLootTable = useCallback((newLootTable: LootTable) => {
    setLootTable(newLootTable);
    onLootTableChange?.(newLootTable);
  }, [onLootTableChange]);

  // Add new pool
  const addPool = useCallback(() => {
    const newPool: LootPool = {
      id: `pool_${Date.now()}`,
      name: `Pool ${lootTable.pools.length + 1}`,
      conditions: [],
      functions: [],
      entries: [],
      rolls: { type: 'exact', value: 1 }
    };
    updateLootTable({
      ...lootTable,
      pools: [...lootTable.pools, newPool]
    });
  }, [lootTable, updateLootTable]);

  // Delete pool
  const deletePool = useCallback((poolId: string) => {
    updateLootTable({
      ...lootTable,
      pools: lootTable.pools.filter(p => p.id !== poolId)
    });
  }, [lootTable, updateLootTable]);

  // Update pool
  const updatePool = useCallback((poolId: string, updates: Partial<LootPool>) => {
    updateLootTable({
      ...lootTable,
      pools: lootTable.pools.map(p => 
        p.id === poolId ? { ...p, ...updates } : p
      )
    });
  }, [lootTable, updateLootTable]);

  // Add entry to pool
  const addEntry = useCallback((poolId: string) => {
    const newEntry: LootEntry = {
      id: `entry_${Date.now()}`,
      type: 'item',
      name: 'minecraft:air',
      weight: 1,
      conditions: [],
      functions: []
    };
    updatePool(poolId, {
      entries: [...lootTable.pools.find(p => p.id === poolId)!.entries, newEntry]
    });
  }, [lootTable, updatePool]);

  // Delete entry
  const deleteEntry = useCallback((poolId: string, entryId: string) => {
    updatePool(poolId, {
      entries: lootTable.pools.find(p => p.id === poolId)!.entries.filter(e => e.id !== entryId)
    });
  }, [lootTable, updatePool]);

  // Update entry
  const updateEntry = useCallback((poolId: string, entryId: string, updates: Partial<LootEntry>) => {
    updatePool(poolId, {
      entries: lootTable.pools.find(p => p.id === poolId)!.entries.map(e => 
        e.id === entryId ? { ...e, ...updates } : e
      )
    });
  }, [lootTable, updatePool]);

  // Add condition to pool or entry
  const addCondition = useCallback((target: { type: 'pool' | 'entry'; id: string; poolId?: string }) => {
    const newCondition: LootCondition = {
      id: `condition_${Date.now()}`,
      condition: 'minecraft:killed_by_player',
      parameters: {}
    };
    setConditionDialogOpen(true);
    
    // Apply condition after dialog closes
    setTimeout(() => {
      if (target.type === 'pool') {
        updatePool(target.id, {
          conditions: [...lootTable.pools.find(p => p.id === target.id)!.conditions, newCondition]
        });
      } else {
        updateEntry(target.poolId!, target.id, {
          conditions: [...lootTable.pools.find(p => p.id === target.poolId)!.entries.find(e => e.id === target.id)!.conditions, newCondition]
        });
      }
    }, 100);
  }, [lootTable, updatePool, updateEntry]);

  // Add function to pool or entry
  const addFunction = useCallback((target: { type: 'pool' | 'entry'; id: string; poolId?: string }) => {
    const newFunction: LootFunction = {
      id: `function_${Date.now()}`,
      function: 'minecraft:set_count',
      parameters: {}
    };
    setFunctionDialogOpen(true);
    
    // Apply function after dialog closes
    setTimeout(() => {
      if (target.type === 'pool') {
        updatePool(target.id, {
          functions: [...lootTable.pools.find(p => p.id === target.id)!.functions, newFunction]
        });
      } else {
        updateEntry(target.poolId!, target.id, {
          functions: [...lootTable.pools.find(p => p.id === target.poolId)!.entries.find(e => e.id === target.id)!.functions, newFunction]
        });
      }
    }, 100);
  }, [lootTable, updatePool, updateEntry]);

  // Generate preview data
  const generatePreview = useCallback(() => {
    const preview = {
      ...lootTable,
      generated_at: new Date().toISOString(),
      pool_count: lootTable.pools.length,
      total_entries: lootTable.pools.reduce((sum, pool) => sum + pool.entries.length, 0)
    };
    setPreviewData(preview);
    setPreviewOpen(true);
    onPreview?.(lootTable);
  }, [lootTable, onPreview]);

  // Export to JSON
  const exportToJSON = useCallback(() => {
    const json = JSON.stringify(lootTable, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${lootTable.id || 'loot_table'}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }, [lootTable]);

  return (
    <Box sx={{ p: 2, height: '100%', overflow: 'auto' }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h5">Loot Table Editor</Typography>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button
            variant="outlined"
            startIcon={<Preview />}
            onClick={generatePreview}
            disabled={lootTable.pools.length === 0}
          >
            Preview
          </Button>
          <Button
            variant="outlined"
            startIcon={<Save />}
            onClick={() => onSave?.(lootTable)}
            disabled={readOnly}
          >
            Save
          </Button>
          <Button
            variant="outlined"
            onClick={exportToJSON}
          >
            Export JSON
          </Button>
        </Box>
      </Box>

      {/* Basic Info */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>Basic Information</Typography>
          <Grid container spacing={2}>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Loot Table ID"
                value={lootTable.id}
                onChange={(e) => updateLootTable({ ...lootTable, id: e.target.value })}
                disabled={readOnly}
                placeholder="minecraft:entities/zombie"
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <FormControl fullWidth>
                <Label>Type</Label>
                <Select
                  value={lootTable.type}
                  onChange={(e) => updateLootTable({ ...lootTable, type: e.target.value })}
                  disabled={readOnly}
                >
                  <MenuItem value="entity">Entity</MenuItem>
                  <MenuItem value="block">Block</MenuItem>
                  <MenuItem value="gift">Gift</MenuItem>
                  <MenuItem value="advancement_reward">Advancement Reward</MenuItem>
                  <MenuItem value="selector">Selector</MenuItem>
                </Select>
              </FormControl>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Info Alert */}
      <Alert severity="info" sx={{ mb: 2 }}>
        This is a placeholder implementation for the Loot Table Editor. Full functionality including:
        visual condition editing, function configuration, and real-time preview will be implemented in the next phase.
      </Alert>

      {/* Pools Section */}
      <Box sx={{ mb: 3 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6">Loot Pools</Typography>
          <Button
            variant="contained"
            startIcon={<Add />}
            onClick={addPool}
            disabled={readOnly}
            size="small"
          >
            Add Pool
          </Button>
        </Box>

        {lootTable.pools.length === 0 ? (
          <Card>
            <CardContent sx={{ textAlign: 'center', py: 4 }}>
              <Inventory2 sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
              <Typography variant="body2" color="text.secondary">
                No loot pools defined. Add a pool to start configuring drops.
              </Typography>
            </CardContent>
          </Card>
        ) : (
          lootTable.pools.map((pool) => (
            <Accordion
              key={pool.id}
              expanded={expandedPool === pool.id}
              onChange={(_, isExpanded) => setExpandedPool(isExpanded ? pool.id : false)}
              sx={{ mb: 1 }}
            >
              <AccordionSummary expandIcon={<ExpandMore />}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%', mr: 2 }}>
                  <Typography variant="subtitle1">{pool.name}</Typography>
                  <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                    <Chip 
                      label={`${pool.entries.length} entries`} 
                      size="small" 
                      color="primary" 
                      variant="outlined"
                    />
                    <Chip 
                      label={pool.rolls.type === 'exact' ? `${pool.rolls.value} rolls` : `${pool.rolls.min}-${pool.rolls.max} rolls`} 
                      size="small" 
                    />
                    {!readOnly && (
                      <IconButton
                        size="small"
                        onClick={(e) => {
                          e.stopPropagation();
                          deletePool(pool.id);
                        }}
                      >
                        <Delete />
                      </IconButton>
                    )}
                  </Box>
                </Box>
              </AccordionSummary>
              
              <AccordionDetails>
                <Grid container spacing={2}>
                  {/* Pool Settings */}
                  <Grid item xs={12} md={6}>
                    <TextField
                      fullWidth
                      label="Pool Name"
                      value={pool.name}
                      onChange={(e) => updatePool(pool.id, { name: e.target.value })}
                      disabled={readOnly}
                      size="small"
                    />
                  </Grid>
                  <Grid item xs={12} md={6}>
                    <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                      <TextField
                        label="Rolls"
                        type="number"
                        value={pool.rolls.value}
                        onChange={(e) => updatePool(pool.id, { 
                          rolls: { ...pool.rolls, value: parseInt(e.target.value) || 0 }
                        })}
                        disabled={readOnly}
                        size="small"
                        sx={{ width: '100px' }}
                      />
                      <FormControlLabel
                        control={
                          <Switch
                            checked={pool.rolls.type === 'range'}
                            onChange={(e) => updatePool(pool.id, { 
                              rolls: { ...pool.rolls, type: e.target.checked ? 'range' : 'exact' }
                            })}
                            disabled={readOnly}
                            size="small"
                          />
                        }
                        label="Range"
                      />
                    </Box>
                  </Grid>

                  {/* Pool Actions */}
                  <Grid item xs={12}>
                    <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
                      <Button
                        variant="outlined"
                        size="small"
                        startIcon={<Add />}
                        onClick={() => addCondition({ type: 'pool', id: pool.id })}
                        disabled={readOnly}
                      >
                        Add Condition
                      </Button>
                      <Button
                        variant="outlined"
                        size="small"
                        startIcon={<functions />}
                        onClick={() => addFunction({ type: 'pool', id: pool.id })}
                        disabled={readOnly}
                      >
                        Add Function
                      </Button>
                      <Button
                        variant="contained"
                        size="small"
                        startIcon={<Add />}
                        onClick={() => addEntry(pool.id)}
                        disabled={readOnly}
                      >
                        Add Entry
                      </Button>
                    </Box>

                    {/* Entries */}
                    {pool.entries.map((entry) => (
                      <Card key={entry.id} sx={{ mb: 1, ml: 2 }}>
                        <CardContent sx={{ py: 1 }}>
                          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <Box>
                              <Typography variant="body2" fontWeight="bold">
                                {entry.name}
                              </Typography>
                              <Typography variant="caption" color="text.secondary">
                                Type: {entry.type} | Weight: {entry.weight}
                                {entry.quality && ` | Quality: ${entry.quality}`}
                              </Typography>
                            </Box>
                            <Box sx={{ display: 'flex', gap: 0.5 }}>
                              {!readOnly && (
                                <>
                                  <IconButton size="small">
                                    <Edit />
                                  </IconButton>
                                  <IconButton
                                    size="small"
                                    onClick={() => deleteEntry(pool.id, entry.id)}
                                  >
                                    <Delete />
                                  </IconButton>
                                </>
                              )}
                            </Box>
                          </Box>
                        </CardContent>
                      </Card>
                    ))}
                  </Grid>
                </Grid>
              </AccordionDetails>
            </Accordion>
          ))
        )}
      </Box>

      {/* Preview Dialog */}
      <Dialog open={previewOpen} onClose={() => setPreviewOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>Loot Table Preview</DialogTitle>
        <DialogContent>
          <pre style={{ fontSize: '12px', maxHeight: '400px', overflow: 'auto' }}>
            {JSON.stringify(previewData, null, 2)}
          </pre>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPreviewOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>

      {/* Condition Dialog */}
      <Dialog open={conditionDialogOpen} onClose={() => setConditionDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Add Condition</DialogTitle>
        <DialogContent>
          <Alert severity="info">
            Condition configuration will be available in the next implementation phase.
          </Alert>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConditionDialogOpen(false)}>Cancel</Button>
        </DialogActions>
      </Dialog>

      {/* Function Dialog */}
      <Dialog open={functionDialogOpen} onClose={() => setFunctionDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Add Function</DialogTitle>
        <DialogContent>
          <Alert severity="info">
            Function configuration will be available in the next implementation phase.
          </Alert>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setFunctionDialogOpen(false)}>Cancel</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

// Helper component for the label
const Label: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <InputLabel sx={{ mb: 0.5, fontSize: '0.875rem' }}>{children}</InputLabel>
);
