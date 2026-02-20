/**
 * Progress Context for Real-Time Conversion Progress Tracking
 * Manages progress state across components with WebSocket integration
 */

import React, { createContext, useContext, useState, useCallback, useEffect, ReactNode } from 'react';
import { ConversionStatus } from '../types/api';
import { createConversionWebSocket, ConversionWebSocket } from '../services/websocket';

// Progress context state
export interface ProgressState {
  // Current conversion status
  status: ConversionStatus | null;
  // Connection status
  connectionStatus: 'connecting' | 'connected' | 'disconnected' | 'error';
  // Using WebSocket or polling
  usingWebSocket: boolean;
  // Connection error message
  connectionError: string | null;
  // Progress history for persistence
  history: ConversionStatus[];
}

// Progress context actions
export interface ProgressActions {
  // Update current status
  updateStatus: (status: ConversionStatus) => void;
  // Clear current status
  clearStatus: () => void;
  // Set connection status
  setConnectionStatus: (status: 'connecting' | 'connected' | 'disconnected' | 'error') => void;
  // Set connection error
  setConnectionError: (error: string | null) => void;
  // Connect to WebSocket for a job
  connectToJob: (jobId: string) => void;
  // Disconnect from current job
  disconnectFromJob: () => void;
}

// Progress context value
export interface ProgressContextValue {
  state: ProgressState;
  actions: ProgressActions;
}

// Create context with default values
const ProgressContext = createContext<ProgressContextValue | null>(null);

// Context provider props
export interface ProgressProviderProps {
  children: ReactNode;
  // Enable/disable persistence to localStorage
  enablePersistence?: boolean;
  // Persistence key for localStorage
  persistenceKey?: string;
}

// Local storage keys
const STORAGE_KEY_PREFIX = 'modporter_progress_';
const HISTORY_KEY_PREFIX = 'modporter_progress_history_';

/**
 * Progress Provider Component
 * Provides progress state and WebSocket management to child components
 */
export const ProgressProvider: React.FC<ProgressProviderProps> = ({
  children,
  enablePersistence = true,
  persistenceKey = 'default'
}) => {
  // Progress state
  const [status, setStatus] = useState<ConversionStatus | null>(null);
  const [connectionStatus, setConnectionStatusState] = useState<'connecting' | 'connected' | 'disconnected' | 'error'>('disconnected');
  const [usingWebSocket, setUsingWebSocket] = useState(false);
  const [connectionError, setConnectionErrorState] = useState<string | null>(null);
  const [history, setHistory] = useState<ConversionStatus[]>([]);

  // WebSocket instance
  const webSocketRef = React.useRef<ConversionWebSocket | null>(null);
  const currentJobIdRef = React.useRef<string | null>(null);

  // Storage keys for this instance
  const storageKey = `${STORAGE_KEY_PREFIX}${persistenceKey}`;
  const historyKey = `${HISTORY_KEY_PREFIX}${persistenceKey}`;

  // Load persisted state on mount
  useEffect(() => {
    if (enablePersistence) {
      try {
        const savedStatus = localStorage.getItem(storageKey);
        const savedHistory = localStorage.getItem(historyKey);

        if (savedStatus) {
          const parsedStatus = JSON.parse(savedStatus) as ConversionStatus;
          setStatus(parsedStatus);
        }

        if (savedHistory) {
          const parsedHistory = JSON.parse(savedHistory) as ConversionStatus[];
          setHistory(parsedHistory);
        }
      } catch (error) {
        console.error('[ProgressContext] Failed to load persisted state:', error);
      }
    }

    // Cleanup on unmount
    return () => {
      if (webSocketRef.current) {
        webSocketRef.current.destroy();
        webSocketRef.current = null;
      }
    };
  }, [enablePersistence, persistenceKey, storageKey, historyKey]);

  // Persist state to localStorage
  useEffect(() => {
    if (enablePersistence && status) {
      try {
        localStorage.setItem(storageKey, JSON.stringify(status));
      } catch (error) {
        console.error('[ProgressContext] Failed to persist status:', error);
      }
    } else if (enablePersistence && status === null) {
      try {
        localStorage.removeItem(storageKey);
      } catch (error) {
        console.error('[ProgressContext] Failed to clear persisted status:', error);
      }
    }
  }, [enablePersistence, storageKey, status]);

  // Persist history to localStorage
  useEffect(() => {
    if (enablePersistence && history.length > 0) {
      try {
        localStorage.setItem(historyKey, JSON.stringify(history));
      } catch (error) {
        console.error('[ProgressContext] Failed to persist history:', error);
      }
    } else if (enablePersistence && history.length === 0) {
      try {
        localStorage.removeItem(historyKey);
      } catch (error) {
        console.error('[ProgressContext] Failed to clear persisted history:', error);
      }
    }
  }, [enablePersistence, historyKey, history]);

  // Update status action
  const updateStatus = useCallback((newStatus: ConversionStatus) => {
    setStatus(newStatus);
    setHistory(prev => {
      // Add to history (keep last 50 entries)
      const newHistory = [...prev, newStatus].slice(-50);
      return newHistory;
    });

    // Auto-disconnect if conversion is terminal
    if (newStatus.status === 'completed' || newStatus.status === 'failed' || newStatus.status === 'cancelled') {
      if (webSocketRef.current) {
        webSocketRef.current.disconnect();
        webSocketRef.current = null;
      }
      currentJobIdRef.current = null;
      setUsingWebSocket(false);
      setConnectionStatusState('disconnected');
    }
  }, []);

  // Clear status action
  const clearStatus = useCallback(() => {
    setStatus(null);
    setConnectionErrorState(null);
    setUsingWebSocket(false);
    setConnectionStatusState('disconnected');
  }, []);

  // Set connection status action
  const setConnectionStatus = useCallback((newStatus: 'connecting' | 'connected' | 'disconnected' | 'error') => {
    setConnectionStatusState(newStatus);
  }, []);

  // Set connection error action
  const setConnectionError = useCallback((error: string | null) => {
    setConnectionErrorState(error);
  }, []);

  // Connect to job action
  const connectToJob = useCallback((jobId: string) => {
    // Disconnect from previous job if any
    if (webSocketRef.current) {
      webSocketRef.current.disconnect();
      webSocketRef.current = null;
    }

    currentJobIdRef.current = jobId;
    setConnectionStatus('connecting');
    setConnectionError(null);

    // Create new WebSocket connection
    webSocketRef.current = createConversionWebSocket(jobId);

    // Register message handler
    const unregisterMessage = webSocketRef.current.onMessage((data) => {
      console.log('[ProgressContext] Message received:', data);
      updateStatus(data);
    });

    // Register status handler
    const unregisterStatus = webSocketRef.current.onStatus((status) => {
      console.log('[ProgressContext] Connection status:', status);
      setConnectionStatus(status);
      if (status === 'connected') {
        setUsingWebSocket(true);
        setConnectionError(null);
      } else if (status === 'error') {
        setUsingWebSocket(false);
        setConnectionError('WebSocket connection error');
      }
    });

    // Connect
    webSocketRef.current.connect();

    // Clean up on disconnect
    const cleanup = () => {
      unregisterMessage();
      unregisterStatus();
    };

    // Store cleanup function for later use
    webSocketRef.current.destroy = () => {
      cleanup();
      webSocketRef.current?.disconnect();
    };
  }, [updateStatus, setConnectionStatus, setConnectionError]);

  // Disconnect from job action
  const disconnectFromJob = useCallback(() => {
    if (webSocketRef.current) {
      webSocketRef.current.destroy();
      webSocketRef.current = null;
    }
    currentJobIdRef.current = null;
    setUsingWebSocket(false);
    setConnectionStatus('disconnected');
  }, [setConnectionStatus]);

  // Context value
  const contextValue: ProgressContextValue = {
    state: {
      status,
      connectionStatus,
      usingWebSocket,
      connectionError,
      history
    },
    actions: {
      updateStatus,
      clearStatus,
      setConnectionStatus,
      setConnectionError,
      connectToJob,
      disconnectFromJob
    }
  };

  return (
    <ProgressContext.Provider value={contextValue}>
      {children}
    </ProgressContext.Provider>
  );
};

/**
 * Hook to use the progress context
 * Throws error if used outside of ProgressProvider
 */
export const useProgress = (): ProgressContextValue => {
  const context = useContext(ProgressContext);
  if (!context) {
    throw new Error('useProgress must be used within a ProgressProvider');
  }
  return context;
};

/**
 * Hook to access progress state only
 */
export const useProgressState = (): ProgressState => {
  const { state } = useProgress();
  return state;
};

/**
 * Hook to access progress actions only
 */
export const useProgressActions = (): ProgressActions => {
  const { actions } = useProgress();
  return actions;
};

export default ProgressContext;
