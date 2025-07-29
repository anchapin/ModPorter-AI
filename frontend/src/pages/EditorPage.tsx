import React, { useEffect, useState, useCallback } from 'react'; // Added useCallback
import { useParams } from 'react-router-dom';
import { EditorProvider, useEditorContext } from '../context/EditorContext';
import * as api from '../services/api'; // Added api import
import { AddonDataUpload, AddonBlockCreate, AddonAssetCreate, AddonRecipeCreate } from '../types/api'; // Added AddonDataUpload and create types
import { BlockList } from '../components/Editor/BlockList/BlockList';
import { PropertiesPanel } from '../components/Editor/PropertiesPanel/PropertiesPanel';
import { AssetManager } from '../components/Editor/AssetManager/AssetManager';
import { RecipeManager } from '../components/Editor/RecipeManager/RecipeManager';
import { PreviewWindow } from '../components/Editor/PreviewWindow/PreviewWindow'; // Added
import { ConversionAssetsManager } from '../components/ConversionAssets';
// import './EditorPage.css'; // We'll create this later if needed, or use App.css

const EditorPageContent: React.FC = () => {
  const { addonId } = useParams<{ addonId: string }>();
  // Added setAddonData from context
  const { addonData, isLoading, error, loadAddon, setAddonData } = useEditorContext();
  const [rightSidebarTab, setRightSidebarTab] = useState<'assets' | 'conversion-assets' | 'recipes' | 'preview'>('assets');
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  useEffect(() => {
    if (addonId) {
      console.log(`EditorPage: useEffect detected addonId: ${addonId}, calling loadAddon.`);
      loadAddon(addonId);
    }
  }, [addonId, loadAddon]);

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

  if (isLoading) {
    return <div className="editor-status">Loading addon data for {addonId}...</div>;
  }

  if (error) {
    return <div className="editor-status editor-error">Error loading addon: {error}</div>;
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
            Addon Assets
          </button>
          <button
            onClick={() => setRightSidebarTab('conversion-assets')}
            className={`sidebar-tab-button ${rightSidebarTab === 'conversion-assets' ? 'active' : ''}`}
          >
            Conversion Assets
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
          {rightSidebarTab === 'conversion-assets' && addonId && <ConversionAssetsManager conversionId={addonId} />}
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
