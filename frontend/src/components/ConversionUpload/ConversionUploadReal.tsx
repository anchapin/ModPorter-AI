/**
 * PRD Feature 1: One-Click Modpack Ingestion Component
 * Connected to real backend API
 */

import React, { useState, useCallback, useEffect } from 'react';
import { useDropzone } from 'react-dropzone';
import './ConversionUpload.css';

interface ConversionUploadProps {
  onConversionStart?: (jobId: string) => void;
  onConversionComplete?: (jobId: string) => void;
}

// Simple types to avoid import issues
interface ConversionStatus {
  job_id: string;
  status: string;
  progress: number;
  message: string;
  error?: string | null;
}

interface ConversionResponse {
  job_id: string;
  status: string;
  message: string;
}

interface UploadResponse {
  file_id: string;
  original_filename: string;
  saved_filename: string;
  message: string;
}

export const ConversionUploadReal: React.FC<ConversionUploadProps> = ({ 
  onConversionStart,
  onConversionComplete
}) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [modUrl, setModUrl] = useState('');
  const [smartAssumptions, setSmartAssumptions] = useState(true);
  const [includeDependencies, setIncludeDependencies] = useState(true);
  const [isConverting, setIsConverting] = useState(false);
  const [currentJobId, setCurrentJobId] = useState<string | null>(null);
  const [currentStatus, setCurrentStatus] = useState<ConversionStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showSmartAssumptionsInfo, setShowSmartAssumptionsInfo] = useState(false);

  // API Base URL - Use proxy path for development, environment variable for production
  const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1';
  
  // Debug logging (only in development)
  if (import.meta.env.DEV) {
    console.log('DEBUG: VITE_API_URL =', import.meta.env.VITE_API_URL);
    console.log('DEBUG: API_BASE_URL =', API_BASE_URL);
  }

  // Centralized API error handling
  const handleApiError = (error: any): Error => {
    if (error instanceof TypeError && error.message.includes('fetch')) {
      return new Error('Unable to connect to the server. Please check if the backend is running.');
    }
    return error instanceof Error ? error : new Error(String(error));
  };

  // Centralized fetch wrapper with error handling
  const apiFetch = useCallback(async (url: string, options?: globalThis.RequestInit): Promise<Response> => {
    try {
      const response = await fetch(url, options);
      return response;
    } catch (error) {
      throw handleApiError(error);
    }
  }, []);

  // File validation
  const validateFile = (file: File): boolean => {
    const validTypes = ['application/java-archive', 'application/zip', 'application/x-zip-compressed'];
    const validExtensions = ['.jar', '.zip'];
    
    const hasValidType = validTypes.includes(file.type);
    const hasValidExtension = validExtensions.some(ext => file.name.toLowerCase().endsWith(ext));
    
    return hasValidType || hasValidExtension;
  };

  // URL validation
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

  // Upload file to backend
  const uploadFile = async (file: File): Promise<UploadResponse> => {
    const formData = new FormData();
    formData.append('file', file);

    const uploadUrl = `${API_BASE_URL}/upload`;
    if (import.meta.env.DEV) {
      console.log('DEBUG: Making upload request to:', uploadUrl);
    }

    const response = await apiFetch(uploadUrl, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Upload failed' }));
      throw new Error(errorData.detail || 'File upload failed');
    }

    return response.json();
  };

  // Start conversion
  const startConversion = async (fileId: string, filename: string): Promise<ConversionResponse> => {
    const response = await apiFetch(`${API_BASE_URL}/convert`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        file_id: fileId,
        original_filename: filename,
        options: {
          smartAssumptions,
          includeDependencies,
          ...(modUrl && { modUrl }),
        },
      }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Conversion failed' }));
      throw new Error(errorData.detail || 'Conversion failed');
    }

    return response.json();
  };

  // Get conversion status
  const getConversionStatus = useCallback(async (jobId: string): Promise<ConversionStatus> => {
    const response = await apiFetch(`${API_BASE_URL}/convert/${jobId}/status`);
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Failed to get status' }));
      throw new Error(errorData.detail || 'Failed to get status');
    }

    return response.json();
  }, [API_BASE_URL, apiFetch]);

  // Polling for status updates (every 2 seconds as per issue #171)
  useEffect(() => {
    let intervalId: number | null = null;
    let attempts = 0;
    const maxAttempts = 300; // 10 minutes with 2-second intervals (was 120)

    if (currentJobId && isConverting) {
      intervalId = setInterval(async () => {
        try {
          const status = await getConversionStatus(currentJobId);
          setCurrentStatus(status);
          attempts++;

          if (status.status === 'completed') {
            setIsConverting(false);
            if (onConversionComplete) {
              onConversionComplete(currentJobId);
            }
          } else if (status.status === 'failed') {
            setIsConverting(false);
            setError(status.error || 'Conversion failed');
          } else if (attempts >= maxAttempts) {
            setIsConverting(false);
            setError('Conversion timed out after 10 minutes. Please try again.');
          }
        } catch (error) {
          console.error('Status check error:', error);
          attempts++;
          if (attempts >= maxAttempts) {
            setIsConverting(false);
            setError('Unable to check conversion status. Please try again.');
          }
        }
      }, 2000); // Check every 2 seconds as per issue requirement
    }

    return () => {
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
  }, [currentJobId, isConverting, onConversionComplete, getConversionStatus]);

  const onDrop = useCallback((acceptedFiles: File[], rejectedFiles: any[]) => {
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
    setModUrl('');
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
      setSelectedFile(null);
    }
    
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

    if (!selectedFile) {
      setError('File upload is required for conversion. URL-only conversion is not yet supported.');
      return;
    }
    
    setIsConverting(true);
    setError(null);
    setCurrentStatus(null);
    
    try {
      if (import.meta.env.DEV) {
        console.log('Starting real conversion...');
      }
      
      // Step 1: Upload file
      const uploadResponse = await uploadFile(selectedFile);
      if (import.meta.env.DEV) {
        console.log('File uploaded:', uploadResponse);
      }
      
      // Step 2: Start conversion
      const conversionResponse = await startConversion(uploadResponse.file_id, uploadResponse.original_filename);
      if (import.meta.env.DEV) {
        console.log('Conversion started:', conversionResponse);
      }
      
      setCurrentJobId(conversionResponse.job_id);
      setCurrentStatus({
        job_id: conversionResponse.job_id,
        status: conversionResponse.status,
        progress: 0,
        message: conversionResponse.message || 'Conversion started'
      });

      if (onConversionStart) {
        onConversionStart(conversionResponse.job_id);
      }
      
    } catch (err: any) {
      console.error('Conversion error:', err);
      setError(err.message || 'Conversion failed. Please try again.');
      setIsConverting(false);
    }
  };

  const downloadResult = async () => {
    if (!currentJobId) return;
    
    try {
      const response = await apiFetch(`${API_BASE_URL}/convert/${currentJobId}/download`);
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Download failed' }));
        throw new Error(errorData.detail || 'Download failed');
      }

      // Determine filename with priority: Content-Disposition > original filename > fallback
      const contentDisposition = response.headers.get('Content-Disposition');
      let filename: string;

      const dispositionMatch = contentDisposition?.match(/filename="([^"]+)"/);
      if (dispositionMatch && dispositionMatch[1]) {
        filename = dispositionMatch[1];
      } else if (selectedFile?.name) {
        const baseName = selectedFile.name.replace(/\.(jar|zip)$/i, '');
        filename = `${baseName}-converted.mcaddon`;
      } else {
        filename = `converted-mod-${currentJobId}.mcaddon`; // fallback
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err: any) {
      setError(err.message || 'Failed to download conversion result');
    }
  };

  const getStatusMessage = () => {
    if (!currentStatus) return 'Ready to convert';
    
    switch (currentStatus.status) {
      case 'queued':
        return 'Queued for processing...';
      case 'processing':
        return currentStatus.message || 'Processing...';
      case 'completed':
        return 'Conversion completed!';
      case 'failed':
        return 'Conversion failed';
      default:
        return currentStatus.message || 'Processing...';
    }
  };

  return (
    <div className="conversion-upload">
      <h2>Convert Your Modpack</h2>
      <p className="description">
        Upload your Java Edition modpack and we'll convert it to Bedrock Edition using AI.
      </p>

      {error && (
        <div className="error-message">
          {error}
        </div>
      )}

      {/* Progress Display */}
      {(isConverting || currentStatus) && currentStatus && (
        <div className={`progress-display status-${currentStatus.status === 'completed' ? 'completed' : currentStatus.status === 'failed' ? 'failed' : 'processing'}`}>
          <div className="progress-header">
            <h4 className="progress-title">
              {currentStatus.status === 'completed' ? '✅ Conversion Complete!' : 
               currentStatus.status === 'failed' ? '❌ Conversion Failed' : '🔄 Converting...'}
            </h4>
            <span className={`progress-status-badge status-${currentStatus.status === 'completed' ? 'completed' : currentStatus.status === 'failed' ? 'failed' : 'processing'}`}>
              {currentStatus.status}
            </span>
          </div>
          <p className="progress-message"><strong>Message:</strong> {getStatusMessage()}</p>
          {currentStatus.progress !== undefined && (
            <>
              <p className="progress-percentage"><strong>Progress:</strong> {currentStatus.progress}%</p>
              <div className="progress-bar-container">
                <div 
                  className={`progress-bar-fill status-${currentStatus.status === 'completed' ? 'completed' : currentStatus.status === 'failed' ? 'failed' : 'processing'}`}
                  style={{ width: `${Math.max(0, Math.min(100, currentStatus.progress))}%` }}
                ></div>
              </div>
            </>
          )}
          <p className="progress-job-id">
            <strong>Job ID:</strong> {currentStatus.job_id.substring(0, 8)}...
          </p>
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
                <div className="status">Ready for real AI conversion</div>
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
              <p><strong>Real AI conversion with {process.env.NODE_ENV === 'development' ? 'Mock LLM' : 'Ollama/OpenAI'}</strong></p>
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
              <span>Supported: CurseForge • Modrinth (File upload required for now)</span>
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
          {!currentStatus || currentStatus.status === 'failed' ? (
            <button
              type="submit"
              className="upload-button"
              disabled={isConverting || (!selectedFile && !modUrl)}
            >
              {isConverting ? 'Converting with AI...' : 'Convert to Bedrock (Real AI)'}
            </button>
          ) : currentStatus.status === 'completed' ? (
            <button
              type="button"
              className="download-button"
              onClick={downloadResult}
            >
              📥 Download .mcaddon
            </button>
          ) : null}
        </div>
      </form>
    </div>
  );
};