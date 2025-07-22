import React, { createContext, useState, useContext, ReactNode, useCallback } from 'react';
import { AddonDetails, AddonAsset } from '../types/api'; // Import AddonAsset
import * as api from '../services/api'; // Import our API service
import { setPropertyByPath } from '../utils/objectUtils'; // Import the utility

// 1. Define the Context State Interface
interface EditorState {
  addonData: AddonDetails | null;
  isLoading: boolean;
  error: string | null;
  loadAddon: (addonId: string) => Promise<void>;
  selectedBlockId: string | null;
  setSelectedBlockId: (blockId: string | null) => void;
  updateBlockProperty: (blockId: string, propertyPath: string, value: any) => void;
  addAsset: (assetData: AddonAsset) => void;
  updateAsset: (assetId: string, updatedAssetData: Partial<AddonAsset>) => void;
  deleteAsset: (assetId: string) => void;
  selectedRecipeId: string | null;
  setSelectedRecipeId: (recipeId: string | null) => void;
  setAddonData: (data: AddonDetails | null) => void; // Changed to AddonDetails | null
}

// 2. Create the React Context
// Providing a default stub for context, actual value comes from Provider
const EditorContext = createContext<EditorState | undefined>(undefined);

// 3. Implement the EditorProvider Component
interface EditorProviderProps {
  children: ReactNode;
}

export const EditorProvider: React.FC<EditorProviderProps> = ({ children }) => {
  const [addonData, setAddonData] = useState<AddonDetails | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedBlockId, setSelectedBlockIdState] = useState<string | null>(null);
  const [selectedRecipeId, setSelectedRecipeIdState] = useState<string | null>(null);

  const loadAddon = useCallback(async (addonId: string) => {
    setIsLoading(true);
    setError(null);
    try {
      console.log(`EditorContext: Calling api.getAddonDetails for addonId: ${addonId}`);
      const data = await api.getAddonDetails(addonId);
      setAddonData(data);
      console.log("EditorContext: Addon data loaded", data);
    } catch (err) {
      console.error("EditorContext: Error loading addon data", err);
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('An unknown error occurred while loading addon data.');
      }
      setAddonData(null); // Clear any stale data
    } finally {
      setIsLoading(false);
    }
  }, []);

  const updateBlockProperty = useCallback((blockId: string, propertyPath: string, value: any) => {
    setAddonData(prevAddonData => {
      if (!prevAddonData) return null;

      const blockIndex = prevAddonData.blocks.findIndex(block => block.id === blockId);
      if (blockIndex === -1) {
        console.warn(`updateBlockProperty: Block with id ${blockId} not found.`);
        return prevAddonData; // Block not found
      }

      // Create a new blocks array with the updated block
      const updatedBlocks = [...prevAddonData.blocks];
      const originalBlock = updatedBlocks[blockIndex];

      // Update the specific block using setPropertyByPath for immutability
      updatedBlocks[blockIndex] = setPropertyByPath(originalBlock, propertyPath, value);

      // Return new addonData object
      return {
        ...prevAddonData,
        blocks: updatedBlocks,
        updated_at: new Date().toISOString(), // Also update addon's updated_at timestamp
      };
    });
  }, []);

  const addAsset = useCallback((assetData: AddonAsset) => {
    setAddonData(prev => {
      if (!prev) return null;
      // Ensure no duplicate asset IDs, though backend should handle this ultimately
      if (prev.assets.find(a => a.id === assetData.id)) return prev;
      return {
        ...prev,
        assets: [...prev.assets, assetData],
        updated_at: new Date().toISOString(),
      };
    });
  }, []);

  const updateAsset = useCallback((assetId: string, updatedAssetData: Partial<AddonAsset>) => {
    setAddonData(prev => {
      if (!prev) return null;
      return {
        ...prev,
        assets: prev.assets.map(asset =>
          asset.id === assetId ? { ...asset, ...updatedAssetData, updated_at: new Date().toISOString() } : asset
        ),
        updated_at: new Date().toISOString(),
      };
    });
  }, []);

  const deleteAsset = useCallback((assetId: string) => {
    setAddonData(prev => {
      if (!prev) return null;
      return {
        ...prev,
        assets: prev.assets.filter(asset => asset.id !== assetId),
        updated_at: new Date().toISOString(),
      };
    });
  }, []);

  // const setAddonDataManual = (data: AddonDetails) => { // Example if manual setting is needed
  //   setAddonData(data);
  // };

  const contextValue: EditorState = {
    addonData,
    isLoading,
    error,
    loadAddon,
    selectedBlockId,
    setSelectedBlockId: setSelectedBlockIdState,
    updateBlockProperty,
    addAsset,
    updateAsset,
    deleteAsset,
    selectedRecipeId,
    setSelectedRecipeId: setSelectedRecipeIdState,
    setAddonData: setAddonData, // Expose the state setter
  };

  return (
    <EditorContext.Provider value={contextValue}>
      {children}
    </EditorContext.Provider>
  );
};

// 4. Custom Hook for using the EditorContext
// eslint-disable-next-line react-refresh/only-export-components
export const useEditorContext = (): EditorState => {
  const context = useContext(EditorContext);
  if (context === undefined) {
    throw new Error('useEditorContext must be used within an EditorProvider');
  }
  return context;
};
