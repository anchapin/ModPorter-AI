/**
 * Upload Page for ModPorter-AI Beta
 * Drag-and-drop file upload with conversion options
 */

import React, { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDropzone } from 'react-dropzone';
import {
  Box,
  Container,
  Typography,
  Paper,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Button,
  LinearProgress,
  Alert,
  Stack,
  Chip,
} from '@mui/material';
import {
  CloudUpload as UploadIcon,
  FilePresent as FileIcon,
  Close as CloseIcon,
} from '@mui/icons-material';
import { apiClient, JobOptions } from '../api/client';
import './UploadPage.css';

interface UploadedFile {
  file: File;
  preview: string;
  progress: number;
  status: 'pending' | 'uploading' | 'uploaded' | 'error';
  error?: string;
  jobId?: string;
}

const TARGET_VERSIONS = [
  { value: '1.21.0', label: 'Minecraft 1.21' },
  { value: '1.20.4', label: 'Minecraft 1.20.4' },
  { value: '1.20.0', label: 'Minecraft 1.20' },
  { value: '1.19.0', label: 'Minecraft 1.19' },
];

const CONVERSION_MODES = [
  {
    value: 'simple',
    label: 'Simple',
    description: 'Basic block/item conversion',
  },
  {
    value: 'standard',
    label: 'Standard',
    description: 'Full conversion with AI assistance',
  },
  {
    value: 'complex',
    label: 'Complex',
    description: 'Advanced conversion with behaviors',
  },
];

const OUTPUT_FORMATS = [
  { value: 'mcaddon', label: '.mcaddon' },
  { value: 'zip', label: '.zip' },
];

export const UploadPage: React.FC = () => {
  const navigate = useNavigate();
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [targetVersion, setTargetVersion] = useState('1.20.0');
  const [conversionMode, setConversionMode] = useState<
    'simple' | 'standard' | 'complex'
  >('standard');
  const [outputFormat, setOutputFormat] = useState<'mcaddon' | 'zip'>(
    'mcaddon'
  );
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    setError(null);

    const newFiles: UploadedFile[] = acceptedFiles.map((file) => ({
      file,
      preview: file.name,
      progress: 0,
      status: 'pending',
    }));

    setFiles((prev) => [...prev, ...newFiles]);
  }, []);

  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const { getRootProps, getInputProps, isDragActive, isDragReject } =
    useDropzone({
      onDrop,
      accept: {
        'application/java-archive': ['.jar'],
        'application/zip': ['.zip', '.mcaddon'],
      },
      maxSize: 100 * 1024 * 1024, // 100MB
      multiple: true,
    });

  const handleUpload = async () => {
    if (files.length === 0) {
      setError('Please select at least one file');
      return;
    }

    setUploading(true);
    setError(null);

    const jobOptions: JobOptions = {
      conversion_mode: conversionMode,
      target_version: targetVersion,
      output_format: outputFormat,
    };

    try {
      // Process each file sequentially
      for (let i = 0; i < files.length; i++) {
        const uploadedFile = files[i];

        // Update status to uploading
        setFiles((prev) =>
          prev.map((f, idx) =>
            idx === i ? { ...f, status: 'uploading' as const } : f
          )
        );

        try {
          // Upload the file
          const uploadResponse = await apiClient.uploadFile(uploadedFile.file, {
            onProgress: (progress) => {
              setFiles((prev) =>
                prev.map((f, idx) => (idx === i ? { ...f, progress } : f))
              );
            },
          });

          // Create conversion job
          const jobResponse = await apiClient.createJob({
            file_path:
              uploadResponse.filename || uploadResponse.original_filename,
            original_filename: uploadResponse.original_filename,
            options: jobOptions,
          });

          // Update file with job ID
          setFiles((prev) =>
            prev.map((f, idx) =>
              idx === i
                ? {
                    ...f,
                    status: 'uploaded' as const,
                    jobId: jobResponse.job_id,
                  }
                : f
            )
          );

          // Navigate to progress page with first job
          if (i === 0) {
            navigate(`/progress/${jobResponse.job_id}`);
          }
        } catch (err) {
          const errorMessage =
            err instanceof Error ? err.message : 'Upload failed';
          setFiles((prev) =>
            prev.map((f, idx) =>
              idx === i
                ? { ...f, status: 'error' as const, error: errorMessage }
                : f
            )
          );
        }
      }
    } finally {
      setUploading(false);
    }
  };

  return (
    <Container maxWidth="md" className="upload-page">
      <Box sx={{ textAlign: 'center', mb: 4 }}>
        <Typography variant="h3" component="h1" gutterBottom>
          Convert Your Mods
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Upload Minecraft Java Edition mods and convert them to Bedrock Edition
        </Typography>
      </Box>

      {/* File Drop Zone */}
      <Paper
        {...getRootProps()}
        className={`dropzone ${isDragActive ? 'dropzone-active' : ''} ${
          isDragReject ? 'dropzone-reject' : ''
        }`}
        elevation={0}
      >
        <input {...getInputProps()} />
        <Stack alignItems="center" spacing={2}>
          <UploadIcon sx={{ fontSize: 48, color: 'primary.main' }} />
          <Typography variant="h6">
            {isDragActive
              ? 'Drop the files here...'
              : 'Drag and drop JAR, ZIP, or mcaddon files here'}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            or click to browse files
          </Typography>
          <Stack direction="row" spacing={1}>
            <Chip label=".jar" size="small" />
            <Chip label=".zip" size="small" />
            <Chip label=".mcaddon" size="small" />
            <Chip label="Max 100MB" size="small" variant="outlined" />
          </Stack>
        </Stack>
      </Paper>

      {/* File List */}
      {files.length > 0 && (
        <Paper className="file-list" elevation={0}>
          <Typography variant="h6" gutterBottom>
            Selected Files ({files.length})
          </Typography>
          <Stack spacing={1}>
            {files.map((uploadedFile, index) => (
              <Box key={index} className="file-item">
                <Box
                  sx={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 2,
                    flex: 1,
                  }}
                >
                  <FileIcon color="primary" />
                  <Box sx={{ flex: 1 }}>
                    <Typography variant="body2" noWrap>
                      {uploadedFile.preview}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {(uploadedFile.file.size / (1024 * 1024)).toFixed(2)} MB
                    </Typography>
                    {uploadedFile.status === 'uploading' && (
                      <LinearProgress
                        variant="determinate"
                        value={uploadedFile.progress}
                        sx={{ mt: 1 }}
                      />
                    )}
                    {uploadedFile.status === 'error' && (
                      <Alert severity="error" sx={{ mt: 1, py: 0 }}>
                        {uploadedFile.error}
                      </Alert>
                    )}
                  </Box>
                </Box>
                <Button
                  size="small"
                  onClick={() => removeFile(index)}
                  disabled={uploadedFile.status === 'uploading'}
                >
                  <CloseIcon />
                </Button>
              </Box>
            ))}
          </Stack>
        </Paper>
      )}

      {/* Error Alert */}
      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Conversion Options */}
      <Paper className="options-panel" elevation={0}>
        <Typography variant="h6" gutterBottom>
          Conversion Options
        </Typography>
        <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
          <FormControl sx={{ minWidth: 150 }}>
            <InputLabel>Target Version</InputLabel>
            <Select
              value={targetVersion}
              label="Target Version"
              onChange={(e) => setTargetVersion(e.target.value)}
            >
              {TARGET_VERSIONS.map((version) => (
                <MenuItem key={version.value} value={version.value}>
                  {version.label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <FormControl sx={{ minWidth: 150 }}>
            <InputLabel>Conversion Mode</InputLabel>
            <Select
              value={conversionMode}
              label="Conversion Mode"
              onChange={(e) =>
                setConversionMode(e.target.value as typeof conversionMode)
              }
            >
              {CONVERSION_MODES.map((mode) => (
                <MenuItem key={mode.value} value={mode.value}>
                  <Box>
                    <Typography variant="body2">{mode.label}</Typography>
                    <Typography variant="caption" color="text.secondary">
                      {mode.description}
                    </Typography>
                  </Box>
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <FormControl sx={{ minWidth: 120 }}>
            <InputLabel>Output Format</InputLabel>
            <Select
              value={outputFormat}
              label="Output Format"
              onChange={(e) =>
                setOutputFormat(e.target.value as typeof outputFormat)
              }
            >
              {OUTPUT_FORMATS.map((format) => (
                <MenuItem key={format.value} value={format.value}>
                  {format.label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </Box>
      </Paper>

      {/* Upload Button */}
      <Box sx={{ display: 'flex', justifyContent: 'center', mt: 3 }}>
        <Button
          variant="contained"
          size="large"
          onClick={handleUpload}
          disabled={files.length === 0 || uploading}
          startIcon={<UploadIcon />}
        >
          {uploading
            ? 'Uploading...'
            : `Upload${files.length > 1 ? ` ${files.length} Files` : ''}`}
        </Button>
      </Box>
    </Container>
  );
};

export default UploadPage;
