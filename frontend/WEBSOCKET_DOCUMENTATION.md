# WebSocket Integration Documentation

## Overview

This document describes the WebSocket integration for real-time conversion progress tracking in the ModPorter-AI frontend.

## Architecture

### Components

1. **ProgressContext** (`frontend/src/contexts/ProgressContext.tsx`)
   - React context for managing progress state across components
   - Handles WebSocket lifecycle (connect, disconnect, reconnect)
   - Provides state persistence to localStorage
   - Manages progress history

2. **ConversionWebSocket Service** (`frontend/src/services/websocket.ts`)
   - Low-level WebSocket wrapper
   - Handles connection management
   - Implements exponential backoff reconnection
   - Provides event-based message handling

3. **ConnectionStatusIndicator** (`frontend/src/components/ui/ConnectionStatusIndicator.tsx`)
   - Visual component for displaying connection status
   - Shows connection state (connecting, connected, disconnected, error)
   - Provides user-friendly messages

4. **ConversionProgress Component** (`frontend/src/components/ConversionProgress/ConversionProgress.tsx`)
   - Main UI component for displaying conversion progress
   - Uses ProgressContext for state management
   - Wrapped with ProgressErrorBoundary for error handling

5. **ProgressErrorBoundary** (`frontend/src/components/ErrorBoundary/ProgressErrorBoundary.tsx`)
   - Specialized error boundary for progress components
   - Catches and recovers from WebSocket and state errors
   - Provides user-friendly error recovery options

## WebSocket Message Protocol

### Connection URL

```
ws://<API_BASE_URL>/api/v1/conversions/<job_id>/ws
```

Where:
- `<API_BASE_URL>` is derived from `VITE_API_BASE_URL` environment variable
- `<job_id>` is the unique conversion job identifier

### Message Format

All WebSocket messages are JSON-encoded with the following structure:

```typescript
interface ConversionStatus {
  job_id: string;
  status: string; // 'queued', 'processing', 'completed', 'failed', 'cancelled'
  progress: number; // 0-100
  message: string;
  stage?: string | null;
  estimated_time_remaining?: number | null; // seconds
  result_url?: string | null;
  error?: string | null;
  created_at: string; // ISO datetime
}
```

### Extended Message Format

The backend may send extended messages with additional agent information:

```typescript
interface ExtendedConversionStatus extends ConversionStatus {
  agents?: AgentStatus[];
  current_agent?: string;
}

interface AgentStatus {
  name: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress: number;
  message?: string;
}
```

### Message Flow

1. **Initial Connection**
   - Frontend connects to WebSocket endpoint
   - No initial message required from frontend
   - Backend sends initial status immediately upon connection

2. **Progress Updates**
   - Backend sends status updates as conversion progresses
   - Each message contains the complete current state
   - Frontend updates UI on each message

3. **Completion**
   - Backend sends final status (completed/failed/cancelled)
   - Frontend automatically disconnects after terminal status
   - Connection is cleaned up

4. **Error Handling**
   - Backend sends error status if conversion fails
   - Error details included in `error` field
   - Frontend displays error to user

## Connection Management

### Connection States

- **`connecting`**: Attempting to establish WebSocket connection
- **`connected`**: WebSocket connection active, receiving updates
- **`disconnected`**: Connection closed, using fallback polling
- **`error`**: Connection error occurred

### Reconnection Logic

The WebSocket service implements exponential backoff reconnection:

1. Initial connection attempt
2. If connection fails, wait 1 second and retry
3. Each subsequent retry doubles the wait time
4. Maximum wait time: 30 seconds
5. Maximum retry attempts: 5
6. After 5 failed attempts, fall back to HTTP polling

### Fallback Polling

If WebSocket connection cannot be established after 5 attempts:

- Frontend switches to HTTP polling mode
- Polls conversion status every 3 seconds via REST API
- Updates continue to be displayed to user
- Connection status indicator shows "Using fallback polling"

## State Management

### ProgressContext State

```typescript
interface ProgressState {
  status: ConversionStatus | null;        // Current conversion status
  connectionStatus: ConnectionStatus;      // WebSocket connection state
  usingWebSocket: boolean;                // Using WebSocket or polling
  connectionError: string | null;         // Connection error message
  history: ConversionStatus[];           // Progress history (last 50)
}
```

### ProgressContext Actions

```typescript
interface ProgressActions {
  updateStatus: (status: ConversionStatus) => void;  // Update conversion status
  clearStatus: () => void;                            // Clear current status
  setConnectionStatus: (status: ConnectionStatus) => void;  // Update connection state
  setConnectionError: (error: string | null) => void;     // Set connection error
  connectToJob: (jobId: string) => void;              // Connect to job WebSocket
  disconnectFromJob: () => void;                     // Disconnect from job
}
```

### State Persistence

Progress state is persisted to localStorage for recovery:

- **Storage Key**: `modporter_progress_<persistenceKey>`
- **History Key**: `modporter_progress_history_<persistenceKey>`
- **Default Persistence**: Enabled
- **History Limit**: 50 entries (most recent)

To disable persistence:
```tsx
<ProgressProvider enablePersistence={false}>
  {/* children */}
</ProgressProvider>
```

To use custom persistence key:
```tsx
<ProgressProvider persistenceKey="custom-key">
  {/* children */}
</ProgressProvider>
```

## Usage Examples

### Basic Usage

```tsx
import { ProgressProvider, useProgress } from '../contexts/ProgressContext';
import { ConnectionStatusIndicator } from '../components/ui/ConnectionStatusIndicator';

function MyComponent() {
  const { state, actions } = useProgress();

  const handleStartConversion = () => {
    // Start conversion and get job ID
    const jobId = '123e4567-e89b-12d3-a456-426614174000';
    actions.connectToJob(jobId);
  };

  return (
    <div>
      <ConnectionStatusIndicator
        status={state.connectionStatus}
        usingWebSocket={state.usingWebSocket}
        error={state.connectionError}
      />
      {state.status && (
        <div>Progress: {state.status.progress}%</div>
      )}
      <button onClick={handleStartConversion}>Start Conversion</button>
    </div>
  );
}

// Wrap your app with ProgressProvider
function App() {
  return (
    <ProgressProvider>
      <MyComponent />
    </ProgressProvider>
  );
}
```

### Using ConversionProgress Component

```tsx
import ConversionProgress from '../components/ConversionProgress/ConversionProgress';

function MyComponent() {
  const jobId = '123e4567-e89b-12d3-a456-426614174000';

  return (
    <ConversionProgress
      jobId={jobId}
      status="queued"
      progress={0}
      message="Starting conversion..."
      stage="Queued"
    />
  );
}
```

### Error Handling

```tsx
import { ProgressErrorBoundary } from '../components/ErrorBoundary/ProgressErrorBoundary';

function MyComponent() {
  const { state } = useProgress();

  const handleError = (error: Error, errorInfo: any) => {
    console.error('Progress error:', error, errorInfo);
    // Log to error reporting service
  };

  return (
    <ProgressErrorBoundary onError={handleError}>
      <ConversionProgress jobId="123e4567-e89b-12d3-a456-426614174000" />
    </ProgressErrorBoundary>
  );
}
```

## Performance Considerations

### Memory Management

1. **WebSocket Cleanup**
   - Always disconnect WebSocket when component unmounts
   - ProgressProvider handles cleanup automatically
   - No manual cleanup required when using ProgressContext

2. **History Limiting**
   - Progress history limited to 50 entries
   - Old entries automatically removed
   - Prevents unbounded memory growth

3. **Event Handler Registration**
   - Message and status handlers are properly unregistered
   - No memory leaks from unclosed WebSocket connections
   - Cleanup happens on disconnect

### Network Efficiency

1. **WebSocket vs Polling**
   - WebSocket: Single connection, push updates
   - Polling: 1 request every 3 seconds
   - WebSocket preferred for real-time updates

2. **Connection Reuse**
   - Single WebSocket connection per job
   - Reused across component re-renders
   - Closed only when job completes or user navigates away

## Security Considerations

1. **Authentication**
   - WebSocket inherits authentication from parent HTTP connection
   - No separate authentication required
   - Uses same cookies/tokens as REST API

2. **Input Validation**
   - All messages validated against TypeScript interfaces
   - Invalid messages logged and ignored
   - No code execution from WebSocket messages

3. **Error Messages**
   - Error messages sanitized before display
   - No sensitive information leaked
   - User-friendly error messages only

## Testing

### Mocking WebSocket

```typescript
import { vi } from 'vitest';

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
```

### Testing ProgressContext

```typescript
import { render, screen } from '@testing-library/react';
import { ProgressProvider, useProgress } from './ProgressContext';

const TestComponent = () => {
  const { state, actions } = useProgress();

  return (
    <div>
      <div>Status: {state.status?.status || 'null'}</div>
      <button onClick={() => actions.connectToJob('test-job')}>
        Connect
      </button>
    </div>
  );
};

test('should connect to job', () => {
  render(
    <ProgressProvider>
      <TestComponent />
    </ProgressProvider>
  );

  screen.getByText('Connect').click();
  // Assert connection established
});
```

## Troubleshooting

### Common Issues

1. **WebSocket Connection Fails**
   - Check `VITE_API_BASE_URL` environment variable
   - Verify backend WebSocket endpoint is accessible
   - Check browser console for WebSocket errors
   - Verify CORS configuration

2. **Connection Drops Frequently**
   - Check network stability
   - Verify timeout settings on backend
   - Check for proxy/firewall issues
   - Review exponential backoff configuration

3. **State Not Updating**
   - Verify ProgressProvider wraps your component
   - Check console for error messages
   - Ensure job ID is correct
   - Verify WebSocket message format

4. **Memory Leaks**
   - Ensure components unmount properly
   - Check for infinite re-render loops
   - Verify event handlers are cleaned up
   - Review React DevTools Profiler

### Debugging

Enable debug logging:

```typescript
// In development
if (process.env.NODE_ENV === 'development') {
  // ProgressContext logs to console
  // WebSocket service logs to console
  // Enable browser DevTools Network tab to see WebSocket frames
}
```

## Future Enhancements

1. **Connection Pooling**
   - Support multiple simultaneous jobs
   - Shared WebSocket connections
   - Reduced overhead

2. **Offline Support**
   - Service worker for offline caching
   - Queue progress updates
   - Sync when reconnected

3. **Advanced Metrics**
   - Connection latency tracking
   - Message loss detection
   - Performance monitoring

4. **Custom Backoff Strategies**
   - Configurable reconnection delays
   - User-defined retry limits
   - Adaptive backoff algorithms

## References

- [WebSocket API](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)
- [React Context API](https://react.dev/reference/react/useContext)
- [React Error Boundaries](https://react.dev/reference/react/Component#catching-rendering-errors-with-an-error-boundary)
- [Project Issue #577](https://github.com/anchapin/ModPorter-AI/issues/577)
