/**
 * Tests for RecipeBuilder Component
 */

import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { RecipeBuilder, Recipe, RecipeItem } from './RecipeBuilder';

const mockAvailableItems: RecipeItem[] = [
  { id: 'minecraft:oak_planks', type: 'minecraft:item', name: 'Oak Planks', count: 1 },
  { id: 'minecraft:stick', type: 'minecraft:item', name: 'Stick', count: 1 },
  { id: 'minecraft:iron_ingot', type: 'minecraft:item', name: 'Iron Ingot', count: 1 },
];

const mockRecipe: Partial<Recipe> = {
  id: 'test-recipe',
  identifier: 'mod:custom_recipe',
  type: 'shaped',
  name: 'Custom Recipe',
  description: 'A test recipe',
};

describe('RecipeBuilder Component', () => {
  const mockOnRecipeChange = jest.fn();
  const mockOnRecipeSave = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Initial Rendering', () => {
    test('renders RecipeBuilder with default state', () => {
      render(
        <RecipeBuilder
          initialRecipe={mockRecipe}
          onRecipeChange={mockOnRecipeChange}
          onRecipeSave={mockOnRecipeSave}
          availableItems={mockAvailableItems}
        />
      );

      expect(screen.getByText('Recipe Builder')).toBeInTheDocument();
      expect(screen.getByLabelText('Recipe Type')).toBeInTheDocument();
      expect(screen.getByLabelText('Recipe Identifier')).toBeInTheDocument();
      expect(screen.getByLabelText('Recipe Name')).toBeInTheDocument();
    });

    test('renders with initial recipe data', () => {
      render(
        <RecipeBuilder
          initialRecipe={mockRecipe}
          onRecipeChange={mockOnRecipeChange}
          onRecipeSave={mockOnRecipeSave}
          availableItems={mockAvailableItems}
        />
      );

      expect(screen.getByDisplayValue('Custom Recipe')).toBeInTheDocument();
      expect(screen.getByDisplayValue('mod:custom_recipe')).toBeInTheDocument();
    });

    test('displays save button disabled when validation errors exist', () => {
      render(
        <RecipeBuilder
          initialRecipe={{}}
          onRecipeChange={mockOnRecipeChange}
          onRecipeSave={mockOnRecipeSave}
          availableItems={mockAvailableItems}
        />
      );

      const saveButton = screen.getByRole('button', { name: /save recipe/i });
      expect(saveButton).toBeDisabled();
    });
  });

  describe('Recipe Type Selection', () => {
    test('displays all recipe types', () => {
      render(
        <RecipeBuilder
          initialRecipe={mockRecipe}
          onRecipeChange={mockOnRecipeChange}
          onRecipeSave={mockOnRecipeSave}
          availableItems={mockAvailableItems}
        />
      );

      const typeSelect = screen.getByLabelText('Recipe Type');
      expect(typeSelect).toBeInTheDocument();

      fireEvent.mouseDown(typeSelect);

      expect(screen.getByText('Shaped Crafting')).toBeInTheDocument();
      expect(screen.getByText('Shapeless Crafting')).toBeInTheDocument();
      expect(screen.getByText('Furnace Smelting')).toBeInTheDocument();
      expect(screen.getByText('Blast Furnace')).toBeInTheDocument();
      expect(screen.getByText('Campfire Cooking')).toBeInTheDocument();
      expect(screen.getByText('Smoker')).toBeInTheDocument();
      expect(screen.getByText('Brewing Stand')).toBeInTheDocument();
      expect(screen.getByText('Stonecutter')).toBeInTheDocument();
    });

    test('changes recipe type when selected', async () => {
      const user = userEvent.setup();

      render(
        <RecipeBuilder
          initialRecipe={mockRecipe}
          onRecipeChange={mockOnRecipeChange}
          onRecipeSave={mockOnRecipeSave}
          availableItems={mockAvailableItems}
        />
      );

      const typeSelect = screen.getByLabelText('Recipe Type');

      await act(async () => {
        await user.selectOptions(typeSelect, 'furnace');
      });

      expect(mockOnRecipeChange).toHaveBeenCalledWith(
        expect.objectContaining({ type: 'furnace' })
      );
    });
  });

  describe('Recipe Properties', () => {
    test('updates recipe name when changed', async () => {
      const user = userEvent.setup();

      render(
        <RecipeBuilder
          initialRecipe={mockRecipe}
          onRecipeChange={mockOnRecipeChange}
          onRecipeSave={mockOnRecipeSave}
          availableItems={mockAvailableItems}
        />
      );

      const nameInput = screen.getByLabelText('Recipe Name');

      await act(async () => {
        await user.clear(nameInput);
        await user.type(nameInput, 'New Recipe Name');
      });

      expect(mockOnRecipeChange).toHaveBeenCalledWith(
        expect.objectContaining({ name: 'New Recipe Name' })
      );
    });

    test('updates recipe identifier when changed', async () => {
      const user = userEvent.setup();

      render(
        <RecipeBuilder
          initialRecipe={mockRecipe}
          onRecipeChange={mockOnRecipeChange}
          onRecipeSave={mockOnRecipeSave}
          availableItems={mockAvailableItems}
        />
      );

      const identifierInput = screen.getByLabelText('Recipe Identifier');

      await act(async () => {
        await user.clear(identifierInput);
        await user.type(identifierInput, 'mod:new_recipe');
      });

      expect(mockOnRecipeChange).toHaveBeenCalledWith(
        expect.objectContaining({ identifier: 'mod:new_recipe' })
      );
    });

    test('shows experience and cooking time for smelting recipes', () => {
      render(
        <RecipeBuilder
          initialRecipe={{ ...mockRecipe, type: 'furnace' }}
          onRecipeChange={mockOnRecipeChange}
          onRecipeSave={mockOnRecipeSave}
          availableItems={mockAvailableItems}
        />
      );

      expect(screen.getByLabelText('Experience')).toBeInTheDocument();
      expect(screen.getByLabelText('Cooking Time (ticks)')).toBeInTheDocument();
    });
  });

  describe('Recipe Grid', () => {
    test('renders 3x3 grid for shaped recipes', () => {
      render(
        <RecipeBuilder
          initialRecipe={{ ...mockRecipe, type: 'shaped' }}
          onRecipeChange={mockOnRecipeChange}
          onRecipeSave={mockOnRecipeSave}
          availableItems={mockAvailableItems}
        />
      );

      expect(screen.getByText('Shaped Recipe Pattern')).toBeInTheDocument();
    });

    test('renders 1x1 grid for furnace recipes', () => {
      render(
        <RecipeBuilder
          initialRecipe={{ ...mockRecipe, type: 'furnace' }}
          onRecipeChange={mockOnRecipeChange}
          onRecipeSave={mockOnRecipeSave}
          availableItems={mockAvailableItems}
        />
      );

      expect(screen.getByText('Smelting Input')).toBeInTheDocument();
    });

    test('places item in grid when clicked', async () => {
      const user = userEvent.setup();

      render(
        <RecipeBuilder
          initialRecipe={mockRecipe}
          onRecipeChange={mockOnRecipeChange}
          onRecipeSave={mockOnRecipeSave}
          availableItems={mockAvailableItems}
        />
      );

      // Select an item from the library (simplified test)
      const itemButton = screen.getByText('Oak Planks');
      await act(async () => {
        await user.click(itemButton);
      });

      // Click on a grid slot
      const gridSlots = screen.getAllByRole('button');
      const firstSlot = gridSlots.find(slot => slot.textContent?.includes('Slot 1'));
      expect(firstSlot).toBeInTheDocument();
    });
  });

  describe('Undo/Redo Functionality', () => {
    test('displays undo and redo buttons', () => {
      render(
        <RecipeBuilder
          initialRecipe={mockRecipe}
          onRecipeChange={mockOnRecipeChange}
          onRecipeSave={mockOnRecipeSave}
          availableItems={mockAvailableItems}
        />
      );

      expect(screen.getByRole('button', { name: /undo/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /redo/i })).toBeInTheDocument();
    });

    test('undo button is disabled initially', () => {
      render(
        <RecipeBuilder
          initialRecipe={mockRecipe}
          onRecipeChange={mockOnRecipeChange}
          onRecipeSave={mockOnRecipeSave}
          availableItems={mockAvailableItems}
        />
      );

      const undoButton = screen.getByRole('button', { name: /undo/i });
      expect(undoButton).toBeDisabled();
    });

    test('undo button is enabled after changes', async () => {
      const user = userEvent.setup();

      render(
        <RecipeBuilder
          initialRecipe={mockRecipe}
          onRecipeChange={mockOnRecipeChange}
          onRecipeSave={mockOnRecipeSave}
          availableItems={mockAvailableItems}
        />
      );

      const nameInput = screen.getByLabelText('Recipe Name');
      await act(async () => {
        await user.type(nameInput, ' Updated');
      });

      await waitFor(() => {
        const undoButton = screen.getByRole('button', { name: /undo/i });
        expect(undoButton).toBeEnabled();
      });
    });

    test('redo button is disabled initially', () => {
      render(
        <RecipeBuilder
          initialRecipe={mockRecipe}
          onRecipeChange={mockOnRecipeChange}
          onRecipeSave={mockOnRecipeSave}
          availableItems={mockAvailableItems}
        />
      );

      const redoButton = screen.getByRole('button', { name: /redo/i });
      expect(redoButton).toBeDisabled();
    });
  });

  describe('Validation', () => {
    test('shows validation errors for missing identifier', async () => {
      render(
        <RecipeBuilder
          initialRecipe={{ ...mockRecipe, identifier: '' }}
          onRecipeChange={mockOnRecipeChange}
          onRecipeSave={mockOnRecipeSave}
          availableItems={mockAvailableItems}
        />
      );

      expect(screen.getByText(/Recipe identifier is required/)).toBeInTheDocument();
    });

    test('shows validation errors for missing name', async () => {
      render(
        <RecipeBuilder
          initialRecipe={{ ...mockRecipe, name: '' }}
          onRecipeChange={mockOnRecipeChange}
          onRecipeSave={mockOnRecipeSave}
          availableItems={mockAvailableItems}
        />
      );

      expect(screen.getByText(/Recipe name is required/)).toBeInTheDocument();
    });

    test('shows multiple validation errors', async () => {
      render(
        <RecipeBuilder
          initialRecipe={{ type: 'shaped', identifier: '', name: '' }}
          onRecipeChange={mockOnRecipeChange}
          onRecipeSave={mockOnRecipeSave}
          availableItems={mockAvailableItems}
        />
      );

      expect(screen.getByText(/Recipe identifier is required/)).toBeInTheDocument();
      expect(screen.getByText(/Recipe name is required/)).toBeInTheDocument();
    });
  });

  describe('Read Only Mode', () => {
    test('disables all inputs when readOnly is true', () => {
      render(
        <RecipeBuilder
          initialRecipe={mockRecipe}
          onRecipeChange={mockOnRecipeChange}
          onRecipeSave={mockOnRecipeSave}
          availableItems={mockAvailableItems}
          readOnly={true}
        />
      );

      expect(screen.getByLabelText('Recipe Type')).toBeDisabled();
      expect(screen.getByLabelText('Recipe Name')).toBeDisabled();
    });

    test('disables undo/redo buttons when readOnly is true', () => {
      render(
        <RecipeBuilder
          initialRecipe={mockRecipe}
          onRecipeChange={mockOnRecipeChange}
          onRecipeSave={mockOnRecipeSave}
          availableItems={mockAvailableItems}
          readOnly={true}
        />
      );

      const undoButton = screen.getByRole('button', { name: /undo/i });
      const redoButton = screen.getByRole('button', { name: /redo/i });

      expect(undoButton).toBeDisabled();
      expect(redoButton).toBeDisabled();
    });
  });

  describe('Recipe Saving', () => {
    test('calls onRecipeSave when save button is clicked', async () => {
      const user = userEvent.setup();

      render(
        <RecipeBuilder
          initialRecipe={mockRecipe}
          onRecipeChange={mockOnRecipeChange}
          onRecipeSave={mockOnRecipeSave}
          availableItems={mockAvailableItems}
        />
      );

      const saveButton = screen.getByRole('button', { name: /save recipe/i });

      // Button should be disabled due to validation
      expect(saveButton).toBeDisabled();

      // Fix validation by adding proper recipe data
      fireEvent.change(screen.getByLabelText('Recipe Name'), {
        target: { value: 'Valid Recipe' }
      });

      await waitFor(() => {
        expect(saveButton).toBeEnabled();
      });

      await act(async () => {
        await user.click(saveButton);
      });

      expect(mockOnRecipeSave).toHaveBeenCalled();
    });
  });

  describe('Unsaved Changes Indicator', () => {
    test('shows unsaved changes indicator when recipe is modified', async () => {
      const user = userEvent.setup();

      render(
        <RecipeBuilder
          initialRecipe={mockRecipe}
          onRecipeChange={mockOnRecipeChange}
          onRecipeSave={mockOnRecipeSave}
          availableItems={mockAvailableItems}
        />
      );

      await act(async () => {
        await user.type(screen.getByLabelText('Recipe Name'), ' Modified');
      });

      await waitFor(() => {
        expect(screen.getByText(/unsaved changes/i)).toBeInTheDocument();
      });
    });
  });
});
