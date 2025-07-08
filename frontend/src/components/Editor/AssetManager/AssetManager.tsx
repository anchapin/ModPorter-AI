import React from 'react';
import { AssetList } from './AssetList';
import { AssetUpload } from './AssetUpload';
import './AssetManager.css'; // Shared CSS

export const AssetManager: React.FC = () => {
  return (
    <div className="asset-manager-container">
      {/* <h3>Asset Manager</h3> */} {/* Title can be part of EditorPage's sidebar section title */}
      <AssetUpload />
      <AssetList />
    </div>
  );
};
