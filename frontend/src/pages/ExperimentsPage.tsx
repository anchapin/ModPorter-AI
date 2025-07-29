import React, { useState, useEffect } from 'react';
import { 
  Box, 
  Button, 
  Card, 
  CardContent, 
  CardHeader, 
  Chip, 
  CircularProgress, 
  Dialog, 
  DialogActions, 
  DialogContent, 
  DialogContentText, 
  DialogTitle, 
  FormControl, 
  Grid, 
  IconButton, 
  InputLabel, 
  MenuItem, 
  Select, 
  Table, 
  TableBody, 
  TableCell, 
  TableContainer, 
  TableHead, 
  TableRow, 
  TextField, 
  Typography 
} from '@mui/material';
import { 
  Add as AddIcon, 
  Delete as DeleteIcon, 
  Edit as EditIcon,
  PlayArrow as PlayIcon,
  Pause as PauseIcon,
  Stop as StopIcon
} from '@mui/icons-material';
import { format } from 'date-fns';
import {
  fetchExperiments,
  createExperiment,
  updateExperiment,
  deleteExperiment,
  fetchExperimentVariants,
  createExperimentVariant,
  updateExperimentVariant,
  deleteExperimentVariant
} from '../services/experiments';
import { Experiment, ExperimentVariant } from '../types/experiment';


const ExperimentsPage: React.FC = () => {
  // State
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [selectedExperiment, setSelectedExperiment] = useState<Experiment | null>(null);
  const [variants, setVariants] = useState<ExperimentVariant[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [openExperimentDialog, setOpenExperimentDialog] = useState<boolean>(false);
  const [openVariantDialog, setOpenVariantDialog] = useState<boolean>(false);
  const [editingExperiment, setEditingExperiment] = useState<Experiment | null>(null);
  const [editingVariant, setEditingVariant] = useState<ExperimentVariant | null>(null);
  const [newVariantExperimentId, setNewVariantExperimentId] = useState<string>('');

  // Form states
  const [experimentForm, setExperimentForm] = useState<Omit<Experiment, 'id' | 'created_at' | 'updated_at'>>({
    name: '',
    description: '',
    start_date: null,
    end_date: null,
    status: 'draft',
    traffic_allocation: 100,
  });

  const [variantForm, setVariantForm] = useState<Omit<ExperimentVariant, 'id' | 'experiment_id' | 'created_at' | 'updated_at'>>({
    name: '',
    description: '',
    is_control: false,
    strategy_config: null,
  });

  // Fetch experiments on component mount
  useEffect(() => {
    const loadExperiments = async () => {
      try {
        setLoading(true);
        const data = await fetchExperiments();
        setExperiments(data);
      } catch (err) {
        setError('Failed to load experiments');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    loadExperiments();
  }, []);

  // Fetch variants when an experiment is selected
  useEffect(() => {
    const loadVariants = async () => {
      if (!selectedExperiment) {
        setVariants([]);
        return;
      }

      try {
        const data = await fetchExperimentVariants(selectedExperiment.id);
        setVariants(data);
      } catch (err) {
        setError('Failed to load experiment variants');
        console.error(err);
      }
    };

    loadVariants();
  }, [selectedExperiment]);

  // Handle experiment form changes
  const handleExperimentFormChange = (field: keyof Omit<Experiment, 'id' | 'created_at' | 'updated_at'>, value: any) => {
    setExperimentForm(prev => ({
      ...prev,
      [field]: value,
    }));
  };

  // Handle variant form changes
  const handleVariantFormChange = (field: keyof Omit<ExperimentVariant, 'id' | 'experiment_id' | 'created_at' | 'updated_at'>, value: any) => {
    setVariantForm(prev => ({
      ...prev,
      [field]: value,
    }));
  };

  // Handle experiment form submit
  const handleExperimentSubmit = async () => {
    try {
      if (editingExperiment) {
        // Update existing experiment
        const updated = await updateExperiment(editingExperiment.id, experimentForm);
        setExperiments(prev => prev.map(exp => exp.id === updated.id ? updated : exp));
      } else {
        // Create new experiment
        const created = await createExperiment(experimentForm);
        setExperiments(prev => [...prev, created]);
      }
      
      // Reset form and close dialog
      setExperimentForm({
        name: '',
        description: '',
        start_date: null,
        end_date: null,
        status: 'draft',
        traffic_allocation: 100,
      });
      setEditingExperiment(null);
      setOpenExperimentDialog(false);
    } catch (err) {
      setError('Failed to save experiment');
      console.error(err);
    }
  };

  // Handle variant form submit
  const handleVariantSubmit = async () => {
    if (!newVariantExperimentId) return;

    try {
      if (editingVariant) {
        // Update existing variant
        const updated = await updateExperimentVariant(newVariantExperimentId, editingVariant.id, variantForm);
        setVariants(prev => prev.map(variant => variant.id === updated.id ? updated : variant));
      } else {
        // Create new variant
        const created = await createExperimentVariant(newVariantExperimentId, variantForm);
        setVariants(prev => [...prev, created]);
      }
      
      // Reset form and close dialog
      setVariantForm({
        name: '',
        description: '',
        is_control: false,
        strategy_config: null,
      });
      setEditingVariant(null);
      setOpenVariantDialog(false);
    } catch (err) {
      setError('Failed to save variant');
      console.error(err);
    }
  };

  // Handle experiment edit
  const handleEditExperiment = (experiment: Experiment) => {
    setEditingExperiment(experiment);
    setExperimentForm({
      name: experiment.name,
      description: experiment.description,
      start_date: experiment.start_date,
      end_date: experiment.end_date,
      status: experiment.status,
      traffic_allocation: experiment.traffic_allocation,
    });
    setOpenExperimentDialog(true);
  };

  // Handle variant edit
  const handleEditVariant = (variant: ExperimentVariant) => {
    setEditingVariant(variant);
    setNewVariantExperimentId(variant.experiment_id);
    setVariantForm({
      name: variant.name,
      description: variant.description,
      is_control: variant.is_control,
      strategy_config: variant.strategy_config,
    });
    setOpenVariantDialog(true);
  };

  // Handle experiment delete
  const handleDeleteExperiment = async (id: string) => {
    try {
      await deleteExperiment(id);
      setExperiments(prev => prev.filter(exp => exp.id !== id));
      if (selectedExperiment?.id === id) {
        setSelectedExperiment(null);
      }
    } catch (err) {
      setError('Failed to delete experiment');
      console.error(err);
    }
  };

  // Handle variant delete
  const handleDeleteVariant = async (experimentId: string, variantId: string) => {
    try {
      await deleteExperimentVariant(experimentId, variantId);
      setVariants(prev => prev.filter(variant => variant.id !== variantId));
    } catch (err) {
      setError('Failed to delete variant');
      console.error(err);
    }
  };

  // Handle experiment status change
  const handleExperimentStatusChange = async (id: string, status: 'active' | 'paused' | 'completed') => {
    try {
      const updated = await updateExperiment(id, { status });
      setExperiments(prev => prev.map(exp => exp.id === id ? updated : exp));
      if (selectedExperiment?.id === id) {
        setSelectedExperiment(updated);
      }
    } catch (err) {
      setError('Failed to update experiment status');
      console.error(err);
    }
  };

  // Format date for display
  /* const formatDate = (dateString: string | null) => {
    if (!dateString) return 'N/A';
    return format(new Date(dateString), 'MMM dd, yyyy HH:mm');
  }; */

  // Get status chip color
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'success';
      case 'paused': return 'warning';
      case 'completed': return 'info';
      default: return 'default';
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">A/B Testing Experiments</Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => {
            setEditingExperiment(null);
            setExperimentForm({
              name: '',
              description: '',
              start_date: null,
              end_date: null,
              status: 'draft',
              traffic_allocation: 100,
            });
            setOpenExperimentDialog(true);
          }}
        >
          New Experiment
        </Button>
      </Box>

      {error && (
        <Box mb={3}>
          <Typography color="error">{error}</Typography>
        </Box>
      )}

      <Grid container spacing={3}>
        {/* Experiments List */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardHeader title="Experiments" />
            <CardContent>
              <TableContainer>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>Name</TableCell>
                      <TableCell>Status</TableCell>
                      <TableCell>Traffic</TableCell>
                      <TableCell>Actions</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {experiments.map(experiment => (
                      <TableRow 
                        key={experiment.id} 
                        selected={selectedExperiment?.id === experiment.id}
                        onClick={() => setSelectedExperiment(experiment)}
                        style={{ cursor: 'pointer' }}
                      >
                        <TableCell>{experiment.name}</TableCell>
                        <TableCell>
                          <Chip 
                            label={experiment.status} 
                            color={getStatusColor(experiment.status) as any} 
                            size="small"
                          />
                        </TableCell>
                        <TableCell>{experiment.traffic_allocation}%</TableCell>
                        <TableCell>
                          <IconButton 
                            size="small" 
                            onClick={(e) => {
                              e.stopPropagation();
                              handleEditExperiment(experiment);
                            }}
                          >
                            <EditIcon fontSize="small" />
                          </IconButton>
                          <IconButton 
                            size="small" 
                            onClick={(e) => {
                              e.stopPropagation();
                              handleDeleteExperiment(experiment.id);
                            }}
                          >
                            <DeleteIcon fontSize="small" />
                          </IconButton>
                          {experiment.status === 'draft' && (
                            <IconButton 
                              size="small" 
                              onClick={(e) => {
                                e.stopPropagation();
                                handleExperimentStatusChange(experiment.id, 'active');
                              }}
                            >
                              <PlayIcon fontSize="small" />
                            </IconButton>
                          )}
                          {experiment.status === 'active' && (
                            <IconButton 
                              size="small" 
                              onClick={(e) => {
                                e.stopPropagation();
                                handleExperimentStatusChange(experiment.id, 'paused');
                              }}
                            >
                              <PauseIcon fontSize="small" />
                            </IconButton>
                          )}
                          {(experiment.status === 'active' || experiment.status === 'paused') && (
                            <IconButton 
                              size="small" 
                              onClick={(e) => {
                                e.stopPropagation();
                                handleExperimentStatusChange(experiment.id, 'completed');
                              }}
                            >
                              <StopIcon fontSize="small" />
                            </IconButton>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>
        </Grid>

        {/* Variants List */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardHeader 
              title={selectedExperiment ? `Variants for ${selectedExperiment.name}` : "Select an Experiment"}
              action={
                selectedExperiment && (
                  <Button
                    size="small"
                    startIcon={<AddIcon />}
                    onClick={() => {
                      setEditingVariant(null);
                      setNewVariantExperimentId(selectedExperiment.id);
                      setVariantForm({
                        name: '',
                        description: '',
                        is_control: false,
                        strategy_config: null,
                      });
                      setOpenVariantDialog(true);
                    }}
                  >
                    Add Variant
                  </Button>
                )
              }
            />
            <CardContent>
              {selectedExperiment ? (
                <TableContainer>
                  <Table>
                    <TableHead>
                      <TableRow>
                        <TableCell>Name</TableCell>
                        <TableCell>Control</TableCell>
                        <TableCell>Actions</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {variants.map(variant => (
                        <TableRow key={variant.id}>
                          <TableCell>
                            {variant.name}
                            {variant.is_control && (
                              <Chip 
                                label="Control" 
                                size="small" 
                                sx={{ ml: 1 }}
                              />
                            )}
                          </TableCell>
                          <TableCell>
                            {variant.is_control ? 'Yes' : 'No'}
                          </TableCell>
                          <TableCell>
                            <IconButton 
                              size="small" 
                              onClick={() => handleEditVariant(variant)}
                            >
                              <EditIcon fontSize="small" />
                            </IconButton>
                            <IconButton 
                              size="small" 
                              onClick={() => handleDeleteVariant(selectedExperiment.id, variant.id)}
                            >
                              <DeleteIcon fontSize="small" />
                            </IconButton>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              ) : (
                <Typography>Select an experiment to view its variants</Typography>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Experiment Dialog */}
      <Dialog open={openExperimentDialog} onClose={() => setOpenExperimentDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>
          {editingExperiment ? 'Edit Experiment' : 'Create New Experiment'}
        </DialogTitle>
        <DialogContent>
          <DialogContentText sx={{ mb: 2 }}>
            {editingExperiment 
              ? 'Update the details of your experiment' 
              : 'Create a new A/B testing experiment'}
          </DialogContentText>
          
          <TextField
            autoFocus
            margin="dense"
            label="Name"
            fullWidth
            value={experimentForm.name}
            onChange={(e) => handleExperimentFormChange('name', e.target.value)}
            sx={{ mb: 2 }}
          />
          
          <TextField
            margin="dense"
            label="Description"
            fullWidth
            multiline
            rows={3}
            value={experimentForm.description}
            onChange={(e) => handleExperimentFormChange('description', e.target.value)}
            sx={{ mb: 2 }}
          />
          
          <FormControl fullWidth sx={{ mb: 2 }}>
            <InputLabel>Status</InputLabel>
            <Select
              value={experimentForm.status}
              onChange={(e) => handleExperimentFormChange('status', e.target.value as any)}
              label="Status"
            >
              <MenuItem value="draft">Draft</MenuItem>
              <MenuItem value="active">Active</MenuItem>
              <MenuItem value="paused">Paused</MenuItem>
              <MenuItem value="completed">Completed</MenuItem>
            </Select>
          </FormControl>
          
          <TextField
            margin="dense"
            label="Traffic Allocation (%)"
            fullWidth
            type="number"
            InputProps={{ inputProps: { min: 0, max: 100 } }}
            value={experimentForm.traffic_allocation}
            onChange={(e) => handleExperimentFormChange('traffic_allocation', parseInt(e.target.value) || 0)}
            sx={{ mb: 2 }}
          />
          
          <TextField
            margin="dense"
            label="Start Date"
            fullWidth
            type="datetime-local"
            InputLabelProps={{ shrink: true }}
            value={experimentForm.start_date ? format(new Date(experimentForm.start_date), "yyyy-MM-dd'T'HH:mm") : ''}
            onChange={(e) => handleExperimentFormChange('start_date', e.target.value || null)}
            sx={{ mb: 2 }}
          />
          
          <TextField
            margin="dense"
            label="End Date"
            fullWidth
            type="datetime-local"
            InputLabelProps={{ shrink: true }}
            value={experimentForm.end_date ? format(new Date(experimentForm.end_date), "yyyy-MM-dd'T'HH:mm") : ''}
            onChange={(e) => handleExperimentFormChange('end_date', e.target.value || null)}
            sx={{ mb: 2 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenExperimentDialog(false)}>Cancel</Button>
          <Button onClick={handleExperimentSubmit} variant="contained">
            {editingExperiment ? 'Update' : 'Create'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Variant Dialog */}
      <Dialog open={openVariantDialog} onClose={() => setOpenVariantDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>
          {editingVariant ? 'Edit Variant' : 'Create New Variant'}
        </DialogTitle>
        <DialogContent>
          <DialogContentText sx={{ mb: 2 }}>
            {editingVariant 
              ? 'Update the details of your experiment variant' 
              : 'Create a new variant for your experiment'}
          </DialogContentText>
          
          <TextField
            autoFocus
            margin="dense"
            label="Name"
            fullWidth
            value={variantForm.name}
            onChange={(e) => handleVariantFormChange('name', e.target.value)}
            sx={{ mb: 2 }}
          />
          
          <TextField
            margin="dense"
            label="Description"
            fullWidth
            multiline
            rows={3}
            value={variantForm.description}
            onChange={(e) => handleVariantFormChange('description', e.target.value)}
            sx={{ mb: 2 }}
          />
          
          <FormControl fullWidth sx={{ mb: 2 }}>
            <InputLabel>Is Control Variant</InputLabel>
            <Select
              value={variantForm.is_control ? 'true' : 'false'}
              onChange={(e) => handleVariantFormChange('is_control', e.target.value === 'true')}
              label="Is Control Variant"
            >
              <MenuItem value="false">No</MenuItem>
              <MenuItem value="true">Yes</MenuItem>
            </Select>
          </FormControl>
          
          <TextField
            margin="dense"
            label="Strategy Configuration (JSON)"
            fullWidth
            multiline
            rows={4}
            value={variantForm.strategy_config ? JSON.stringify(variantForm.strategy_config, null, 2) : ''}
            onChange={(e) => {
              try {
                const parsed = e.target.value ? JSON.parse(e.target.value) : null;
                handleVariantFormChange('strategy_config', parsed);
              } catch {
                // Invalid JSON, ignore for now
              }
            }}
            sx={{ mb: 2 }}
            placeholder='{"agent_name": {"model": "gpt-4", "temperature": 0.7}}'
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenVariantDialog(false)}>Cancel</Button>
          <Button onClick={handleVariantSubmit} variant="contained">
            {editingVariant ? 'Update' : 'Create'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default ExperimentsPage;