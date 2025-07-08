import React from 'react';
import { useEditorContext } from '../../../context/EditorContext';
import * as api from '../../../services/api'; // For API calls
import { API_BASE_URL } from '../../../services/api'; // Import API_BASE_URL
import './AssetManager.css'; // Shared CSS for AssetManager components

export const AssetList: React.FC = () => {
  const { addonData, deleteAsset, isLoading } = useEditorContext();

  const handleDeleteAsset = async (addonId: string, assetId: string) => {
    if (!window.confirm(`Are you sure you want to delete asset ${assetId}?`)) {
      return;
    }
    try {
      await api.deleteAddonAssetAPI(addonId, assetId); // Mocked API call
      deleteAsset(assetId); // Update context state
      console.log(`Asset ${assetId} deleted.`);
    } catch (error) {
      console.error("Error deleting asset:", error);
      alert(`Failed to delete asset: ${error instanceof Error ? error.message : String(error)}`);
    }
  };

  const handleReplaceAsset = (assetId: string) => {
    // For now, just log. Later, this could open a file dialog.
    console.log(`Replace asset clicked for: ${assetId}. (Functionality not fully implemented)`);
    alert("Replace functionality: Trigger file input here.");
    // Example:
    // const input = document.createElement('input');
    // input.type = 'file';
    // input.onchange = async (e) => {
    //   const file = (e.target as HTMLInputElement).files?.[0];
    //   if (file && addonData?.id && assetId) {
    //     try {
    //       const updatedAsset = await api.replaceAddonAsset(addonData.id, assetId, file);
    //       updateAsset(assetId, updatedAsset); // updateAsset needs to be added to context
    //     } catch (err) { console.error(err); }
    //   }
    // };
    // input.click();
  };


  if (isLoading && !addonData) {
    return <div className="asset-list-status">Loading assets...</div>;
  }

  if (!addonData || !addonData.assets || addonData.assets.length === 0) {
    return <div className="asset-list-status">No assets found in this addon.</div>;
  }

  return (
    <div className="asset-list-container">
      <h4>Assets</h4>
      <ul className="asset-list">
        {addonData.assets.map((asset) => (
          <li key={asset.id} className="asset-item">
            <div className="asset-preview">
              {/* Basic preview: if path suggests image, try to render, else icon/text */}
              {asset.type.startsWith('texture') && (asset.path.endsWith('.png') || asset.path.endsWith('.jpg')) ? (
                // This path won't work directly. For actual preview, this needs to be a URL
                // served by the backend or a blob URL from local upload.
                // For now, it's a broken image or alt text.
                <img src={`${API_BASE_URL}/addons/${addonData.id}/assets/${asset.id}`} alt={asset.original_filename || 'asset'} style={{width: "40px", height: "40px", objectFit: "contain" }}/>
              ) : (
                <span className="asset-icon">📄</span> // Placeholder icon
              )}
            </div>
            <div className="asset-info">
              <span className="asset-name" title={asset.original_filename || asset.id}>
                {asset.original_filename || `Asset ID: ${asset.id.substring(0,8)}...`}
              </span>
              <span className="asset-type">{asset.type}</span>
              <span className="asset-path" title={asset.path}>{asset.path}</span>
            </div>
            <div className="asset-actions">
              <button onClick={() => handleReplaceAsset(asset.id)} className="asset-action-btn">
                Replace
              </button>
              <button onClick={() => handleDeleteAsset(addonData.id, asset.id)} className="asset-action-btn delete">
                Delete
              </button>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
};
