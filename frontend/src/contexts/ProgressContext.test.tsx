/**
 * Progress Context Tests
 * Tests for ProgressContext including state management, WebSocket integration, and memory leak detection
 */

import { render, screen, act } from '@testing-library/react';
import { vi, describe, beforeEach, afterEach, test, expect } from 'vitest';
import React from 'react';
import { ProgressProvider, useProgress, useProgressState, useProgressActions } from './ProgressContext';
import { ConversionStatus } from '../types/api';
import { createConversionWebSocket } from '../services/websocket';

// Mock the WebSocket service
vi.mock('../services/websocket', () => ({
  createConversionWebSocket: vi.fn(),
  ConversionWebSocket: class MockConversionWebSocket {
    onMessage = vi.fn();
    onStatus = vi.fn();
    connect = vi.fn();
    disconnect = vi.fn();
    destroy = vi.fn();
  }
}));

describe('ProgressContext', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Clear localStorage
    localStorage.clear();
    // Suppress console errors during tests
    vi.spyOn(console, 'error').mockImplementation(() => {});
    vi.spyOn(console, 'log').mockImplementation(() => {});
    vi.spyOn(console, 'warn').mockImplementation(() => {});
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('ProgressProvider', () => {
    test('should provide progress context to children', () => {
      const TestComponent = () => {
        const progress = useProgress();
        return <div>Context available: {progress ? 'Yes' : 'No'}</div>;
      };

      render(
        <ProgressProvider>
          <TestComponent />
        </ProgressProvider>
      );

      expect(screen.getByText('Context available: Yes')).toBeInTheDocument();
    });

    test('should throw error when useProgress is used outside provider', () => {
      const TestComponent = () => {
        useProgress();
        return <div>Test</div>;
      };

      expect(() => render(<TestComponent />)).toThrow('useProgress must be used within a ProgressProvider');
    });

    test('should initialize with default state', () => {
      const TestComponent = () => {
        const state = useProgressState();
        return (
          <div>
            <div>Status: {state.status ? state.status.status : 'null'}</div>
            <div>Connection: {state.connectionStatus}</div>
            <div>WebSocket: {state.usingWebSocket ? 'Yes' : 'No'}</div>
          </div>
        );
      };

      render(
        <ProgressProvider>
          <TestComponent />
        </ProgressProvider>
      );

      expect(screen.getByText('Status: null')).toBeInTheDocument();
      expect(screen.getByText('Connection: disconnected')).toBeInTheDocument();
      expect(screen.getByText('WebSocket: No')).toBeInTheDocument();
    });

    test('should update status when updateStatus is called', () => {
      const TestComponent = () => {
        const { state, actions } = useProgress();
        const handleUpdate = () => {
          actions.updateStatus({
            job_id: 'test-job',
            status: 'processing',
            progress: 50,
            message: 'Processing...',
            stage: 'Processing',
            estimated_time_remaining: 60,
            result_url: null,
            error: null,
            created_at: new Date().toISOString()
          });
        };

        return (
          <div>
            <div>Status: {state.status?.status || 'null'}</div>
            <div>Progress: {state.status?.progress || 0}</div>
            <button onClick={handleUpdate}>Update</button>
          </div>
        );
      };

      render(
        <ProgressProvider>
          <TestComponent />
        </ProgressProvider>
      );

      expect(screen.getByText('Status: null')).toBeInTheDocument();
      expect(screen.getByText('Progress: 0')).toBeInTheDocument();

      act(() => {
        screen.getByText('Update').click();
      });

      expect(screen.getByText('Status: processing')).toBeInTheDocument();
      expect(screen.getByText('Progress: 50')).toBeInTheDocument();
    });

    test('should clear status when clearStatus is called', () => {
      const TestComponent = () => {
        const { state, actions } = useProgress();
        const handleUpdate = () => {
          actions.updateStatus({
            job_id: 'test-job',
            status: 'processing',
            progress: 50,
            message: 'Processing...',
            stage: 'Processing',
            estimated_time_remaining: 60,
            result_url: null,
            error: null,
            created_at: new Date().toISOString()
          });
        };

        const handleClear = () => {
          actions.clearStatus();
        };

        return (
          <div>
            <div>Status: {state.status?.status || 'null'}</div>
            <button onClick={handleUpdate}>Update</button>
            <button onClick={handleClear}>Clear</button>
          </div>
        );
      };

      render(
        <ProgressProvider>
          <TestComponent />
        </ProgressProvider>
      );

      act(() => {
        screen.getByText('Update').click();
      });

      expect(screen.getByText('Status: processing')).toBeInTheDocument();

      act(() => {
        screen.getByText('Clear').click();
      });

      expect(screen.getByText('Status: null')).toBeInTheDocument();
    });

    test('should update connection status', () => {
      const TestComponent = () => {
        const { state, actions } = useProgress();
        const handleConnect = () => {
          actions.setConnectionStatus('connecting');
        };

        return (
          <div>
            <div>Connection: {state.connectionStatus}</div>
            <button onClick={handleConnect}>Connect</button>
          </div>
        );
      };

      render(
        <ProgressProvider>
          <TestComponent />
        </ProgressProvider>
      );

      expect(screen.getByText('Connection: disconnected')).toBeInTheDocument();

      act(() => {
        screen.getByText('Connect').click();
      });

      expect(screen.getByText('Connection: connecting')).toBeInTheDocument();
    });

    test('should update connection error', () => {
      const TestComponent = () => {
        const { state, actions } = useProgress();
        const handleSetError = () => {
          actions.setConnectionError('Connection failed');
        };

        return (
          <div>
            <div>Error: {state.connectionError || 'null'}</div>
            <button onClick={handleSetError}>Set Error</button>
          </div>
        );
      };

      render(
        <ProgressProvider>
          <TestComponent />
        </ProgressProvider>
      );

      expect(screen.getByText('Error: null')).toBeInTheDocument();

      act(() => {
        screen.getByText('Set Error').click();
      });

      expect(screen.getByText('Error: Connection failed')).toBeInTheDocument();
    });

    test('should persist state to localStorage when enabled', () => {
      const persistenceKey = 'test-persistence';

      const TestComponent = () => {
        const { actions } = useProgress();
        const handleUpdate = () => {
          actions.updateStatus({
            job_id: 'test-job',
            status: 'processing',
            progress: 75,
            message: 'Processing...',
            stage: 'Processing',
            estimated_time_remaining: 60,
            result_url: null,
            error: null,
            created_at: new Date().toISOString()
          });
        };

        return <button onClick={handleUpdate}>Update</button>;
      };

      render(
        <ProgressProvider enablePersistence={true} persistenceKey={persistenceKey}>
          <TestComponent />
        </ProgressProvider>
      );

      act(() => {
        screen.getByText('Update').click();
      });

      // Check localStorage
      const savedData = localStorage.getItem(`modporter_progress_${persistenceKey}`);
      expect(savedData).toBeTruthy();
      const parsedData = JSON.parse(savedData!);
      expect(parsedData.status).toBe('processing');
      expect(parsedData.progress).toBe(75);
    });

    test('should not persist state to localStorage when disabled', () => {
      const persistenceKey = 'test-persistence';

      const TestComponent = () => {
        const { actions } = useProgress();
        const handleUpdate = () => {
          actions.updateStatus({
            job_id: 'test-job',
            status: 'processing',
            progress: 75,
            message: 'Processing...',
            stage: 'Processing',
            estimated_time_remaining: 60,
            result_url: null,
            error: null,
            created_at: new Date().toISOString()
          });
        };

        return <button onClick={handleUpdate}>Update</button>;
      };

      render(
        <ProgressProvider enablePersistence={false} persistenceKey={persistenceKey}>
          <TestComponent />
        </ProgressProvider>
      );

      act(() => {
        screen.getByText('Update').click();
      });

      // Check localStorage should be empty
      const savedData = localStorage.getItem(`modporter_progress_${persistenceKey}`);
      expect(savedData).toBeNull();
    });

    test('should load persisted state on mount', () => {
      const persistenceKey = 'test-persistence';

      // Pre-populate localStorage
      const prePersistedData: ConversionStatus = {
        job_id: 'test-job',
        status: 'completed',
        progress: 100,
        message: 'Completed',
        stage: 'Completed',
        estimated_time_remaining: 0,
        result_url: '/download/test.zip',
        error: null,
        created_at: new Date().toISOString()
      };
      localStorage.setItem(`modporter_progress_${persistenceKey}`, JSON.stringify(prePersistedData));

      const TestComponent = () => {
        const state = useProgressState();
        return (
          <div>
            <div>Status: {state.status?.status || 'null'}</div>
            <div>Progress: {state.status?.progress || 0}</div>
          </div>
        );
      };

      render(
        <ProgressProvider enablePersistence={true} persistenceKey={persistenceKey}>
          <TestComponent />
        </ProgressProvider>
      );

      expect(screen.getByText('Status: completed')).toBeInTheDocument();
      expect(screen.getByText('Progress: 100')).toBeInTheDocument();
    });

    test('should maintain history of status updates', () => {
      const TestComponent = () => {
        const { state, actions } = useProgress();
        const handleUpdate = (status: string, progress: number) => {
          actions.updateStatus({
            job_id: 'test-job',
            status: status as any,
            progress: progress,
            message: `${status}...`,
            stage: status,
            estimated_time_remaining: 60,
            result_url: null,
            error: null,
            created_at: new Date().toISOString()
          });
        };

        return (
          <div>
            <div>History count: {state.history.length}</div>
            <button onClick={() => handleUpdate('queued', 0)}>Queue</button>
            <button onClick={() => handleUpdate('processing', 50)}>Process</button>
            <button onClick={() => handleUpdate('completed', 100)}>Complete</button>
          </div>
        );
      };

      render(
        <ProgressProvider>
          <TestComponent />
        </ProgressProvider>
      );

      expect(screen.getByText('History count: 0')).toBeInTheDocument();

      act(() => {
        screen.getByText('Queue').click();
      });
      expect(screen.getByText('History count: 1')).toBeInTheDocument();

      act(() => {
        screen.getByText('Process').click();
      });
      expect(screen.getByText('History count: 2')).toBeInTheDocument();

      act(() => {
        screen.getByText('Complete').click();
      });
      expect(screen.getByText('History count: 3')).toBeInTheDocument();
    });

    test('should limit history to last 50 entries', () => {
      const TestComponent = () => {
        const { state, actions } = useProgress();

        const handleAddMany = () => {
          for (let i = 0; i < 100; i++) {
            actions.updateStatus({
              job_id: 'test-job',
              status: 'processing',
              progress: i,
              message: `Step ${i}`,
              stage: 'Processing',
              estimated_time_remaining: 60,
              result_url: null,
              error: null,
              created_at: new Date().toISOString()
            });
          }
        };

        return (
          <div>
            <div>History count: {state.history.length}</div>
            <button onClick={handleAddMany}>Add 100</button>
          </div>
        );
      };

      render(
        <ProgressProvider>
          <TestComponent />
        </ProgressProvider>
      );

      expect(screen.getByText('History count: 0')).toBeInTheDocument();

      act(() => {
        screen.getByText('Add 100').click();
      });

      expect(screen.getByText('History count: 50')).toBeInTheDocument();
    });
  });

  describe('useProgressState', () => {
    test('should return progress state only', () => {
      const TestComponent = () => {
        const state = useProgressState();
        return (
          <div>
            <div>Has state: {state ? 'Yes' : 'No'}</div>
            <div>Has actions: {(state as any).actions ? 'Yes' : 'No'}</div>
          </div>
        );
      };

      render(
        <ProgressProvider>
          <TestComponent />
        </ProgressProvider>
      );

      expect(screen.getByText('Has state: Yes')).toBeInTheDocument();
      expect(screen.getByText('Has actions: No')).toBeInTheDocument();
    });
  });

  describe('useProgressActions', () => {
    test('should return progress actions only', () => {
      const TestComponent = () => {
        const actions = useProgressActions();
        return (
          <div>
            <div>Has actions: {actions ? 'Yes' : 'No'}</div>
            <div>Has state: {(actions as any).status ? 'Yes' : 'No'}</div>
          </div>
        );
      };

      render(
        <ProgressProvider>
          <TestComponent />
        </ProgressProvider>
      );

      expect(screen.getByText('Has actions: Yes')).toBeInTheDocument();
      expect(screen.getByText('Has state: No')).toBeInTheDocument();
    });

    test('should allow updating status via actions', () => {
      const TestComponent = () => {
        const actions = useProgressActions();
        const [localStatus, setLocalStatus] = React.useState('null');

        const handleUpdate = () => {
          actions.updateStatus({
            job_id: 'test-job',
            status: 'processing',
            progress: 50,
            message: 'Processing...',
            stage: 'Processing',
            estimated_time_remaining: 60,
            result_url: null,
            error: null,
            created_at: new Date().toISOString()
          });
          setLocalStatus('processing');
        };

        return (
          <div>
            <div>Local status: {localStatus}</div>
            <button onClick={handleUpdate}>Update</button>
          </div>
        );
      };

      render(
        <ProgressProvider>
          <TestComponent />
        </ProgressProvider>
      );

      expect(screen.getByText('Local status: null')).toBeInTheDocument();

      act(() => {
        screen.getByText('Update').click();
      });

      expect(screen.getByText('Local status: processing')).toBeInTheDocument();
    });
  });

  describe('Memory Leak Detection', () => {
    test('should clean up WebSocket on unmount', () => {
      const mockWebSocket = {
        onMessage: vi.fn(),
        onStatus: vi.fn(),
        connect: vi.fn(),
        disconnect: vi.fn(),
        destroy: vi.fn()
      };

      createConversionWebSocket.mockReturnValue(mockWebSocket);

      const TestComponent = ({ jobId }: { jobId: string }) => {
        const { actions } = useProgress();
        React.useEffect(() => {
          actions.connectToJob(jobId);
        }, [actions, jobId]);

        return <div>Job: {jobId}</div>;
      };

      const { unmount } = render(
        <ProgressProvider>
          <TestComponent jobId="test-job-1" />
        </ProgressProvider>
      );

      expect(createConversionWebSocket).toHaveBeenCalledWith('test-job-1');
      expect(mockWebSocket.connect).toHaveBeenCalled();

      // Unmount component
      unmount();

      // Verify WebSocket was destroyed (via provider cleanup)
      expect(mockWebSocket.disconnect).toHaveBeenCalled();
    });

    test('should disconnect from previous job when connecting to new job', () => {
      const mockWebSocket1 = {
        onMessage: vi.fn(),
        onStatus: vi.fn(),
        connect: vi.fn(),
        disconnect: vi.fn(),
        destroy: vi.fn()
      };
      const mockWebSocket2 = {
        onMessage: vi.fn(),
        onStatus: vi.fn(),
        connect: vi.fn(),
        disconnect: vi.fn(),
        destroy: vi.fn()
      };

      createConversionWebSocket
        .mockReturnValueOnce(mockWebSocket1)
        .mockReturnValueOnce(mockWebSocket2);

      const TestComponent = ({ jobId }: { jobId: string }) => {
        const { actions } = useProgress();
        React.useEffect(() => {
          actions.connectToJob(jobId);
        }, [actions, jobId]);

        return <div>Job: {jobId}</div>;
      };

      const { rerender } = render(
        <ProgressProvider>
          <TestComponent jobId="test-job-1" />
        </ProgressProvider>
      );

      expect(createConversionWebSocket).toHaveBeenCalledWith('test-job-1');
      expect(mockWebSocket1.connect).toHaveBeenCalled();

      // Change job ID
      rerender(
        <ProgressProvider>
          <TestComponent jobId="test-job-2" />
        </ProgressProvider>
      );

      expect(createConversionWebSocket).toHaveBeenCalledWith('test-job-2');
      expect(mockWebSocket1.disconnect).toHaveBeenCalled();
      expect(mockWebSocket2.connect).toHaveBeenCalled();
    });

    test('should not create memory leaks with rapid status updates', () => {
      const TestComponent = () => {
        const { actions } = useProgress();
        const [updateCount, setUpdateCount] = React.useState(0);

        const handleRapidUpdates = () => {
          // Simulate rapid updates
          for (let i = 0; i < 100; i++) {
            setUpdateCount(i + 1);
            actions.updateStatus({
              job_id: 'test-job',
              status: 'processing',
              progress: i,
              message: `Update ${i}`,
              stage: 'Processing',
              estimated_time_remaining: 60,
              result_url: null,
              error: null,
              created_at: new Date().toISOString()
            });
          }
          setUpdateCount(100);
        };

        return (
          <div>
            <div>Update count: {updateCount}</div>
            <div>History length: {useProgressState().history.length}</div>
            <button onClick={handleRapidUpdates}>Rapid Updates</button>
          </div>
        );
      };

      render(
        <ProgressProvider>
          <TestComponent />
        </ProgressProvider>
      );

      expect(screen.getByText('Update count: 0')).toBeInTheDocument();

      act(() => {
        screen.getByText('Rapid Updates').click();
      });

      expect(screen.getByText('Update count: 100')).toBeInTheDocument();
      // History should be limited to 50, not all 100
      expect(screen.getByText('History length: 50')).toBeInTheDocument();
    });

    test('should clear persisted state when clearing status', () => {
      const persistenceKey = 'test-persistence';

      const TestComponent = () => {
        const { actions } = useProgress();
        const [status, setStatus] = React.useState('null');

        const handleUpdate = () => {
          actions.updateStatus({
            job_id: 'test-job',
            status: 'processing',
            progress: 50,
            message: 'Processing...',
            stage: 'Processing',
            estimated_time_remaining: 60,
            result_url: null,
            error: null,
            created_at: new Date().toISOString()
          });
          setStatus('processing');
        };

        const handleClear = () => {
          actions.clearStatus();
          setStatus('null');
        };

        return (
          <div>
            <div>Status: {status}</div>
            <button onClick={handleUpdate}>Update</button>
            <button onClick={handleClear}>Clear</button>
          </div>
        );
      };

      render(
        <ProgressProvider enablePersistence={true} persistenceKey={persistenceKey}>
          <TestComponent />
        </ProgressProvider>
      );

      act(() => {
        screen.getByText('Update').click();
      });

      let savedData = localStorage.getItem(`modporter_progress_${persistenceKey}`);
      expect(savedData).toBeTruthy();

      act(() => {
        screen.getByText('Clear').click();
      });

      savedData = localStorage.getItem(`modporter_progress_${persistenceKey}`);
      expect(savedData).toBeNull();
    });

    test('should handle localStorage errors gracefully', () => {
      // Mock localStorage to throw errors
      const originalSetItem = localStorage.setItem;
      localStorage.setItem = vi.fn(() => {
        throw new Error('Storage quota exceeded');
      });

      const TestComponent = () => {
        const { actions } = useProgress();
        const handleUpdate = () => {
          actions.updateStatus({
            job_id: 'test-job',
            status: 'processing',
            progress: 50,
            message: 'Processing...',
            stage: 'Processing',
            estimated_time_remaining: 60,
            result_url: null,
            error: null,
            created_at: new Date().toISOString()
          });
        };

        return (
          <div>
            <div>Status updated</div>
            <button onClick={handleUpdate}>Update</button>
          </div>
        );
      };

      const consoleError = vi.spyOn(console, 'error');

      render(
        <ProgressProvider enablePersistence={true}>
          <TestComponent />
        </ProgressProvider>
      );

      act(() => {
        screen.getByText('Update').click();
      });

      // Should still update UI despite localStorage error
      expect(screen.getByText('Status updated')).toBeInTheDocument();
      // Should log the error
      expect(consoleError).toHaveBeenCalledWith(
        '[ProgressContext] Failed to persist status:',
        expect.any(Error)
      );

      // Restore localStorage
      localStorage.setItem = originalSetItem;
    });
  });
});
