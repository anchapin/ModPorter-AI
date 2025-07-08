import React from 'react';
import { useEditorContext } from '../../../context/EditorContext';
import './RecipeManager.css'; // Shared CSS

export const RecipeList: React.FC = () => {
  const { addonData, selectedRecipeId, setSelectedRecipeId, isLoading } = useEditorContext();

  if (isLoading && !addonData) {
    return <div className="recipe-list-status">Loading recipes...</div>;
  }

  if (!addonData || !addonData.recipes || addonData.recipes.length === 0) {
    return <div className="recipe-list-status">No recipes found in this addon.</div>;
  }

  const getRecipeDisplayName = (recipeData: any): string => {
    // Try to find common identifier patterns in recipe JSON
    if (typeof recipeData === 'object' && recipeData !== null) {
      const description = recipeData['minecraft:recipe_shaped']?.description?.identifier ||
                          recipeData['minecraft:recipe_furnace']?.description?.identifier ||
                          recipeData['minecraft:recipe_brewing_container']?.description?.identifier ||
                          recipeData['minecraft:recipe_brewing_mix']?.description?.identifier ||
                          recipeData['minecraft:recipe_shapeless']?.description?.identifier;
      if (description) return description.split(':').pop() || description;

      const resultItem = recipeData['minecraft:recipe_shaped']?.result?.item ||
                         recipeData['minecraft:recipe_furnace']?.result || // string or object
                         recipeData['minecraft:recipe_brewing_container']?.output ||
                         recipeData['minecraft:recipe_brewing_mix']?.output ||
                         recipeData['minecraft:recipe_shapeless']?.result?.item;
      if (typeof resultItem === 'string') return resultItem.split(':').pop() || resultItem;
      if (typeof resultItem === 'object' && resultItem?.item) return String(resultItem.item).split(':').pop() || String(resultItem.item);
    }
    return "Unnamed Recipe";
  };


  return (
    <div className="recipe-list-container">
      <h4>Recipes</h4>
      <ul className="recipe-list">
        {addonData.recipes.map((recipe) => (
          <li
            key={recipe.id}
            className={`recipe-list-item ${selectedRecipeId === recipe.id ? 'selected' : ''}`}
            onClick={() => setSelectedRecipeId(recipe.id)}
            role="button"
            tabIndex={0}
            onKeyPress={(e) => { if (e.key === 'Enter' || e.key === ' ') setSelectedRecipeId(recipe.id);}}
          >
            {getRecipeDisplayName(recipe.data)} (ID: {recipe.id.substring(0,5)}...)
          </li>
        ))}
      </ul>
    </div>
  );
};
