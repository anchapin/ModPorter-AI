import React, { useState, useEffect, useCallback } from 'react';
import { ConversionAsset } from '../../types/api';
import * as api from '../../services/api';
import './ConversionAssets.css';

interface ConversionAssetsListProps {
  conversionId: string;
  onAssetSelect?: (asset: ConversionAsset) => void;
  onRefresh?: () => void;
}

export const ConversionAssetsList: React.FC<ConversionAssetsListProps> = ({
  conversionId,
  onAssetSelect,
  onRefresh
}) => {
  const [assets, setAssets] = useState<ConversionAsset[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<{
    assetType: string;
    status: string;
  }>({
    assetType: '',
    status: ''
  });

  const loadAssets = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const assetsList = await api.listConversionAssets(
        conversionId,
        filter.assetType || undefined,
        filter.status || undefined
      );
      setAssets(assetsList);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to load assets';
      setError(errorMessage);
      console.error('Error loading assets:', err);
    } finally {
      setLoading(false);
    }
  }, [conversionId, filter.assetType, filter.status]);

  useEffect(() => {
    if (conversionId) {
      loadAssets();
    }
  }, [conversionId, loadAssets]);

  const handleDeleteAsset = async (assetId: string) => {
    if (!window.confirm('Are you sure you want to delete this asset?')) {
      return;
    }

    try {
      await api.deleteConversionAsset(assetId);
      await loadAssets(); // Refresh the list
      if (onRefresh) onRefresh();
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to delete asset';
      alert(`Error deleting asset: ${errorMessage}`);
    }
  };

  const handleConvertAsset = async (assetId: string) => {
    try {
      await api.convertConversionAsset(assetId);
      await loadAssets(); // Refresh to show updated status
      if (onRefresh) onRefresh();
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to convert asset';
      alert(`Error converting asset: ${errorMessage}`);
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

  const getStatusClass = (status: string) => {
    return `asset-status asset-status-${status}`;
  };

  const getAssetTypeIcon = (assetType: string) => {
    if (assetType.includes('texture')) return '🖼️';
    if (assetType.includes('sound')) return '🔊';
    if (assetType.includes('model')) return '🎲';
    if (assetType.includes('script')) return '📜';
    return '📄';
  };

  if (loading) {
    return (
      <div className="assets-list-container">
        <div className="assets-loading">Loading assets...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="assets-list-container">
        <div className="assets-error">
          <p>Error loading assets: {error}</p>
          <button onClick={loadAssets} className="retry-button">
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="assets-list-container">
      <div className="assets-list-header">
        <h3>Conversion Assets</h3>
        <div className="assets-filters">
          <select
            value={filter.assetType}
            onChange={(e) => setFilter(prev => ({ ...prev, assetType: e.target.value }))}
            className="filter-select"
          >
            <option value="">All Types</option>
            <option value="texture">Textures</option>
            <option value="sound">Sounds</option>
            <option value="model">Models</option>
            <option value="script">Scripts</option>
          </select>
          <select
            value={filter.status}
            onChange={(e) => setFilter(prev => ({ ...prev, status: e.target.value }))}
            className="filter-select"
          >
            <option value="">All Status</option>
            <option value="pending">Pending</option>
            <option value="processing">Processing</option>
            <option value="converted">Converted</option>
            <option value="failed">Failed</option>
          </select>
          <button onClick={loadAssets} className="refresh-button">
            🔄 Refresh
          </button>
        </div>
      </div>

      {assets.length === 0 ? (
        <div className="assets-empty">
          <p>No assets found for this conversion.</p>
          <p>Upload assets to begin the conversion process.</p>
        </div>
      ) : (
        <div className="assets-grid">
          {assets.map((asset) => (
            <div
              key={asset.id}
              className="asset-card"
              onClick={() => onAssetSelect?.(asset)}
            >
              <div className="asset-card-header">
                <div className="asset-type-icon">
                  {getAssetTypeIcon(asset.asset_type)}
                </div>
                <div className={getStatusClass(asset.status)}>
                  {getStatusIcon(asset.status)}
                  <span className="status-text">{asset.status}</span>
                </div>
              </div>

              <div className="asset-card-content">
                <h4 className="asset-filename" title={asset.original_filename}>
                  {asset.original_filename}
                </h4>
                <p className="asset-type">{asset.asset_type}</p>
                {asset.file_size && (
                  <p className="asset-size">
                    {(asset.file_size / 1024).toFixed(1)} KB
                  </p>
                )}
                {asset.error_message && (
                  <p className="asset-error" title={asset.error_message}>
                    Error: {asset.error_message.substring(0, 50)}...
                  </p>
                )}
              </div>

              <div className="asset-card-actions">
                {asset.status === 'pending' && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleConvertAsset(asset.id);
                    }}
                    className="action-button convert-button"
                  >
                    Convert
                  </button>
                )}
                {asset.status === 'failed' && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleConvertAsset(asset.id);
                    }}
                    className="action-button retry-button"
                  >
                    Retry
                  </button>
                )}
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDeleteAsset(asset.id);
                  }}
                  className="action-button delete-button"
                >
                  Delete
                </button>
              </div>

              <div className="asset-card-footer">
                <span className="asset-date">
                  {new Date(asset.created_at).toLocaleDateString()}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};