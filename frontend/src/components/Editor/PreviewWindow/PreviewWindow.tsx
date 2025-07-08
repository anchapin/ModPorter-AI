import React from 'react';
import { useEditorContext } from '../../../context/EditorContext';
import { AddonAsset } from '../../../types/api'; // For typing
import { API_BASE_URL } from '../../../services/api'; // Import API_BASE_URL
import './PreviewWindow.css';

export const PreviewWindow: React.FC = () => {
  const { addonData, selectedBlockId } = useEditorContext();

  if (!selectedBlockId) {
    return <div className="preview-window-empty">Select a block to preview.</div>;
  }

  if (!addonData || !addonData.blocks) {
    return <div className="preview-window-empty">Addon data not available.</div>;
  }

  const selectedBlock = addonData.blocks.find(block => block.id === selectedBlockId);

  if (!selectedBlock) {
    return <div className="preview-window-empty">Selected block not found.</div>;
  }

  // Attempt to find texture asset
  // Convention: block.properties.rp_texture_name stores the key used in terrain_texture.json
  // which often corresponds to the asset's original_filename without extension.
  const textureKey = selectedBlock.properties?.rp_texture_name as string ||
                     (selectedBlock.identifier ? selectedBlock.identifier.split(':')[1] : null);

  let textureAsset: AddonAsset | undefined = undefined;
  if (textureKey && addonData.assets) {
    textureAsset = addonData.assets.find(asset => {
      if (!asset.original_filename) return false;
      const assetNameWithoutExt = asset.original_filename.substring(0, asset.original_filename.lastIndexOf('.')) || asset.original_filename;
      return assetNameWithoutExt === textureKey && asset.type.startsWith('texture');
    });
  }

  // For actual image src:
  // If asset was just uploaded, a blob URL might be available.
  // If asset is from backend, its `path` is backend-relative.
  // We'd need a proper API endpoint like `/api/v1/addons/{addonId}/assets/{assetId}/file`
  // For now, we cannot reliably render images from `asset.path`.

  return (
    <div className="preview-window-container">
      <h4>Preview: {selectedBlock.identifier}</h4>
      <div className="preview-content">
        <p><strong>Identifier:</strong> {selectedBlock.identifier}</p>
        <div className="texture-preview-area">
          <strong>Texture:</strong>
          {textureAsset ? (
            <div className="texture-info">
              <p>Name: {textureAsset.original_filename}</p>
              <p>Type: {textureAsset.type}</p>
              <p>Path: {textureAsset.path}</p>
              <div className="texture-image-placeholder">
                {addonData && textureAsset.type.startsWith('texture') && (textureAsset.original_filename?.match(/\.(jpeg|jpg|gif|png)$/) != null) ? (
                  <img
                    src={`${API_BASE_URL}/addons/${addonData.id}/assets/${textureAsset.id}`}
                    alt={textureAsset.original_filename || 'texture preview'}
                    style={{ maxWidth: '100%', maxHeight: '150px', objectFit: 'contain' }}
                  />
                ) : (
                  <span>🖼️ (Preview for {textureAsset.original_filename})</span>
                )}
              </div>
            </div>
          ) : (
            <p>Texture not available or reference not found (key: {textureKey || 'N/A'}).</p>
          )}
        </div>
        {/* Future: Could display a simple 3D representation or other properties */}
      </div>
    </div>
  );
};
