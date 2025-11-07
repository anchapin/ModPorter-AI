import React, { useState, useCallback } from 'react';
import { ConversionAsset } from '../../types/api';
import * as api from '../../services/api';
import './ConversionAssets.css';

interface ConversionAssetsUploadProps {
  conversionId: string;
  onAssetUploaded?: (asset: ConversionAsset) => void;
}

export const ConversionAssetsUpload: React.FC<ConversionAssetsUploadProps> = ({
  conversionId,
  onAssetUploaded
}) => {
  const [selectedFiles, setSelectedFiles] = useState<FileList | null>(null);
  const [assetType, setAssetType] = useState<string>('texture');
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [dragActive, setDragActive] = useState<boolean>(false);

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setSelectedFiles(event.target.files);
    setUploadError(null);
  };

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setSelectedFiles(e.dataTransfer.files);
      setUploadError(null);
    }
  }, []);

  const handleUpload = async () => {
    if (!selectedFiles || selectedFiles.length === 0) {
      setUploadError("Please select at least one file to upload.");
      return;
    }

    setIsUploading(true);
    setUploadError(null);

    try {
      const uploadedAssets: ConversionAsset[] = [];
      
      // Upload files one by one
      for (let i = 0; i < selectedFiles.length; i++) {
        const file = selectedFiles[i];
        const uploadedAsset = await api.uploadConversionAsset(conversionId, file, assetType);
        uploadedAssets.push(uploadedAsset);
        
        if (onAssetUploaded) {
          onAssetUploaded(uploadedAsset);
        }
      }

      // Clear form after successful upload
      setSelectedFiles(null);
      const fileInput = document.getElementById('conversion-asset-file-input') as HTMLInputElement;
      if (fileInput) fileInput.value = '';

      console.log(`Successfully uploaded ${uploadedAssets.length} assets`);

    } catch (error) {
      console.error("Error uploading assets:", error);
      const errorMessage = error instanceof Error ? error.message : String(error);
      setUploadError(`Upload failed: ${errorMessage}`);
    } finally {
      setIsUploading(false);
    }
  };

  const getFilePreview = (file: File) => {
    if (file.type.startsWith('image/')) {
      return URL.createObjectURL(file);
    }
    return null;
  };

  const getFileIcon = (file: File) => {
    if (file.type.startsWith('image/')) return '🖼️';
    if (file.type.startsWith('audio/')) return '🔊';
    if (file.name.endsWith('.obj') || file.name.endsWith('.json')) return '🎲';
    if (file.name.endsWith('.js') || file.name.endsWith('.ts')) return '📜';
    return '📄';
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <div className="assets-upload-container">
      <div className="upload-header">
        <h3>Upload Assets</h3>
        <p>Upload textures, models, sounds, and other assets for conversion.</p>
      </div>

      <div className="upload-form">
        <div className="asset-type-selector">
          <label htmlFor="asset-type-select">Asset Type:</label>
          <select
            id="asset-type-select"
            value={assetType}
            onChange={(e) => setAssetType(e.target.value)}
            disabled={isUploading}
            className="asset-type-select"
          >
            <option value="texture">Texture</option>
            <option value="sound">Sound</option>
            <option value="model">Model</option>
            <option value="script">Script</option>
            <option value="other">Other</option>
          </select>
        </div>

        <div
          className={`file-drop-zone ${dragActive ? 'drag-active' : ''}`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
        >
          <div className="drop-zone-content">
            <div className="drop-zone-icon">📁</div>
            <p className="drop-zone-text">
              Drag and drop files here, or{' '}
              <label htmlFor="conversion-asset-file-input" className="file-input-label">
                browse files
              </label>
            </p>
            <input
              id="conversion-asset-file-input"
              type="file"
              multiple
              onChange={handleFileChange}
              disabled={isUploading}
              className="file-input-hidden"
              accept="image/*,audio/*,.obj,.json,.js,.ts"
            />
          </div>
        </div>

        {selectedFiles && selectedFiles.length > 0 && (
          <div className="selected-files">
            <h4>Selected Files ({selectedFiles.length})</h4>
            <div className="files-preview">
              {Array.from(selectedFiles).map((file, index) => (
                <div key={index} className="file-preview-item">
                  <div className="file-preview-icon">
                    {getFilePreview(file) ? (
                      <img
                        src={getFilePreview(file)!}
                        alt={file.name}
                        className="file-preview-image"
                      />
                    ) : (
                      <span className="file-icon">{getFileIcon(file)}</span>
                    )}
                  </div>
                  <div className="file-info">
                    <p className="file-name" title={file.name}>
                      {file.name}
                    </p>
                    <p className="file-size">{formatFileSize(file.size)}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="upload-actions">
          <button
            onClick={handleUpload}
            disabled={!selectedFiles || selectedFiles.length === 0 || isUploading}
            className="upload-button"
          >
            {isUploading ? (
              <>
                <span className="loading-spinner">⏳</span>
                Uploading...
              </>
            ) : (
              `Upload ${selectedFiles?.length || 0} Asset${selectedFiles && selectedFiles.length !== 1 ? 's' : ''}`
            )}
          </button>
        </div>

        {uploadError && (
          <div className="upload-error">
            <p>{uploadError}</p>
          </div>
        )}
      </div>
    </div>
  );
};