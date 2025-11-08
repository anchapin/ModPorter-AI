import React, { useState, useCallback } from 'react';
import {
  Snackbar,
  Alert,
  AlertTitle,
  AlertProps,
  SnackbarProps,
  IconButton,
  Box,
  Typography,
  Slide,
  SlideProps,
} from '@mui/material';
import {
  CheckCircle,
  Error as ErrorIcon,
  Warning,
  Info,
  Close,
} from '@mui/icons-material';

export type ToastType = 'success' | 'error' | 'warning' | 'info';

export interface ToastMessage {
  id: string;
  type: ToastType;
  title?: string;
  message: string;
  duration?: number;
  action?: {
    label: string;
    onClick: () => void;
  };
  persistent?: boolean;
}

interface ToastProps {
  toast: ToastMessage;
  onClose: (id: string) => void;
  position?: SnackbarProps['anchorOrigin'];
}

// Toast Component
const Toast: React.FC<ToastProps> = ({
  toast,
  onClose,
  position = { vertical: 'bottom', horizontal: 'right' },
}) => {
  const [open, setOpen] = useState(true);

  const handleClose = useCallback(() => {
    setOpen(false);
    // Give the close animation time to complete
    setTimeout(() => onClose(toast.id), 300);
  }, [onClose, toast.id]);

  const getSeverity = (type: ToastType): AlertProps['severity'] => {
    switch (type) {
      case 'success': return 'success';
      case 'error': return 'error';
      case 'warning': return 'warning';
      case 'info': return 'info';
      default: return 'info';
    }
  };

  const getIcon = (type: ToastType) => {
    switch (type) {
      case 'success': return <CheckCircle />;
      case 'error': return <ErrorIcon />;
      case 'warning': return <Warning />;
      case 'info': return <Info />;
      default: return <Info />;
    }
  };

  const autoHideDuration = toast.persistent ? null : (toast.duration || 5000);

  return (
    <Snackbar
      open={open}
      autoHideDuration={autoHideDuration}
      onClose={handleClose}
      anchorOrigin={position}
      TransitionComponent={Slide}
      TransitionProps={{
        direction: 'left',
        appear: false,
      } as SlideProps}
    >
      <Alert
        severity={getSeverity(toast.type)}
        icon={getIcon(toast.type)}
        onClose={toast.persistent ? undefined : handleClose}
        action={
          <>
            {toast.action && (
              <Box
                component="button"
                onClick={(e) => {
                  e.stopPropagation();
                  toast.action.onClick();
                  handleClose();
                }}
                sx={{
                  background: 'none',
                  border: 'none',
                  padding: '4px 8px',
                  borderRadius: 1,
                  cursor: 'pointer',
                  '&:hover': {
                    backgroundColor: 'rgba(255, 255, 255, 0.1)',
                  },
                }}
              >
                <Typography variant="body2" sx={{ color: 'inherit' }}>
                  {toast.action.label}
                </Typography>
              </Box>
            )}
            <IconButton
              size="small"
              onClick={(e) => {
                e.stopPropagation();
                handleClose();
              }}
              sx={{ color: 'inherit' }}
            >
              <Close fontSize="small" />
            </IconButton>
          </>
        }
        sx={{
          minWidth: '300px',
          maxWidth: '500px',
          '& .MuiAlert-message': {
            flex: 1,
          },
        }}
      >
        {toast.title && <AlertTitle>{toast.title}</AlertTitle>}
        {toast.message}
      </Alert>
    </Snackbar>
  );
};

// Toast Container for managing multiple toasts
interface ToastContainerProps {
  toasts: ToastMessage[];
  onClose: (id: string) => void;
  position?: SnackbarProps['anchorOrigin'];
  maxToasts?: number;
}

export const ToastContainer: React.FC<ToastContainerProps> = ({
  toasts,
  onClose,
  position = { vertical: 'bottom', horizontal: 'right' },
  maxToasts = 3,
}) => {
  // Limit the number of toasts shown
  const visibleToasts = toasts.slice(-maxToasts);

  // Calculate positioning for multiple toasts
  const getToastStyle = (index: number) => {
    const spacing = 8; // Space between toasts
    const offset = index * (80 + spacing); // Approximate height of toast + spacing
    return {
      transform: `translateY(-${offset}px)`,
      zIndex: 9999 - index, // Stack higher toasts on top
    };
  };

  return (
    <>
      {visibleToasts.map((toast, index) => (
        <Box
          key={toast.id}
          sx={{
            position: 'fixed',
            ...position,
            ...getToastStyle(index, visibleToasts.length),
            pointerEvents: 'auto',
          }}
        >
          <Box sx={{ mb: 1 }}>
            <Toast toast={toast} onClose={onClose} position={position} />
          </Box>
        </Box>
      ))}
    </>
  );
};

// Toast Hook for easy usage
export interface UseToastReturn {
  toasts: ToastMessage[];
  success: (message: string, options?: Partial<ToastMessage>) => void;
  error: (message: string, options?: Partial<ToastMessage>) => void;
  warning: (message: string, options?: Partial<ToastMessage>) => void;
  info: (message: string, options?: Partial<ToastMessage>) => void;
  clear: (id?: string) => void;
  clearAll: () => void;
}

const useToastHook = (): UseToastReturn => {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const addToast = useCallback((
    type: ToastType,
    message: string,
    options: Partial<ToastMessage> = {}
  ) => {
    const id = `toast-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    const newToast: ToastMessage = {
      id,
      type,
      message,
      duration: 5000,
      ...options,
    };
    
    setToasts(prev => [...prev, newToast]);
  }, []);

  const removeToast = useCallback((id: string) => {
    setToasts(prev => prev.filter(toast => toast.id !== id));
  }, []);

  const success = useCallback((message: string, options: Partial<ToastMessage> = {}) => {
    addToast('success', message, options);
  }, [addToast]);

  const error = useCallback((message: string, options: Partial<ToastMessage> = {}) => {
    addToast('error', message, { persistent: true, ...options });
  }, [addToast]);

  const warning = useCallback((message: string, options: Partial<ToastMessage> = {}) => {
    addToast('warning', message, { duration: 7000, ...options });
  }, [addToast]);

  const info = useCallback((message: string, options: Partial<ToastMessage> = {}) => {
    addToast('info', message, options);
  }, [addToast]);

  const clear = useCallback((id?: string) => {
    if (id) {
      removeToast(id);
    } else {
      setToasts([]);
    }
  }, [removeToast]);

  const clearAll = useCallback(() => {
    setToasts([]);
  }, []);

  return {
    toasts,
    success,
    error,
    warning,
    info,
    clear,
    clearAll,
  };
};

// eslint-disable-next-line react-refresh/only-export-components
export { useToastHook as useToast };

export default Toast;
