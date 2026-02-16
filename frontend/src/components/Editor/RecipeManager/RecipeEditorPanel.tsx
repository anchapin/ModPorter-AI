import React, { useState, useEffect } from 'react';
import { useEditorContext } from '../../../context/EditorContext';
import './RecipeManager.css'; // Shared CSS

export const RecipeEditorPanel: React.FC = () => {
  const { addonData, selectedRecipeId, updateRecipe } = useEditorContext();
  
  // Local state for editable fields
  const [description, setDescription] = useState<string>('');
  const [tags, setTags] = useState<string>('');
  const [group, setGroup] = useState<string>('');
  const [showJsonPreview, setShowJsonPreview] = useState<boolean>(true);

  // Find selected recipe - safe to do here as it doesn't affect hooks
  const selectedRecipe = addonData?.recipes?.find(recipe => recipe.id === selectedRecipeId);

  // Initialize form fields from recipe data - MUST be before any returns
  useEffect(() => {
    if (selectedRecipe?.data) {
      setDescription(selectedRecipe.data.description || '');
      setTags(selectedRecipe.data.tags?.join(', ') || '');
      setGroup(selectedRecipe.data.group || '');
    }
  }, [selectedRecipe]);

  // Use conditional rendering instead of early returns to satisfy hooks rules
  if (!selectedRecipeId) {
    return <div className="recipe-editor-empty">Select a recipe to view its details.</div>;
  }

  if (!selectedRecipe) {
    return <div className="recipe-editor-empty">Selected recipe not found.</div>;
  }

  const handleDescriptionChange = (value: string) => {
    setDescription(value);
    if (selectedRecipe) {
      const updatedData = { ...selectedRecipe.data, description: value };
      updateRecipe(selectedRecipe.id, updatedData);
    }
  };

  const handleTagsChange = (value: string) => {
    setTags(value);
    if (selectedRecipe) {
      const tagsArray = value.split(',').map(t => t.trim()).filter(t => t);
      const updatedData = { ...selectedRecipe.data, tags: tagsArray };
      updateRecipe(selectedRecipe.id, updatedData);
    }
  };

  const handleGroupChange = (value: string) => {
    setGroup(value);
    if (selectedRecipe) {
      const updatedData = { ...selectedRecipe.data, group: value };
      updateRecipe(selectedRecipe.id, updatedData);
    }
  };

  return (
    <div className="recipe-editor-panel-container">
      <h4>Recipe Details: {selectedRecipe.id.substring(0,8)}...</h4>
      
      <div className="recipe-editor-form">
        <div className="recipe-field">
          <label htmlFor="recipe-description">Description:</label>
          <input
            id="recipe-description"
            type="text"
            value={description}
            onChange={(e) => handleDescriptionChange(e.target.value)}
            placeholder="Enter recipe description"
          />
        </div>
        
        <div className="recipe-field">
          <label htmlFor="recipe-tags">Tags (comma-separated):</label>
          <input
            id="recipe-tags"
            type="text"
            value={tags}
            onChange={(e) => handleTagsChange(e.target.value)}
            placeholder="e.g., crafting_table, furnace"
          />
        </div>
        
        <div className="recipe-field">
          <label htmlFor="recipe-group">Group:</label>
          <input
            id="recipe-group"
            type="text"
            value={group}
            onChange={(e) => handleGroupChange(e.target.value)}
            placeholder="Recipe group identifier"
          />
        </div>
        
        <div className="recipe-field">
          <label>
            <input
              type="checkbox"
              checked={showJsonPreview}
              onChange={(e) => setShowJsonPreview(e.target.checked)}
            />
            Show JSON Preview
          </label>
        </div>
      </div>

      {showJsonPreview && (
        <div className="recipe-json-display">
          <h5>Raw Recipe Data (JSON):</h5>
          <pre>{JSON.stringify(selectedRecipe.data, null, 2)}</pre>
        </div>
      )}
    </div>
  );
};
