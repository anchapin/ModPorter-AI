import React, { Component, ErrorInfo, ReactNode } from 'react';
import {
  Box,
  Typography,
  Button,
  Alert,
  AlertTitle,
  Accordion,
  AccordionSummary,
  AccordionDetails,
} from '@mui/material';
import {
  Error as ErrorIcon,
  Refresh,
  BugReport,
  ExpandMore,
} from '@mui/icons-material';

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
  errorId: string;
}

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
  showRetry?: boolean;
  showDetails?: boolean;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      errorId: '',
    };
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return {
      hasError: true,
      error,
      errorId: `err-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    this.setState({
      error,
      errorInfo,
    });

    // Log error to console in development
    if (process.env.NODE_ENV === 'development') {
      console.error('ErrorBoundary caught an error:', error, errorInfo);
    }

    // Call optional error handler prop
    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    }

    // In production, you might want to send this to an error reporting service
    if (process.env.NODE_ENV === 'production') {
      // Example: sendToErrorReporting(error, errorInfo, this.state.errorId);
    }
  }

  handleRetry = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
      errorId: '',
    });
  };

  render() {
    const { hasError, error, errorInfo, errorId } = this.state;
    const { children, fallback, showRetry = true, showDetails = true } = this.props;

    if (!hasError) {
      return children;
    }

    // Use custom fallback if provided
    if (fallback) {
      return fallback;
    }

    return (
      <Box
        sx={{
          p: 3,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          minHeight: '400px',
        }}
      >
        <Alert
          severity="error"
          icon={<ErrorIcon />}
          sx={{
            width: '100%',
            maxWidth: '800px',
            mb: 2,
          }}
        >
          <AlertTitle>
            Something went wrong
          </AlertTitle>
          <Typography variant="body2" gutterBottom>
            {error?.message || 'An unexpected error occurred'}
          </Typography>
          
          {showRetry && (
            <Button
              variant="outlined"
              startIcon={<Refresh />}
              onClick={this.handleRetry}
              sx={{ mt: 1 }}
            >
              Try Again
            </Button>
          )}
        </Alert>

        {/* Error Details */}
        {showDetails && error && (
          <Accordion sx={{ width: '100%', maxWidth: '800px' }}>
            <AccordionSummary
              expandIcon={<ExpandMore />}
              aria-controls="error-details-content"
              id="error-details-header"
            >
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <BugReport color="action" />
                <Typography variant="body2">
                  Error Details (ID: {errorId})
                </Typography>
              </Box>
            </AccordionSummary>
            <AccordionDetails>
              <Box sx={{ width: '100%' }}>
                {/* Error Message */}
                <Box sx={{ mb: 2 }}>
                  <Typography variant="subtitle2" gutterBottom>
                    Error Message:
                  </Typography>
                  <Box
                    sx={{
                      p: 2,
                      bgcolor: 'grey.100',
                      borderRadius: 1,
                      fontFamily: 'monospace',
                      fontSize: '0.875rem',
                      wordBreak: 'break-all',
                    }}
                  >
                    {error.message}
                  </Box>
                </Box>

                {/* Stack Trace */}
                {error.stack && (
                  <Box sx={{ mb: 2 }}>
                    <Typography variant="subtitle2" gutterBottom>
                      Stack Trace:
                    </Typography>
                    <Box
                      sx={{
                        p: 2,
                        bgcolor: 'grey.100',
                        borderRadius: 1,
                        fontFamily: 'monospace',
                        fontSize: '0.8rem',
                        maxHeight: 200,
                        overflow: 'auto',
                        whiteSpace: 'pre-wrap',
                      }}
                    >
                      {error.stack}
                    </Box>
                  </Box>
                )}

                {/* Component Stack */}
                {errorInfo && (
                  <Box sx={{ mb: 2 }}>
                    <Typography variant="subtitle2" gutterBottom>
                      Component Stack:
                    </Typography>
                    <Box
                      sx={{
                        p: 2,
                        bgcolor: 'grey.100',
                        borderRadius: 1,
                        fontFamily: 'monospace',
                        fontSize: '0.8rem',
                        maxHeight: 200,
                        overflow: 'auto',
                        whiteSpace: 'pre-wrap',
                      }}
                    >
                      {errorInfo.componentStack}
                    </Box>
                  </Box>
                )}

                {/* Additional Info */}
                <Box>
                  <Typography variant="subtitle2" gutterBottom>
                    Additional Information:
                  </Typography>
                  <Typography variant="body2" component="div">
                    <strong>Error ID:</strong> {errorId}<br />
                    <strong>Time:</strong> {new Date().toISOString()}<br />
                    <strong>User Agent:</strong> {navigator.userAgent}<br />
                    <strong>URL:</strong> {window.location.href}
                  </Typography>
                </Box>
              </Box>
            </AccordionDetails>
          </Accordion>
        )}
      </Box>
    );
  }
}

// Functional wrapper for easier usage with hooks
interface ErrorBoundaryWrapperProps {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
  showRetry?: boolean;
  showDetails?: boolean;
}

export const ErrorBoundaryWrapper: React.FC<ErrorBoundaryWrapperProps> = (props) => {
  return <ErrorBoundary {...props} />;
};

export default ErrorBoundary;
