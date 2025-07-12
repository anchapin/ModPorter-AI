/**
 * PRD Feature 1: One-Click Modpack Ingestion Component
 * Designed for visual learners with clear feedback and intuitive UI
 */

import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import './ConversionUpload.css';

interface ConversionUploadProps {
  onConversionStart?: (jobId: string) => void;
  onConversionComplete?: (jobId: string) => void;
}

export const ConversionUploadFixed: React.FC<ConversionUploadProps> = ({ 
  onConversionStart,
  onConversionComplete
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

  const onDrop = useCallback((acceptedFiles: File[], rejectedFiles: any[]) => {
    // Handle rejected files first
    if (rejectedFiles.length > 0) {
      setError('Unsupported file type. Please upload .jar or .zip files only.');
      return;
    }
    
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
    accept: {
      'application/java-archive': ['.jar'],
      'application/zip': ['.zip'],
      'application/x-zip-compressed': ['.zip']
    },
    maxFiles: 1,
    multiple: false
  });

  const handleUrlChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const url = e.target.value;
    setModUrl(url);
    
    if (url) {
      setSelectedFile(null); // Clear file if URL is entered
    }
    
    // Validate URL on input
    if (url && !validateUrl(url)) {
      setError('Please enter a valid CurseForge or Modrinth URL.');
    } else {
      setError(null);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!selectedFile && !modUrl) {
      setError('Please select a file or enter a URL.');
      return;
    }
    
    if (modUrl && !validateUrl(modUrl)) {
      setError('Please enter a valid CurseForge or Modrinth URL.');
      return;
    }
    
    setIsConverting(true);
    setError(null);
    
    try {
      // For now, just simulate the conversion process
      const mockJobId = 'job-' + Date.now();
      
      if (onConversionStart) {
        onConversionStart(mockJobId);
      }
      
      // Simulate processing time
      setTimeout(() => {
        setIsConverting(false);
        if (onConversionComplete) {
          onConversionComplete(mockJobId);
        }
        alert('Conversion completed! (This is a simulation - backend integration pending)');
      }, 3000);
      
    } catch (err: any) {
      console.error('Conversion error:', err);
      setError('Conversion request failed. Please try again.');
      setIsConverting(false);
    }
  };

  return (
    <div className="conversion-upload">
      <h2>Convert Your Modpack</h2>
      <p className="description">
        Upload your Java Edition modpack and we'll convert it to Bedrock Edition using smart assumptions.
      </p>

      {error && (
        <div className="error-message">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit}>
        {/* File Upload Area */}
        <div 
          {...getRootProps()} 
          className={`dropzone ${isDragActive ? 'drag-active' : ''} ${selectedFile ? 'file-selected' : ''} ${isConverting ? 'disabled-dropzone' : ''}`}
        >
          <input {...getInputProps()} aria-label="File upload" disabled={isConverting} />
          
          {selectedFile ? (
            <div className="file-preview">
              <div className="file-icon">📦</div>
              <div className="file-info">
                <div className="file-name">{selectedFile.name}</div>
                <div className="file-size">{(selectedFile.size / 1024 / 1024).toFixed(2)} MB</div>
                <div className="status">Ready to convert</div>
              </div>
              <button 
                type="button"
                className="remove-file"
                onClick={(e) => {
                  e.stopPropagation();
                  if (!isConverting) setSelectedFile(null);
                }}
                disabled={isConverting}
              >
                ✕
              </button>
            </div>
          ) : (
            <div className="upload-prompt">
              <div className="upload-icon">📁</div>
              <h3>Drag & drop your modpack here</h3>
              <p>Supports .jar files and .zip modpack archives</p>
              <button type="button" className="browse-button" disabled={isConverting}>
                Browse Files
              </button>
            </div>
          )}
        </div>

        {/* URL Input */}
        {!selectedFile && (
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
              disabled={!!selectedFile || isConverting}
            />

            <div className="supported-sites">
              <span>Supported: CurseForge • Modrinth</span>
            </div>
          </div>
        )}

        {/* Configuration Options */}
        <div className={`conversion-options ${isConverting ? 'disabled-options' : ''}`}>
          <div className="option-group">
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={smartAssumptions}
                onChange={(e) => setSmartAssumptions(e.target.checked)}
                disabled={isConverting}
              />
              <span className="checkmark"></span>
              Enable Smart Assumptions
              <button 
                type="button"
                className="info-button"
                onClick={() => setShowSmartAssumptionsInfo(!showSmartAssumptionsInfo)}
                aria-label="Learn more about smart assumptions"
                disabled={isConverting}
              >
                ?
              </button>
            </label>

            {showSmartAssumptionsInfo && (
              <div className="info-panel">
                <h4>Smart Assumptions</h4>
                <p>
                  When enabled, our AI will make intelligent assumptions to convert incompatible features:
                </p>
                <ul>
                  <li>Custom dimensions → Large structures in existing dimensions</li>
                  <li>Complex machinery → Simplified blocks with similar functionality</li>
                  <li>Custom GUIs → Book or sign-based interfaces</li>
                </ul>
                <p>This increases conversion success rate but may alter some mod features.</p>
              </div>
            )}
          </div>

          <div className="option-group">
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={includeDependencies}
                onChange={(e) => setIncludeDependencies(e.target.checked)}
                disabled={isConverting}
              />
              <span className="checkmark"></span>
              Include Dependencies
            </label>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="action-buttons">
          <button
            type="submit"
            className="convert-button"
            disabled={isConverting || (!selectedFile && !modUrl)}
          >
            {isConverting ? 'Converting...' : 'Convert to Bedrock'}
          </button>
        </div>
      </form>
    </div>
  );
};