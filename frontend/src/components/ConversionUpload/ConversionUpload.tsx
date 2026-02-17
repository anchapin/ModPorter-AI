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
import { parseModUrl, getPlatformInfo } from '../../utils/urlParser';
import './ConversionUpload.css';

// Configuration constants
const MAX_POLLING_ATTEMPTS = 30; // Poll for 30 * 2s = 1 minute
const POLLING_INTERVAL_MS = 2000;
const MAX_FILE_SIZE_MB = 500;

interface ConversionUploadProps {
  onConversionStart?: (jobId: string) => void;
  onConversionComplete?: (jobId: string) => void;
}

// Supported file types and extensions
const SUPPORTED_FILE_TYPES = [
  'application/java-archive',
  'application/zip', 
  'application/x-zip-compressed'
] as const;

const SUPPORTED_EXTENSIONS = ['.jar', '.zip'] as const;

const SUPPORTED_DOMAINS = [
  'curseforge.com',
  'www.curseforge.com',
  'modrinth.com',
  'www.modrinth.com'
] as const;

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

  // File validation with size check
  const validateFile = useCallback((file: File): { isValid: boolean; error?: string } => {
    if (file.size > MAX_FILE_SIZE_MB * 1024 * 1024) {
      return { isValid: false, error: `File too large. Maximum size is ${MAX_FILE_SIZE_MB}MB.` };
    }
    
    const hasValidType = SUPPORTED_FILE_TYPES.some(type => type === file.type);
    const hasValidExtension = SUPPORTED_EXTENSIONS.some(ext => 
      file.name.toLowerCase().endsWith(ext)
    );
    
    const isValid = hasValidType || hasValidExtension;
    return {
      isValid,
      error: isValid ? undefined : 'Unsupported file type. Please upload .jar or .zip files only.'
    };
  }, []);

  // URL validation for supported mod platforms
  const validateUrl = useCallback((url: string): { isValid: boolean; error?: string } => {
    if (!url.trim()) {
      return { isValid: false, error: 'URL cannot be empty.' };
    }
    
    try {
      const urlObj = new URL(url);
      const isValid = SUPPORTED_DOMAINS.some(domain => urlObj.hostname === domain);
      return {
        isValid,
        error: isValid ? undefined : 'Please enter a valid CurseForge or Modrinth URL.'
      };
    } catch {
      return { isValid: false, error: 'Please enter a valid URL.' };
    }
  }, []);

  const resetConversionState = useCallback(() => {
    setSelectedFile(null);
    setModUrl('');
    setCurrentConversionId(null);
    setCurrentStatus(null);
    setProgressPercentage(0);
    setIsPolling(false);
    setPollingAttempts(0);
    setIsConverting(false);
    setError(null);
  }, []);

  const getStatusMessage = useCallback((): string => {
    if (!currentStatus) return 'Ready to convert';
    
    const statusMessages: Record<ConversionStatusEnum, string> = {
      [ConversionStatusEnum.PENDING]: 'Queued for processing...',
      [ConversionStatusEnum.UPLOADING]: 'Uploading file...',
      [ConversionStatusEnum.IN_PROGRESS]: 'Processing...',
      [ConversionStatusEnum.ANALYZING]: 'Analyzing mod structure...',
      [ConversionStatusEnum.CONVERTING]: 'Converting to Bedrock...',
      [ConversionStatusEnum.PACKAGING]: 'Packaging add-on...',
      [ConversionStatusEnum.COMPLETED]: 'Conversion completed!',
      [ConversionStatusEnum.FAILED]: 'Conversion failed',
      [ConversionStatusEnum.CANCELLED]: 'Conversion cancelled'
    };
    
    return statusMessages[currentStatus.status] || currentStatus.message || 'Processing...';
  }, [currentStatus]);

  const onDrop = useCallback((acceptedFiles: File[], rejectedFiles: any[]) => {
    // Handle rejected files first
    if (rejectedFiles.length > 0) {
      setError('Unsupported file type. Please upload .jar or .zip files only.');
      return;
    }
    
    const file = acceptedFiles[0];
    if (!file) return;
    
    const validation = validateFile(file);
    if (!validation.isValid) {
      setError(validation.error!);
      return;
    }
    
    setSelectedFile(file);
    setModUrl(''); // Clear URL if file is selected
    setError(null);
    
    // Reset conversion state when new file is selected
    if (currentConversionId) {
      resetConversionState();
    }
  }, [currentConversionId, validateFile, resetConversionState]);

  const { getRootProps, getInputProps, isDragActive, open } = useDropzone({
    onDrop,
    accept: {
      'application/java-archive': ['.jar'],
      'application/zip': ['.zip'],
      'application/x-zip-compressed': ['.zip']
    },
    maxFiles: 1,
    multiple: false
  });

  const handleUrlChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const url = e.target.value;
    setModUrl(url);
    
    if (url) {
      setSelectedFile(null); // Clear file if URL is entered
      if (currentConversionId) {
        resetConversionState();
      }
    }
    
    // Validate URL on input
    if (url) {
      const validation = validateUrl(url);
      setError(validation.isValid ? null : validation.error!);
    } else {
      setError(null);
    }
  }, [currentConversionId, validateUrl, resetConversionState]);

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
    
    if (modUrl) {
      const urlValidation = validateUrl(modUrl);
      if (!urlValidation.isValid) {
        setError(urlValidation.error!);
        return;
      }
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

  // Polling effect with proper dependency array
  useEffect(() => {
    let intervalId: ReturnType<typeof setInterval> | null = null;

    if (currentConversionId && isPolling) {
      if (pollingAttempts >= MAX_POLLING_ATTEMPTS) {
        // Defer state updates to avoid setting state directly in effect
        setTimeout(() => {
          setError('Conversion is taking longer than expected. Please try cancelling and starting again, or check back later.');
          setIsPolling(false);
          setIsConverting(false);
        }, 0);
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
      }, POLLING_INTERVAL_MS);
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
        <div className="error-message" role="alert" aria-live="polite">
          <span className="error-icon" aria-hidden="true">⚠️</span>
          <span>{error}</span>
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
                aria-label={`Remove ${selectedFile.name}`}
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
                onClick={(e) => {
                  e.stopPropagation();
                  open();
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
            {modUrl && (
              <div className="url-platform-indicator" style={{
                marginTop: '8px',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '8px 12px',
                borderRadius: '6px',
                backgroundColor: getPlatformInfo(parseModUrl(modUrl).platform).bgColor,
                color: getPlatformInfo(parseModUrl(modUrl).platform).color,
                fontSize: '14px',
                fontWeight: 500
              }}>
                {parseModUrl(modUrl).isValid ? (
                  <>
                    <span>{getPlatformInfo(parseModUrl(modUrl).name} detected</span>
                    <span style={{ opacity: 0.7 }}>• {parseModUrl(modUrl).slug}</span>
                  </>
                ) : (
                  <span style={{ color: '#ef4444' }}>Invalid URL - Supported: CurseForge, Modrinth</span>
                )}
              </div>
            )}
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
                  aria-expanded={showSmartAssumptionsInfo}
                  aria-controls="smart-assumptions-info-legacy"
                  disabled={isProcessing || isCompleted}
                >
                  ?
                </button>
              </label>

              {showSmartAssumptionsInfo && (
                <div className="info-panel" id="smart-assumptions-info-legacy">
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