import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Button,
  Chip,
  TextField,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Rating,
  IconButton,
  InputAdornment,
  Grid,
  Paper,
  Tabs,
  Tab,
} from '@mui/material';
import {
  Search,
  Add,
  FilterList,
  Star,
  CheckCircle,
  Cancel,
  Visibility,
  ContentCopy,
  Download,
} from '@mui/icons-material';
import { API_BASE_URL } from '../../services/api';
import './PatternLibrary.css';

export interface Pattern {
  id: string;
  name: string;
  description: string;
  category: string;
  tags: string[];
  javaCode: string;
  bedrockCode: string;
  author: string;
  rating: number;
  ratingCount: number;
  downloads: number;
  status: 'draft' | 'pending' | 'approved' | 'rejected';
  createdAt: string;
  updatedAt: string;
  version: string;
}

interface PatternLibraryProps {
  onPatternSelect?: (pattern: Pattern) => void;
  onPatternUse?: (pattern: Pattern) => void;
  showReviewWorkflow?: boolean;
}

const CATEGORIES = [
  'Blocks',
  'Items',
  'Recipes',
  'Entities',
  'Biomes',
  'Loot Tables',
  'Trading',
  'Custom Commands',
  'Other',
];

const PatternLibrary: React.FC<PatternLibraryProps> = ({
  onPatternSelect,
  onPatternUse,
  showReviewWorkflow = false,
}) => {
  const [patterns, setPatterns] = useState<Pattern[]>([]);
  const [pendingPatterns, setPendingPatterns] = useState<Pattern[]>([]);
  const [myPatterns, setMyPatterns] = useState<Pattern[]>([]);
  const [featuredPatterns, setFeaturedPatterns] = useState<Pattern[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<string>('');
  const [sortBy, setSortBy] = useState<'rating' | 'downloads' | 'newest'>('rating');
  const [selectedPattern, setSelectedPattern] = useState<Pattern | null>(null);
  const [tabValue, setTabValue] = useState(0);
  const [submitDialogOpen, setSubmitDialogOpen] = useState(false);
  const [reviewDialogOpen, setReviewDialogOpen] = useState(false);
  const [patternToReview, setPatternToReview] = useState<Pattern | null>(null);
  const [reviewComment, setReviewComment] = useState('');
  const [newPattern, setNewPattern] = useState<Partial<Pattern>>({
    name: '',
    description: '',
    category: '',
    tags: [],
    javaCode: '',
    bedrockCode: '',
  });

  // Fetch patterns
  const fetchPatterns = useCallback(async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      if (searchQuery) params.set('search', searchQuery);
      if (categoryFilter) params.set('category', categoryFilter);
      params.set('sort', sortBy);
      params.set('status', 'approved');

      const response = await fetch(`${API_BASE_URL}/patterns?${params}`);
      if (!response.ok) throw new Error('Failed to fetch patterns');

      const data = await response.json();
      setPatterns(data.patterns || []);
    } catch (err) {
      console.error('Error fetching patterns:', err);
      // Use mock data for demo
      setPatterns(getMockPatterns());
    } finally {
      setLoading(false);
    }
  }, [searchQuery, categoryFilter, sortBy]);

  useEffect(() => {
    fetchPatterns();
    if (showReviewWorkflow) {
      fetchPendingPatterns();
      fetchMyPatterns();
      fetchFeaturedPatterns();
    }
  }, [fetchPatterns, showReviewWorkflow]);

  // Fetch pending patterns for review
  const fetchPendingPatterns = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/patterns?status=pending`);
      if (!response.ok) throw new Error('Failed to fetch pending patterns');
      const data = await response.json();
      setPendingPatterns(data.patterns || []);
    } catch (err) {
      console.error('Error fetching pending patterns:', err);
      setPendingPatterns(getMockPatterns().filter(p => p.status === 'pending'));
    }
  }, []);

  // Fetch user's patterns
  const fetchMyPatterns = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/patterns/my`);
      if (!response.ok) throw new Error('Failed to fetch my patterns');
      const data = await response.json();
      setMyPatterns(data.patterns || []);
    } catch (err) {
      console.error('Error fetching my patterns:', err);
      setMyPatterns(getMockPatterns().slice(0, 2));
    }
  }, []);

  // Fetch featured patterns
  const fetchFeaturedPatterns = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/patterns?featured=true`);
      if (!response.ok) throw new Error('Failed to fetch featured patterns');
      const data = await response.json();
      setFeaturedPatterns(data.patterns || []);
    } catch (err) {
      console.error('Error fetching featured patterns:', err);
      setFeaturedPatterns(getMockPatterns().slice(0, 3));
    }
  }, []);

  // Handle pattern review (approve/reject)
  const handleReviewPattern = async (pattern: Pattern, approved: boolean) => {
    try {
      const response = await fetch(`${API_BASE_URL}/patterns/${pattern.id}/review`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ approved, comment: reviewComment }),
      });

      if (!response.ok) throw new Error('Failed to review pattern');

      setReviewDialogOpen(false);
      setPatternToReview(null);
      setReviewComment('');
      fetchPendingPatterns();
    } catch (err) {
      console.error('Error reviewing pattern:', err);
    }
  };

  // Handle rate pattern
  const handleRatePattern = async (pattern: Pattern, rating: number) => {
    try {
      await fetch(`${API_BASE_URL}/patterns/${pattern.id}/rate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rating }),
      });
      fetchPatterns();
    } catch (err) {
      console.error('Error rating pattern:', err);
    }
  };

  const handlePatternClick = (pattern: Pattern) => {
    setSelectedPattern(pattern);
    onPatternSelect?.(pattern);
  };

  const handleUsePattern = (pattern: Pattern) => {
    onPatternUse?.(pattern);
  };

  const handleCopyCode = (code: string) => {
    navigator.clipboard.writeText(code);
  };

  const handleSubmitPattern = async () => {
    if (!newPattern.name || !newPattern.category || !newPattern.bedrockCode) {
      return;
    }

    try {
      const response = await fetch(`${API_BASE_URL}/patterns`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...newPattern,
          status: 'pending',
        }),
      });

      if (!response.ok) throw new Error('Failed to submit pattern');

      setSubmitDialogOpen(false);
      setNewPattern({
        name: '',
        description: '',
        category: '',
        tags: [],
        javaCode: '',
        bedrockCode: '',
      });
      fetchPatterns();
    } catch (err) {
      console.error('Error submitting pattern:', err);
    }
  };

  const filteredPatterns = patterns.filter((pattern) =>
    pattern.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    pattern.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
    pattern.tags.some((tag) => tag.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  return (
    <Box className="pattern-library">
      {/* Header */}
      <Paper className="pattern-library-header" elevation={2}>
        <Box className="header-content">
          <Typography variant="h5" component="h2">
            Community Pattern Library
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Share and discover conversion patterns
          </Typography>
        </Box>
        <Button
          variant="contained"
          startIcon={<Add />}
          onClick={() => setSubmitDialogOpen(true)}
        >
          Submit Pattern
        </Button>
      </Paper>

      {/* Tabs */}
      <Tabs
        value={tabValue}
        onChange={(_, value) => setTabValue(value)}
        className="pattern-tabs"
      >
        <Tab label="Browse Patterns" />
        <Tab label="My Patterns" />
        <Tab label="Pending Review" />
      </Tabs>

      {/* Search and Filters */}
      <Paper className="pattern-filters" elevation={1}>
        <TextField
          placeholder="Search patterns..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          size="small"
          className="search-field"
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <Search />
              </InputAdornment>
            ),
          }}
        />
        <FormControl size="small" className="category-filter">
          <InputLabel>Category</InputLabel>
          <Select
            value={categoryFilter}
            label="Category"
            onChange={(e) => setCategoryFilter(e.target.value)}
          >
            <MenuItem value="">All Categories</MenuItem>
            {CATEGORIES.map((cat) => (
              <MenuItem key={cat} value={cat}>
                {cat}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
        <FormControl size="small" className="sort-filter">
          <InputLabel>Sort By</InputLabel>
          <Select
            value={sortBy}
            label="Sort By"
            onChange={(e) => setSortBy(e.target.value as any)}
          >
            <MenuItem value="rating">Top Rated</MenuItem>
            <MenuItem value="downloads">Most Downloads</MenuItem>
            <MenuItem value="newest">Newest</MenuItem>
          </Select>
        </FormControl>
      </Paper>

      {/* Pattern Grid */}
      <Grid container spacing={2} className="pattern-grid">
        {filteredPatterns.map((pattern) => (
          <Grid item xs={12} sm={6} md={4} key={pattern.id}>
            <Card
              className="pattern-card"
              onClick={() => handlePatternClick(pattern)}
            >
              <CardContent>
                <Box className="pattern-card-header">
                  <Typography variant="h6" className="pattern-name">
                    {pattern.name}
                  </Typography>
                  <Chip
                    label={pattern.category}
                    size="small"
                    className="category-chip"
                  />
                </Box>
                <Typography
                  variant="body2"
                  color="text.secondary"
                  className="pattern-description"
                >
                  {pattern.description}
                </Typography>
                <Box className="pattern-tags">
                  {pattern.tags.slice(0, 3).map((tag) => (
                    <Chip
                      key={tag}
                      label={tag}
                      size="small"
                      variant="outlined"
                      className="tag-chip"
                    />
                  ))}
                </Box>
                <Box className="pattern-stats">
                  <Box className="stat">
                    <Star fontSize="small" className="rating-icon" />
                    <Typography variant="caption">
                      {pattern.rating.toFixed(1)} ({pattern.ratingCount})
                    </Typography>
                  </Box>
                  <Box className="stat">
                    <Download fontSize="small" />
                    <Typography variant="caption">{pattern.downloads}</Typography>
                  </Box>
                  <Box className="stat">
                    <Typography variant="caption" className="author">
                      by {pattern.author}
                    </Typography>
                  </Box>
                </Box>
              </CardContent>
              <Box className="pattern-actions">
                <Button
                  size="small"
                  startIcon={<Visibility />}
                  onClick={(e) => {
                    e.stopPropagation();
                    handlePatternClick(pattern);
                  }}
                >
                  View
                </Button>
                <Button
                  size="small"
                  variant="contained"
                  startIcon={<CheckCircle />}
                  onClick={(e) => {
                    e.stopPropagation();
                    handleUsePattern(pattern);
                  }}
                >
                  Use
                </Button>
              </Box>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Pattern Detail Dialog */}
      <Dialog
        open={!!selectedPattern}
        onClose={() => setSelectedPattern(null)}
        maxWidth="md"
        fullWidth
        className="pattern-detail-dialog"
      >
        {selectedPattern && (
          <>
            <DialogTitle>
              <Box className="dialog-header">
                <Typography variant="h5">{selectedPattern.name}</Typography>
                <IconButton onClick={() => setSelectedPattern(null)}>
                  <Cancel />
                </IconButton>
              </Box>
            </DialogTitle>
            <DialogContent>
              <Box className="pattern-detail">
                <Box className="detail-info">
                  <Chip label={selectedPattern.category} className="category-chip" />
                  <Rating value={selectedPattern.rating} readOnly />
                  <Typography variant="body2">
                    by {selectedPattern.author} • {selectedPattern.downloads} downloads
                  </Typography>
                </Box>
                <Typography variant="body1" className="detail-description">
                  {selectedPattern.description}
                </Typography>
                <Grid container spacing={2}>
                  <Grid item xs={12} md={6}>
                    <Typography variant="subtitle2" className="code-label">
                      Java (Source)
                    </Typography>
                    <Paper className="code-block">
                      <IconButton
                        size="small"
                        className="copy-button"
                        onClick={() => handleCopyCode(selectedPattern.javaCode)}
                      >
                        <ContentCopy fontSize="small" />
                      </IconButton>
                      <pre>{selectedPattern.javaCode}</pre>
                    </Paper>
                  </Grid>
                  <Grid item xs={12} md={6}>
                    <Typography variant="subtitle2" className="code-label">
                      Bedrock (Target)
                    </Typography>
                    <Paper className="code-block">
                      <IconButton
                        size="small"
                        className="copy-button"
                        onClick={() => handleCopyCode(selectedPattern.bedrockCode)}
                      >
                        <ContentCopy fontSize="small" />
                      </IconButton>
                      <pre>{selectedPattern.bedrockCode}</pre>
                    </Paper>
                  </Grid>
                </Grid>
              </Box>
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setSelectedPattern(null)}>Close</Button>
              <Button
                variant="contained"
                startIcon={<CheckCircle />}
                onClick={() => handleUsePattern(selectedPattern)}
              >
                Use This Pattern
              </Button>
            </DialogActions>
          </>
        )}
      </Dialog>

      {/* Submit Pattern Dialog */}
      <Dialog
        open={submitDialogOpen}
        onClose={() => setSubmitDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>Submit a New Pattern</DialogTitle>
        <DialogContent>
          <Box className="submit-form">
            <TextField
              label="Pattern Name"
              value={newPattern.name}
              onChange={(e) =>
                setNewPattern({ ...newPattern, name: e.target.value })
              }
              fullWidth
              required
              margin="normal"
            />
            <TextField
              label="Description"
              value={newPattern.description}
              onChange={(e) =>
                setNewPattern({ ...newPattern, description: e.target.value })
              }
              fullWidth
              multiline
              rows={2}
              margin="normal"
            />
            <FormControl fullWidth margin="normal" required>
              <InputLabel>Category</InputLabel>
              <Select
                value={newPattern.category}
                label="Category"
                onChange={(e) =>
                  setNewPattern({ ...newPattern, category: e.target.value })
                }
              >
                {CATEGORIES.map((cat) => (
                  <MenuItem key={cat} value={cat}>
                    {cat}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <TextField
              label="Tags (comma-separated)"
              value={newPattern.tags?.join(', ')}
              onChange={(e) =>
                setNewPattern({
                  ...newPattern,
                  tags: e.target.value.split(',').map((t) => t.trim()),
                })
              }
              fullWidth
              margin="normal"
            />
            <TextField
              label="Java Code (optional)"
              value={newPattern.javaCode}
              onChange={(e) =>
                setNewPattern({ ...newPattern, javaCode: e.target.value })
              }
              fullWidth
              multiline
              rows={4}
              margin="normal"
            />
            <TextField
              label="Bedrock Code"
              value={newPattern.bedrockCode}
              onChange={(e) =>
                setNewPattern({ ...newPattern, bedrockCode: e.target.value })
              }
              fullWidth
              multiline
              rows={4}
              required
              margin="normal"
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSubmitDialogOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleSubmitPattern}>
            Submit for Review
          </Button>
        </DialogActions>
      </Dialog>

      {/* Review Pattern Dialog */}
      <Dialog
        open={reviewDialogOpen}
        onClose={() => setReviewDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Review Pattern: {patternToReview?.name}</DialogTitle>
        <DialogContent>
          <Box className="review-form">
            <Typography variant="body2" color="text.secondary" paragraph>
              Review this pattern submission and decide whether to approve or reject it.
            </Typography>
            <TextField
              label="Review Comment"
              value={reviewComment}
              onChange={(e) => setReviewComment(e.target.value)}
              fullWidth
              multiline
              rows={3}
              margin="normal"
              placeholder="Optional feedback for the author..."
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setReviewDialogOpen(false)}>Cancel</Button>
          <Button
            color="error"
            startIcon={<Cancel />}
            onClick={() => patternToReview && handleReviewPattern(patternToReview, false)}
          >
            Reject
          </Button>
          <Button
            variant="contained"
            color="success"
            startIcon={<CheckCircle />}
            onClick={() => patternToReview && handleReviewPattern(patternToReview, true)}
          >
            Approve
          </Button>
        </DialogActions>
      </Dialog>

      {/* Featured Patterns Section */}
      {showReviewWorkflow && featuredPatterns.length > 0 && (
        <Paper className="featured-patterns" elevation={1}>
          <Typography variant="h6" className="section-title">
            ⭐ Featured Patterns
          </Typography>
          <Grid container spacing={2}>
            {featuredPatterns.map((pattern) => (
              <Grid item xs={12} sm={4} key={pattern.id}>
                <Card className="featured-card" onClick={() => handlePatternClick(pattern)}>
                  <CardContent>
                    <Typography variant="subtitle1" fontWeight="bold">
                      {pattern.name}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {pattern.description}
                    </Typography>
                    <Box className="pattern-stats">
                      <Rating value={pattern.rating} readOnly size="small" />
                      <Typography variant="caption">
                        {pattern.downloads} downloads
                      </Typography>
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        </Paper>
      )}

      {/* Pending Review Section */}
      {showReviewWorkflow && pendingPatterns.length > 0 && (
        <Paper className="pending-review" elevation={1}>
          <Typography variant="h6" className="section-title">
            📋 Pending Review ({pendingPatterns.length})
          </Typography>
          <List>
            {pendingPatterns.map((pattern) => (
              <ListItem
                key={pattern.id}
                className="pending-item"
                secondaryAction={
                  <Box>
                    <IconButton
                      color="success"
                      onClick={() => {
                        setPatternToReview(pattern);
                        setReviewDialogOpen(true);
                      }}
                    >
                      <CheckCircle />
                    </IconButton>
                    <IconButton
                      color="error"
                      onClick={() => {
                        setPatternToReview(pattern);
                        setReviewDialogOpen(true);
                      }}
                    >
                      <Cancel />
                    </IconButton>
                  </Box>
                }
              >
                <ListItemAvatar>
                  <Avatar>{pattern.name.charAt(0)}</Avatar>
                </ListItemAvatar>
                <ListItemText
                  primary={pattern.name}
                  secondary={`by ${pattern.author} • ${pattern.category}`}
                />
              </ListItem>
            ))}
          </List>
        </Paper>
      )}
    </Box>
  );
};

// Mock patterns for demo
function getMockPatterns(): Pattern[] {
  return [
    {
      id: '1',
      name: 'Custom Crafting Table',
      description: 'A simple crafting table recipe pattern',
      category: 'Recipes',
      tags: ['crafting', 'table', 'recipe'],
      javaCode: 'public class CustomCraftingTable extends Item { }',
      bedrockCode: '// Use crafting_table component',
      author: 'ModPorter',
      rating: 4.5,
      ratingCount: 120,
      downloads: 540,
      status: 'approved',
      createdAt: '2024-01-15',
      updatedAt: '2024-02-20',
      version: '1.0',
    },
    {
      id: '2',
      name: 'Diamond Block Recipe',
      description: 'Convert diamond block crafting from Java to Bedrock',
      category: 'Recipes',
      tags: ['diamond', 'recipe', 'block'],
      javaCode: "recipeShaped('diamond_block', 'DDD', 'D', 'D', 'D', Items.DIAMOND);",
      bedrockCode: '{"pattern": ["DDD", "DDD", "DDD"], "key": {"D": "minecraft:diamond"}}',
      author: 'ModPorter',
      rating: 4.8,
      ratingCount: 230,
      downloads: 890,
      status: 'approved',
      createdAt: '2024-01-20',
      updatedAt: '2024-02-15',
      version: '1.2',
    },
    {
      id: '3',
      name: 'Zombie Villager Conversion',
      description: 'Convert zombie villager cure mechanism',
      category: 'Entities',
      tags: ['zombie', 'villager', 'cure'],
      javaCode: 'entity.getType() == EntityType.ZOMBIE_VILLAGER',
      bedrockCode: "minecraft:entity = { queries: { is_zombie_villager: true } }",
      author: 'ModPorter',
      rating: 4.2,
      ratingCount: 85,
      downloads: 320,
      status: 'approved',
      createdAt: '2024-02-01',
      updatedAt: '2024-02-10',
      version: '1.0',
    },
  ];
}

export default PatternLibrary;
