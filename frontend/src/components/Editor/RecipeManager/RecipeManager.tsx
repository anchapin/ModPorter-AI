import React from 'react';
import { RecipeList } from './RecipeList';
import { RecipeEditorPanel } from './RecipeEditorPanel';
import './RecipeManager.css'; // Shared CSS

export const RecipeManager: React.FC = () => {
  return (
    <div className="recipe-manager-container">
      <RecipeList />
      <RecipeEditorPanel />
    </div>
  );
};
