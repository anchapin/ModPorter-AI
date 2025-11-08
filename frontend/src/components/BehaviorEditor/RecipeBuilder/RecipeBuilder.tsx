import React, { useState, useCallback, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  Grid,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TextField,
  Alert
} from '@mui/material';
import {
  Save
} from '@mui/icons-material';
import { RecipeGrid } from './RecipeGrid';
import { ItemLibrary } from './ItemLibrary';
import { RecipeValidation } from './RecipeValidation';
import './RecipeBuilder.css';

export interface RecipeItem {
  id: string;
  type: 'minecraft:item' | 'minecraft:item_tag' | 'minecraft:block' | 'minecraft:block_tag';
  name: string;
  count?: number;
  data?: number;
  texture?: string;
}

export interface RecipeSlot {
  x: number;
  y: number;
  item: RecipeItem | null;
}

export interface Recipe {
  id: string;
  identifier: string;
  type: 'shaped' | 'shapeless' | 'furnace' | 'blast_furnace' | 'campfire' | 'smoker' | 'brewing' | 'stonecutter';
  name: string;
  description?: string;
  pattern?: RecipeSlot[][];
  ingredients: RecipeItem[];
  result: RecipeItem;
  experience?: number;
  cookingTime?: number;
  priority: number;
  group?: string;
  tags?: string[];
}

export interface RecipeBuilderProps {
  initialRecipe?: Partial<Recipe>;
  onRecipeChange: (recipe: Recipe) => void;
  onRecipeSave?: (recipe: Recipe) => void;
  availableItems: RecipeItem[];
  readOnly?: boolean;
}

export const RecipeBuilder: React.FC<RecipeBuilderProps> = ({
  initialRecipe = {},
  onRecipeChange,
  onRecipeSave,
  availableItems = [],
  readOnly = false
}) => {
  const [currentRecipe, setCurrentRecipe] = useState<Recipe>({
    id: '',
    identifier: '',
    type: 'shaped',
    name: '',
    description: '',
    pattern: [],
    ingredients: [],
    result: { id: 'result', type: 'minecraft:item', name: '', count: 1 },
    experience: 0,
    cookingTime: 200,
    priority: 0,
    group: '',
    tags: [],
    ...initialRecipe
  });

  const [selectedItem, setSelectedItem] = useState<RecipeItem | null>(null);
  const [validationErrors, setValidationErrors] = useState<string[]>([]);

  // Grid size based on recipe type
  const getGridSize = () => {
    switch (currentRecipe.type) {
      case 'shaped':
      case 'shapeless':
        return { width: 3, height: 3 };
      case 'furnace':
      case 'blast_furnace':
      case 'campfire':
      case 'smoker':
        return { width: 1, height: 1 };
      case 'brewing':
        return { width: 3, height: 3 }; // 3 ingredient slots + 1 output
      case 'stonecutter':
        return { width: 1, height: 1 };
      default:
        return { width: 3, height: 3 };
    }
  };

  // Initialize empty pattern if needed
  useEffect(() => {
    const { width, height } = getGridSize();
    if (!currentRecipe.pattern || currentRecipe.pattern.length === 0) {
      const emptyPattern: RecipeSlot[][] = [];
      for (let y = 0; y < height; y++) {
        const row: RecipeSlot[] = [];
        for (let x = 0; x < width; x++) {
          row.push({ x, y, item: null });
        }
        emptyPattern.push(row);
      }
      setCurrentRecipe(prev => ({ ...prev, pattern: emptyPattern }));
    }
  }, [currentRecipe.type, currentRecipe.pattern]);

  // Handle recipe field changes
  const handleFieldChange = useCallback((field: keyof Recipe, value: any) => {
    const updatedRecipe = { ...currentRecipe, [field]: value };
    setCurrentRecipe(updatedRecipe);
    onRecipeChange(updatedRecipe);
  }, [currentRecipe, onRecipeChange]);

  // Handle item placement in grid
  const handleItemPlace = useCallback((slot: RecipeSlot, item: RecipeItem) => {
    const newPattern = [...currentRecipe.pattern!];
    const slotRow = newPattern[slot.y];
    const updatedSlot = { ...slot, item };
    newPattern[slot.y] = [...slotRow.slice(0, slot.x), updatedSlot, ...slotRow.slice(slot.x + 1)];
    
    const updatedRecipe = { ...currentRecipe, pattern: newPattern };
    setCurrentRecipe(updatedRecipe);
    onRecipeChange(updatedRecipe);
  }, [currentRecipe, onRecipeChange]);

  // Handle item removal from grid
  const handleItemRemove = useCallback((slot: RecipeSlot) => {
    const newPattern = [...currentRecipe.pattern!];
    const slotRow = newPattern[slot.y];
    const updatedSlot = { ...slot, item: null };
    newPattern[slot.y] = [...slotRow.slice(0, slot.x), updatedSlot, ...slotRow.slice(slot.x + 1)];
    
    const updatedRecipe = { ...currentRecipe, pattern: newPattern };
    setCurrentRecipe(updatedRecipe);
    onRecipeChange(updatedRecipe);
  }, [currentRecipe, onRecipeChange]);



  // History functionality is disabled - undo/redo functions removed

  // Validate recipe
  useEffect(() => {
    const validator = new RecipeValidation();
    const errors = validator.validate(currentRecipe, availableItems);
    setValidationErrors(errors);
  }, [currentRecipe, availableItems]);

  const gridSize = getGridSize();
  const hasUnsavedChanges = JSON.stringify(currentRecipe) !== JSON.stringify(initialRecipe);

  return (
    <Box className="recipe-builder">
      <Paper className="recipe-builder-header" sx={{ p: 2, mb: 2 }}>
        <Box display="flex" justifyContent="space-between" alignItems="center">
          <Typography variant="h6">
            Recipe Builder
          </Typography>
          <Box display="flex" gap={1}>
            {/* Undo/Redo functionality temporarily disabled */}
          </Box>
            {onRecipeSave && (
              <Button
                variant="contained"
                startIcon={<Save />}
                onClick={() => onRecipeSave(currentRecipe)}
                disabled={validationErrors.length > 0 || readOnly}
              >
                Save Recipe
              </Button>
            )}
          </Box>
      </Paper>

      <Grid container spacing={2}>
        {/* Recipe Properties */}
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 2, height: '100%' }}>
            <Typography variant="subtitle1" gutterBottom>
              Recipe Properties
            </Typography>
            
            <FormControl fullWidth sx={{ mb: 2 }}>
              <InputLabel>Recipe Type</InputLabel>
              <Select
                value={currentRecipe.type}
                onChange={(e) => handleFieldChange('type', e.target.value)}
                disabled={readOnly}
              >
                <MenuItem value="shaped">Shaped Crafting</MenuItem>
                <MenuItem value="shapeless">Shapeless Crafting</MenuItem>
                <MenuItem value="furnace">Furnace Smelting</MenuItem>
                <MenuItem value="blast_furnace">Blast Furnace</MenuItem>
                <MenuItem value="campfire">Campfire Cooking</MenuItem>
                <MenuItem value="smoker">Smoker</MenuItem>
                <MenuItem value="brewing">Brewing Stand</MenuItem>
                <MenuItem value="stonecutter">Stonecutter</MenuItem>
              </Select>
            </FormControl>

            <TextField
              fullWidth
              label="Recipe Identifier"
              value={currentRecipe.identifier}
              onChange={(e) => handleFieldChange('identifier', e.target.value)}
              disabled={readOnly}
              sx={{ mb: 2 }}
              helperText="Unique identifier (e.g., 'minecraft:oak_planks')"
            />

            <TextField
              fullWidth
              label="Recipe Name"
              value={currentRecipe.name}
              onChange={(e) => handleFieldChange('name', e.target.value)}
              disabled={readOnly}
              sx={{ mb: 2 }}
            />

            <TextField
              fullWidth
              label="Description"
              value={currentRecipe.description || ''}
              onChange={(e) => handleFieldChange('description', e.target.value)}
              disabled={readOnly}
              multiline
              rows={3}
              sx={{ mb: 2 }}
            />

            {/* Type-specific fields */}
            {currentRecipe.type === 'shaped' && (
              <TextField
                fullWidth
                label="Pattern Shape (optional)"
                value={currentRecipe.group || ''}
                onChange={(e) => handleFieldChange('group', e.target.value)}
                disabled={readOnly}
                sx={{ mb: 2 }}
                helperText="For shaped recipes with flexible patterns"
              />
            )}

            {(currentRecipe.type === 'furnace' || 
              currentRecipe.type === 'blast_furnace' || 
              currentRecipe.type === 'campfire' || 
              currentRecipe.type === 'smoker') && (
              <>
                <TextField
                  fullWidth
                  label="Experience"
                  type="number"
                  value={currentRecipe.experience || 0}
                  onChange={(e) => handleFieldChange('experience', parseFloat(e.target.value) || 0)}
                  disabled={readOnly}
                  sx={{ mb: 2 }}
                  inputProps={{ min: 0, max: 1, step: 0.1 }}
                />
                <TextField
                  fullWidth
                  label="Cooking Time (ticks)"
                  type="number"
                  value={currentRecipe.cookingTime || 200}
                  onChange={(e) => handleFieldChange('cookingTime', parseInt(e.target.value) || 200)}
                  disabled={readOnly}
                  sx={{ mb: 2 }}
                  inputProps={{ min: 1, max: 32767 }}
                />
              </>
            )}

            <TextField
              fullWidth
              label="Priority"
              type="number"
              value={currentRecipe.priority || 0}
              onChange={(e) => handleFieldChange('priority', parseInt(e.target.value) || 0)}
              disabled={readOnly}
              sx={{ mb: 2 }}
              helperText="Higher priority recipes are checked first"
            />
          </Paper>
        </Grid>

        {/* Recipe Grid */}
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 2, height: '100%' }}>
            <Typography variant="subtitle1" gutterBottom>
              Recipe Grid
            </Typography>
            
            <RecipeGrid
              pattern={currentRecipe.pattern || []}
              width={gridSize.width}
              height={gridSize.height}
              onItemPlace={handleItemPlace}
              onItemRemove={handleItemRemove}
              selectedItem={selectedItem}
              readOnly={readOnly}
              recipeType={currentRecipe.type}
            />

            {/* Result Section */}
            <Box mt={2} p={2} sx={{ border: '1px dashed #ccc', borderRadius: 1 }}>
              <Typography variant="subtitle2" gutterBottom>
                Result:
              </Typography>
              <Box display="flex" alignItems="center" gap={2}>
                <Box className="result-item">
                  {currentRecipe.result.texture && (
                    <img 
                      src={currentRecipe.result.texture} 
                      alt={currentRecipe.result.name}
                      className="item-icon"
                    />
                  )}
                  <Typography variant="body2">
                    {currentRecipe.result.name || 'Empty'}
                  </Typography>
                </Box>
                <TextField
                  label="Count"
                  type="number"
                  value={currentRecipe.result.count || 1}
                  onChange={(e) => handleFieldChange('result', {
                    ...currentRecipe.result,
                    count: parseInt(e.target.value) || 1
                  })}
                  disabled={readOnly}
                  size="small"
                  inputProps={{ min: 1, max: 64 }}
                />
              </Box>
            </Box>
          </Paper>
        </Grid>

        {/* Item Library */}
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 2, height: '100%' }}>
            <Typography variant="subtitle1" gutterBottom>
              Item Library
            </Typography>
            
            <ItemLibrary
              items={availableItems}
              selectedItem={selectedItem}
              onItemSelect={setSelectedItem}
              onResultSelect={(item) => handleFieldChange('result', { ...item, count: 1 })}
              readOnly={readOnly}
            />
          </Paper>
        </Grid>
      </Grid>

      {/* Validation Errors */}
      {validationErrors.length > 0 && (
        <Alert severity="error" sx={{ mt: 2 }}>
          <Typography variant="subtitle2" gutterBottom>
            Validation Errors:
          </Typography>
          <ul>
            {validationErrors.map((error, index) => (
              <li key={index}>{error}</li>
            ))}
          </ul>
        </Alert>
      )}

      {/* Status Indicator */}
      {hasUnsavedChanges && (
        <Box sx={{ mt: 2, textAlign: 'center' }}>
          <Typography variant="caption" color="warning.main">
            You have unsaved changes
          </Typography>
        </Box>
      )}
    </Box>
  );
};
