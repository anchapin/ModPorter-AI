import React, { useEffect, useState } from 'react';
import { ConversionStatus } from '../../types/api';
import { useProgress } from '../../contexts/ProgressContext';
import { ConnectionStatusIndicator } from '../ui/ConnectionStatusIndicator';
import { ProgressErrorBoundary } from '../ErrorBoundary/ProgressErrorBoundary';
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

const SpinnerIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="14px" height="14px" className="spinner-icon">
    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8z" opacity="0.3"/>
    <path d="M12 2v4c3.31 0 6 2.69 6 6h4c0-5.52-4.48-10-10-10z"/>
  </svg>
);

// Agent status interface for detailed tracking
interface AgentStatus {
  name: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress: number;
  message?: string;
}

// Extended conversion status with agent details
interface ExtendedConversionStatus extends ConversionStatus {
  agents?: AgentStatus[];
  current_agent?: string;
}

// Define the props for the component
export interface ConversionProgressProps {
  jobId: string | null;
  status?: string;
  progress?: number;
  message?: string;
  stage?: string | null;
}

/**
 * ConversionProgress Component - Inner Component
 * This component uses the ProgressContext for state management and WebSocket integration
 */
const ConversionProgressInner: React.FC<ConversionProgressProps> = ({
  jobId,
  status: initialStatus,
  progress: initialProgress,
  message: initialMessage,
  stage: initialStage
}) => {
  const { state, actions } = useProgress();

  // Local state for agents
  const [agents, setAgents] = useState<AgentStatus[]>([]);

  // Define the steps for the conversion process
  const conversionSteps = ["Queued", "Processing", "Completed"];

  // Initialize progress data from props or context
  const progressData: ConversionStatus = state.status || {
    job_id: jobId || '',
    status: initialStatus || 'queued',
    progress: initialProgress || 0,
    message: initialMessage || 'Processing...',
    stage: initialStage || 'Queued',
    estimated_time_remaining: null,
    result_url: null,
    error: null,
    created_at: new Date().toISOString(),
  };

  // Connect to WebSocket when jobId changes
  useEffect(() => {
    if (jobId && jobId !== state.status?.job_id) {
      actions.connectToJob(jobId);
    }

    return () => {
      if (jobId && !state.status?.job_id) {
        actions.disconnectFromJob();
      }
    };
  }, [jobId, state.status?.job_id, actions]);

  // Extract agent information from extended status
  useEffect(() => {
    if (state.status) {
      const extendedData = state.status as ExtendedConversionStatus;
      if (extendedData.agents) {
        setAgents(extendedData.agents);
      }
    }
  }, [state.status]);

  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8080';

  const handleDownload = () => {
    if (progressData.result_url) {
      const downloadUrl = progressData.result_url.startsWith('http')
        ? progressData.result_url
        : `${API_BASE_URL}${progressData.result_url}`;
      window.open(downloadUrl, '_blank');
    }
  };

  const handleReconnect = () => {
    if (jobId) {
      actions.connectToJob(jobId);
    }
  };

  let statusMessage = progressData.message;
  if (state.connectionError && !state.usingWebSocket) {
    statusMessage = state.connectionError;
  } else if (state.usingWebSocket && progressData.message) {
    statusMessage = `Connected via WebSocket. ${progressData.message}`;
  } else if (state.usingWebSocket) {
    statusMessage = "Connected via WebSocket. Processing..."
  }

  // Determine the current step index
  let currentStepIndex = conversionSteps.indexOf(progressData.stage || "Queued");
  if (currentStepIndex === -1) {
    if (progressData.status === 'completed') {
      currentStepIndex = conversionSteps.length - 1;
    } else if (progressData.status === 'failed' || progressData.status === 'cancelled') {
      currentStepIndex = 0;
    } else {
      currentStepIndex = 0;
    }
  }
  if (progressData.status === 'completed') {
    currentStepIndex = conversionSteps.indexOf("Completed");
  }

  if (!jobId) {
    return (
      <div className="conversion-progress-container">
        <p>No conversion in progress</p>
      </div>
    );
  }

  return (
    <div className="conversion-progress-container">
      <h4>Conversion Progress{jobId ? ` (ID: ${jobId})` : ''}</h4>

      {/* Connection Status Indicator */}
      <div className="connection-status">
        <ConnectionStatusIndicator
          status={state.connectionStatus}
          usingWebSocket={state.usingWebSocket}
          error={state.connectionError}
          onClick={handleReconnect}
        />
      </div>

      {/* Progress Steps */}
      <ul className="conversion-steps-list">
        {conversionSteps.map((step, index) => {
          let stepCompleted = index < currentStepIndex;
          if (progressData.status === 'completed' && step === "Completed") {
            stepCompleted = true;
          }

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

      {/* Agent-Level Progress (if available) */}
      {agents.length > 0 && (
        <div className="agents-progress">
          <h5>Agent Progress</h5>
          <div className="agents-list">
            {agents.map((agent, index) => (
              <div key={index} className={`agent-item agent-${agent.status}`}>
                <div className="agent-header">
                  <div className="agent-icon">
                    {agent.status === 'completed' && <CheckmarkIcon />}
                    {agent.status === 'running' && <SpinnerIcon />}
                    {agent.status === 'pending' && <PendingIcon />}
                    {agent.status === 'failed' && <span className="error-icon">✕</span>}
                  </div>
                  <span className="agent-name">{agent.name}</span>
                  <span className="agent-status">{agent.status}</span>
                </div>
                {agent.status === 'running' && (
                  <div className="agent-progress-bar">
                    <div
                      className="agent-progress-fill"
                      style={{ width: `${Math.min(agent.progress, 100)}%` }}
                    />
                  </div>
                )}
                {agent.message && (
                  <div className="agent-message">{agent.message}</div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Overall Progress Bar */}
      <div className="progress-bar-container">
        <div
          className={`progress-bar-fill ${progressData.status === 'completed' ? 'progress-bar-filler' : ''}`}
          role="progressbar"
          aria-valuenow={Math.min(progressData.progress, 100)}
          aria-valuemin="0"
          aria-valuemax="100"
          style={{ width: `${Math.min(progressData.progress, 100)}%` }}
        >
          {Math.round(Math.min(progressData.progress, 100))}%
        </div>
      </div>

      {/* Status Message */}
      <div className="status-message">
        <strong>Status:</strong> {progressData.status}
      </div>

      {/* Stage Information */}
      {progressData.stage && (
        <div className="stage-message">
          <strong>Stage:</strong> {progressData.stage}
        </div>
      )}

      {/* Estimated Time Remaining */}
      <div className="time-remaining">
        <strong>Estimated Time Remaining:</strong> {progressData.estimated_time_remaining || 'N/A'}
      </div>

      {statusMessage && statusMessage !== progressData.status && progressData.status !== 'failed' && (
        <div className="additional-message">
          <strong>Message:</strong> {statusMessage}
        </div>
      )}

      {/* Connection Error */}
      {state.connectionError && (
        <div className="connection-error-message">
          <strong>Connection Issue:</strong> {state.connectionError}
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
          <p><strong>Error:</strong> {progressData.error || progressData.message || 'An unknown error occurred.'}</p>
          {progressData.message && progressData.message !== progressData.error && progressData.error && (
            <p><strong>Details:</strong> {progressData.message}</p>
          )}
        </div>
      )}
    </div>
  );
};

/**
 * ConversionProgress Component - Wrapped with ProgressErrorBoundary
 * This is the exported component that should be used
 */
const ConversionProgress: React.FC<ConversionProgressProps> = (props) => {
  return (
    <ProgressErrorBoundary progressActions={undefined}>
      <ConversionProgressInner {...props} />
    </ProgressErrorBoundary>
  );
};

export default ConversionProgress;
