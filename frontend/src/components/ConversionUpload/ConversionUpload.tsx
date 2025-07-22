/**
 * PRD Feature 1: One-Click Modpack Ingestion Component
 * Designed for visual learners with clear feedback and intuitive UI
 */

import React, { useState, useCallback, useEffect } from 'react';
import { useDropzone } from 'react-dropzone';
import { convertMod, getConversionStatus, cancelJob, downloadResult } from '../../services/api';
import {
  InitiateConversionParams,
  ConversionResponse,
  ConversionStatus,
  ConversionStatusEnum
} from '../../types/api';
import ConversionProgress from '../ConversionProgress/ConversionProgress';
import './ConversionUpload.css';

// Move constant outside component as suggested by Copilot
const MAX_POLLING_ATTEMPTS = 30; // Poll for 30 * 2s = 1 minute

interface ConversionUploadProps {
  onConversionStart?: (jobId: string) => void;
  onConversionComplete?: (jobId: string) => void;
}

export const ConversionUpload: React.FC<ConversionUploadProps> = ({ 
  onConversionStart,
  onConversionComplete
}) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [modUrl, setModUrl] = useState('');
  const [smartAssumptions, setSmartAssumptions] = useState(true);
  const [includeDependencies, setIncludeDependencies] = useState(true);
  const [isConverting, setIsConverting] = useState(false);
  const [currentConversionId, setCurrentConversionId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showSmartAssumptionsInfo, setShowSmartAssumptionsInfo] = useState(false);

  // Extended state for polling functionality
  const [currentStatus, setCurrentStatus] = useState<ConversionStatus | null>(null);
  const [progressPercentage, setProgressPercentage] = useState<number>(0);
  const [isPolling, setIsPolling] = useState<boolean>(false);
  const [pollingAttempts, setPollingAttempts] = useState<number>(0);

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

  const resetConversionState = () => {
    setSelectedFile(null);
    setModUrl('');
    setCurrentConversionId(null);
    setCurrentStatus(null);
    setProgressPercentage(0);
    setIsPolling(false);
    setPollingAttempts(0);
    setIsConverting(false);
    setError(null);
  };

  const getStatusMessage = () => {
    if (!currentStatus) return 'Ready to convert';
    
    switch (currentStatus.status) {
      case ConversionStatusEnum.PENDING:
        return 'Queued for processing...';
      case ConversionStatusEnum.UPLOADING:
        return 'Uploading file...';
      case ConversionStatusEnum.IN_PROGRESS:
        return 'Processing...';
      case ConversionStatusEnum.ANALYZING:
        return 'Analyzing mod structure...';
      case ConversionStatusEnum.CONVERTING:
        return 'Converting to Bedrock...';
      case ConversionStatusEnum.PACKAGING:
        return 'Packaging add-on...';
      case ConversionStatusEnum.COMPLETED:
        return 'Conversion completed!';
      case ConversionStatusEnum.FAILED:
        return 'Conversion failed';
      case ConversionStatusEnum.CANCELLED:
        return 'Conversion cancelled';
      default:
        return currentStatus.message || 'Processing...';
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
    // Reset conversion state when new file is selected
    if (currentConversionId) {
      resetConversionState();
    }
  }, [currentConversionId]);

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
      if (currentConversionId) {
        resetConversionState();
      }
    }
    
    // Validate URL on input
    if (url && !validateUrl(url)) {
      setError('Please enter a valid CurseForge or Modrinth URL.');
    } else {
      setError(null);
    }
  };

  const handleCancel = async () => {
    if (!currentConversionId) return;
    
    try {
      await cancelJob(currentConversionId);
      setCurrentStatus(prev => prev ? { ...prev, status: ConversionStatusEnum.CANCELLED } : null);
      setIsPolling(false);
      setIsConverting(false);
    } catch (err: any) {
      setError(err.message || 'Failed to cancel conversion');
    }
  };

  const handleDownload = async () => {
    if (!currentConversionId) return;
    
    try {
      const { blob, filename } = await downloadResult(currentConversionId);
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
      const request: InitiateConversionParams = {
        file: selectedFile || undefined,
        modUrl: modUrl || undefined,
        smartAssumptions,
        includeDependencies,
      };

      const response: ConversionResponse = await convertMod(request);
      
      setCurrentConversionId(response.job_id);
      setIsPolling(true);
      setProgressPercentage(0);

      if (onConversionStart) {
        onConversionStart(response.job_id);
      }
      setPollingAttempts(0);
    } catch (err: any) {
      setError(err.message ? `Conversion request failed: ${err.message}. Please try again.` : 'Conversion request failed. Please check your connection and try again.');
      setIsConverting(false);
    }
  };

  // Polling effect with proper dependency array as suggested by Copilot
  useEffect(() => {
    let intervalId: number | null = null;

    if (currentConversionId && isPolling) {
      if (pollingAttempts >= MAX_POLLING_ATTEMPTS) {
        setError('Conversion is taking longer than expected. Please try cancelling and starting again, or check back later.');
        setIsPolling(false);
        setIsConverting(false);
        return;
      }

      intervalId = setInterval(async () => {
        try {
          const status = await getConversionStatus(currentConversionId);
          setCurrentStatus(status);
          setProgressPercentage(status.progress);
          setPollingAttempts(prev => prev + 1);

          // Check if conversion is complete
          if (status.status === ConversionStatusEnum.COMPLETED) {
            setIsPolling(false);
            setIsConverting(false);
            if (onConversionComplete) {
              onConversionComplete(currentConversionId);
            }
          } else if (status.status === ConversionStatusEnum.FAILED || status.status === ConversionStatusEnum.CANCELLED) {
            setIsPolling(false);
            setIsConverting(false);
            if (status.error) {
              setError(status.error);
            }
          }
        } catch (error: any) {
          setPollingAttempts(prev => prev + 1);
          if (pollingAttempts >= MAX_POLLING_ATTEMPTS - 1) {
            setError(`Unable to check conversion status: ${error.message || 'Unknown error'}. Please try again later.`);
            setIsPolling(false);
            setIsConverting(false);
          }
        }
      }, 2000); // Poll every 2 seconds
    }

    return () => {
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
  }, [currentConversionId, isPolling, pollingAttempts, onConversionComplete]); // Fixed dependency array

  const isProcessing = isConverting || isPolling;
  const isCompleted = currentStatus?.status === ConversionStatusEnum.COMPLETED;
  const isFailed = currentStatus?.status === ConversionStatusEnum.FAILED;
  const isCancelled = currentStatus?.status === ConversionStatusEnum.CANCELLED;
  const isFinished = isCompleted || isFailed || isCancelled;

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
        {/* File Upload Area */}
        <div
          {...getRootProps()}
          className={`dropzone ${isDragActive ? 'drag-active' : ''} ${selectedFile ? 'file-selected' : ''} ${isProcessing || isCompleted ? 'disabled-dropzone' : ''}`}
        >
          <input {...getInputProps()} aria-label="File upload" disabled={isProcessing || isCompleted} />

          {isFinished ? ( // Displayed after completion/failure/cancellation
            <div className="upload-prompt">
              <div className="upload-icon">🎉</div> {/* Or other relevant icon */}
              <h3>{getStatusMessage()}</h3>
              <button type="button" className="browse-button" onClick={resetConversionState}>
                Start New Conversion
              </button>
            </div>
          ) : selectedFile ? ( // Displayed when a file is selected
            <div className="file-preview">
              <div className="file-icon">📦</div>
              <div className="file-info">
                <div className="file-name">{selectedFile.name}</div>
                <div className="file-size">{(selectedFile.size / 1024 / 1024).toFixed(2)} MB</div>
                <div className="status">{getStatusMessage()}</div>
              </div>
              <button
                type="button"
                className="remove-file"
                onClick={(e) => {
                  e.stopPropagation();
                  if (!isProcessing && !isCompleted) setSelectedFile(null);
                }}
                disabled={isProcessing || isCompleted}
              >
                ✕
              </button>
            </div>
          ) : ( // Initial state of the dropzone
            <div className="upload-prompt initial-prompt">
              <div className="upload-icon-large">☁️</div>
              <h3>Drag & drop your modpack here</h3>
              {/* Clicking this button will open the file dialog */}
              <button
                type="button"
                className="browse-button"
                onClick={() => {
                  // Hack to trigger file input:
                  // Query for the input element and click it.
                  // This assumes the input element is a descendant of the form.
                  // A more robust solution might involve passing a ref from getInputProps.
                  const fileInput = document.querySelector('input[type="file"][aria-label="File upload"]');
                  if (fileInput instanceof HTMLElement) {
                    fileInput.click();
                  }
                }}
                disabled={isProcessing || isCompleted}
              >
                Browse Files
              </button>
              <p className="supporting-text">Supports .jar files and .zip modpack archives</p>
            </div>
          )}
        </div>

        {/* URL Input Section - appears below drag-and-drop */}
        {/* Hide if file selected or in finished states */}
        {!selectedFile && !isFinished && (
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
              disabled={!!selectedFile || isProcessing || isCompleted}
            />
            <div className="supported-sites">
              <span>Supported: CurseForge • Modrinth</span>
            </div>
          </div>
        )}

        {/* Configuration Options - appears below URL input */}
        {/* Hide on final states */}
        {!isFinished && (
          <div className={`conversion-options ${isProcessing || isCompleted ? 'disabled-options' : ''}`}>
            <div className="option-group">
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={smartAssumptions}
                  onChange={(e) => setSmartAssumptions(e.target.checked)}
                  disabled={isProcessing || isCompleted}
                />
                <span className="checkmark"></span>
                Enable Smart Assumptions
                <button
                  type="button"
                  className="info-button"
                  onClick={() => setShowSmartAssumptionsInfo(!showSmartAssumptionsInfo)}
                  aria-label="Learn more about smart assumptions"
                  disabled={isProcessing || isCompleted}
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
                  disabled={isProcessing || isCompleted}
                />
                <span className="checkmark"></span>
                Include Dependencies
              </label>
            </div>
          </div>
        )}

        {/* Progress Display - appears when isProcessing is true */}
        {isProcessing && currentStatus && (
          <ConversionProgress
            jobId={currentConversionId}
            status={currentStatus.status}
            progress={progressPercentage}
            message={currentStatus.message}
            stage={currentStatus.stage}
          />
        )}

        {/* Action Buttons - appears below configuration options or progress display */}
        <div className="action-buttons">
          {!isFinished && (
            <>
              <button
                type="submit"
                className="convert-button" // Assuming this class will be styled for "Upload"
                disabled={isProcessing || (!selectedFile && !modUrl)}
              >
                {isProcessing ? 'Uploading...' : 'Upload'}
              </button>
              
              {isProcessing && (
                <button
                  type="button"
                  className="cancel-button"
                  onClick={handleCancel}
                >
                  Cancel
                </button>
              )}
            </>
          )}
          
          {isCompleted && (
            <button
              type="button"
              className="download-button"
              onClick={handleDownload}
            >
              Download Converted Mod
            </button>
          )}
        </div>
      </form>
    </div>
  );
};