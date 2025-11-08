import React, { useCallback } from 'react';
import {
  Box,
  Paper,
  Typography,
  IconButton,
  Tooltip
} from '@mui/material';
import {
  Delete,
  Add
} from '@mui/icons-material';
import { RecipeSlot, RecipeItem } from './RecipeBuilder';
import './RecipeGrid.css';

export interface RecipeGridProps {
  pattern: RecipeSlot[][];
  width: number;
  height: number;
  onItemPlace: (slot: RecipeSlot, item: RecipeItem) => void;
  onItemRemove: (slot: RecipeSlot) => void;
  selectedItem: RecipeItem | null;
  readOnly?: boolean;
  recipeType: string;
}

export const RecipeGrid: React.FC<RecipeGridProps> = ({
  pattern,
  width,
  height,
  onItemPlace,
  onItemRemove,
  selectedItem,
  readOnly = false,
  recipeType
}) => {
  const handleSlotClick = useCallback((slot: RecipeSlot) => {
    if (readOnly) return;

    if (slot.item) {
      // Remove item from slot
      onItemRemove(slot);
    } else if (selectedItem) {
      // Place item in slot
      onItemPlace(slot, selectedItem);
    }
  }, [selectedItem, onItemPlace, onItemRemove, readOnly]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    if (readOnly) return;
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  }, [readOnly]);

  const handleDrop = useCallback((e: React.DragEvent, slot: RecipeSlot) => {
    if (readOnly) return;
    e.preventDefault();
    
    const itemData = e.dataTransfer.getData('application/json');
    if (itemData) {
      try {
        const item: RecipeItem = JSON.parse(itemData);
        onItemPlace(slot, item);
      } catch (error) {
        console.error('Failed to parse dragged item data:', error);
      }
    }
  }, [onItemPlace, readOnly]);

  const handleDragStart = useCallback((e: React.DragEvent, item: RecipeItem) => {
    if (readOnly) return;
    e.dataTransfer.setData('application/json', JSON.stringify(item));
    e.dataTransfer.effectAllowed = 'move';
  }, [readOnly]);

  const getSlotStyle = (slot: RecipeSlot) => {
    const baseStyle = {
      width: `${100 / width}%`,
      height: `${100 / height}%`,
      border: '1px dashed #ccc',
      backgroundColor: slot.item ? '#f5f5f5' : '#fafafa',
      cursor: readOnly ? 'default' : 'pointer',
      position: 'relative' as const,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      transition: 'all 0.2s ease',
      borderRadius: '4px',
      margin: '2px'
    };

    if (!readOnly && selectedItem && !slot.item) {
      baseStyle.backgroundColor = '#e3f2fd';
      baseStyle.border = '2px dashed #2196f3';
    }

    if (slot.item) {
      baseStyle.backgroundColor = '#e8f5e8';
      baseStyle.border = '2px solid #4caf50';
    }

    return baseStyle;
  };

  const renderSlot = (slot: RecipeSlot) => {
    const isCraftingRecipe = ['shaped', 'shapeless', 'brewing', 'stonecutter'].includes(recipeType);
    const isSmeltingRecipe = ['furnace', 'blast_furnace', 'campfire', 'smoker'].includes(recipeType);

    return (
      <Box
        key={`${slot.x}-${slot.y}`}
        sx={getSlotStyle(slot)}
        onClick={() => handleSlotClick(slot)}
        onDragOver={handleDragOver}
        onDrop={(e) => handleDrop(e, slot)}
        className="recipe-slot"
      >
        {slot.item ? (
          <Box className="slot-content">
            {slot.item.texture && (
              <img
                src={slot.item.texture}
                alt={slot.item.name}
                className="item-icon"
                draggable={!readOnly}
                onDragStart={(e) => handleDragStart(e, slot.item!)}
              />
            )}
            <Typography variant="caption" className="item-name">
              {slot.item.name}
              {slot.item.count && slot.item.count > 1 && ` x${slot.item.count}`}
            </Typography>
            {!readOnly && (
              <IconButton
                size="small"
                className="remove-button"
                onClick={(e) => {
                  e.stopPropagation();
                  onItemRemove(slot);
                }}
              >
                <Delete fontSize="small" />
              </IconButton>
            )}
          </Box>
        ) : (
          <Box className="empty-slot">
            {selectedItem && !readOnly && (
              <Add fontSize="small" color="action" />
            )}
            {isCraftingRecipe && (
              <Typography variant="caption" color="text.secondary">
                Slot {slot.y * width + slot.x + 1}
              </Typography>
            )}
            {isSmeltingRecipe && slot.x === 0 && slot.y === 0 && (
              <Typography variant="caption" color="text.secondary">
                Input
              </Typography>
            )}
          </Box>
        )}
      </Box>
    );
  };

  return (
    <Box className="recipe-grid">
      <Typography variant="subtitle2" gutterBottom>
        {recipeType === 'shaped' && 'Shaped Recipe Pattern'}
        {recipeType === 'shapeless' && 'Shapeless Recipe Ingredients'}
        {recipeType === 'furnace' && 'Smelting Input'}
        {recipeType === 'blast_furnace' && 'Blasting Input'}
        {recipeType === 'campfire' && 'Campfire Input'}
        {recipeType === 'smoker' && 'Smoking Input'}
        {recipeType === 'brewing' && 'Brewing Ingredients'}
        {recipeType === 'stonecutter' && 'Stonecutting Input'}
      </Typography>
      
      <Paper className="grid-container" sx={{ p: 2, minHeight: 200 }}>
        <Box
          className="grid"
          sx={{
            display: 'grid',
            gridTemplateColumns: `repeat(${width}, 1fr)`,
            gridTemplateRows: `repeat(${height}, 1fr)`,
            gap: '4px',
            aspectRatio: width / height
          }}
        >
          {pattern.map(row =>
            row.map(slot => renderSlot(slot))
          )}
        </Box>
      </Paper>

      {/* Instructions */}
      {!readOnly && (
        <Box className="grid-instructions" sx={{ mt: 2 }}>
          <Typography variant="caption" color="text.secondary">
            Click empty slots to place selected item • Click filled slots to remove • Drag items to reorder
          </Typography>
        </Box>
      )}
    </Box>
  );
};
