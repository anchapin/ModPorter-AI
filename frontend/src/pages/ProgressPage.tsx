/**
 * Progress Page for portkit Beta
 * Real-time conversion progress tracking
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Container,
  Typography,
  Paper,
  LinearProgress,
  Button,
  Chip,
  Stack,
  Divider,
  Alert,
} from '@mui/material';
import {
  HourglassEmpty as PendingIcon,
  Sync as ProcessingIcon,
  CheckCircle as CompleteIcon,
  Error as ErrorIcon,
  ArrowBack as BackIcon,
  Refresh as RefreshIcon,
  Download as DownloadIcon,
} from '@mui/icons-material';
import { apiClient, JobResponse } from '../api/client';
import './ProgressPage.css';

// Stage names mapping
const STAGE_LABELS: Record<string, string> = {
  pending: 'Pending',
  uploading: 'Uploading',
  preprocessing: 'Analyzing',
  ai_conversion: 'AI Conversion',
  postprocessing: 'Finalizing',
  completed: 'Complete',
  failed: 'Failed',
  cancelled: 'Cancelled',
};

const STATUS_COLORS: Record<
  string,
  'default' | 'primary' | 'success' | 'error' | 'warning'
> = {
  pending: 'default',
  uploading: 'primary',
  preprocessing: 'warning',
  ai_conversion: 'primary',
  postprocessing: 'warning',
  completed: 'success',
  failed: 'error',
  cancelled: 'error',
};

export const ProgressPage: React.FC = () => {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();
  const [job, setJob] = useState<JobResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [polling, setPolling] = useState(true);

  const fetchJobStatus = useCallback(async () => {
    if (!jobId) return;

    try {
      const status = await apiClient.getJobStatus(jobId);
      setJob(status);
      setError(null);

      // Stop polling when job is complete
      if (['completed', 'failed', 'cancelled'].includes(status.status)) {
        setPolling(false);
      }
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Failed to fetch job status'
      );
    } finally {
      setLoading(false);
    }
  }, [jobId]);

  // Initial fetch and polling
  useEffect(() => {
    fetchJobStatus();

    if (polling) {
      const interval = setInterval(fetchJobStatus, 2000);
      return () => clearInterval(interval);
    }
  }, [fetchJobStatus, polling]);

  const handleCancel = async () => {
    if (!jobId) return;

    try {
      await apiClient.cancelJob(jobId);
      setPolling(false);
      fetchJobStatus();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to cancel job');
    }
  };

  const handleViewResults = () => {
    if (jobId) {
      navigate(`/results/${jobId}`);
    }
  };

  const getStatusIcon = () => {
    if (!job) return <PendingIcon />;

    switch (job.status) {
      case 'completed':
        return <CompleteIcon color="success" />;
      case 'failed':
      case 'cancelled':
        return <ErrorIcon color="error" />;
      case 'preprocessing':
      case 'ai_conversion':
      case 'postprocessing':
        return <ProcessingIcon color="primary" className="spinning" />;
      default:
        return <PendingIcon />;
    }
  };

  if (loading) {
    return (
      <Container maxWidth="sm" className="progress-page">
        <Box sx={{ textAlign: 'center', py: 8 }}>
          <Typography variant="h6" color="text.secondary">
            Loading...
          </Typography>
        </Box>
      </Container>
    );
  }

  if (error && !job) {
    return (
      <Container maxWidth="sm" className="progress-page">
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
        <Button startIcon={<BackIcon />} onClick={() => navigate('/')}>
          Back to Upload
        </Button>
      </Container>
    );
  }

  const isComplete =
    job && ['completed', 'failed', 'cancelled'].includes(job.status);

  return (
    <Container maxWidth="sm" className="progress-page">
      <Button
        startIcon={<BackIcon />}
        onClick={() => navigate('/')}
        sx={{ mb: 2 }}
      >
        Upload More
      </Button>

      <Paper className="progress-card" elevation={2}>
        <Box sx={{ textAlign: 'center', mb: 3 }}>
          <Box sx={{ fontSize: 48, mb: 2 }}>{getStatusIcon()}</Box>
          <Typography variant="h5" component="h1">
            {STAGE_LABELS[job?.status || 'pending']}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {job?.original_filename}
          </Typography>
        </Box>

        {/* Progress Bar */}
        <Box sx={{ mb: 3 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
            <Typography variant="body2" color="text.secondary">
              Progress
            </Typography>
            <Typography variant="body2" fontWeight="bold">
              {job?.progress || 0}%
            </Typography>
          </Box>
          <LinearProgress
            variant="determinate"
            value={job?.progress || 0}
            sx={{ height: 10, borderRadius: 5 }}
          />
        </Box>

        {/* Status Details */}
        <Stack spacing={2}>
          <Box className="status-row">
            <Typography variant="body2" color="text.secondary">
              Current Step
            </Typography>
            <Chip
              label={job?.current_step || 'Waiting...'}
              size="small"
              color={STATUS_COLORS[job?.status || 'pending']}
            />
          </Box>

          <Box className="status-row">
            <Typography variant="body2" color="text.secondary">
              Status
            </Typography>
            <Chip
              label={job?.status || 'unknown'}
              size="small"
              color={STATUS_COLORS[job?.status || 'pending']}
            />
          </Box>

          {job?.error_message && (
            <Alert severity="error">{job.error_message}</Alert>
          )}

          <Divider />

          {/* Actions */}
          <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
            {!isComplete && (
              <Button variant="outlined" color="error" onClick={handleCancel}>
                Cancel
              </Button>
            )}

            {isComplete && job?.status === 'completed' && (
              <Button
                variant="contained"
                startIcon={<DownloadIcon />}
                onClick={handleViewResults}
              >
                View Results
              </Button>
            )}

            <Button
              variant="outlined"
              startIcon={<RefreshIcon />}
              onClick={fetchJobStatus}
            >
              Refresh
            </Button>
          </Box>
        </Stack>
      </Paper>

      {/* Tips while waiting */}
      {!isComplete && (
        <Paper className="tips-card" elevation={0}>
          <Typography variant="subtitle2" gutterBottom>
            While you wait:
          </Typography>
          <ul className="tips-list">
            <li>Large mods may take several minutes</li>
            <li>AI conversion analyzes complex code patterns</li>
            <li>You can close this page and check back later</li>
          </ul>
        </Paper>
      )}
    </Container>
  );
};

export default ProgressPage;
