import React, { useState, useEffect, useRef, useCallback } from 'react';
import { ConversionStatus } from '../../types/api';
import { getConversionStatus } from '../../services/api'; // Import the API service
import './ConversionProgress.css';

// Define the props for the component
export interface ConversionProgressProps {
  jobId: string | null;
  status?: string;
  progress?: number;
  message?: string;
  stage?: string | null;
}

// Helper function to format seconds into minutes and seconds
const formatTime = (totalSeconds: number | undefined | null): string => {
  if (totalSeconds === undefined || totalSeconds === null || totalSeconds < 0) {
    return 'N/A';
  }
  if (totalSeconds === 0) {
    return '0s';
  }
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  let formattedTime = '';
  if (minutes > 0) {
    formattedTime += `${minutes}m `;
  }
  formattedTime += `${seconds}s`;
  return formattedTime.trim();
};

const ConversionProgress: React.FC<ConversionProgressProps> = ({
  jobId,
  status,
  progress,
  message,
  stage
}) => {
  // Initialize all hooks first before any early returns
  const [progressData, setProgressData] = useState<ConversionStatus>({
    job_id: jobId || '',
    status: status || 'queued',
    progress: progress || 0,
    message: message || 'Processing...',
    stage: stage || 'Queued',
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

  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
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

  const progressBarFillerClass = progressData.progress === 100
    ? "progress-bar-filler completed"
    : "progress-bar-filler";

  let statusMessage = progressData.message;
  if (connectionError && !usingWebSocket) {
    statusMessage = connectionError;
  } else if (usingWebSocket) {
    statusMessage = `Connected via WebSocket. ${progressData.message}`;
  }


  return (
    <div className="conversion-progress-container">
      <h4>Conversion Progress (ID: {jobId})</h4>
      <p><i>{usingWebSocket ? 'Real-time updates active' : 'Using fallback polling'}</i></p>
      {connectionError && <p className="error-message">Connection issue: {connectionError}</p>}

      <div className="progress-info">
        <p><strong>Status:</strong> {progressData.status}</p>
        <p><strong>Stage:</strong> {progressData.stage || 'N/A'}</p>
        <p><strong>Message:</strong> {statusMessage}</p>
        <p><strong>Estimated Time Remaining:</strong> {formatTime(progressData.estimated_time_remaining)}</p>
      </div>

      <div className="progress-bar-container">
        <div
          className={progressBarFillerClass}
          style={{ width: `${progressData.progress}%` }}
          role="progressbar"
          aria-valuenow={progressData.progress}
          aria-valuemin={0}
          aria-valuemax={100}
        >
          {progressData.progress}%
        </div>
      </div>

      {progressData.status === 'completed' && progressData.result_url && (
        <button onClick={handleDownload} className="download-button">
          Download Converted File
        </button>
      )}

      {progressData.status === 'failed' && (
        <div className="error-message">
          <p><strong>Error:</strong> {progressData.error || 'An unknown error occurred.'}</p>
          <p>Details: {progressData.message}</p>
        </div>
      )}
    </div>
  );
};

export default ConversionProgress;
