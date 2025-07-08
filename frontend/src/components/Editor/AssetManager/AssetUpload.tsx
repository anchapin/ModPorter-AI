import React, { useState, useCallback } from 'react';
import { useEditorContext } from '../../../context/EditorContext';
import * as api from '../../../services/api'; // For mocked API calls
// Styles are in AssetManager.css (shared)

export const AssetUpload: React.FC = () => {
  const { addonData, addAsset } = useEditorContext();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [assetType, setAssetType] = useState<string>('texture_block'); // Default type
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files && event.target.files[0]) {
      setSelectedFile(event.target.files[0]);
      setUploadError(null); // Clear previous error on new file selection
    } else {
      setSelectedFile(null);
    }
  };

  const handleAssetTypeChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
    setAssetType(event.target.value);
  };

  const handleUpload = useCallback(async () => {
    if (!selectedFile || !addonData?.id) {
      setUploadError("Please select a file and ensure an addon is loaded.");
      return;
    }

    setIsUploading(true);
    setUploadError(null);

    try {
      // Call the (mocked) API function
      const newAsset = await api.uploadAddonAsset(addonData.id, selectedFile, assetType);
      addAsset(newAsset); // Update context state
      console.log("Asset uploaded and added to context:", newAsset);
      setSelectedFile(null); // Clear file input after successful upload
      // Optionally reset assetType or clear form fully
      // setAssetType('texture_block');
      const fileInput = document.getElementById('asset-file-input') as HTMLInputElement;
      if (fileInput) fileInput.value = '';


    } catch (error) {
      console.error("Error uploading asset:", error);
      const errorMessage = error instanceof Error ? error.message : String(error);
      setUploadError(`Upload failed: ${errorMessage}`);
    } finally {
      setIsUploading(false);
    }
  }, [selectedFile, assetType, addonData, addAsset]);

  return (
    <div className="asset-upload-container">
      <h4>Upload New Asset</h4>
      <div className="upload-form-fields">
        <div>
          <label htmlFor="asset-file-input">Asset File:</label>
          <input
            id="asset-file-input"
            type="file"
            onChange={handleFileChange}
            disabled={isUploading}
          />
        </div>
        <div>
          <label htmlFor="asset-type-select">Asset Type:</label>
          <select
            id="asset-type-select"
            value={assetType}
            onChange={handleAssetTypeChange}
            disabled={isUploading}
          >
            <option value="texture_block">Texture (Block)</option>
            <option value="texture_item">Texture (Item)</option>
            <option value="texture_entity">Texture (Entity)</option>
            <option value="texture_ui">Texture (UI)</option>
            <option value="sound_effect">Sound Effect</option>
            <option value="sound_music">Music</option>
            <option value="model_entity">Model (Entity)</option>
            <option value="model_block">Model (Block/Custom)</option>
            <option value="script">Script</option>
            <option value="other">Other</option>
          </select>
        </div>
        <button onClick={handleUpload} disabled={!selectedFile || isUploading}>
          {isUploading ? 'Uploading...' : 'Upload Asset'}
        </button>
        {uploadError && <p className="upload-error-message">{uploadError}</p>}
      </div>
    </div>
  );
};
