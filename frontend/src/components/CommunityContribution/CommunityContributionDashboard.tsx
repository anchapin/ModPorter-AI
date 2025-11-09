import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Typography,
  Tabs,
  Tab,
  Card,
  CardContent,
  Grid,
  Button,
  LinearProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Avatar,
  IconButton,
  Tooltip,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TextField,
  InputAdornment,
  Alert,
  CircularProgress,
  Chip
} from '@mui/material';
import {
  Add as AddIcon,
  Search as SearchIcon,
  Visibility as ViewIcon,
  RateReview as ReviewIcon,
  TrendingUp as TrendingUpIcon,
  Schedule as ScheduleIcon,
  CheckCircle as CheckIcon,
  Error as ErrorIcon,
  HourglassEmpty as PendingIcon,
  Refresh as RefreshIcon,
  Download as DownloadIcon,
  Timeline as TimelineIcon,
  People as PeopleIcon,
  Assessment as AssessmentIcon
} from '@mui/icons-material';
import { format } from 'date-fns';
import axios from 'axios';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`contribution-tabpanel-${index}`}
      aria-labelledby={`contribution-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

interface Contribution {
  id: string;
  title: string;
  description: string;
  contributor_id: string;
  contribution_type: string;
  review_status: string;
  votes: number;
  minecraft_version: string;
  tags: string[];
  created_at: string;
  updated_at: string;
  review_count?: number;
  average_score?: number;
}

interface Review {
  id: string;
  contribution_id: string;
  reviewer_id: string;
  review_type: string;
  status: string;
  overall_score?: number;
  review_comments: string;
  created_at: string;
  reviewer?: {
    reputation_score: number;
    expertise_areas: string[];
  };
}

interface Reviewer {
  reviewer_id: string;
  expertise_areas: string[];
  minecraft_versions: string[];
  review_count: number;
  average_review_score?: number;
  approval_rate?: number;
  current_reviews: number;
  max_concurrent_reviews: number;
  expertise_score?: number;
  reputation_score?: number;
  is_active_reviewer: boolean;
}

interface Analytics {
  total_submitted: number;
  total_approved: number;
  total_rejected: number;
  total_needing_revision: number;
  approval_rate: number;
  rejection_rate: number;
  avg_review_time: number;
  avg_review_score: number;
  active_reviewers: number;
}

const CommunityContributionDashboard: React.FC = () => {
  const [tabValue, setTabValue] = useState(0);
  const [contributions, setContributions] = useState<Contribution[]>([]);
  const [reviews, setReviews] = useState<Review[]>([]);
  const [reviewers, setReviewers] = useState<Reviewer[]>([]);
  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [typeFilter, setTypeFilter] = useState('all');

  const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

  useEffect(() => {
    loadDashboardData();
  }, [tabValue, loadDashboardData]);

  const loadDashboardData = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      const contributionsPromise = axios.get(`${API_BASE}/knowledge-graph/contributions`);
      const reviewsPromise = axios.get(`${API_BASE}/peer-review/reviews/pending`);
      const reviewersPromise = axios.get(`${API_BASE}/peer-review/reviewers/available?expertise_area=patterns&limit=10`);
      const analyticsPromise = axios.get(`${API_BASE}/peer-review/analytics/summary`);

      const [contributionsRes, reviewsRes, reviewersRes, analyticsRes] = await Promise.all([
        contributionsPromise,
        reviewsPromise,
        reviewersPromise,
        analyticsPromise
      ]);

      setContributions(contributionsRes.data);
      setReviews(reviewsRes.data);
      setReviewers(reviewersRes.data);
      setAnalytics(analyticsRes.data);
    } catch (err) {
      console.error('Error loading dashboard data:', err);
      setError('Failed to load dashboard data. Please try again.');
    } finally {
      setLoading(false);
    }
  }, [tabValue]);

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'approved':
        return 'success';
      case 'rejected':
        return 'error';
      case 'needs_revision':
        return 'warning';
      default:
        return 'default';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'approved':
        return <CheckIcon />;
      case 'rejected':
        return <ErrorIcon />;
      default:
        return <PendingIcon />;
    }
  };

  const filteredContributions = contributions.filter(contribution => {
    const matchesSearch = contribution.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         contribution.description.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = statusFilter === 'all' || contribution.review_status === statusFilter;
    const matchesType = typeFilter === 'all' || contribution.contribution_type === typeFilter;
    return matchesSearch && matchesStatus && matchesType;
  });

  if (loading && !contributions.length) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ width: '100%' }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" component="h1">
          Community Contribution Dashboard
        </Typography>
        <Box>
          <Tooltip title="Refresh Data">
            <IconButton onClick={loadDashboardData} disabled={loading}>
              <RefreshIcon />
            </IconButton>
          </Tooltip>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            href="/knowledge-graph/contribute"
          >
            New Contribution
          </Button>
        </Box>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Analytics Overview */}
      {analytics && (
        <Grid container spacing={3} sx={{ mb: 3 }}>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center">
                  <Box flexGrow={1}>
                    <Typography color="textSecondary" gutterBottom>
                      Total Submitted
                    </Typography>
                    <Typography variant="h5">
                      {analytics.total_submitted}
                    </Typography>
                  </Box>
                  <Avatar sx={{ bgcolor: 'primary.main' }}>
                    <TrendingUpIcon />
                  </Avatar>
                </Box>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center">
                  <Box flexGrow={1}>
                    <Typography color="textSecondary" gutterBottom>
                      Approval Rate
                    </Typography>
                    <Typography variant="h5">
                      {analytics.approval_rate.toFixed(1)}%
                    </Typography>
                  </Box>
                  <Avatar sx={{ bgcolor: 'success.main' }}>
                    <CheckIcon />
                  </Avatar>
                </Box>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center">
                  <Box flexGrow={1}>
                    <Typography color="textSecondary" gutterBottom>
                      Avg Review Time
                    </Typography>
                    <Typography variant="h5">
                      {analytics.avg_review_time.toFixed(1)}h
                    </Typography>
                  </Box>
                  <Avatar sx={{ bgcolor: 'warning.main' }}>
                    <ScheduleIcon />
                  </Avatar>
                </Box>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center">
                  <Box flexGrow={1}>
                    <Typography color="textSecondary" gutterBottom>
                      Active Reviewers
                    </Typography>
                    <Typography variant="h5">
                      {analytics.active_reviewers}
                    </Typography>
                  </Box>
                  <Avatar sx={{ bgcolor: 'info.main' }}>
                    <PeopleIcon />
                  </Avatar>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
        <Tabs value={tabValue} onChange={handleTabChange} aria-label="Contribution tabs">
          <Tab label="Contributions" />
          <Tab label="Pending Reviews" />
          <Tab label="Reviewers" />
          <Tab label="Analytics" />
        </Tabs>
      </Box>

      {/* Contributions Tab */}
      <TabPanel value={tabValue} index={0}>
        <Box sx={{ mb: 2, display: 'flex', gap: 2, alignItems: 'center' }}>
          <TextField
            placeholder="Search contributions..."
            variant="outlined"
            size="small"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon />
                </InputAdornment>
              ),
            }}
            sx={{ flexGrow: 1, maxWidth: 400 }}
          />
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel>Status</InputLabel>
            <Select
              value={statusFilter}
              label="Status"
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <MenuItem value="all">All</MenuItem>
              <MenuItem value="pending">Pending</MenuItem>
              <MenuItem value="approved">Approved</MenuItem>
              <MenuItem value="rejected">Rejected</MenuItem>
              <MenuItem value="needs_revision">Needs Revision</MenuItem>
            </Select>
          </FormControl>
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel>Type</InputLabel>
            <Select
              value={typeFilter}
              label="Type"
              onChange={(e) => setTypeFilter(e.target.value)}
            >
              <MenuItem value="all">All</MenuItem>
              <MenuItem value="pattern">Pattern</MenuItem>
              <MenuItem value="node">Node</MenuItem>
              <MenuItem value="relationship">Relationship</MenuItem>
              <MenuItem value="correction">Correction</MenuItem>
            </Select>
          </FormControl>
        </Box>

        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Title</TableCell>
                <TableCell>Type</TableCell>
                <TableCell>Contributor</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Votes</TableCell>
                <TableCell>Created</TableCell>
                <TableCell>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {filteredContributions.map((contribution) => (
                <TableRow key={contribution.id} hover>
                  <TableCell>
                    <Box>
                      <Typography variant="subtitle2" sx={{ fontWeight: 'bold' }}>
                        {contribution.title}
                      </Typography>
                      <Typography variant="body2" color="textSecondary" noWrap>
                        {contribution.description}
                      </Typography>
                    </Box>
                  </TableCell>
                  <TableCell>
                    <Chip label={contribution.contribution_type} size="small" />
                  </TableCell>
                  <TableCell>{contribution.contributor_id}</TableCell>
                  <TableCell>
                    <Chip
                      icon={getStatusIcon(contribution.review_status)}
                      label={contribution.review_status}
                      color={getStatusColor(contribution.review_status) as any}
                      size="small"
                    />
                  </TableCell>
                  <TableCell>{contribution.votes}</TableCell>
                  <TableCell>
                    {format(new Date(contribution.created_at), 'MMM dd, yyyy')}
                  </TableCell>
                  <TableCell>
                    <Tooltip title="View Details">
                      <IconButton size="small">
                        <ViewIcon />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Review">
                      <IconButton size="small">
                        <ReviewIcon />
                      </IconButton>
                    </Tooltip>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </TabPanel>

      {/* Pending Reviews Tab */}
      <TabPanel value={tabValue} index={1}>
        <Typography variant="h6" gutterBottom>
          Pending Reviews
        </Typography>
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Contribution</TableCell>
                <TableCell>Reviewer</TableCell>
                <TableCell>Type</TableCell>
                <TableCell>Score</TableCell>
                <TableCell>Submitted</TableCell>
                <TableCell>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {reviews.map((review) => (
                <TableRow key={review.id} hover>
                  <TableCell>{review.contribution_id}</TableCell>
                  <TableCell>{review.reviewer_id}</TableCell>
                  <TableCell>
                    <Chip label={review.review_type} size="small" />
                  </TableCell>
                  <TableCell>
                    {review.overall_score ? (
                      <Chip
                        label={review.overall_score.toFixed(1)}
                        color={review.overall_score >= 7 ? 'success' : review.overall_score >= 4 ? 'warning' : 'error'}
                        size="small"
                      />
                    ) : (
                      <Typography variant="body2" color="textSecondary">
                        Not scored
                      </Typography>
                    )}
                  </TableCell>
                  <TableCell>
                    {format(new Date(review.created_at), 'MMM dd, yyyy')}
                  </TableCell>
                  <TableCell>
                    <Tooltip title="View Review">
                      <IconButton size="small">
                        <ViewIcon />
                      </IconButton>
                    </Tooltip>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </TabPanel>

      {/* Reviewers Tab */}
      <TabPanel value={tabValue} index={2}>
        <Typography variant="h6" gutterBottom>
          Available Reviewers
        </Typography>
        <Grid container spacing={2}>
          {reviewers.map((reviewer) => (
            <Grid item xs={12} sm={6} md={4} key={reviewer.reviewer_id}>
              <Card>
                <CardContent>
                  <Box display="flex" alignItems="center" mb={2}>
                    <Avatar sx={{ mr: 2 }}>
                      {reviewer.reviewer_id.substring(0, 2).toUpperCase()}
                    </Avatar>
                    <Box flexGrow={1}>
                      <Typography variant="subtitle1">
                        {reviewer.reviewer_id}
                      </Typography>
                      <Box display="flex" alignItems="center" gap={1}>
                        <Typography variant="body2" color="textSecondary">
                          Reputation:
                        </Typography>
                        <LinearProgress
                          variant="determinate"
                          value={(reviewer.reputation_score || 0) * 10}
                          sx={{ flexGrow: 1, height: 6 }}
                        />
                        <Typography variant="caption">
                          {reviewer.reputation_score?.toFixed(1) || '0.0'}
                        </Typography>
                      </Box>
                    </Box>
                  </Box>
                  
                  <Box mb={1}>
                    <Typography variant="body2" color="textSecondary" gutterBottom>
                      Expertise: {reviewer.expertise_areas.join(', ')}
                    </Typography>
                    <Typography variant="body2" color="textSecondary">
                      Reviews: {reviewer.review_count} | 
                      Approval Rate: {reviewer.approval_rate?.toFixed(1) || '0.0'}%
                    </Typography>
                  </Box>
                  
                  <Box display="flex" justifyContent="space-between" alignItems="center">
                    <Typography variant="body2" color="textSecondary">
                      Current Load: {reviewer.current_reviews}/{reviewer.max_concurrent_reviews}
                    </Typography>
                    <Button size="small" variant="outlined">
                      Assign Review
                    </Button>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      </TabPanel>

      {/* Analytics Tab */}
      <TabPanel value={tabValue} index={3}>
        <Typography variant="h6" gutterBottom>
          Review Analytics
        </Typography>
        {analytics && (
          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    <AssessmentIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
                    Performance Metrics
                  </Typography>
                  <Box display="flex" flexDirection="column" gap={2}>
                    <Box>
                      <Typography variant="body2" color="textSecondary">
                        Average Review Score
                      </Typography>
                      <Typography variant="h5">
                        {analytics.avg_review_score.toFixed(1)}/10
                      </Typography>
                    </Box>
                    <Box>
                      <Typography variant="body2" color="textSecondary">
                        Average Review Time
                      </Typography>
                      <Typography variant="h5">
                        {analytics.avg_review_time.toFixed(1)} hours
                      </Typography>
                    </Box>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
            
            <Grid item xs={12} md={6}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    <TimelineIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
                    Approval Status
                  </Typography>
                  <Box display="flex" flexDirection="column" gap={2}>
                    <Box>
                      <Box display="flex" justifyContent="space-between" mb={1}>
                        <Typography variant="body2">Approved</Typography>
                        <Typography variant="body2">{analytics.approval_rate.toFixed(1)}%</Typography>
                      </Box>
                      <LinearProgress
                        variant="determinate"
                        value={analytics.approval_rate}
                        color="success"
                      />
                    </Box>
                    <Box>
                      <Box display="flex" justifyContent="space-between" mb={1}>
                        <Typography variant="body2">Rejected</Typography>
                        <Typography variant="body2">{analytics.rejection_rate.toFixed(1)}%</Typography>
                      </Box>
                      <LinearProgress
                        variant="determinate"
                        value={analytics.rejection_rate}
                        color="error"
                      />
                    </Box>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        )}
        
        <Box mt={3}>
          <Button variant="outlined" startIcon={<DownloadIcon />}>
            Export Analytics Report
          </Button>
        </Box>
      </TabPanel>
    </Box>
  );
};

export default CommunityContributionDashboard;
