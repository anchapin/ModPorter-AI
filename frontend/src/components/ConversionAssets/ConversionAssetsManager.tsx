import React, { useState, useCallback } from 'react';
import { ConversionAsset } from '../../types/api';
import { ConversionAssetsList } from './ConversionAssetsList';
import { ConversionAssetsUpload } from './ConversionAssetsUpload';
import { ConversionAssetDetails } from './ConversionAssetDetails';
import * as api from '../../services/api';
import './ConversionAssets.css';

interface ConversionAssetsManagerProps {
  conversionId: string;
  className?: string;
}

export const ConversionAssetsManager: React.FC<ConversionAssetsManagerProps> = ({
  conversionId,
  className = ''
}) => {
  const [selectedAsset, setSelectedAsset] = useState<ConversionAsset | null>(null);
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [isConverting, setIsConverting] = useState(false);

  const handleAssetSelect = useCallback((asset: ConversionAsset) => {
    setSelectedAsset(asset);
  }, []);

  const handleAssetUpdated = useCallback((updatedAsset: ConversionAsset) => {
    setSelectedAsset(updatedAsset);
    setRefreshTrigger(prev => prev + 1);
  }, []);

  const handleAssetUploaded = useCallback((newAsset: ConversionAsset) => {
    setRefreshTrigger(prev => prev + 1);
    console.log('Asset uploaded:', newAsset);
  }, []);

  const handleRefresh = useCallback(() => {
    setRefreshTrigger(prev => prev + 1);
  }, []);

  const handleCloseDetails = useCallback(() => {
    setSelectedAsset(null);
  }, []);

  const handleConvertAllAssets = async () => {
    try {
      setIsConverting(true);
      const result = await api.convertAllConversionAssets(conversionId);
      
      // Show result to user
      const message = `Conversion batch completed:\n` +
        `Total assets: ${result.total_assets}\n` +
        `Converted: ${result.converted_count}\n` +
        `Failed: ${result.failed_count}`;
      
      alert(message);
      handleRefresh();
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to convert assets';
      alert(`Error converting assets: ${errorMessage}`);
    } finally {
      setIsConverting(false);
    }
  };

  return (
    <div className={`conversion-assets-manager ${className}`}>
      <div className="assets-manager-header">
        <div className="assets-manager-title">
          <h2>Asset Management</h2>
          <p>Upload and manage assets for conversion</p>
        </div>
        <div className="assets-manager-actions">
          <button
            onClick={handleConvertAllAssets}
            disabled={isConverting}
            className="convert-all-button"
          >
            {isConverting ? (
              <>
                <span className="loading-spinner">⏳</span>
                Converting All...
              </>
            ) : (
              '🔄 Convert All Assets'
            )}
          </button>
        </div>
      </div>

      <div className="assets-manager-content">
        <div className="assets-upload-section">
          <ConversionAssetsUpload
            conversionId={conversionId}
            onAssetUploaded={handleAssetUploaded}
          />
        </div>

        <div className="assets-list-section">
          <ConversionAssetsList
            conversionId={conversionId}
            onAssetSelect={handleAssetSelect}
            onRefresh={handleRefresh}
            key={refreshTrigger} // Force re-render when refreshTrigger changes
          />
        </div>
      </div>

      {selectedAsset && (
        <ConversionAssetDetails
          asset={selectedAsset}
          onAssetUpdated={handleAssetUpdated}
          onClose={handleCloseDetails}
        />
      )}
    </div>
  );
};