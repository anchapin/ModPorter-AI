/**
 * Notification System - Day 5 Enhancement
 * Toast notifications for user feedback and error handling
 */

import React, { useState, useEffect, useCallback, createContext, useContext } from 'react';
import './NotificationSystem.css';

interface Notification {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  title: string;
  message?: string;
  duration?: number;
  persistent?: boolean;
  action?: {
    label: string;
    onClick: () => void;
  };
}

interface NotificationContextType {
  addNotification: (notification: Omit<Notification, 'id'>) => string;
  removeNotification: (id: string) => void;
  clearAll: () => void;
}

const NotificationContext = createContext<NotificationContextType | null>(null);

export const useNotifications = () => {
  const context = useContext(NotificationContext);
  if (!context) {
    throw new Error('useNotifications must be used within a NotificationProvider');
  }
  return context;
};

interface NotificationProviderProps {
  children: React.ReactNode;
  maxNotifications?: number;
  defaultDuration?: number;
}

export const NotificationProvider: React.FC<NotificationProviderProps> = ({
  children,
  maxNotifications = 5,
  defaultDuration = 5000
}) => {
  const [notifications, setNotifications] = useState<Notification[]>([]);

  const addNotification = useCallback((notification: Omit<Notification, 'id'>): string => {
    const id = `notification-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    
    const newNotification: Notification = {
      ...notification,
      id,
      duration: notification.duration ?? defaultDuration
    };

    setNotifications(prev => {
      const updated = [newNotification, ...prev];
      // Keep only the latest notifications within the limit
      return updated.slice(0, maxNotifications);
    });

    // Auto-remove if not persistent
    if (!notification.persistent && newNotification.duration! > 0) {
      setTimeout(() => {
        removeNotification(id);
      }, newNotification.duration);
    }

    return id;
  }, [defaultDuration, maxNotifications]);

  const removeNotification = useCallback((id: string) => {
    setNotifications(prev => prev.filter(notification => notification.id !== id));
  }, []);

  const clearAll = useCallback(() => {
    setNotifications([]);
  }, []);

  return (
    <NotificationContext.Provider value={{ addNotification, removeNotification, clearAll }}>
      {children}
      <NotificationContainer 
        notifications={notifications}
        onRemove={removeNotification}
      />
    </NotificationContext.Provider>
  );
};

interface NotificationContainerProps {
  notifications: Notification[];
  onRemove: (id: string) => void;
}

const NotificationContainer: React.FC<NotificationContainerProps> = ({
  notifications,
  onRemove
}) => {
  if (notifications.length === 0) return null;

  return (
    <div className="notification-container">
      {notifications.map(notification => (
        <NotificationItem
          key={notification.id}
          notification={notification}
          onRemove={onRemove}
        />
      ))}
    </div>
  );
};

interface NotificationItemProps {
  notification: Notification;
  onRemove: (id: string) => void;
}

const NotificationItem: React.FC<NotificationItemProps> = ({
  notification,
  onRemove
}) => {
  const [isVisible, setIsVisible] = useState(false);
  const [isRemoving, setIsRemoving] = useState(false);

  useEffect(() => {
    // Trigger enter animation
    const timer = setTimeout(() => setIsVisible(true), 50);
    return () => clearTimeout(timer);
  }, []);

  const handleRemove = () => {
    setIsRemoving(true);
    setTimeout(() => {
      onRemove(notification.id);
    }, 300); // Match CSS animation duration
  };

  const getIcon = () => {
    switch (notification.type) {
      case 'success': return '✅';
      case 'error': return '❌';
      case 'warning': return '⚠️';
      case 'info': return 'ℹ️';
      default: return '📢';
    }
  };

  return (
    <div 
      className={`notification notification-${notification.type} ${isVisible ? 'visible' : ''} ${isRemoving ? 'removing' : ''}`}
      role="alert"
      aria-live="polite"
    >
      <div className="notification-content">
        <div className="notification-icon">
          {getIcon()}
        </div>
        
        <div className="notification-text">
          <div className="notification-title">
            {notification.title}
          </div>
          {notification.message && (
            <div className="notification-message">
              {notification.message}
            </div>
          )}
        </div>

        <div className="notification-actions">
          {notification.action && (
            <button
              className="notification-action-btn"
              onClick={notification.action.onClick}
            >
              {notification.action.label}
            </button>
          )}
          
          <button
            className="notification-close-btn"
            onClick={handleRemove}
            aria-label="Close notification"
          >
            ✕
          </button>
        </div>
      </div>

      {/* Progress bar for timed notifications */}
      {!notification.persistent && notification.duration! > 0 && (
        <div 
          className="notification-progress"
          style={{ 
            animationDuration: `${notification.duration}ms`,
            animationPlayState: isRemoving ? 'paused' : 'running'
          }}
        />
      )}
    </div>
  );
};

// Convenience hooks for common notification types
export const useSuccessNotification = () => {
  const { addNotification } = useNotifications();
  
  return useCallback((title: string, message?: string, options?: Partial<Notification>) => {
    return addNotification({
      type: 'success',
      title,
      message,
      ...options
    });
  }, [addNotification]);
};

export const useErrorNotification = () => {
  const { addNotification } = useNotifications();
  
  return useCallback((title: string, message?: string, options?: Partial<Notification>) => {
    return addNotification({
      type: 'error',
      title,
      message,
      persistent: true, // Errors should be persistent by default
      ...options
    });
  }, [addNotification]);
};

export const useWarningNotification = () => {
  const { addNotification } = useNotifications();
  
  return useCallback((title: string, message?: string, options?: Partial<Notification>) => {
    return addNotification({
      type: 'warning',
      title,
      message,
      duration: 8000, // Warnings stay longer
      ...options
    });
  }, [addNotification]);
};

export const useInfoNotification = () => {
  const { addNotification } = useNotifications();
  
  return useCallback((title: string, message?: string, options?: Partial<Notification>) => {
    return addNotification({
      type: 'info',
      title,
      message,
      ...options
    });
  }, [addNotification]);
};

// HOC for automatic error handling
export const withNotificationErrorHandling = <P extends object>(
  Component: React.ComponentType<P>
) => {
  const WrappedComponent = (props: P) => {
    const addErrorNotification = useErrorNotification();

    useEffect(() => {
      const handleError = (event: ErrorEvent) => {
        addErrorNotification(
          'Unexpected Error',
          event.message,
          {
            action: {
              label: 'Reload',
              onClick: () => window.location.reload()
            }
          }
        );
      };

      const handleUnhandledRejection = (event: PromiseRejectionEvent) => {
        addErrorNotification(
          'Promise Rejection',
          String(event.reason),
          {
            action: {
              label: 'Dismiss',
              onClick: () => {}
            }
          }
        );
      };

      window.addEventListener('error', handleError);
      window.addEventListener('unhandledrejection', handleUnhandledRejection);

      return () => {
        window.removeEventListener('error', handleError);
        window.removeEventListener('unhandledrejection', handleUnhandledRejection);
      };
    }, [addErrorNotification]);

    return <Component {...props} />;
  };

  WrappedComponent.displayName = `withNotificationErrorHandling(${Component.displayName || Component.name})`;
  return WrappedComponent;
};

export default NotificationSystem;