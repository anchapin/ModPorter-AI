import React, { useEffect, useState, useCallback } from 'react'; // Added useCallback
import { useParams, useLocation } from 'react-router-dom';
import { EditorProvider, useEditorContext } from '../context/EditorContext';
import * as api from '../services/api'; // Added api import
import { AddonDataUpload, AddonBlockCreate, AddonAssetCreate, AddonRecipeCreate } from '../types/api'; // Added AddonDataUpload and create types
import { BlockList } from '../components/Editor/BlockList/BlockList';
import { PropertiesPanel } from '../components/Editor/PropertiesPanel/PropertiesPanel';
import { AssetManager } from '../components/Editor/AssetManager/AssetManager';
import { RecipeManager } from '../components/Editor/RecipeManager/RecipeManager';
import { PreviewWindow } from '../components/Editor/PreviewWindow/PreviewWindow'; // Added
import { BehaviorEditor } from '../components/BehaviorEditor'; // Added for behavior editing
import './EditorPage.css'; // EditorPage styles

const EditorPageContent: React.FC = () => {
  const { addonId, conversionId } = useParams<{ addonId?: string; conversionId?: string }>();
  const location = useLocation();
  // Added setAddonData from context
  const { addonData, isLoading, error, loadAddon, setAddonData } = useEditorContext();
  const [rightSidebarTab, setRightSidebarTab] = useState<'assets' | 'recipes' | 'preview'>('assets');
  
  // Determine if we're in behavior editor mode
  const isBehaviorEditorMode = location.pathname.includes('/behavior-editor/') || !!conversionId;
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  useEffect(() => {
    if (addonId && !isBehaviorEditorMode) {
      console.log(`EditorPage: useEffect detected addonId: ${addonId}, calling loadAddon.`);
      loadAddon(addonId);
    }
  }, [addonId, loadAddon, isBehaviorEditorMode]);

  const handleSaveChanges = useCallback(async () => {
    if (!addonId || !addonData) {
      setSaveError("No addon data to save.");
      return;
    }

    setIsSaving(true);
    setSaveError(null);

    // Transform AddonDetails to AddonDataUpload
    const blocksToUpload: AddonBlockCreate[] = addonData.blocks.map(b => ({
      identifier: b.identifier,
      properties: b.properties || {},
      behavior: b.behavior ? { data: b.behavior.data } : undefined, // Send undefined if null
    }));
    const assetsToUpload: AddonAssetCreate[] = addonData.assets.map(a => ({
      type: a.type,
      path: a.path,
      original_filename: a.original_filename || undefined,
    }));
    const recipesToUpload: AddonRecipeCreate[] = addonData.recipes.map(r => ({
      data: r.data,
    }));

    const dataToSave: AddonDataUpload = {
      name: addonData.name,
      description: addonData.description || undefined,
      user_id: addonData.user_id,
      blocks: blocksToUpload,
      assets: assetsToUpload,
      recipes: recipesToUpload,
    };

    try {
      const updatedAddon = await api.saveAddonDetails(addonId, dataToSave);
      if (setAddonData) { // Check if setAddonData is defined
        setAddonData(updatedAddon);
      }
      alert("Changes saved successfully!");
    } catch (err) {
      console.error("Error saving addon:", err);
      const errorMessage = err instanceof Error ? err.message : "An unknown error occurred.";
      setSaveError(`Failed to save: ${errorMessage}`);
      alert(`Save failed: ${errorMessage}`);
    } finally {
      setIsSaving(false);
    }
  }, [addonId, addonData, setAddonData]);

  if (isLoading && !isBehaviorEditorMode) {
    return <div className="editor-status">Loading addon data for {addonId}...</div>;
  }

  if (error && !isBehaviorEditorMode) {
    return <div className="editor-status editor-error">Error loading addon: {error}</div>;
  }
  
  // If we're in behavior editor mode, render the behavior editor directly
  if (isBehaviorEditorMode && conversionId) {
    return <BehaviorEditor conversionId={conversionId} className="full-screen-editor" />;
  }

  return (
    <div className="editor-layout">
      <header className="editor-header">
        Editor Navigation - Addon: {addonData ? addonData.name : 'Loading...'} (ID: {addonId})
      </header>
      <aside className="editor-sidebar-left">
        <BlockList />
      </aside>
      <main className="editor-main-content">
        <PropertiesPanel />
      </main>
      <aside className="editor-sidebar-right">
        <div className="sidebar-tabs">
          <button
            onClick={() => setRightSidebarTab('assets')}
            className={`sidebar-tab-button ${rightSidebarTab === 'assets' ? 'active' : ''}`}
          >
            Assets
          </button>
          <button
            onClick={() => setRightSidebarTab('recipes')}
            className={`sidebar-tab-button ${rightSidebarTab === 'recipes' ? 'active' : ''}`}
          >
            Recipes
          </button>
          <button
            onClick={() => setRightSidebarTab('preview')}
            className={`sidebar-tab-button ${rightSidebarTab === 'preview' ? 'active' : ''}`}
          >
            Preview
          </button>
        </div>
        <div className="sidebar-tab-content">
          {rightSidebarTab === 'assets' && <AssetManager />}
          {rightSidebarTab === 'recipes' && <RecipeManager />}
          {rightSidebarTab === 'preview' && <PreviewWindow />}
        </div>
      </aside>
      <footer className="editor-footer">
        <button onClick={handleSaveChanges} disabled={isSaving || isLoading} className="save-changes-button">
          {isSaving ? "Saving..." : "Save Changes"}
        </button>
        {saveError && <span className="save-error-message">Error: {saveError}</span>}
      </footer>
    </div>
  );
};

const EditorPage: React.FC = () => {
  return (
    <EditorProvider>
      <EditorPageContent />
    </EditorProvider>
  );
};

export default EditorPage;
