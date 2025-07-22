import React from 'react';
import { useEditorContext } from '../../../context/EditorContext';
import './RecipeManager.css'; // Shared CSS

export const RecipeEditorPanel: React.FC = () => {
  const { addonData, selectedRecipeId } = useEditorContext();

  if (!selectedRecipeId) {
    return <div className="recipe-editor-empty">Select a recipe to view its details.</div>;
  }

  if (!addonData || !addonData.recipes) {
    return <div className="recipe-editor-empty">Addon data not available.</div>;
  }

  const selectedRecipe = addonData.recipes.find(recipe => recipe.id === selectedRecipeId);

  if (!selectedRecipe) {
    return <div className="recipe-editor-empty">Selected recipe not found.</div>;
  }

  return (
    <div className="recipe-editor-panel-container">
      <h4>Recipe Details: {selectedRecipe.id.substring(0,8)}...</h4>
      <div className="recipe-json-display">
        <pre>{JSON.stringify(selectedRecipe.data, null, 2)}</pre>
      </div>
      {/* TODO: Add editable fields for recipe properties in a future task */}
    </div>
  );
};
