import React, { ReactNode } from 'react';
import {
  Box,
  CircularProgress,
  Typography,
  Skeleton,
  Fade,
  Backdrop,
  Paper,
} from '@mui/material';
import {
  Refresh,
  Save,
  Download,
  CloudUpload,
} from '@mui/icons-material';

interface LoadingWrapperProps {
  loading: boolean;
  children: ReactNode;
  variant?: 'overlay' | 'inline' | 'skeleton' | 'spinner';
  message?: string;
  size?: 'small' | 'medium' | 'large';
  opacity?: number;
  backdrop?: boolean;
  icon?: ReactNode;
  spinnerColor?: 'primary' | 'secondary' | 'inherit';
}

export const LoadingWrapper: React.FC<LoadingWrapperProps> = ({
  loading,
  children,
  variant = 'overlay',
  message,
  size = 'medium',
  opacity = 0.7,
  backdrop = true,
  icon,
  spinnerColor = 'primary',
}) => {
  const getSizeValue = (size: string) => {
    switch (size) {
      case 'small': return 24;
      case 'large': return 48;
      default: return 36;
    }
  };



  const renderCustomIcon = () => {
    if (React.isValidElement(icon)) {
      return icon;
    }
    return <CircularProgress size={getSizeValue(size)} color={spinnerColor} />;
  };

  const renderMessage = () => {
    if (!message) return null;
    
    return (
      <Typography
        variant="body2"
        color="text.secondary"
        sx={{ mt: 1, textAlign: 'center' }}
      >
        {message}
      </Typography>
    );
  };

  switch (variant) {
    case 'overlay':
      return (
        <Box sx={{ position: 'relative' }}>
          {children}
          {loading && (
            <Fade in={loading}>
              <Backdrop
                open={loading}
                sx={{
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  right: 0,
                  bottom: 0,
                  bgcolor: backdrop ? 'rgba(255, 255, 255, 0.8)' : 'transparent',
                  zIndex: 1000,
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  opacity,
                }}
              >
                <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                  {renderCustomIcon()}
                  {renderMessage()}
                </Box>
              </Backdrop>
            </Fade>
          )}
        </Box>
      );

    case 'inline':
      return (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          {loading ? (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              {renderCustomIcon()}
              {renderMessage()}
            </Box>
          ) : (
            children
          )}
        </Box>
      );

    case 'spinner':
      return (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            {loading ? renderCustomIcon() : children}
            {loading && renderMessage()}
          </Box>
        </Box>
      );

    case 'skeleton':
      if (loading) {
        return (
          <Box sx={{ width: '100%' }}>
            <LoadingSkeleton />
          </Box>
        );
      }
      return <>{children}</>;

    default:
      return <>{children}</>;
  }
};

// Skeleton loading component
export const LoadingSkeleton: React.FC = () => {
  return (
    <Box sx={{ p: 2 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
        <Skeleton variant="circular" width={40} height={40} sx={{ mr: 2 }} />
        <Box sx={{ flex: 1 }}>
          <Skeleton variant="text" width="60%" height={20} sx={{ mb: 1 }} />
          <Skeleton variant="text" width="40%" height={16} />
        </Box>
      </Box>
      
      <Skeleton variant="rectangular" width="100%" height={200} sx={{ mb: 2 }} />
      
      <Box sx={{ display: 'flex', gap: 1 }}>
        <Skeleton variant="rectangular" width={80} height={32} />
        <Skeleton variant="rectangular" width={80} height={32} />
        <Skeleton variant="rectangular" width={80} height={32} />
      </Box>
    </Box>
  );
};

// Skeleton for specific component types
export const CardSkeleton: React.FC<{ count?: number }> = ({ count = 1 }) => {
  return (
    <>
      {Array.from({ length: count }).map((_, index) => (
        <Box key={index} sx={{ mb: 2 }}>
          <Paper sx={{ p: 2 }}>
            <Skeleton variant="text" width="70%" height={24} sx={{ mb: 2 }} />
            <Skeleton variant="rectangular" width="100%" height={120} sx={{ mb: 2 }} />
            <Box sx={{ display: 'flex', gap: 1 }}>
              <Skeleton variant="rectangular" width={60} height={24} />
              <Skeleton variant="rectangular" width={60} height={24} />
            </Box>
          </Paper>
        </Box>
      ))}
    </>
  );
};

// Skeleton for list items
export const ListItemSkeleton: React.FC<{ count?: number }> = ({ count = 5 }) => {
  return (
    <>
      {Array.from({ length: count }).map((_, index) => (
        <Box key={index} sx={{ py: 1 }}>
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            <Skeleton variant="circular" width={32} height={32} sx={{ mr: 2 }} />
            <Box sx={{ flex: 1 }}>
              <Skeleton variant="text" width="80%" height={20} sx={{ mb: 0.5 }} />
              <Skeleton variant="text" width="60%" height={16} />
            </Box>
          </Box>
        </Box>
      ))}
    </>
  );
};

// Skeleton for forms
export const FormSkeleton: React.FC = () => {
  return (
    <Box sx={{ p: 2 }}>
      <Box sx={{ mb: 3 }}>
        <Skeleton variant="text" width="30%" height={20} sx={{ mb: 1 }} />
        <Skeleton variant="rectangular" width="100%" height={40} />
      </Box>
      
      <Box sx={{ mb: 3 }}>
        <Skeleton variant="text" width="40%" height={20} sx={{ mb: 1 }} />
        <Skeleton variant="rectangular" width="100%" height={40} />
      </Box>
      
      <Box sx={{ mb: 3 }}>
        <Skeleton variant="text" width="25%" height={20} sx={{ mb: 1 }} />
        <Skeleton variant="rectangular" width="100%" height={120} />
      </Box>
      
      <Box sx={{ display: 'flex', gap: 1, justifyContent: 'flex-end' }}>
        <Skeleton variant="rectangular" width={80} height={36} />
        <Skeleton variant="rectangular" width={100} height={36} />
      </Box>
    </Box>
  );
};

// Specialized loading indicators
export const SaveLoading: React.FC<{ loading: boolean; children: ReactNode }> = ({ loading, children }) => (
  <LoadingWrapper
    loading={loading}
    variant="inline"
    icon={<Save />}
    spinnerColor="primary"
    message="Saving..."
  >
    {children}
  </LoadingWrapper>
);

export const DownloadLoading: React.FC<{ loading: boolean; children: ReactNode }> = ({ loading, children }) => (
  <LoadingWrapper
    loading={loading}
    variant="inline"
    icon={<Download />}
    spinnerColor="primary"
    message="Downloading..."
  >
    {children}
  </LoadingWrapper>
);

export const UploadLoading: React.FC<{ loading: boolean; children: ReactNode }> = ({ loading, children }) => (
  <LoadingWrapper
    loading={loading}
    variant="inline"
    icon={<CloudUpload />}
    spinnerColor="primary"
    message="Uploading..."
  >
    {children}
  </LoadingWrapper>
);

export const RefreshLoading: React.FC<{ loading: boolean; children: ReactNode }> = ({ loading, children }) => (
  <LoadingWrapper
    loading={loading}
    variant="inline"
    icon={<Refresh />}
    spinnerColor="primary"
    message="Refreshing..."
  >
    {children}
  </LoadingWrapper>
);

export default LoadingWrapper;
