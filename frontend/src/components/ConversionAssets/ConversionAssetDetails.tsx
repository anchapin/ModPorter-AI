import React, { useState } from 'react';
import { ConversionAsset } from '../../types/api';
import * as api from '../../services/api';
import './ConversionAssets.css';

interface ConversionAssetDetailsProps {
  asset: ConversionAsset;
  onAssetUpdated?: (asset: ConversionAsset) => void;
  onClose?: () => void;
}

export const ConversionAssetDetails: React.FC<ConversionAssetDetailsProps> = ({
  asset,
  onAssetUpdated,
  onClose
}) => {
  const [editingMetadata, setEditingMetadata] = useState(false);
  const [metadataJson, setMetadataJson] = useState(
    JSON.stringify(asset.asset_metadata || {}, null, 2)
  );
  const [isUpdating, setIsUpdating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleConvertAsset = async () => {
    try {
      setIsUpdating(true);
      setError(null);
      const updatedAsset = await api.convertConversionAsset(asset.id);
      if (onAssetUpdated) {
        onAssetUpdated(updatedAsset);
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to convert asset';
      setError(errorMessage);
    } finally {
      setIsUpdating(false);
    }
  };

  const handleUpdateMetadata = async () => {
    try {
      setIsUpdating(true);
      setError(null);
      
      const newMetadata = JSON.parse(metadataJson);
      const updatedAsset = await api.updateConversionAssetMetadata(asset.id, newMetadata);
      
      if (onAssetUpdated) {
        onAssetUpdated(updatedAsset);
      }
      setEditingMetadata(false);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to update metadata';
      setError(errorMessage);
    } finally {
      setIsUpdating(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pending': return '#f59e0b';
      case 'processing': return '#3b82f6';
      case 'converted': return '#10b981';
      case 'failed': return '#ef4444';
      default: return '#6b7280';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'pending': return '⏳';
      case 'processing': return '🔄';
      case 'converted': return '✅';
      case 'failed': return '❌';
      default: return '❓';
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  return (
    <div className="asset-details-overlay">
      <div className="asset-details-modal">
        <div className="asset-details-header">
          <h2>Asset Details</h2>
          <button onClick={onClose} className="close-button">
            ✕
          </button>
        </div>

        <div className="asset-details-content">
          <div className="asset-info-section">
            <div className="asset-status-badge" style={{ backgroundColor: getStatusColor(asset.status) }}>
              {getStatusIcon(asset.status)} {asset.status.toUpperCase()}
            </div>

            <h3 className="asset-filename">{asset.original_filename}</h3>
            <p className="asset-id">ID: {asset.id}</p>
          </div>

          <div className="asset-properties">
            <div className="property-row">
              <span className="property-label">Type:</span>
              <span className="property-value">{asset.asset_type}</span>
            </div>

            <div className="property-row">
              <span className="property-label">File Size:</span>
              <span className="property-value">
                {asset.file_size ? formatFileSize(asset.file_size) : 'Unknown'}
              </span>
            </div>

            <div className="property-row">
              <span className="property-label">MIME Type:</span>
              <span className="property-value">{asset.mime_type || 'Unknown'}</span>
            </div>

            <div className="property-row">
              <span className="property-label">Original Path:</span>
              <span className="property-value" title={asset.original_path}>
                {asset.original_path}
              </span>
            </div>

            {asset.converted_path && (
              <div className="property-row">
                <span className="property-label">Converted Path:</span>
                <span className="property-value" title={asset.converted_path}>
                  {asset.converted_path}
                </span>
              </div>
            )}

            <div className="property-row">
              <span className="property-label">Created:</span>
              <span className="property-value">{formatDate(asset.created_at)}</span>
            </div>

            <div className="property-row">
              <span className="property-label">Updated:</span>
              <span className="property-value">{formatDate(asset.updated_at)}</span>
            </div>
          </div>

          {asset.error_message && (
            <div className="error-section">
              <h4>Error Message</h4>
              <div className="error-message">
                {asset.error_message}
              </div>
            </div>
          )}

          <div className="metadata-section">
            <div className="metadata-header">
              <h4>Metadata</h4>
              <button
                onClick={() => setEditingMetadata(!editingMetadata)}
                className="edit-metadata-button"
              >
                {editingMetadata ? 'Cancel' : 'Edit'}
              </button>
            </div>

            {editingMetadata ? (
              <div className="metadata-editor">
                <textarea
                  value={metadataJson}
                  onChange={(e) => setMetadataJson(e.target.value)}
                  className="metadata-textarea"
                  rows={10}
                  placeholder="Enter JSON metadata..."
                />
                <div className="metadata-actions">
                  <button
                    onClick={handleUpdateMetadata}
                    disabled={isUpdating}
                    className="save-metadata-button"
                  >
                    {isUpdating ? 'Saving...' : 'Save Metadata'}
                  </button>
                </div>
              </div>
            ) : (
              <div className="metadata-display">
                <pre className="metadata-json">
                  {JSON.stringify(asset.asset_metadata || {}, null, 2)}
                </pre>
              </div>
            )}
          </div>

          {error && (
            <div className="error-section">
              <p className="error-text">{error}</p>
            </div>
          )}
        </div>

        <div className="asset-details-actions">
          {(asset.status === 'pending' || asset.status === 'failed') && (
            <button
              onClick={handleConvertAsset}
              disabled={isUpdating}
              className="convert-asset-button"
            >
              {isUpdating ? 'Converting...' : 'Convert Asset'}
            </button>
          )}
          
          <button
            onClick={onClose}
            className="close-details-button"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};