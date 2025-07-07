/**
 * PRD Feature 1: One-Click Modpack Ingestion Component
 * Designed for visual learners with clear feedback and intuitive UI
 */

import React, { useState, useCallback, useEffect } from 'react';
import { useDropzone } from 'react-dropzone';
import { convertMod, pollJobStatus, cancelJob, downloadResult } from '../../services/api';
import {
  ConversionRequest,
  ConversionResponse,
  ConversionStatus // Ensure this is exported from types/api
} from '../../types/api';
import './ConversionUpload.css';

interface ConversionUploadProps {
  onConversionStart?: (conversionId: string) => void;
  onConversionComplete?: (conversionId: string) => void; // Optional: To notify parent about completion
}

export const ConversionUpload: React.FC<ConversionUploadProps> = ({ 
  onConversionStart,
  onConversionComplete
}) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [modUrl, setModUrl] = useState('');
  const [smartAssumptions, setSmartAssumptions] = useState(true);
  const [includeDependencies, setIncludeDependencies] = useState(true);
  const [isConverting, setIsConverting] = useState(false); // True during initial upload and when polling starts
  const [error, setError] = useState<string | null>(null);
  const [showSmartAssumptionsInfo, setShowSmartAssumptionsInfo] = useState(false);

  const [conversionId, setConversionId] = useState<string | null>(null);
  const [currentStatus, setCurrentStatus] = useState<ConversionStatus | null>(null);
  const [progressPercentage, setProgressPercentage] = useState<number>(0);
  const [isPolling, setIsPolling] = useState<boolean>(false);
  const [pollingAttempts, setPollingAttempts] = useState<number>(0);
  const MAX_POLLING_ATTEMPTS = 30; // Poll for 30 * 2s = 1 minute

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
    setCurrentStatus(ConversionStatus.PENDING); // Initial status
    setProgressPercentage(0);

    try {
      const request: ConversionRequest = {
        file: selectedFile,
        modUrl: modUrl || undefined,
        smartAssumptions,
        includeDependencies
      };

      const response: ConversionResponse = await convertMod(request);
      
      setConversionId(response.conversionId);
      setIsPolling(true); // Start polling
      setCurrentStatus(response.status || ConversionStatus.PENDING); // Use status from initial response
      setProgressPercentage(response.progress || 0);

      if (onConversionStart) {
        onConversionStart(response.conversionId);
      }
      setPollingAttempts(0); // Reset polling attempts
    } catch (err: any) {
      setError(err.message ? `Conversion request failed: ${err.message}. Please try again.` : 'Conversion request failed. Please check your connection and try again.');
      setIsConverting(false); // Stop if initial conversion call fails
    }
    // No finally block for setIsConverting(false) here, as polling will manage this
  };

  useEffect(() => {
    let intervalId: NodeJS.Timeout | null = null;

    if (conversionId && isPolling) {
      if (pollingAttempts >= MAX_POLLING_ATTEMPTS) {
        setError('Conversion is taking longer than expected. Please try cancelling and starting again, or check back later.');
        setIsPolling(false);
        setIsConverting(false);
        // Optionally, you could set a specific status like TIMEOUT
        // setCurrentStatus(ConversionStatus.TIMEOUT);
        return;
      }

      intervalId = setInterval(async () => {
        setPollingAttempts(prev => prev + 1);
        try {
          const statusResponse = await pollJobStatus(conversionId);
          setCurrentStatus(statusResponse.status);
          setProgressPercentage(statusResponse.progress || 0);

          if (statusResponse.status === ConversionStatus.COMPLETED ||
              statusResponse.status === ConversionStatus.FAILED ||
              statusResponse.status === ConversionStatus.CANCELLED) {
            setIsPolling(false);
            setIsConverting(false); // Conversion process finished
            if (statusResponse.status === ConversionStatus.COMPLETED && onConversionComplete) {
              onConversionComplete(conversionId);
            }
            if (statusResponse.status === ConversionStatus.FAILED) {
              setError(statusResponse.error || 'Conversion process failed. Please check the report for details if available, or try again.');
            }
          }
        } catch (err: any) {
          setError(err.message ? `Error fetching status: ${err.message}.` : 'Error fetching conversion status. Please check your connection.');
          setIsPolling(false); // Stop polling on error
          setIsConverting(false);
        }
      }, 2000); // Poll every 2 seconds
    }

    return () => {
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
  }, [conversionId, isPolling, onConversionComplete]);

  const handleCancel = async () => {
    if (!conversionId) return;

    setError(null); // Clear previous errors
    try {
      await cancelJob(conversionId);
      setIsPolling(false);
      setIsConverting(false);
      setCurrentStatus(ConversionStatus.CANCELLED);
      setConversionId(null); // Reset conversion ID
      setProgressPercentage(0);
      // Optionally, provide feedback that cancellation was successful
      setError(null); // Clear any previous errors on successful cancel
    } catch (err: any) {
      setError(err.message ? `Failed to cancel job: ${err.message}.` : 'Failed to cancel job. Please try again.');
      // Keep isConverting and isPolling true if cancel fails, to allow retry or show error
    }
  };

  const handleDownload = async () => {
    if (!conversionId || currentStatus !== ConversionStatus.COMPLETED) return;
    setError(null);
    try {
      const blob = await downloadResult(conversionId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${conversionId}_converted.mcaddon`; // Or get filename from API if available
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err: any) {
      setError(err.message ? `Download failed: ${err.message}.` : 'Download failed. Please try again.');
    }
  };

  const getStatusMessage = (): string => {
    if (!isConverting && !isPolling && currentStatus !== ConversionStatus.COMPLETED && currentStatus !== ConversionStatus.FAILED && currentStatus !== ConversionStatus.CANCELLED) {
      return selectedFile || modUrl ? 'Ready to convert' : 'Awaiting file or URL';
    }
    if (currentStatus === ConversionStatus.PENDING) return 'Upload complete, conversion pending...';
    if (currentStatus === ConversionStatus.IN_PROGRESS) return `Conversion in progress (${progressPercentage.toFixed(0)}%)...`;
    if (currentStatus === ConversionStatus.UPLOADING) return 'Uploading your file(s)...';
    if (currentStatus === ConversionStatus.ANALYZING) return `Analyzing mod structure (${progressPercentage.toFixed(0)}%)...`;
    if (currentStatus === ConversionStatus.CONVERTING) return `AI processing and converting (${progressPercentage.toFixed(0)}%)...`;
    if (currentStatus === ConversionStatus.PACKAGING) return `Packaging Bedrock add-on (${progressPercentage.toFixed(0)}%)...`;
    if (currentStatus === ConversionStatus.COMPLETED) return 'Conversion successful! Your download will begin shortly if not already started.';
    if (currentStatus === ConversionStatus.FAILED) return 'Conversion process failed. Please review the error message below.';
    if (currentStatus === ConversionStatus.CANCELLED) return 'Conversion has been cancelled. You can start a new conversion.';
    if (pollingAttempts >= MAX_POLLING_ATTEMPTS) return 'Conversion is taking longer than expected. You may cancel or continue waiting.';
    return 'Initiating conversion process...';
  };

  const canConvert = (selectedFile || (modUrl && validateUrl(modUrl))) && !isConverting && !isPolling;

  const resetConversionState = () => {
    setSelectedFile(null);
    setModUrl('');
    setIsConverting(false);
    setIsPolling(false);
    setError(null);
    setConversionId(null);
    setCurrentStatus(null);
    setProgressPercentage(0);
    setPollingAttempts(0);
  };

  return (
    <div className="conversion-upload">
      <div className="upload-header">
        <h2>Convert Java Mods to Bedrock</h2>
        <p>Upload your mod or paste a repository URL to get started</p>
      </div>

      {/* File Upload Area */}
      <div 
        {...getRootProps()} 
        className={`dropzone ${isDragActive ? 'drag-active' : ''} ${selectedFile ? 'file-selected' : ''} ${(isConverting || isPolling || currentStatus === ConversionStatus.COMPLETED) ? 'disabled-dropzone' : ''}`}
      >
        <input {...getInputProps()} aria-label="File upload" disabled={isConverting || isPolling || currentStatus === ConversionStatus.COMPLETED} />
        
        {selectedFile ? (
          <div className="file-preview">
            <div className="file-icon">📦</div>
            <div className="file-info">
              <div className="file-name">{selectedFile.name}</div>
              <div className="file-size">{(selectedFile.size / 1024 / 1024).toFixed(2)} MB</div>
              <div className="status">{getStatusMessage()}</div>
            </div>
            <button 
              className="remove-file"
              onClick={(e) => {
                e.stopPropagation();
                if (!(isConverting || isPolling || currentStatus === ConversionStatus.COMPLETED)) setSelectedFile(null);
              }}
              disabled={isConverting || isPolling || currentStatus === ConversionStatus.COMPLETED}
            >
              ✕
            </button>
          </div>
        ) : (currentStatus === ConversionStatus.COMPLETED || currentStatus === ConversionStatus.FAILED || currentStatus === ConversionStatus.CANCELLED) ? (
           <div className="upload-prompt">
            <div className="upload-icon">🎉</div>
            <h3>{getStatusMessage()}</h3>
            <button type="button" className="browse-button" onClick={resetConversionState}>
              Start New Conversion
            </button>
          </div>
        ) : (
          <div className="upload-prompt">
            <div className="upload-icon">📁</div>
            <h3>Drag & drop your modpack here</h3>
            <p>Supports .jar files and .zip modpack archives</p>
            <button type="button" className="browse-button" disabled={isConverting || isPolling || currentStatus === ConversionStatus.COMPLETED}>
              Browse Files
            </button>
          </div>
        )}
      </div>

      {/* URL Input */}
      {/* URL Input - Hide if file selected or in processing states that are not initial */}
      { !selectedFile && currentStatus !== ConversionStatus.COMPLETED && currentStatus !== ConversionStatus.FAILED && currentStatus !== ConversionStatus.CANCELLED && (
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
            disabled={!!selectedFile || isConverting || isPolling || currentStatus === ConversionStatus.COMPLETED}
          />

          <div className="supported-sites">
            <span>Supported: CurseForge • Modrinth</span>
          </div>
        </div>
      )}

      {/* Configuration Options - Hide on final states */}
      { currentStatus !== ConversionStatus.COMPLETED && currentStatus !== ConversionStatus.FAILED && currentStatus !== ConversionStatus.CANCELLED && (
        <div className={`conversion-options ${(isConverting || isPolling || currentStatus === ConversionStatus.COMPLETED) ? 'disabled-options' : ''}`}>
        <div className="option-group">
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={smartAssumptions}
              onChange={(e) => setSmartAssumptions(e.target.checked)}
              disabled={isConverting || isPolling || currentStatus === ConversionStatus.COMPLETED}
            />
            <span className="checkmark"></span>
            Enable Smart Assumptions
            <button 
              className="info-button"
              onClick={() => setShowSmartAssumptionsInfo(!showSmartAssumptionsInfo)}
              aria-label="Learn more about smart assumptions"
              disabled={isConverting || isPolling || currentStatus === ConversionL.COMPLETED}
            >
              ℹ️
            </button>
          </label>
          
          <p className="option-description">
            AI will make intelligent compromises for incompatible features
          </p>
          
          {showSmartAssumptionsInfo && (
            <div className="smart-assumptions-info">
              <h4>What are Smart Assumptions?</h4>
              <p>When direct conversion isn't possible, our AI can make intelligent substitutions:</p>
              <ul>
                <li><strong>Custom Dimensions:</strong> May become unique structures in existing dimensions.</li>
                <li><strong>Complex Machinery:</strong> Could be simplified to functional equivalents or decorative blocks.</li>
                <li><strong>Custom GUIs:</strong> Information might be presented using in-game items like books or signs.</li>
                <li><strong>Client-Side Rendering Effects:</strong> Often excluded, with a note provided.</li>
              </ul>
              <p>This helps maximize compatibility and playability in Bedrock Edition.</p>
            </div>
          )}
        </div>

        <div className="option-group">
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={includeDependencies}
              onChange={(e) => setIncludeDependencies(e.target.checked)}
              disabled={isConverting || isPolling || currentStatus === ConversionStatus.COMPLETED}
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

      {/* Convert/Cancel/Download Buttons */}
      <div className="action-buttons">
        {currentStatus === ConversionStatus.COMPLETED ? (
          <button
            className="download-button"
            onClick={handleDownload}
          >
            <span role="img" aria-label="download">📥</span> Download Converted Mod
          </button>
        ) : (isConverting || isPolling) && currentStatus !== ConversionStatus.FAILED && currentStatus !== ConversionStatus.CANCELLED ? (
          <button
            className="cancel-button"
            onClick={handleCancel}
          >
            <span role="img" aria-label="cancel">🚫</span> Cancel Conversion
          </button>
        ) : currentStatus !== ConversionStatus.FAILED && currentStatus !== ConversionStatus.CANCELLED && (
          <button
            className={`convert-button ${!canConvert ? 'disabled' : ''}`}
            onClick={handleConvert}
            disabled={!canConvert}
          >
            🚀 Convert to Bedrock
          </button>
        )}
        {/* "Start New" button could also be placed here or as part of the status display for FAILED/CANCELLED */}
      </div>

      {/* Progress Bar and Status Message - Show unless it's a final state AND not an error that needs showing message for */}
      {(isConverting || isPolling || currentStatus === ConversionStatus.FAILED || currentStatus === ConversionStatus.CANCELLED) &&
        currentStatus !== ConversionStatus.COMPLETED && (
        <div className="progress-section">
          <div className="status-message">{getStatusMessage()}</div>
          {(isConverting || isPolling) && currentStatus !== ConversionStatus.FAILED && currentStatus !== ConversionStatus.CANCELLED && (
            <div className="progress-bar" role="progressbar" aria-valuenow={progressPercentage} aria-valuemin={0} aria-valuemax={100}>
              <div className="progress-fill" style={{ width: `${progressPercentage}%` }}></div>
            </div>
          )}
        </div>
      )}

      {/* Progress Indicator for Visual Learners - Hide on final states */}
      {(isConverting || isPolling) && currentStatus !== ConversionStatus.COMPLETED && currentStatus !== ConversionStatus.FAILED && currentStatus !== ConversionStatus.CANCELLED && (
        <div className="conversion-steps">
          <div className={`step ${currentStatus === ConversionStatus.ANALYZING || (currentStatus === ConversionStatus.IN_PROGRESS && progressPercentage >=0 && progressPercentage <33) ? 'active' : ''}`}>
            <div className="step-icon">🔍</div>
            <span>{currentStatus === ConversionStatus.ANALYZING ? `Analyzing... (${progressPercentage.toFixed(0)}%)` : 'Analyze Mod'}</span>
          </div>
          <div className={`step ${currentStatus === ConversionStatus.CONVERTING || (currentStatus === ConversionStatus.IN_PROGRESS && progressPercentage >=33 && progressPercentage <66)? 'active' : ''}`}>
            <div className="step-icon">🤖</div>
            <span>{currentStatus === ConversionStatus.CONVERTING ? `AI Converting... (${progressPercentage.toFixed(0)}%)` : 'AI Convert'}</span>
          </div>
          <div className={`step ${currentStatus === ConversionStatus.PACKAGING || (currentStatus === ConversionStatus.IN_PROGRESS && progressPercentage >=66 && progressPercentage <=100) ? 'active' : ''}`}>
            <div className="step-icon">📦</div>
            <span>{currentStatus === ConversionStatus.PACKAGING ? `Packaging Add-on... (${progressPercentage.toFixed(0)}%)` : 'Package Add-on'}</span>
          </div>
        </div>
      )}
    </div>
  );
};