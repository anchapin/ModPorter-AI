/**
 * Results Page for ModPorter-AI Beta
 * Display conversion results and download options
 */

import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Container,
  Typography,
  Paper,
  Button,
  Stack,
  Alert,
  LinearProgress,
} from '@mui/material';
import {
  ArrowBack as BackIcon,
  Download as DownloadIcon,
  Share as ShareIcon,
  ThumbUp as ThumbUpIcon,
  ThumbDown as ThumbDownIcon,
  Refresh as RefreshIcon,
  CheckCircle as SuccessIcon,
  Error as ErrorIcon,
} from '@mui/icons-material';
import { apiClient, JobResponse, ConversionResult } from '../api/client';
import './ResultsPage.css';

interface JobResult {
  job: JobResponse | null;
  conversionResult: ConversionResult | null;
}

export const ResultsPage: React.FC = () => {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<JobResult>({
    job: null,
    conversionResult: null,
  });
  const [feedback, setFeedback] = useState<'thumbs_up' | 'thumbs_down' | null>(
    null
  );

  const fetchResults = async () => {
    if (!jobId) return;

    setLoading(true);
    try {
      const [job, conversionResult] = await Promise.all([
        apiClient.getJobStatus(jobId).catch(() => null),
        apiClient.getResults(jobId).catch(() => null),
      ]);

      setResult({ job, conversionResult });
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load results');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchResults();
  }, [jobId]);

  const handleDownload = () => {
    if (!jobId || !result.job?.result_url) return;
    const filename = result.job.original_filename.replace(
      /\.[^.]+$/,
      '.mcaddon'
    );
    apiClient.downloadResult(result.job.result_url, filename);
  };

  const handleFeedback = async (type: 'thumbs_up' | 'thumbs_down') => {
    setFeedback(type);
    // TODO: Submit feedback to API
    console.log('Feedback submitted:', type, jobId);
  };

  const _getSuccessRateColor = (
    rate: number
  ): 'success' | 'warning' | 'error' => {
    if (rate >= 80) return 'success';
    if (rate >= 50) return 'warning';
    return 'error';
  };

  if (loading) {
    return (
      <Container maxWidth="md" className="results-page">
        <Box sx={{ textAlign: 'center', py: 8 }}>
          <Typography variant="h6" color="text.secondary">
            Loading results...
          </Typography>
          <LinearProgress sx={{ mt: 2, maxWidth: 400, mx: 'auto' }} />
        </Box>
      </Container>
    );
  }

  if (error && !result.job) {
    return (
      <Container maxWidth="md" className="results-page">
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
        <Button startIcon={<BackIcon />} onClick={() => navigate('/')}>
          Back to Upload
        </Button>
      </Container>
    );
  }

  const { job, conversionResult } = result;
  const isSuccess = job?.status === 'completed';

  return (
    <Container maxWidth="md" className="results-page">
      <Button
        startIcon={<BackIcon />}
        onClick={() => navigate('/')}
        sx={{ mb: 2 }}
      >
        Upload More
      </Button>

      {/* Header */}
      <Paper className="results-header" elevation={0}>
        <Box sx={{ textAlign: 'center', py: 3 }}>
          {isSuccess ? (
            <SuccessIcon sx={{ fontSize: 64, color: 'success.main', mb: 2 }} />
          ) : (
            <ErrorIcon sx={{ fontSize: 64, color: 'error.main', mb: 2 }} />
          )}
          <Typography variant="h4" component="h1">
            {isSuccess ? 'Conversion Complete!' : 'Conversion Failed'}
          </Typography>
          <Typography variant="body1" color="text.secondary">
            {job?.original_filename}
          </Typography>
        </Box>
      </Paper>

      {/* Error State */}
      {!isSuccess && job?.error_message && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {job.error_message}
        </Alert>
      )}

      {/* Download Button */}
      {isSuccess && job?.result_url && (
        <Paper className="download-card" elevation={2}>
          <Box
            sx={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              flexWrap: 'wrap',
              gap: 2,
            }}
          >
            <Box>
              <Typography variant="h6">Ready to Download</Typography>
              <Typography variant="body2" color="text.secondary">
                Your converted mod is ready
              </Typography>
            </Box>
            <Button
              variant="contained"
              size="large"
              startIcon={<DownloadIcon />}
              onClick={handleDownload}
            >
              Download .mcaddon
            </Button>
          </Box>
        </Paper>
      )}

      {/* Stats */}
      {isSuccess && conversionResult?.summary && (
        <Paper className="stats-card" elevation={2}>
          <Typography variant="h6" gutterBottom>
            Conversion Summary
          </Typography>
          <Box className="stats-grid">
            <Box className="stat-item">
              <Typography variant="h4" color="primary">
                {conversionResult.summary.overall_success_rate}%
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Success Rate
              </Typography>
            </Box>
            <Box className="stat-item">
              <Typography variant="h4">
                {conversionResult.summary.total_features}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Total Features
              </Typography>
            </Box>
            <Box className="stat-item">
              <Typography variant="h4" color="success.main">
                {conversionResult.summary.converted_features}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Converted
              </Typography>
            </Box>
            <Box className="stat-item">
              <Typography variant="h4" color="warning.main">
                {conversionResult.summary.partially_converted_features}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Partial
              </Typography>
            </Box>
            <Box className="stat-item">
              <Typography variant="h4" color="error.main">
                {conversionResult.summary.failed_features}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Failed
              </Typography>
            </Box>
            <Box className="stat-item">
              <Typography variant="h4">
                {conversionResult.summary.processing_time_seconds}s
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Processing Time
              </Typography>
            </Box>
          </Box>
        </Paper>
      )}

      {/* Feedback */}
      {isSuccess && (
        <Paper className="feedback-card" elevation={0}>
          <Typography variant="h6" gutterBottom>
            Was this conversion helpful?
          </Typography>
          <Stack direction="row" spacing={2}>
            <Button
              variant={feedback === 'thumbs_up' ? 'contained' : 'outlined'}
              startIcon={<ThumbUpIcon />}
              onClick={() => handleFeedback('thumbs_up')}
              color="success"
            >
              Yes
            </Button>
            <Button
              variant={feedback === 'thumbs_down' ? 'contained' : 'outlined'}
              startIcon={<ThumbDownIcon />}
              onClick={() => handleFeedback('thumbs_down')}
              color="error"
            >
              No
            </Button>
          </Stack>
          {feedback && (
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
              Thanks for your feedback!
            </Typography>
          )}
        </Paper>
      )}

      {/* Actions */}
      <Stack
        direction="row"
        spacing={2}
        sx={{ mt: 3 }}
        flexWrap="wrap"
        useFlexGap
      >
        <Button
          variant="outlined"
          startIcon={<RefreshIcon />}
          onClick={fetchResults}
        >
          Refresh
        </Button>
        <Button
          variant="outlined"
          startIcon={<ShareIcon />}
          onClick={() => {
            navigator.clipboard.writeText(window.location.href);
          }}
        >
          Share
        </Button>
      </Stack>
    </Container>
  );
};

export default ResultsPage;
