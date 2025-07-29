import React, { useState, useEffect } from 'react';
import { 
  Box, 
  Card, 
  CardContent, 
  CardHeader, 
  CircularProgress, 
  FormControl, 
  Grid, 
  InputLabel, 
  MenuItem, 
  Select, 
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper
} from '@mui/material';
import { fetchExperiments, fetchExperimentResults } from '../services/experiments';
import { Experiment, ExperimentResult } from '../types/experiment';

const ExperimentResultsPage: React.FC = () => {
  // State
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [results, setResults] = useState<ExperimentResult[]>([]);
  const [selectedExperimentId, setSelectedExperimentId] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch experiments on component mount
  useEffect(() => {
    const loadExperiments = async () => {
      try {
        const data = await fetchExperiments();
        setExperiments(data);
      } catch (err) {
        setError('Failed to load experiments');
        console.error(err);
      }
    };

    loadExperiments();
  }, []);

  // Fetch results when experiment is selected
  useEffect(() => {
    const loadResults = async () => {
      if (!selectedExperimentId) {
        setResults([]);
        return;
      }

      try {
        setLoading(true);
        const data = await fetchExperimentResults();
        // Filter results by experiment (would be done on backend in a real implementation)
        setResults(data);
      } catch (err) {
        setError('Failed to load experiment results');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    loadResults();
  }, [selectedExperimentId]);

  // Calculate statistics
  const calculateStats = () => {
    if (results.length === 0) return null;

    const stats = {
      total: results.length,
      avgQuality: 0,
      avgSpeed: 0,
      avgCost: 0,
      avgFeedback: 0,
      qualityScores: [] as number[],
      speedScores: [] as number[],
      costScores: [] as number[],
      feedbackScores: [] as number[],
    };

    let qualitySum = 0;
    let speedSum = 0;
    let costSum = 0;
    let feedbackSum = 0;
    let qualityCount = 0;
    let speedCount = 0;
    let costCount = 0;
    let feedbackCount = 0;

    results.forEach(result => {
      if (result.kpi_quality !== null) {
        qualitySum += result.kpi_quality;
        qualityCount++;
        stats.qualityScores.push(result.kpi_quality);
      }
      if (result.kpi_speed !== null) {
        speedSum += result.kpi_speed;
        speedCount++;
        stats.speedScores.push(result.kpi_speed);
      }
      if (result.kpi_cost !== null) {
        costSum += result.kpi_cost;
        costCount++;
        stats.costScores.push(result.kpi_cost);
      }
      if (result.user_feedback_score !== null) {
        feedbackSum += result.user_feedback_score;
        feedbackCount++;
        stats.feedbackScores.push(result.user_feedback_score);
      }
    });

    stats.avgQuality = qualityCount > 0 ? qualitySum / qualityCount : 0;
    stats.avgSpeed = speedCount > 0 ? speedSum / speedCount : 0;
    stats.avgCost = costCount > 0 ? costSum / costCount : 0;
    stats.avgFeedback = feedbackCount > 0 ? feedbackSum / feedbackCount : 0;

    return stats;
  };

  const stats = calculateStats();

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
        <Typography variant="h4">Experiment Results</Typography>
      </Box>

      {error && (
        <Box mb={3}>
          <Typography color="error">{error}</Typography>
        </Box>
      )}

      <Grid container spacing={3}>
        {/* Experiment Selector */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <FormControl fullWidth>
                <InputLabel>Select Experiment</InputLabel>
                <Select
                  value={selectedExperimentId}
                  onChange={(e) => setSelectedExperimentId(e.target.value as string)}
                  label="Select Experiment"
                >
                  <MenuItem value="">
                    <em>Select an experiment</em>
                  </MenuItem>
                  {experiments.map(experiment => (
                    <MenuItem key={experiment.id} value={experiment.id}>
                      {experiment.name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </CardContent>
          </Card>
        </Grid>

        {/* Statistics */}
        {stats && (
          <>
            <Grid item xs={12} md={3}>
              <Card>
                <CardHeader title="Total Conversions" />
                <CardContent>
                  <Typography variant="h4" align="center">
                    {stats.total}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            
            <Grid item xs={12} md={3}>
              <Card>
                <CardHeader title="Avg Quality Score" />
                <CardContent>
                  <Typography variant="h4" align="center">
                    {stats.avgQuality.toFixed(2)}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            
            <Grid item xs={12} md={3}>
              <Card>
                <CardHeader title="Avg Speed (ms)" />
                <CardContent>
                  <Typography variant="h4" align="center">
                    {stats.avgSpeed.toFixed(0)}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            
            <Grid item xs={12} md={3}>
              <Card>
                <CardHeader title="Avg User Feedback" />
                <CardContent>
                  <Typography variant="h4" align="center">
                    {stats.avgFeedback.toFixed(2)}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          </>
        )}

        {/* Results Table */}
        <Grid item xs={12}>
          <Card>
            <CardHeader title="Conversion Results" />
            <CardContent>
              <TableContainer component={Paper}>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>Session ID</TableCell>
                      <TableCell>Quality</TableCell>
                      <TableCell>Speed (ms)</TableCell>
                      <TableCell>Cost</TableCell>
                      <TableCell>User Feedback</TableCell>
                      <TableCell>Date</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {results.map(result => (
                      <TableRow key={result.id}>
                        <TableCell>{result.session_id.substring(0, 8)}...</TableCell>
                        <TableCell>{result.kpi_quality !== null ? result.kpi_quality.toFixed(2) : 'N/A'}</TableCell>
                        <TableCell>{result.kpi_speed !== null ? result.kpi_speed : 'N/A'}</TableCell>
                        <TableCell>{result.kpi_cost !== null ? result.kpi_cost.toFixed(2) : 'N/A'}</TableCell>
                        <TableCell>{result.user_feedback_score !== null ? result.user_feedback_score.toFixed(2) : 'N/A'}</TableCell>
                        <TableCell>{new Date(result.created_at).toLocaleDateString()}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default ExperimentResultsPage;