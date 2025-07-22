import React, { useState, useEffect, useRef, useCallback } from 'react';
import { ConversionStatus } from '../../types/api';
import { getConversionStatus } from '../../services/api'; // Import the API service
import './ConversionProgress.css';
// SVG icons as inline components for better compatibility
const CheckmarkIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="14px" height="14px">
    <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
  </svg>
);

const PendingIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="14px" height="14px">
    <circle cx="12" cy="12" r="10"/>
  </svg>
);

// Define the props for the component
export interface ConversionProgressProps {
  jobId: string | null;
  status?: string;
  progress?: number;
  message?: string;
  stage?: string | null;
}


const ConversionProgress: React.FC<ConversionProgressProps> = ({
  jobId,
  status,
  progress,
  message,
  stage
}) => {
  // Define the steps for the conversion process
  const conversionSteps = ["Queued", "Processing", "Completed"];

  // Initialize all hooks first before any early returns
  const [progressData, setProgressData] = useState<ConversionStatus>({
    job_id: jobId || '',
    status: status || 'queued',
    progress: progress || 0,
    message: message || 'Processing...',
    stage: stage || 'Queued', // Default to 'Queued'
    estimated_time_remaining: null,
    result_url: null,
    error: null,
    created_at: new Date().toISOString(),
  });

  const [usingWebSocket, setUsingWebSocket] = useState<boolean>(false);
  const [connectionError, setConnectionError] = useState<string | null>(null);

  const webSocketRef = useRef<WebSocket | null>(null);
  const pollingIntervalRef = useRef<number | null>(null);
  const currentStatusRef = useRef<string>('queued');

  const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';
  const WS_BASE_URL = API_BASE_URL.replace(/^http/, 'ws');

  const stopPolling = () => {
    if (pollingIntervalRef.current) {
      window.clearInterval(pollingIntervalRef.current);
      pollingIntervalRef.current = null;
      console.log('Polling stopped.');
    }
  };

  const updateProgressData = useCallback((newData: ConversionStatus) => {
    setProgressData(newData);
    currentStatusRef.current = newData.status;
    if (newData.status === 'completed' || newData.status === 'failed' || newData.status === 'cancelled') {
      console.log(`Conversion ended with status: ${newData.status}. Cleaning up connections.`);
      if (webSocketRef.current && webSocketRef.current.readyState === WebSocket.OPEN) {
        webSocketRef.current.close(1000, `Conversion ${newData.status}`);
      }
      if (pollingIntervalRef.current) {
        window.clearInterval(pollingIntervalRef.current);
        pollingIntervalRef.current = null;
      }
      setUsingWebSocket(false); // Ensure this is reset
    }
  }, []);

  const startPolling = useCallback(() => {
    // Prevent multiple polling intervals
    stopPolling();
    console.log(`WebSocket failed or not supported. Falling back to polling for ${jobId}.`);
    setUsingWebSocket(false);

    pollingIntervalRef.current = window.setInterval(async () => {
      try {
        const status = await getConversionStatus(jobId);
        console.log('Polling: Fetched status:', status);
        updateProgressData(status);
        setConnectionError(null); // Clear previous errors if polling succeeds
      } catch (error) {
        console.error('Polling error:', error);
        setConnectionError('Failed to fetch conversion status. Retrying...');
        // Optional: Implement max retries for polling or different error handling
      }
    }, 3000); // Poll every 3 seconds
  }, [jobId, updateProgressData]);

  useEffect(() => {
    // Cleanup function to be called when component unmounts or conversionId changes
    const cleanup = () => {
      console.log(`Cleaning up resources for conversion ID: ${jobId}`);
      if (webSocketRef.current) {
        webSocketRef.current.onclose = null; // Avoid triggering onclose logic during cleanup
        webSocketRef.current.onerror = null;
        webSocketRef.current.close(1000, 'Component unmounting or ID changed');
        webSocketRef.current = null;
      }
      stopPolling();
      setProgressData({ // Reset state
        job_id: jobId, status: status || 'queued', progress: progress || 0, message: message || 'Initializing...',
        stage: stage || 'Queued', estimated_time_remaining: null, result_url: null, error: null,
        created_at: new Date().toISOString(),
      });
      setUsingWebSocket(false);
      setConnectionError(null);
    };

    cleanup(); // Clean up previous connection/polling before starting new one

    const connectWebSocket = () => {
      const wsUrl = `${WS_BASE_URL}/ws/v1/convert/${jobId}/progress`;
      console.log(`Attempting to connect WebSocket: ${wsUrl}`);
      const ws = new WebSocket(wsUrl);
      webSocketRef.current = ws;

      ws.onopen = () => {
        console.log(`WebSocket connected for ${jobId}`);
        setUsingWebSocket(true);
        setConnectionError(null); // Clear any previous errors
        stopPolling(); // Stop polling if WebSocket connects successfully
        // Optionally, fetch initial status once via HTTP to ensure no missed updates
        getConversionStatus(jobId).then(updateProgressData).catch(console.error);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data as string);
          // The server sends the full ConversionStatus object as a JSON string
          console.log('WebSocket message received:', data);
          updateProgressData(data as ConversionStatus);
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      ws.onerror = (error) => {
        console.error(`WebSocket error for ${jobId}:`, error);
        // Don't setConnectionError here, as onclose will handle fallback
        // ws.close(); // Ensure it's closed if not already
      };

      ws.onclose = (event) => {
        console.log(`WebSocket closed for ${jobId}. Code: ${event.code}, Reason: ${event.reason}`);
        webSocketRef.current = null; // Clear the ref
        // Only start polling if the closure was unexpected and not a terminal state
        if (currentStatusRef.current !== 'completed' && currentStatusRef.current !== 'failed' && currentStatusRef.current !== 'cancelled') {
            setConnectionError('WebSocket connection lost. Attempting to use polling.');
            startPolling();
        } else {
            setUsingWebSocket(false); // Ensure this is reset for terminal states
        }
      };
    };

    // Initial connection attempt
    connectWebSocket();

    return cleanup; // Return the cleanup function

  }, [jobId, WS_BASE_URL, updateProgressData, startPolling, message, progress, stage, status]); // Re-run effect if dependencies change

  if (!jobId) {
    return (
      <div className="conversion-progress-container">
        <p>No conversion in progress</p>
      </div>
    );
  }

  const handleDownload = () => {
    if (progressData.result_url) {
      const downloadUrl = progressData.result_url.startsWith('http')
        ? progressData.result_url
        : `${API_BASE_URL}${progressData.result_url}`;
      window.open(downloadUrl, '_blank');
    }
  };

  let statusMessage = progressData.message;
  if (connectionError && !usingWebSocket) {
    statusMessage = connectionError;
  } else if (usingWebSocket && progressData.message) {
    statusMessage = `Connected via WebSocket. ${progressData.message}`;
  } else if (usingWebSocket) {
    statusMessage = "Connected via WebSocket. Processing..."
  }


  // Determine the current step index
  // This is a simplified mapping. A more robust solution might be needed.
  let currentStepIndex = conversionSteps.indexOf(progressData.stage || "Queued");
  if (currentStepIndex === -1) {
    if (progressData.status === 'completed') {
      currentStepIndex = conversionSteps.length -1;
    } else if (progressData.status === 'failed' || progressData.status === 'cancelled') {
      // Handle error/cancelled state - perhaps show all steps as pending or a specific error step
      // For now, let's assume it stays at the last known stage or resets.
      // Or find the last non-completed step if stages are dynamic from backend.
      // Setting to 0 for now if stage is unknown and not completed/failed.
      currentStepIndex = 0; // Default to first step if stage is unrecognized
    } else {
      currentStepIndex = 0; // Default for unknown stages if not terminal
    }
  }
  // If status is 'completed', all steps up to "Completed" are done.
  // If status is 'failed', we might want to show the step it failed on.
  // For this implementation, 'Completed' stage implies all steps are done.
  if (progressData.status === 'completed') {
    currentStepIndex = conversionSteps.indexOf("Completed");
  }


  return (
    <div className="conversion-progress-container">
      <h4>Conversion Progress</h4>
      
      {/* Connection Status Indicator */}
      <div className="connection-status">
        <div className={`connection-indicator ${usingWebSocket ? '' : 'polling'}${connectionError ? ' error' : ''}`}></div>
        <span>{usingWebSocket ? 'Real-time updates' : connectionError ? 'Connection issues' : 'Polling updates'}</span>
      </div>

      {/* Progress Steps */}
      <ul className="conversion-steps-list">
        {conversionSteps.map((step, index) => {
          // Determine step completion status
          let stepCompleted = index < currentStepIndex;
          if (progressData.status === 'completed' && step === "Completed") {
            stepCompleted = true;
          }
          
          // Determine if this is the current/active step
          const isCurrent = index === currentStepIndex && progressData.status !== 'completed' && progressData.status !== 'failed';

          return (
            <li key={step} className={`conversion-step ${isCurrent ? 'current' : ''} ${stepCompleted ? 'completed' : 'pending'}`}>
              <div className="step-icon">
                {stepCompleted ? <CheckmarkIcon /> : <PendingIcon />}
              </div>
              <div className="step-name">{step}</div>
            </li>
          );
        })}
      </ul>

      {/* Overall Progress Bar */}
      <div className="progress-bar-container">
        <div 
          className="progress-bar-fill" 
          style={{ width: `${Math.min(progressData.progress, 100)}%` }}
        ></div>
      </div>

      {/* Status Message */}
      {statusMessage && (
        <div className="status-message">
          <strong>Status:</strong> {statusMessage}
        </div>
      )}

      {/* Connection Error */}
      {connectionError && (
        <div className="connection-error-message">
          <strong>Connection Issue:</strong> {connectionError}
        </div>
      )}

      {/* Download Button */}
      {progressData.status === 'completed' && progressData.result_url && (
        <button onClick={handleDownload} className="download-button">
          <span>📥</span>
          Download Converted File
        </button>
      )}

      {/* Error Display */}
      {progressData.status === 'failed' && (
        <div className="error-message">
          <p><strong>Conversion Failed:</strong> {progressData.error || 'An unknown error occurred.'}</p>
          {progressData.message && progressData.message !== progressData.error && (
            <p><strong>Details:</strong> {progressData.message}</p>
          )}
        </div>
      )}
    </div>
  );
};

export default ConversionProgress;
