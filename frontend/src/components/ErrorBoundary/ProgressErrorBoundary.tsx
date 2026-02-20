/**
 * Progress Error Boundary - Specialized for Progress Components
 * Catches errors in progress tracking components and provides recovery options
 */

import React, { Component, ErrorInfo, ReactNode } from 'react';
import { ProgressActions } from '../../contexts/ProgressContext';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  progressActions?: ProgressActions; // Optional progress actions for recovery
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
  errorType: 'websocket' | 'state' | 'render' | 'unknown';
}

/**
 * Classify error type based on error message and stack
 */
const classifyError = (error: Error): State['errorType'] => {
  const errorMessage = error.message.toLowerCase();
  const errorStack = error.stack?.toLowerCase() || '';

  if (errorMessage.includes('websocket') || errorMessage.includes('connection')) {
    return 'websocket';
  }
  if (errorMessage.includes('state') || errorMessage.includes('hook') || errorMessage.includes('context')) {
    return 'state';
  }
  if (errorStack.includes('render')) {
    return 'render';
  }
  return 'unknown';
};

export class ProgressErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      errorType: 'unknown'
    };
  }

  static getDerivedStateFromError(error: Error): State {
    return {
      hasError: true,
      error,
      errorInfo: null,
      errorType: classifyError(error)
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('[ProgressErrorBoundary] Error caught:', error, errorInfo);

    this.setState({
      error,
      errorInfo,
      errorType: classifyError(error)
    });

    // Call custom error handler if provided
    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    }

    // Log to backend error service in production
    if (process.env.NODE_ENV === 'production') {
      this.logErrorToService(error, errorInfo);
    }
  }

  private logErrorToService = (error: Error, errorInfo: ErrorInfo) => {
    const errorData = {
      message: error.message,
      stack: error.stack,
      componentStack: errorInfo.componentStack,
      errorType: this.state.errorType,
      url: window.location.href,
      userAgent: navigator.userAgent,
      timestamp: new Date().toISOString(),
      boundary: 'ProgressErrorBoundary'
    };

    fetch('/api/v1/errors', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(errorData),
    }).catch(err => {
      console.error('[ProgressErrorBoundary] Failed to log error to service:', err);
    });
  };

  private handleRetry = () => {
    // Clear progress state if actions are available
    if (this.props.progressActions) {
      this.props.progressActions.clearStatus();
    }

    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
      errorType: 'unknown'
    });
  };

  private handleReconnect = () => {
    // If we have a job ID, try to reconnect
    if (this.props.progressActions && this.state.status?.job_id) {
      this.props.progressActions.connectToJob(this.state.status!.job_id);
    }

    this.handleRetry();
  };

  private getErrorTitle = (): string => {
    switch (this.state.errorType) {
      case 'websocket':
        return 'Connection Error';
      case 'state':
        return 'State Error';
      case 'render':
        return 'Display Error';
      default:
        return 'Progress Error';
    }
  };

  private getErrorDescription = (): string => {
    switch (this.state.errorType) {
      case 'websocket':
        return 'We lost connection to the conversion server. Your conversion may still be running.';
      case 'state':
        return 'There was an issue with the progress tracking state.';
      case 'render':
        return 'We encountered an issue displaying the progress information.';
      default:
        return 'We encountered an unexpected error while tracking conversion progress.';
    }
  };

  private getRecoveryActions = () => {
    const actions = [];

    // Reconnect action for WebSocket errors
    if (this.state.errorType === 'websocket') {
      actions.push({
        label: 'Reconnect',
        action: this.handleReconnect,
        primary: true,
        icon: '🔌'
      });
    }

    // Retry action for all errors
    actions.push({
      label: 'Try Again',
      action: this.handleRetry,
      primary: false,
      icon: '🔄'
    });

    // Reload action as fallback
    actions.push({
      label: 'Reload Page',
      action: () => window.location.reload(),
      primary: false,
      icon: '🔃'
    });

    return actions;
  };

  render() {
    if (!this.state.hasError) {
      return this.props.children;
    }

    // Use custom fallback if provided
    if (this.props.fallback) {
      return this.props.fallback;
    }

    const title = this.getErrorTitle();
    const description = this.getErrorDescription();
    const recoveryActions = this.getRecoveryActions();

    return (
      <div className="progress-error-boundary">
        <div className="progress-error-container">
          <div className="error-icon">
            {this.state.errorType === 'websocket' && '🔌'}
            {this.state.errorType === 'state' && '🔄'}
            {this.state.errorType === 'render' && '🖥️'}
            {this.state.errorType === 'unknown' && '⚠️'}
          </div>

          <h2 className="error-title">{title}</h2>
          <p className="error-description">{description}</p>

          {/* Error Actions */}
          <div className="error-actions">
            {recoveryActions.map((action, index) => (
              <button
                key={index}
                className={`error-btn ${action.primary ? 'primary' : 'secondary'}`}
                onClick={action.action}
              >
                <span className="action-icon">{action.icon}</span>
                {action.label}
              </button>
            ))}
          </div>

          {/* Error Details (Development only) */}
          {process.env.NODE_ENV === 'development' && this.state.error && (
            <details className="error-details">
              <summary>🔍 Error Details (Development)</summary>
              <div className="error-stack">
                <h4>Error Type:</h4>
                <pre>{this.state.errorType}</pre>

                <h4>Error Message:</h4>
                <pre>{String(this.state.error.message)}</pre>

                <h4>Stack Trace:</h4>
                <pre>{String(this.state.error.stack)}</pre>

                {this.state.errorInfo && (
                  <>
                    <h4>Component Stack:</h4>
                    <pre>{String(this.state.errorInfo.componentStack)}</pre>
                  </>
                )}
              </div>
            </details>
          )}
        </div>

        <style jsx>{`
          .progress-error-boundary {
            padding: 20px;
            border-radius: 8px;
            background-color: #fff5f5;
            border: 1px solid #fc8181;
            margin: 16px 0;
          }

          .progress-error-container {
            text-align: center;
          }

          .error-icon {
            font-size: 48px;
            margin-bottom: 16px;
          }

          .error-title {
            font-size: 24px;
            font-weight: bold;
            color: #c53030;
            margin: 0 0 12px 0;
          }

          .error-description {
            color: #4a5568;
            margin-bottom: 24px;
            line-height: 1.5;
          }

          .error-actions {
            display: flex;
            gap: 12px;
            justify-content: center;
            flex-wrap: wrap;
            margin-bottom: 16px;
          }

          .error-btn {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 10px 20px;
            border: 2px solid transparent;
            border-radius: 6px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
          }

          .error-btn.primary {
            background-color: #3182ce;
            color: white;
            border-color: #3182ce;
          }

          .error-btn.primary:hover {
            background-color: #2c5282;
            border-color: #2c5282;
          }

          .error-btn.secondary {
            background-color: white;
            color: #4a5568;
            border-color: #cbd5e0;
          }

          .error-btn.secondary:hover {
            background-color: #f7fafc;
            border-color: #a0aec0;
          }

          .action-icon {
            font-size: 16px;
          }

          .error-details {
            margin-top: 24px;
            text-align: left;
          }

          .error-details summary {
            cursor: pointer;
            color: #4a5568;
            font-weight: 600;
            padding: 8px;
            background-color: #f7fafc;
            border-radius: 4px;
          }

          .error-details summary:hover {
            background-color: #edf2f7;
          }

          .error-stack {
            margin-top: 12px;
            padding: 12px;
            background-color: #2d3748;
            color: #e2e8f0;
            border-radius: 4px;
            overflow-x: auto;
          }

          .error-stack h4 {
            color: #a0aec0;
            margin: 12px 0 8px 0;
            font-size: 12px;
            text-transform: uppercase;
          }

          .error-stack h4:first-child {
            margin-top: 0;
          }

          .error-stack pre {
            font-family: 'Courier New', monospace;
            font-size: 12px;
            line-height: 1.5;
            margin: 0;
            white-space: pre-wrap;
            word-break: break-all;
          }
        `}</style>
      </div>
    );
  }
}

/**
 * Higher-order component to wrap progress components with error boundary
 */
export const withProgressErrorBoundary = <P extends object>(
  Component: React.ComponentType<P>,
  fallback?: ReactNode
) => {
  const WrappedComponent = (props: P) => (
    <ProgressErrorBoundary fallback={fallback}>
      <Component {...props} />
    </ProgressErrorBoundary>
  );

  WrappedComponent.displayName = `withProgressErrorBoundary(${Component.displayName || Component.name})`;
  return WrappedComponent;
};

export default ProgressErrorBoundary;
