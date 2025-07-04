/**
 * PRD Feature 1: One-Click Modpack Ingestion Component
 * Designed for visual learners with clear feedback and intuitive UI
 */

import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { convertMod } from '../../services/api';
import { ConversionRequest, ConversionResponse } from '../../types/api';
import './ConversionUpload.css';

interface ConversionUploadProps {
  onConversionStart?: (conversionId: string) => void;
}

export const ConversionUpload: React.FC<ConversionUploadProps> = ({ 
  onConversionStart 
}) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [modUrl, setModUrl] = useState('');
  const [smartAssumptions, setSmartAssumptions] = useState(true);
  const [includeDependencies, setIncludeDependencies] = useState(true);
  const [isConverting, setIsConverting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showSmartAssumptionsInfo, setShowSmartAssumptionsInfo] = useState(false);

  // PRD Feature 1: File validation
  const validateFile = (file: File): boolean => {
    const validTypes = ['application/java-archive', 'application/zip', 'application/x-zip-compressed'];
    const validExtensions = ['.jar', '.zip'];
    
    const hasValidType = validTypes.includes(file.type);
    const hasValidExtension = validExtensions.some(ext => file.name.toLowerCase().endsWith(ext));
    
    return hasValidType || hasValidExtension;
  };

  // PRD Feature 1: URL validation for CurseForge and Modrinth
  const validateUrl = (url: string): boolean => {
    const validDomains = [
      'curseforge.com',
      'www.curseforge.com',
      'modrinth.com',
      'www.modrinth.com'
    ];
    
    try {
      const urlObj = new URL(url);
      return validDomains.some(domain => urlObj.hostname === domain);
    } catch {
      return false;
    }
  };

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const file = acceptedFiles[0];
    
    if (!file) return;
    
    if (!validateFile(file)) {
      setError('Unsupported file type. Please upload .jar or .zip files only.');
      return;
    }
    
    setSelectedFile(file);
    setModUrl(''); // Clear URL if file is selected
    setError(null);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    multiple: false,
    accept: {
      'application/java-archive': ['.jar'],
      'application/zip': ['.zip']
    }
  });

  const handleUrlChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const url = e.target.value;
    setModUrl(url);
    
    if (url && !validateUrl(url)) {
      setError('Invalid URL. Please use CurseForge or Modrinth links only.');
    } else {
      setError(null);
      setSelectedFile(null); // Clear file if URL is entered
    }
  };

  const handleConvert = async () => {
    if (!selectedFile && !modUrl) {
      setError('Please upload a file or enter a URL');
      return;
    }

    if (modUrl && !validateUrl(modUrl)) {
      setError('Please enter a valid CurseForge or Modrinth URL');
      return;
    }

    setIsConverting(true);
    setError(null);

    try {
      const request: ConversionRequest = {
        file: selectedFile,
        modUrl: modUrl || undefined,
        smartAssumptions,
        includeDependencies
      };

      const response: ConversionResponse = await convertMod(request);
      
      if (onConversionStart) {
        onConversionStart(response.conversionId);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Conversion failed');
    } finally {
      setIsConverting(false);
    }
  };

  const canConvert = (selectedFile || (modUrl && validateUrl(modUrl))) && !isConverting;

  return (
    <div className="conversion-upload">
      <div className="upload-header">
        <h2>Convert Java Mods to Bedrock</h2>
        <p>Upload your mod or paste a repository URL to get started</p>
      </div>

      {/* File Upload Area */}
      <div 
        {...getRootProps()} 
        className={`dropzone ${isDragActive ? 'drag-active' : ''} ${selectedFile ? 'file-selected' : ''}`}
      >
        <input {...getInputProps()} aria-label="File upload" />
        
        {selectedFile ? (
          <div className="file-preview">
            <div className="file-icon">📦</div>
            <div className="file-info">
              <div className="file-name">{selectedFile.name}</div>
              <div className="file-size">{(selectedFile.size / 1024 / 1024).toFixed(2)} MB</div>
              <div className="status">Ready to convert</div>
            </div>
            <button 
              className="remove-file"
              onClick={(e) => {
                e.stopPropagation();
                setSelectedFile(null);
              }}
            >
              ✕
            </button>
          </div>
        ) : (
          <div className="upload-prompt">
            <div className="upload-icon">📁</div>
            <h3>Drag & drop your modpack here</h3>
            <p>Supports .jar files and .zip modpack archives</p>
            <button type="button" className="browse-button">
              Browse Files
            </button>
          </div>
        )}
      </div>

      {/* URL Input */}
      <div className="url-input-section">
        <div className="divider">
          <span>or paste URL</span>
        </div>
        
        <input
          type="url"
          value={modUrl}
          onChange={handleUrlChange}
          placeholder="https://www.curseforge.com/minecraft/mc-mods/your-mod or https://modrinth.com/mod/your-mod"
          className="url-input"
          disabled={!!selectedFile}
        />
        
        <div className="supported-sites">
          <span>Supported: CurseForge • Modrinth</span>
        </div>
      </div>

      {/* Configuration Options */}
      <div className="conversion-options">
        <div className="option-group">
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={smartAssumptions}
              onChange={(e) => setSmartAssumptions(e.target.checked)}
            />
            <span className="checkmark"></span>
            Enable Smart Assumptions
            <button 
              className="info-button"
              onClick={() => setShowSmartAssumptionsInfo(!showSmartAssumptionsInfo)}
              aria-label="Learn more about smart assumptions"
            >
              ℹ️
            </button>
          </label>
          
          <p className="option-description">
            AI will make intelligent compromises for incompatible features
          </p>
          
          {showSmartAssumptionsInfo && (
            <div className="smart-assumptions-info">
              <h4>Smart Assumptions Examples:</h4>
              <ul>
                <li><strong>Custom Dimensions:</strong> Converted to large structures in existing dimensions</li>
                <li><strong>Complex Machinery:</strong> Simplified to decorative blocks or containers</li>
                <li><strong>Custom GUI:</strong> Recreated using books or signs for information display</li>
                <li><strong>Client-Side Rendering:</strong> Excluded with clear notification</li>
              </ul>
            </div>
          )}
        </div>

        <div className="option-group">
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={includeDependencies}
              onChange={(e) => setIncludeDependencies(e.target.checked)}
            />
            <span className="checkmark"></span>
            Include Dependencies
          </label>
          
          <p className="option-description">
            Automatically bundle required libraries and dependencies
          </p>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="error-message">
          <span className="error-icon">⚠️</span>
          {error}
        </div>
      )}

      {/* Convert Button */}
      <button
        className={`convert-button ${!canConvert ? 'disabled' : ''}`}
        onClick={handleConvert}
        disabled={!canConvert}
      >
        {isConverting ? (
          <>
            <div className="spinner"></div>
            Converting...
            <div className="progress-bar" role="progressbar">
              <div className="progress-fill"></div>
            </div>
          </>
        ) : (
          <>
            🚀 Convert to Bedrock
          </>
        )}
      </button>

      {/* Progress Indicator for Visual Learners */}
      {isConverting && (
        <div className="conversion-steps">
          <div className="step active">
            <div className="step-icon">🔍</div>
            <span>Analyzing mod structure...</span>
          </div>
          <div className="step">
            <div className="step-icon">🤖</div>
            <span>AI processing conversion...</span>
          </div>
          <div className="step">
            <div className="step-icon">📦</div>
            <span>Packaging Bedrock add-on...</span>
          </div>
        </div>
      )}
    </div>
  );
};