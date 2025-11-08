import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  CardActions,
  Typography,
  Button,
  Chip,
  Grid,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Pagination,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  LinearProgress,
  Alert,
  Collapse,
} from '@mui/material';
import {
  Search,
  FilterList,
  Info,
  Close,
  CheckCircle,
  ExpandMore,
  ExpandLess,
} from '@mui/icons-material';
import { useTemplates } from '../../../contexts/BehaviorTemplatesContext';
import { BehaviorTemplate, BehaviorTemplateCategory } from '../../../services/api';

interface TemplateSelectorProps {
  onTemplateSelect: (template: BehaviorTemplate) => void;
  onTemplateApply?: (template: BehaviorTemplate) => void;
  category?: string;
  templateType?: string;
  excludeTemplateIds?: string[];
  showApplyButton?: boolean;
  disabled?: boolean;
}

export const TemplateSelector: React.FC<TemplateSelectorProps> = ({
  onTemplateSelect,
  onTemplateApply,
  category,
  templateType,
  excludeTemplateIds = [],
  showApplyButton = false,
  disabled = false,
}) => {
  const { state, actions } = useTemplates();
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>(category || '');
  const [selectedTemplateType, setSelectedTemplateType] = useState<string>(templateType || '');
  const [showFilters, setShowFilters] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState<BehaviorTemplate | null>(null);
  const [previewDialogOpen, setPreviewDialogOpen] = useState(false);
  const [applyingTemplate, setApplyingTemplate] = useState<string | null>(null);
  const [applySuccess, setApplySuccess] = useState<string | null>(null);

  // Apply filters
  useEffect(() => {
    const filters: any = {};
    if (searchTerm) filters.search = searchTerm;
    if (selectedCategory) filters.category = selectedCategory;
    if (selectedTemplateType) filters.template_type = selectedTemplateType;
    if (excludeTemplateIds.length > 0) {
      // Note: This would need to be implemented in the API
      // For now, we'll filter on the client side
    }
    actions.setFilters(filters);
  }, [searchTerm, selectedCategory, selectedTemplateType, excludeTemplateIds.length, actions]);

  // Filter templates on client side for excludeTemplateIds
  const filteredTemplates = state.templates.filter(
    template => !excludeTemplateIds.includes(template.id)
  );

  const handleTemplateSelect = (template: BehaviorTemplate) => {
    setSelectedTemplate(template);
    onTemplateSelect(template);
  };

  const handleTemplatePreview = (template: BehaviorTemplate) => {
    setSelectedTemplate(template);
    setPreviewDialogOpen(true);
  };

  const handleApplyTemplate = async (template: BehaviorTemplate) => {
    if (!onTemplateApply || disabled) return;
    
    try {
      setApplyingTemplate(template.id);
      await onTemplateApply(template);
      setApplySuccess(template.id);
      setTimeout(() => setApplySuccess(null), 3000);
    } catch (error) {
      console.error('Failed to apply template:', error);
    } finally {
      setApplyingTemplate(null);
    }
  };

  const handlePageChange = (event: React.ChangeEvent<unknown>, value: number) => {
    actions.loadTemplates();
  };

  const getCategoryDisplayName = (categoryName: string) => {
    const category = state.categories.find(cat => cat.name === categoryName);
    return category?.display_name || categoryName;
  };

  const getCategoryIcon = (categoryName: string) => {
    const category = state.categories.find(cat => cat.name === categoryName);
    return category?.icon || '📄';
  };

  return (
    <Box>
      {/* Search and Filters */}
      <Box sx={{ mb: 3 }}>
        <Grid container spacing={2} alignItems="center">
          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              placeholder="Search templates..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              InputProps={{
                startAdornment: <Search sx={{ mr: 1, color: 'text.secondary' }} />,
              }}
              disabled={disabled}
            />
          </Grid>
          <Grid item xs={12} md={6}>
            <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
              <IconButton
                onClick={() => setShowFilters(!showFilters)}
                disabled={disabled}
              >
                <FilterList />
              </IconButton>
              <Typography variant="body2" color="text.secondary">
                {filteredTemplates.length} templates found
              </Typography>
            </Box>
          </Grid>
        </Grid>

        <Collapse in={showFilters}>
          <Box sx={{ mt: 2 }}>
            <Grid container spacing={2}>
              <Grid item xs={12} md={6}>
                <FormControl fullWidth size="small">
                  <InputLabel>Category</InputLabel>
                  <Select
                    value={selectedCategory}
                    onChange={(e) => setSelectedCategory(e.target.value)}
                    label="Category"
                    disabled={disabled}
                  >
                    <MenuItem value="">All Categories</MenuItem>
                    {state.categories.map((cat) => (
                      <MenuItem key={cat.name} value={cat.name}>
                        {cat.icon && <span style={{ marginRight: 8 }}>{cat.icon}</span>}
                        {cat.display_name}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} md={6}>
                <FormControl fullWidth size="small">
                  <InputLabel>Template Type</InputLabel>
                  <Select
                    value={selectedTemplateType}
                    onChange={(e) => setSelectedTemplateType(e.target.value)}
                    label="Template Type"
                    disabled={disabled}
                  >
                    <MenuItem value="">All Types</MenuItem>
                    <MenuItem value="simple_block">Simple Block</MenuItem>
                    <MenuItem value="custom_block">Custom Block</MenuItem>
                    <MenuItem value="entity_behavior">Entity Behavior</MenuItem>
                    <MenuItem value="shaped_crafting">Shaped Crafting</MenuItem>
                    <MenuItem value="shapeless_crafting">Shapeless Crafting</MenuItem>
                    <MenuItem value="entity_drops">Entity Drops</MenuItem>
                    <MenuItem value="block_drops">Block Drops</MenuItem>
                    <MenuItem value="visual_logic">Visual Logic</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
            </Grid>
          </Box>
        </Collapse>
      </Box>

      {/* Loading State */}
      {state.loading && <LinearProgress sx={{ mb: 2 }} />}

      {/* Error State */}
      {state.error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {state.error}
        </Alert>
      )}

      {/* Template Grid */}
      <Grid container spacing={2}>
        {filteredTemplates.map((template) => (
          <Grid item xs={12} sm={6} lg={4} key={template.id}>
            <Card
              sx={{
                height: '100%',
                display: 'flex',
                flexDirection: 'column',
                cursor: disabled ? 'not-allowed' : 'pointer',
                border: selectedTemplate?.id === template.id ? 2 : 1,
                borderColor: selectedTemplate?.id === template.id ? 'primary.main' : 'divider',
                opacity: disabled ? 0.6 : 1,
              }}
              onClick={() => !disabled && handleTemplateSelect(template)}
            >
              <CardContent sx={{ flexGrow: 1 }}>
                <Box sx={{ display: 'flex', alignItems: 'flex-start', mb: 1 }}>
                  <Typography variant="h6" component="h3" sx={{ flexGrow: 1 }}>
                    {getCategoryIcon(template.category)} {template.name}
                  </Typography>
                  <Tooltip title="Preview template">
                    <IconButton
                      size="small"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleTemplatePreview(template);
                      }}
                      disabled={disabled}
                    >
                      <Info />
                    </IconButton>
                  </Tooltip>
                </Box>
                
                <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                  {template.description}
                </Typography>
                
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mb: 1 }}>
                  <Chip
                    size="small"
                    label={getCategoryDisplayName(template.category)}
                    color="primary"
                    variant="outlined"
                  />
                  <Chip
                    size="small"
                    label={template.template_type.replace(/_/g, ' ')}
                    variant="outlined"
                  />
                  {template.is_public && (
                    <Chip
                      size="small"
                      label="Public"
                      color="success"
                      variant="outlined"
                    />
                  )}
                </Box>

                {template.tags.length > 0 && (
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                    {template.tags.slice(0, 3).map((tag) => (
                      <Chip
                        key={tag}
                        size="small"
                        label={tag}
                        variant="filled"
                        sx={{ fontSize: '0.7rem' }}
                      />
                    ))}
                    {template.tags.length > 3 && (
                      <Chip
                        size="small"
                        label={`+${template.tags.length - 3}`}
                        variant="filled"
                        sx={{ fontSize: '0.7rem' }}
                      />
                    )}
                  </Box>
                )}
              </CardContent>
              
              <CardActions>
                {showApplyButton && onTemplateApply && (
                  <Button
                    size="small"
                    variant="contained"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleApplyTemplate(template);
                    }}
                    disabled={disabled || applyingTemplate === template.id}
                    startIcon={
                      applyingTemplate === template.id ? (
                        <LinearProgress sx={{ width: 16 }} />
                      ) : applySuccess === template.id ? (
                        <CheckCircle />
                      ) : null
                    }
                  >
                    {applyingTemplate === template.id ? 'Applying...' : 
                     applySuccess === template.id ? 'Applied!' : 'Apply'}
                  </Button>
                )}
                <Button
                  size="small"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleTemplatePreview(template);
                  }}
                  disabled={disabled}
                >
                  Preview
                </Button>
              </CardActions>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Load More */}
      {state.pagination.hasMore && !state.loading && (
        <Box sx={{ display: 'flex', justifyContent: 'center', mt: 3 }}>
          <Button
            onClick={() => actions.loadMore()}
            disabled={state.loading}
          >
            Load More
          </Button>
        </Box>
      )}

      {/* Preview Dialog */}
      <Dialog
        open={previewDialogOpen}
        onClose={() => setPreviewDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <Typography variant="h6">
              {selectedTemplate?.name}
            </Typography>
            <IconButton onClick={() => setPreviewDialogOpen(false)}>
              <Close />
            </IconButton>
          </Box>
        </DialogTitle>
        <DialogContent>
          {selectedTemplate && (
            <Box>
              <Typography variant="body1" sx={{ mb: 2 }}>
                {selectedTemplate.description}
              </Typography>
              
              <Box sx={{ display: 'flex', gap: 1, mb: 2, flexWrap: 'wrap' }}>
                <Chip label={`Category: ${getCategoryDisplayName(selectedTemplate.category)}`} />
                <Chip label={`Type: ${selectedTemplate.template_type}`} />
                <Chip label={`Version: ${selectedTemplate.version}`} />
                {selectedTemplate.is_public && <Chip label="Public" color="success" />}
              </Box>

              {selectedTemplate.tags.length > 0 && (
                <Box sx={{ mb: 2 }}>
                  <Typography variant="subtitle2" gutterBottom>
                    Tags:
                  </Typography>
                  <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                    {selectedTemplate.tags.map((tag) => (
                      <Chip key={tag} size="small" label={tag} />
                    ))}
                  </Box>
                </Box>
              )}

              <Box>
                <Typography variant="subtitle2" gutterBottom>
                  Template Data Preview:
                </Typography>
                <Box
                  sx={{
                    bgcolor: 'grey.100',
                    p: 2,
                    borderRadius: 1,
                    fontFamily: 'monospace',
                    fontSize: '0.875rem',
                    maxHeight: 300,
                    overflow: 'auto',
                  }}
                >
                  <pre>{JSON.stringify(selectedTemplate.template_data, null, 2)}</pre>
                </Box>
              </Box>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPreviewDialogOpen(false)}>
            Close
          </Button>
          {showApplyButton && onTemplateApply && selectedTemplate && (
            <Button
              variant="contained"
              onClick={() => {
                handleApplyTemplate(selectedTemplate);
                setPreviewDialogOpen(false);
              }}
              disabled={disabled || applyingTemplate === selectedTemplate.id}
            >
              Apply Template
            </Button>
          )}
        </DialogActions>
      </Dialog>
    </Box>
  );
};
