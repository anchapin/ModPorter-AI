import { Recipe, RecipeItem } from './RecipeBuilder';

export class RecipeValidation {
  validate(recipe: Recipe, availableItems: RecipeItem[]): string[] {
    const errors: string[] = [];

    // Basic validation
    if (!recipe.identifier) {
      errors.push('Recipe identifier is required');
    } else if (!this.isValidIdentifier(recipe.identifier)) {
      errors.push('Recipe identifier must be in format "namespace:name"');
    }

    if (!recipe.name) {
      errors.push('Recipe name is required');
    }

    if (!recipe.type) {
      errors.push('Recipe type is required');
    }

    // Type-specific validation
    switch (recipe.type) {
      case 'shaped':
        this.validateShapedRecipe(recipe, availableItems, errors);
        break;
      case 'shapeless':
        this.validateShapelessRecipe(recipe, availableItems, errors);
        break;
      case 'furnace':
      case 'blast_furnace':
      case 'campfire':
      case 'smoker':
        this.validateSmeltingRecipe(recipe, availableItems, errors);
        break;
      case 'brewing':
        this.validateBrewingRecipe(recipe, availableItems, errors);
        break;
      case 'stonecutter':
        this.validateStonecutterRecipe(recipe, availableItems, errors);
        break;
      default:
        errors.push(`Unknown recipe type: ${recipe.type}`);
    }

    // Result validation
    this.validateResult(recipe, availableItems, errors);

    return errors;
  }

  private isValidIdentifier(identifier: string): boolean {
    return /^[a-z0-9_]+:[a-z0-9_\-/]+$/.test(identifier);
  }

  private validateShapedRecipe(recipe: Recipe, availableItems: RecipeItem[], errors: string[]): void {
    if (!recipe.pattern || recipe.pattern.length === 0) {
      errors.push('Shaped recipe requires a pattern');
      return;
    }

    const usedSlots: RecipeItem[] = [];
    let hasEmptyRow = false;
    let emptyRowStart = -1;

    // Count used slots and validate pattern shape
    for (let y = 0; y < recipe.pattern.length; y++) {
      const row = recipe.pattern[y];
      let rowHasItems = false;

      for (let x = 0; x < row.length; x++) {
        const slot = row[x];
        if (slot.item) {
          usedSlots.push(slot.item);
          rowHasItems = true;

          // Validate item exists
          if (!this.itemExists(slot.item, availableItems)) {
            errors.push(`Item "${slot.item.name}" in slot (${x},${y}) is not available`);
          }
        }
      }

      if (!rowHasItems) {
        if (!hasEmptyRow) {
          hasEmptyRow = true;
          emptyRowStart = y;
        }
      } else if (hasEmptyRow) {
        errors.push(`Empty rows must be at the end (found empty row at ${emptyRowStart} with items below)`);
      }
    }

    if (usedSlots.length === 0) {
      errors.push('Shaped recipe must have at least one ingredient');
    }

    // Check if pattern is too large (max 3x3)
    if (recipe.pattern.length > 3) {
      errors.push('Shaped recipe pattern cannot exceed 3 rows');
    }

    for (const row of recipe.pattern) {
      if (row.length > 3) {
        errors.push('Shaped recipe pattern cannot exceed 3 columns');
      }
    }
  }

  private validateShapelessRecipe(recipe: Recipe, availableItems: RecipeItem[], errors: string[]): void {
    if (!recipe.pattern || recipe.pattern.length === 0) {
      errors.push('Shapeless recipe requires ingredients');
      return;
    }

    const usedSlots: RecipeItem[] = [];

    for (const row of recipe.pattern) {
      for (const slot of row) {
        if (slot.item) {
          usedSlots.push(slot.item);

          // Validate item exists
          if (!this.itemExists(slot.item, availableItems)) {
            errors.push(`Ingredient "${slot.item.name}" is not available`);
          }
        }
      }
    }

    if (usedSlots.length === 0) {
      errors.push('Shapeless recipe must have at least one ingredient');
    }

    if (usedSlots.length > 9) {
      errors.push('Shapeless recipe cannot have more than 9 ingredients');
    }
  }

  private validateSmeltingRecipe(recipe: Recipe, availableItems: RecipeItem[], errors: string[]): void {
    if (!recipe.pattern || recipe.pattern.length === 0 || !recipe.pattern[0] || recipe.pattern[0].length === 0) {
      errors.push('Smelting recipe requires an input item');
      return;
    }

    const inputSlot = recipe.pattern[0][0];
    if (!inputSlot.item) {
      errors.push('Smelting recipe requires an input item');
      return;
    }

    // Validate input item exists
    if (!this.itemExists(inputSlot.item, availableItems)) {
      errors.push(`Input item "${inputSlot.item.name}" is not available`);
    }

    // Validate experience
    if (recipe.experience !== undefined) {
      if (recipe.experience < 0) {
        errors.push('Experience cannot be negative');
      }
      if (recipe.experience > 1) {
        errors.push('Experience cannot exceed 1.0');
      }
    }

    // Validate cooking time
    if (recipe.cookingTime !== undefined) {
      if (recipe.cookingTime < 1) {
        errors.push('Cooking time must be at least 1 tick');
      }
      if (recipe.cookingTime > 32767) {
        errors.push('Cooking time cannot exceed 32767 ticks');
      }
    }
  }

  private validateBrewingRecipe(recipe: Recipe, availableItems: RecipeItem[], errors: string[]): void {
    if (!recipe.pattern || recipe.pattern.length < 3) {
      errors.push('Brewing recipe requires a 3x3 pattern');
      return;
    }

    // Brewing stand: top slot (0,0) = ingredient, bottom slots (1,0), (2,0) = bottles
    const topSlot = recipe.pattern[0][0];
    const bottomSlots = [recipe.pattern[1][0], recipe.pattern[2][0]];

    if (!topSlot.item) {
      errors.push('Brewing recipe requires an ingredient in the top slot');
      return;
    }

    const hasBottle = bottomSlots.some(slot => slot.item);
    if (!hasBottle) {
      errors.push('Brewing recipe requires at least one bottle in the bottom slots');
      return;
    }

    // Validate ingredient exists
    if (!this.itemExists(topSlot.item, availableItems)) {
      errors.push(`Brewing ingredient "${topSlot.item.name}" is not available`);
    }

    // Validate bottles
    bottomSlots.forEach((slot, index) => {
      if (slot.item && !this.itemExists(slot.item, availableItems)) {
        errors.push(`Bottom slot ${index + 1} item "${slot.item.name}" is not available`);
      }
    });
  }

  private validateStonecutterRecipe(recipe: Recipe, availableItems: RecipeItem[], errors: string[]): void {
    if (!recipe.pattern || recipe.pattern.length === 0 || !recipe.pattern[0] || recipe.pattern[0].length === 0) {
      errors.push('Stonecutter recipe requires an input item');
      return;
    }

    const inputSlot = recipe.pattern[0][0];
    if (!inputSlot.item) {
      errors.push('Stonecutter recipe requires an input item');
      return;
    }

    // Validate input item exists
    if (!this.itemExists(inputSlot.item, availableItems)) {
      errors.push(`Input item "${inputSlot.item.name}" is not available`);
    }
  }

  private validateResult(recipe: Recipe, availableItems: RecipeItem[], errors: string[]): void {
    if (!recipe.result) {
      errors.push('Recipe result is required');
      return;
    }

    if (!recipe.result.name) {
      errors.push('Recipe result name is required');
      return;
    }

    // Validate result count
    if (recipe.result.count !== undefined) {
      if (recipe.result.count < 1) {
        errors.push('Result count must be at least 1');
      }
      if (recipe.result.count > 64) {
        errors.push('Result count cannot exceed 64');
      }
    }

    // Check if result item is valid (optional, as some recipes create new items)
    if (recipe.result.id && !this.itemExists(recipe.result, availableItems)) {
      // This is just a warning, not an error
      console.warn(`Result item "${recipe.result.name}" is not in available items list`);
    }

    // Validate priority
    if (recipe.priority !== undefined) {
      if (recipe.priority < 0) {
        errors.push('Recipe priority cannot be negative');
      }
    }
  }

  private itemExists(item: RecipeItem, availableItems: RecipeItem[]): boolean {
    return availableItems.some(availableItem => 
      availableItem.id === item.id || 
      availableItem.name === item.name
    );
  }

  // Helper method to get recipe summary
  getRecipeSummary(recipe: Recipe): {
    type: string;
    ingredients: number;
    result: string;
    complexity: 'simple' | 'medium' | 'complex';
  } {
    const ingredientCount = recipe.pattern?.flat().filter(slot => slot.item).length || 0;
    
    let complexity: 'simple' | 'medium' | 'complex' = 'simple';
    if (ingredientCount > 3) {
      complexity = 'complex';
    } else if (ingredientCount > 1) {
      complexity = 'medium';
    }

    return {
      type: recipe.type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase()),
      ingredients: ingredientCount,
      result: recipe.result?.name || 'Unknown',
      complexity
    };
  }

  // Helper method to validate recipe conflicts
  checkRecipeConflicts(recipe: Recipe, existingRecipes: Recipe[]): string[] {
    const conflicts: string[] = [];

    for (const existing of existingRecipes) {
      if (existing.id === recipe.id) continue;

      // Check for same identifier
      if (existing.identifier === recipe.identifier) {
        conflicts.push(`Recipe with identifier "${recipe.identifier}" already exists`);
      }

      // Check for identical ingredients and result (same recipe)
      if (this.recipesAreIdentical(recipe, existing)) {
        conflicts.push(`Duplicate recipe detected: ${existing.name}`);
      }

      // Check for conflicts in priority
      if (existing.priority === recipe.priority && 
          this.hasSameIngredients(recipe, existing) &&
          existing.result.id === recipe.result.id) {
        conflicts.push(`Recipe priority conflict with: ${existing.name}`);
      }
    }

    return conflicts;
  }

  private recipesAreIdentical(recipe1: Recipe, recipe2: Recipe): boolean {
    if (recipe1.type !== recipe2.type) return false;
    if (recipe1.result.id !== recipe2.result.id) return false;

    const ingredients1 = recipe1.pattern?.flat().filter(slot => slot.item).map(slot => slot.item?.id).sort() || [];
    const ingredients2 = recipe2.pattern?.flat().filter(slot => slot.item).map(slot => slot.item?.id).sort() || [];

    return JSON.stringify(ingredients1) === JSON.stringify(ingredients2);
  }

  private hasSameIngredients(recipe1: Recipe, recipe2: Recipe): boolean {
    const ingredients1 = recipe1.pattern?.flat().filter(slot => slot.item).map(slot => slot.item?.id).sort() || [];
    const ingredients2 = recipe2.pattern?.flat().filter(slot => slot.item).map(slot => slot.item?.id).sort() || [];

    return JSON.stringify(ingredients1) === JSON.stringify(ingredients2);
  }
}
