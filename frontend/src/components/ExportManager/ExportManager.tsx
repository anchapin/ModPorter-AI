import React, { useState } from 'react';
import {
  Box,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Typography,
  Grid,
  Card,
  CardContent,
  CardActions,
  Chip,
  Divider,
  Switch,
  FormControlLabel,
  TextField,
  MenuItem,
  FormControl,
  InputLabel,
  Select,
  LinearProgress,
  Alert,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Tooltip,
} from '@mui/material';
import {
  Download,
  Close,
  Settings,
  Info,
  CheckCircle,
  Error as ErrorIcon,
  ExpandMore,
  CloudDownload,
  Description,
  Archive,
  Code,
} from '@mui/icons-material';
import {
  useBehaviorExportPreview,
  useExportBehaviorPack,
  useDownloadBehaviorPack,
  useBehaviorExportFormats,
} from '../../hooks/useBehaviorQueries';
import { LoadingWrapper } from '../common/LoadingWrapper';
import { useToast } from '../common/Toast';

interface ExportManagerProps {
  conversionId: string;
  open: boolean;
  onClose: () => void;
}

interface ExportOptions {
  format: 'mcaddon' | 'zip' | 'json';
  includeTemplates: boolean;
  includeMetadata: boolean;
  compression: 'none' | 'standard' | 'maximum';
  customFileName?: string;
}

export const ExportManager: React.FC<ExportManagerProps> = ({
  conversionId,
  open,
  onClose,
}) => {
  const [exportOptions, setExportOptions] = useState<ExportOptions>({
    format: 'mcaddon',
    includeTemplates: true,
    includeMetadata: true,
    compression: 'standard',
  });
  const [showAdvanced, setShowAdvanced] = useState(false);

  const toast = useToast();
  const exportPreviewQuery = useBehaviorExportPreview(conversionId, {
    enabled: open,
  });
  const exportPackMutation = useExportBehaviorPack();
  const downloadPackMutation = useDownloadBehaviorPack();
  const exportFormatsQuery = useBehaviorExportFormats();

  const handleExport = async () => {
    try {
      const exportResult = await exportPackMutation.mutateAsync({
        conversion_id: conversionId,
        file_types: [], // All files
        include_templates: exportOptions.includeTemplates,
        export_format: exportOptions.format,
      });

      // Download immediately after export
      const { blob, filename } = await downloadPackMutation.mutateAsync({
        conversionId,
        format: exportOptions.format,
      });

      toast.success(`Export completed: ${exportResult.file_count} files`);
      onClose();
    } catch (error) {
      // Error is handled by the mutations
    }
  };

  const handleDownloadOnly = async () => {
    try {
      const { blob, filename } = await downloadPackMutation.mutateAsync({
        conversionId,
        format: exportOptions.format,
      });
      toast.success(`Downloaded: ${filename}`);
    } catch (error) {
      // Error is handled by the mutation
    }
  };

  const getFormatIcon = (format: string) => {
    switch (format) {
      case 'mcaddon': return <CloudDownload />;
      case 'zip': return <Archive />;
      case 'json': return <Code />;
      default: return <Download />;
    }
  };

  const getFormatDescription = (format: string) => {
    switch (format) {
      case 'mcaddon': return 'Minecraft add-on package (.mcaddon)';
      case 'zip': return 'Standard ZIP archive (.zip)';
      case 'json': return 'Raw JSON data (.json)';
      default: return 'Unknown format';
    }
  };

  const isLoading = exportPreviewQuery.isFetching || exportPackMutation.isPending || downloadPackMutation.isPending;

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="h6">Export Behavior Pack</Typography>
          <Button onClick={onClose} size="small">
            <Close />
          </Button>
        </Box>
      </DialogTitle>

      <DialogContent sx={{ pb: 0 }}>
        <LoadingWrapper loading={isLoading} variant="overlay">
          <Box>
            {/* Export Preview */}
            {exportPreviewQuery.data && (
              <Box sx={{ mb: 3 }}>
                <Typography variant="subtitle1" gutterBottom>
                  Export Preview
                </Typography>
                <Grid container spacing={2}>
                  <Grid item xs={12} sm={6}>
                    <Card variant="outlined">
                      <CardContent>
                        <Typography variant="h6" gutterBottom>
                          File Statistics
                        </Typography>
                        <Typography variant="body2" display="block">
                          Total Files: {exportPreviewQuery.data.analysis?.total_files || 0}
                        </Typography>
                        <Typography variant="body2" display="block">
                          Total Size: {exportPreviewQuery.data.analysis?.total_size_mb || 0} MB
                        </Typography>
                        <Typography variant="body2" display="block">
                          Status: {exportPreviewQuery.data.conversion_status}
                        </Typography>
                      </CardContent>
                    </Card>
                  </Grid>

                  <Grid item xs={12} sm={6}>
                    <Card variant="outlined">
                      <CardContent>
                        <Typography variant="h6" gutterBottom>
                          File Types
                        </Typography>
                        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                          {Object.entries(exportPreviewQuery.data.analysis?.file_types || {}).map(([type, count]) => (
                            <Chip
                              key={type}
                              label={`${type}: ${count}`}
                              size="small"
                              variant="outlined"
                            />
                          ))}
                        </Box>
                      </CardContent>
                    </Card>
                  </Grid>
                </Grid>
              </Box>
            )}

            <Divider sx={{ my: 2 }} />

            {/* Export Options */}
            <Box sx={{ mb: 3 }}>
              <Typography variant="subtitle1" gutterBottom>
                Export Options
              </Typography>

              {/* Format Selection */}
              <Box sx={{ mb: 2 }}>
                <FormControl fullWidth>
                  <InputLabel>Export Format</InputLabel>
                  <Select
                    value={exportOptions.format}
                    onChange={(e) => setExportOptions(prev => ({
                      ...prev,
                      format: e.target.value as ExportOptions['format']
                    }))}
                  >
                    {exportFormatsQuery.data?.map((format) => (
                      <MenuItem key={format.format} value={format.format}>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          {getFormatIcon(format.format)}
                          <Box>
                            <Typography variant="body1">
                              {format.name}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                              {format.description}
                            </Typography>
                          </Box>
                        </Box>
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
                </Box>

              {/* Format Info */}
              <Alert severity="info" sx={{ mb: 2 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  {getFormatIcon(exportOptions.format)}
                  <Box>
                    <Typography variant="body2">
                      {getFormatDescription(exportOptions.format)}
                    </Typography>
                  </Box>
                </Box>
              </Alert>

              {/* Basic Options */}
              <Box sx={{ mb: 2 }}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={exportOptions.includeTemplates}
                      onChange={(e) => setExportOptions(prev => ({
                        ...prev,
                        includeTemplates: e.target.checked
                      }))}
                    />
                  }
                  label="Include behavior templates"
                />
                <FormControlLabel
                  control={
                    <Switch
                      checked={exportOptions.includeMetadata}
                      onChange={(e) => setExportOptions(prev => ({
                        ...prev,
                        includeMetadata: e.target.checked
                      }))}
                    />
                  }
                  label="Include metadata and comments"
                />
              </Box>

              {/* Advanced Options */}
              <Accordion expanded={showAdvanced} onChange={() => setShowAdvanced(!showAdvanced)}>
                <AccordionSummary expandIcon={<ExpandMore />}>
                  <Typography variant="body2">Advanced Options</Typography>
                </AccordionSummary>
                <AccordionDetails>
                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                    <FormControl fullWidth>
                      <InputLabel>Compression</InputLabel>
                      <Select
                        value={exportOptions.compression}
                        onChange={(e) => setExportOptions(prev => ({
                          ...prev,
                          compression: e.target.value as ExportOptions['compression']
                        }))}
                      >
                        <MenuItem value="none">No compression</MenuItem>
                        <MenuItem value="standard">Standard compression</MenuItem>
                        <MenuItem value="maximum">Maximum compression</MenuItem>
                      </Select>
                    </FormControl>

                    <TextField
                      fullWidth
                      label="Custom filename (optional)"
                      value={exportOptions.customFileName || ''}
                      onChange={(e) => setExportOptions(prev => ({
                        ...prev,
                        customFileName: e.target.value
                      }))}
                      helperText="Without extension. If not provided, default naming will be used."
                    />
                  </Box>
                </AccordionDetails>
              </Accordion>
            </Box>

            {/* Files List */}
            {exportPreviewQuery.data?.files && (
              <Box>
                <Typography variant="subtitle1" gutterBottom>
                  Files to Export
                </Typography>
                <Box sx={{ maxHeight: 200, overflow: 'auto' }}>
                  <List dense>
                    {exportPreviewQuery.data.files.map((file: any, index: number) => (
                      <ListItem key={index}>
                        <ListItemIcon>
                          {file.type === 'directory' ? '📁' : '📄'}
                        </ListItemIcon>
                        <ListItemText
                          primary={file.name}
                          secondary={`${file.type} • ${file.size || 'Unknown size'}`}
                        />
                      </ListItem>
                    ))}
                  </List>
                </Box>
              </Box>
            )}
          </Box>
        </LoadingWrapper>
      </DialogContent>

      <DialogActions sx={{ p: 2, gap: 1 }}>
        <Button onClick={onClose} variant="outlined">
          Cancel
        </Button>
        <Button
          onClick={handleDownloadOnly}
          variant="outlined"
          disabled={isLoading}
          startIcon={<Download />}
        >
          Download Only
        </Button>
        <Button
          onClick={handleExport}
          variant="contained"
          disabled={isLoading}
          startIcon={exportPackMutation.isPending || downloadPackMutation.isPending ? undefined : <CloudDownload />}
        >
          {exportPackMutation.isPending || downloadPackMutation.isPending ? 'Exporting...' : 'Export'}
        </Button>
      </DialogActions>

      {/* Status Messages */}
      {exportPackMutation.error && (
        <Alert severity="error" sx={{ m: 2 }}>
          Export failed: {exportPackMutation.error.message}
        </Alert>
      )}

      {downloadPackMutation.error && (
        <Alert severity="error" sx={{ m: 2 }}>
          Download failed: {downloadPackMutation.error.message}
        </Alert>
      )}

      {exportPackMutation.isSuccess && (
        <Alert severity="success" sx={{ m: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <CheckCircle />
            <Typography variant="body2">
              Export completed successfully! Your behavior pack has been prepared.
            </Typography>
          </Box>
        </Alert>
      )}
    </Dialog>
  );
};

export default ExportManager;
