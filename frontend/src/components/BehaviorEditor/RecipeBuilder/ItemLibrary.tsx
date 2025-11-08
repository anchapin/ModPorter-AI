import React, { useState, useMemo } from 'react';
import {
  Box,
  TextField,
  Typography,
  Grid,
  Paper,
  Chip,
  Button
} from '@mui/material';
import { Search } from '@mui/icons-material';
import { RecipeItem } from './RecipeBuilder';


export interface ItemLibraryProps {
  items: RecipeItem[];
  selectedItem: RecipeItem | null;
  onItemSelect: (item: RecipeItem | null) => void;
  onResultSelect?: (item: RecipeItem) => void;
  readOnly?: boolean;
}

export const ItemLibrary: React.FC<ItemLibraryProps> = ({
  items,
  selectedItem,
  onItemSelect,
  onResultSelect,
  readOnly = false
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');

  // Get unique categories from items
  const categories = useMemo(() => {
    const cats = [...new Set(items.map(item => item.type))];
    return ['all', ...cats];
  }, [items]);

  // Filter items based on search and category
  const filteredItems = useMemo(() => {
    let filtered = items;

    // Filter by category
    if (selectedCategory !== 'all') {
      filtered = filtered.filter(item => item.type === selectedCategory);
    }

    // Filter by search query
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(item =>
        item.name.toLowerCase().includes(query) ||
        item.id.toLowerCase().includes(query) ||
        (item.type && item.type.toLowerCase().includes(query))
      );
    }

    return filtered.sort((a, b) => a.name.localeCompare(b.name));
  }, [items, searchQuery, selectedCategory]);

  const handleItemClick = (item: RecipeItem) => {
    if (readOnly) return;
    
    if (selectedItem?.id === item.id) {
      onItemSelect(null); // Deselect if already selected
    } else {
      onItemSelect(item); // Select new item
    }
  };

  const handleItemDragStart = (e: React.DragEvent, item: RecipeItem) => {
    if (readOnly) return;
    e.dataTransfer.setData('application/json', JSON.stringify(item));
    e.dataTransfer.effectAllowed = 'move';
  };

  const handleSetAsResult = (item: RecipeItem) => {
    if (readOnly || !onResultSelect) return;
    onResultSelect(item);
  };

  const getItemTypeLabel = (type: string) => {
    const labels: Record<string, string> = {
      'minecraft:item': 'Item',
      'minecraft:item_tag': 'Item Tag',
      'minecraft:block': 'Block',
      'minecraft:block_tag': 'Block Tag'
    };
    return labels[type] || type;
  };

  const getItemTypeColor = (type: string) => {
    const colors: Record<string, string> = {
      'minecraft:item': 'primary',
      'minecraft:item_tag': 'secondary',
      'minecraft:block': 'success',
      'minecraft:block_tag': 'warning'
    };
    return colors[type] || 'default';
  };

  return (
    <Box className="item-library">
      {/* Search and Filter */}
      <Box className="library-header" sx={{ mb: 2 }}>
        <TextField
          fullWidth
          placeholder="Search items..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          size="small"
          InputProps={{
            startAdornment: <Search />,
          }}
          sx={{ mb: 1 }}
        />
        
        {/* Category Filter */}
        <Box className="category-filter">
          {categories.map(category => (
            <Chip
              key={category}
              label={category === 'all' ? 'All Items' : getItemTypeLabel(category)}
              onClick={() => setSelectedCategory(category)}
              color={selectedCategory === category ? 'primary' : 'default'}
              variant={selectedCategory === category ? 'filled' : 'outlined'}
              size="small"
              sx={{ mr: 0.5, mb: 0.5 }}
            />
          ))}
        </Box>
      </Box>

      {/* Item Count */}
      <Typography variant="caption" color="text.secondary" sx={{ mb: 1, display: 'block' }}>
        Showing {filteredItems.length} of {items.length} items
      </Typography>

      {/* Items Grid */}
      <Box className="items-grid" sx={{ maxHeight: 400, overflowY: 'auto' }}>
        <Grid container spacing={1}>
          {filteredItems.map(item => (
            <Grid item xs={6} sm={4} md={3} key={item.id}>
              <Paper
                className={`item-card ${selectedItem?.id === item.id ? 'selected' : ''}`}
                onClick={() => handleItemClick(item)}
                draggable={!readOnly}
                onDragStart={(e) => handleItemDragStart(e, item)}
                sx={{
                  p: 1,
                  cursor: readOnly ? 'default' : 'pointer',
                  border: selectedItem?.id === item.id ? '2px solid #1976d2' : '1px solid #e0e0e0',
                  backgroundColor: selectedItem?.id === item.id ? '#e3f2fd' : '#fff',
                  '&:hover': !readOnly ? {
                    backgroundColor: '#f5f5f5',
                    transform: 'translateY(-2px)',
                    boxShadow: 2
                  } : {}
                }}
              >
                <Box className="item-content" textAlign="center">
                  {item.texture && (
                    <img
                      src={item.texture}
                      alt={item.name}
                      className="item-icon"
                      draggable={false}
                    />
                  )}
                  
                  <Typography variant="body2" noWrap title={item.name}>
                    {item.name}
                  </Typography>
                  
                  <Typography variant="caption" color="text.secondary" noWrap>
                    {item.id.split(':').pop()}
                  </Typography>
                  
                  <Box mt={0.5}>
                    <Chip
                      label={getItemTypeLabel(item.type)}
                      size="small"
                      color={getItemTypeColor(item.type) as any}
                      variant="outlined"
                      sx={{ fontSize: '0.6rem', height: 20 }}
                    />
                  </Box>

                  {item.count && item.count > 1 && (
                    <Chip
                      label={`x${item.count}`}
                      size="small"
                      color="default"
                      variant="filled"
                      sx={{ 
                        fontSize: '0.6rem', 
                        height: 16,
                        position: 'absolute',
                        top: 4,
                        right: 4
                      }}
                    />
                  )}
                </Box>

                {/* Action Buttons */}
                {onResultSelect && !readOnly && (
                  <Box className="item-actions" sx={{ mt: 1, textAlign: 'center' }}>
                    <Button
                      size="small"
                      variant="text"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleSetAsResult(item);
                      }}
                      sx={{ fontSize: '0.7rem', minWidth: 'auto' }}
                    >
                      Set as Result
                    </Button>
                  </Box>
                )}
              </Paper>
            </Grid>
          ))}
        </Grid>
      </Box>

      {/* No Results */}
      {filteredItems.length === 0 && (
        <Box className="no-results" sx={{ textAlign: 'center', py: 4 }}>
          <Typography variant="body2" color="text.secondary">
            No items found matching your search
          </Typography>
        </Box>
      )}

      {/* Instructions */}
      {!readOnly && (
        <Box className="library-instructions" sx={{ mt: 2, p: 1, bgcolor: '#f5f5f5', borderRadius: 1 }}>
          <Typography variant="caption" color="text.secondary">
            Click to select item for placement • Drag items directly to recipe grid • Selected item: {selectedItem?.name || 'None'}
          </Typography>
        </Box>
      )}
    </Box>
  );
};
