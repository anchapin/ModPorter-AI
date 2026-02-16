/**
 * Error Boundary Component - Day 5 Enhancement
 * Catches JavaScript errors and provides user-friendly error handling
 */

import React, { Component, ErrorInfo, ReactNode } from 'react';
import './ErrorBoundary.css';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null
    };
  }

  static getDerivedStateFromError(error: Error): State {
    // Update state so the next render will show the fallback UI.
    return {
      hasError: true,
      error,
      errorInfo: null
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // You can also log the error to an error reporting service
    console.error('Error caught by boundary:', error, errorInfo);
    
    this.setState({
      error,
      errorInfo
    });

    // Log to backend error service in production
    if (process.env.NODE_ENV === 'production') {
      this.logErrorToService(error, errorInfo);
    }
  }

  private logErrorToService = (error: Error, errorInfo: ErrorInfo) => {
    // In production, send error to logging service
    const errorData = {
      message: error.message,
      stack: error.stack,
      componentStack: errorInfo.componentStack,
      url: window.location.href,
      userAgent: navigator.userAgent,
      timestamp: new Date().toISOString()
    };

    // Example API call to error logging service
    fetch('/api/v1/errors', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(errorData),
    }).catch(err => {
      console.error('Failed to log error to service:', err);
    });
  };

  private handleRetry = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null
    });
  };

  private handleReload = () => {
    window.location.reload();
  };

  private handleReportIssue = () => {
    // Safely extract error message, handling cases where error.message might be an object
    const getErrorMessage = (error: Error | null): string => {
      if (!error) return 'Unknown error occurred';
      
      const message = error.message;
      // Handle case where message is an object (causes "Cannot convert object to primitive value")
      if (typeof message === 'object' && message !== null) {
        try {
          return JSON.stringify(message);
        } catch {
          return 'Error message is an object that could not be stringified';
        }
      }
      return String(message);
    };

    const errorMessage = getErrorMessage(this.state.error);
    const errorStack = this.state.error?.stack ? 
      (typeof this.state.error.stack === 'object' ? JSON.stringify(this.state.error.stack) : this.state.error.stack) 
      : 'No stack trace available';
    
    const errorDetails = `Error: ${errorMessage}\nStack: ${errorStack}`;
    
    const githubUrl = `https://github.com/anchapin/ModPorter-AI/issues/new?title=Frontend Error&body=${encodeURIComponent(errorDetails)}`;
    window.open(githubUrl, '_blank');
  };

  render() {
    if (this.state.hasError) {
      // Custom fallback UI
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="error-boundary">
          <div className="error-container">
            <div className="error-icon">💥</div>
            <h1 className="error-title">Oops! Something went wrong</h1>
            <p className="error-description">
              We encountered an unexpected error. Don't worry, your data is safe.
            </p>
            
            <div className="error-actions">
              <button 
                className="error-btn primary"
                onClick={this.handleRetry}
              >
                🔄 Try Again
              </button>
              
              <button 
                className="error-btn secondary"
                onClick={this.handleReload}
              >
                🔃 Reload Page
              </button>
              
              <button 
                className="error-btn outline"
                onClick={this.handleReportIssue}
              >
                🐛 Report Issue
              </button>
            </div>

            {/* Error Details (Development only) */}
            {process.env.NODE_ENV === 'development' && this.state.error && (
              <details className="error-details">
                <summary>🔍 Error Details (Development)</summary>
                <div className="error-stack">
                  <h4>Error Message:</h4>
                  <pre>{typeof this.state.error.message === 'object' ? JSON.stringify(this.state.error.message) : String(this.state.error.message)}</pre>
                  
                  <h4>Stack Trace:</h4>
                  <pre>{typeof this.state.error.stack === 'object' ? JSON.stringify(this.state.error.stack) : String(this.state.error.stack)}</pre>
                  
                  {this.state.errorInfo && (
                    <>
                      <h4>Component Stack:</h4>
                      <pre>{typeof this.state.errorInfo.componentStack === 'object' ? JSON.stringify(this.state.errorInfo.componentStack) : String(this.state.errorInfo.componentStack)}</pre>
                    </>
                  )}
                </div>
              </details>
            )}
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

// Hook version for functional components
// eslint-disable-next-line react-refresh/only-export-components
export const useErrorHandler = () => {
  const [error, setError] = React.useState<Error | null>(null);

  const resetError = React.useCallback(() => {
    setError(null);
  }, []);

  const handleError = React.useCallback((error: Error) => {
    console.error('Error caught by hook:', error);
    setError(error);
  }, []);

  React.useEffect(() => {
    if (error) {
      throw error;
    }
  }, [error]);

  return { handleError, resetError };
};

// Higher-order component for error handling
// eslint-disable-next-line react-refresh/only-export-components
export const withErrorBoundary = <P extends object>(
  Component: React.ComponentType<P>,
  fallback?: ReactNode
) => {
  const WrappedComponent = (props: P) => (
    <ErrorBoundary fallback={fallback}>
      <Component {...props} />
    </ErrorBoundary>
  );

  WrappedComponent.displayName = `withErrorBoundary(${Component.displayName || Component.name})`;
  return WrappedComponent;
};

export default ErrorBoundary;