/**
 * Conversion Flow Manager
 * Orchestrates the complete upload-to-download experience
 * Handles state management, progress tracking, and error recovery
 */

import React, { useState, useCallback, useEffect, useRef } from 'react';
import { ConversionUploadEnhanced } from '../ConversionUpload/ConversionUploadEnhanced';
import ConversionProgress from '../ConversionProgress/ConversionProgress';
import { ConversionReportContainer } from '../ConversionReport/ConversionReportContainer';
import { downloadResult } from '../../services/api';
import './ConversionFlowManager.css';

export interface ConversionFlowState {
  jobId: string | null;
  filename: string;
  status: 'idle' | 'uploading' | 'converting' | 'completed' | 'failed' | 'cancelled';
  progress: number;
  error: string | null;
  resultUrl: string | null;
}

interface ConversionFlowManagerProps {
  onComplete?: (jobId: string, filename: string) => void;
  onError?: (error: string) => void;
  showReport?: boolean;
  autoReset?: boolean;
  resetDelay?: number;
}

export const ConversionFlowManager: React.FC<ConversionFlowManagerProps> = ({
  onComplete,
  onError,
  showReport = true,
  autoReset = false,
  resetDelay = 30000
}) => {
  const [flowState, setFlowState] = useState<ConversionFlowState>({
    jobId: null,
    filename: '',
    status: 'idle',
    progress: 0,
    error: null,
    resultUrl: null
  });

  const [currentStatus, setCurrentStatus] = useState<any>(null);
  const resetTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Clear any pending reset timeout
  useEffect(() => {
    return () => {
      if (resetTimeoutRef.current) {
        clearTimeout(resetTimeoutRef.current);
      }
    };
  }, []);

  // Reset flow state
  const resetFlow = useCallback(() => {
    if (resetTimeoutRef.current) {
      clearTimeout(resetTimeoutRef.current);
      resetTimeoutRef.current = null;
    }

    setFlowState({
      jobId: null,
      filename: '',
      status: 'idle',
      progress: 0,
      error: null,
      resultUrl: null
    });
    setCurrentStatus(null);
  }, []);

  // Handle conversion start
  const handleConversionStart = useCallback((jobId: string, filename: string) => {
    console.log('[ConversionFlow] Started:', jobId, filename);

    setFlowState({
      jobId,
      filename,
      status: 'converting',
      progress: 0,
      error: null,
      resultUrl: null
    });
  }, []);

  // Handle conversion complete
  const handleConversionComplete = useCallback((jobId: string) => {
    console.log('[ConversionFlow] Completed:', jobId);

    setFlowState(prev => ({
      ...prev,
      status: 'completed',
      progress: 100,
      resultUrl: `/api/v1/conversions/${jobId}/download`
    }));

    if (onComplete) {
      onComplete(jobId, flowState.filename);
    }

    // Auto-reset if enabled
    if (autoReset) {
      resetTimeoutRef.current = setTimeout(() => {
        resetFlow();
      }, resetDelay);
    }
  }, [flowState.filename, onComplete, autoReset, resetDelay, resetFlow]);

  // Handle conversion failed
  const handleConversionFailed = useCallback((jobId: string, error: string) => {
    console.error('[ConversionFlow] Failed:', jobId, error);

    setFlowState(prev => ({
      ...prev,
      status: 'failed',
      error
    }));

    if (onError) {
      onError(error);
    }
  }, [onError]);

  // Handle manual download
  const handleDownload = useCallback(async () => {
    if (!flowState.jobId) return;

    try {
      const { blob, filename } = await downloadResult(flowState.jobId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error: any) {
      console.error('[ConversionFlow] Download failed:', error);
      setFlowState(prev => ({
        ...prev,
        error: `Download failed: ${error.message || 'Unknown error'}`
      }));
    }
  }, [flowState.jobId]);

  // Render upload component when idle
  if (flowState.status === 'idle') {
    return (
      <div className="conversion-flow-manager">
        <ConversionUploadEnhanced
          onConversionStart={handleConversionStart}
          onConversionComplete={handleConversionComplete}
          onConversionFailed={handleConversionFailed}
        />
      </div>
    );
  }

  // Render progress during conversion
  if (flowState.status === 'uploading' || flowState.status === 'converting') {
    return (
      <div className="conversion-flow-manager">
        <div className="conversion-flow-progress">
          <div className="flow-header">
            <h2>Converting {flowState.filename}</h2>
            <button
              className="reset-button"
              onClick={resetFlow}
              title="Cancel and start over"
            >
              ✕
            </button>
          </div>

          {currentStatus && (
            <ConversionProgress
              jobId={flowState.jobId}
              status={currentStatus.status}
              progress={currentStatus.progress}
              message={currentStatus.message}
              stage={currentStatus.stage}
            />
          )}

          {/* Progress Summary */}
          <div className="progress-summary">
            <div className="summary-item">
              <span className="label">Status:</span>
              <span className="value">{flowState.status}</span>
            </div>
            {flowState.jobId && (
              <div className="summary-item">
                <span className="label">Job ID:</span>
                <span className="value mono">{flowState.jobId}</span>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  // Render completion screen
  if (flowState.status === 'completed') {
    return (
      <div className="conversion-flow-manager">
        <div className="conversion-flow-complete">
          <div className="success-animation">
            <div className="checkmark">✓</div>
          </div>

          <h2>Conversion Complete!</h2>
          <p className="filename">{flowState.filename}</p>

          <div className="action-buttons">
            <button className="download-button primary" onClick={handleDownload}>
              <span className="icon">⬇</span>
              Download .mcaddon
            </button>

            {showReport && flowState.jobId && (
              <button
                className="report-button secondary"
                onClick={() => {
                  // Scroll to report
                  const reportElement = document.getElementById(`conversion-report-${flowState.jobId}`);
                  if (reportElement) {
                    reportElement.scrollIntoView({ behavior: 'smooth' });
                  }
                }}
              >
                <span className="icon">📋</span>
                View Report
              </button>
            )}

            <button className="reset-button tertiary" onClick={resetFlow}>
              <span className="icon">🔄</span>
              Convert Another
            </button>
          </div>

          {showReport && flowState.jobId && (
            <div id={`conversion-report-${flowState.jobId}`} className="flow-report">
              <ConversionReportContainer
                jobId={flowState.jobId}
                jobStatus="completed"
              />
            </div>
          )}

          {autoReset && (
            <div className="auto-reset-notice">
              Page will reset in {Math.ceil(resetDelay / 1000)} seconds...
            </div>
          )}
        </div>
      </div>
    );
  }

  // Render error screen
  if (flowState.status === 'failed') {
    return (
      <div className="conversion-flow-manager">
        <div className="conversion-flow-error">
          <div className="error-animation">
            <div className="error-icon">✕</div>
          </div>

          <h2>Conversion Failed</h2>
          <p className="filename">{flowState.filename}</p>

          {flowState.error && (
            <div className="error-message">
              <strong>Error:</strong>
              <p>{flowState.error}</p>
            </div>
          )}

          <div className="error-tips">
            <h4>What you can try:</h4>
            <ul>
              <li>Check that the file is a valid .jar or .zip archive</li>
              <li>Ensure the file is not corrupted</li>
              <li>Try enabling "Smart Assumptions" for better compatibility</li>
              <li>For large modpacks, try converting with fewer mods first</li>
            </ul>
          </div>

          <div className="action-buttons">
            <button className="retry-button primary" onClick={resetFlow}>
              <span className="icon">🔄</span>
              Try Again
            </button>

            {flowState.jobId && (
              <button
                className="report-button secondary"
                onClick={() => {
                  // Even failed conversions might have partial reports
                  const reportElement = document.getElementById(`conversion-report-${flowState.jobId}`);
                  if (reportElement) {
                    reportElement.scrollIntoView({ behavior: 'smooth' });
                  }
                }}
              >
                <span className="icon">📋</span>
                View Partial Report
              </button>
            )}
          </div>

          {showReport && flowState.jobId && (
            <div id={`conversion-report-${flowState.jobId}`} className="flow-report">
              <ConversionReportContainer
                jobId={flowState.jobId}
                jobStatus="failed"
              />
            </div>
          )}
        </div>
      </div>
    );
  }

  // Render cancelled screen
  if (flowState.status === 'cancelled') {
    return (
      <div className="conversion-flow-manager">
        <div className="conversion-flow-cancelled">
          <h2>Conversion Cancelled</h2>
          <p>The conversion was cancelled.</p>

          <button className="reset-button primary" onClick={resetFlow}>
            Start New Conversion
          </button>
        </div>
      </div>
    );
  }

  return null;
};

export default ConversionFlowManager;
