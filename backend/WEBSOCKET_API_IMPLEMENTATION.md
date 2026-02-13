# WebSocket and Conversion API Implementation

This document describes the implementation of WebSocket support and Conversion REST API endpoints for the ModPorter-AI backend.

## Overview

This implementation adds:
- **WebSocket server** for real-time conversion progress updates
- **REST API endpoints** for managing conversion jobs
- **Integration** with existing conversion workflow

## Architecture

### Components

1. **WebSocket Manager** (`websocket/manager.py`)
   - Manages active WebSocket connections
   - Supports multiple concurrent clients per conversion
   - Handles connection lifecycle (connect/disconnect)
   - Broadcasts messages to connected clients

2. **Progress Handler** (`websocket/progress_handler.py`)
   - Defines message schemas for progress updates
   - Provides helper methods for broadcasting agent status
   - Handles conversion completion/failure notifications

3. **Conversion API** (`api/conversions.py`)
   - REST endpoints for conversion management
   - WebSocket endpoint for real-time progress
   - File upload validation and processing
   - Integration with database and cache

### Message Flow

```
Client                    Backend                    AI Engine
  |                          |                            |
  |-- POST /conversions ---->|                            |
  |                          |-- Create job in DB -------->|
  |<-- 202 Accepted ---------|                            |
  |                          |                            |
  |-- WS connect ----------->|                            |
  |<-- Connection confirmed -|                            |
  |                          |                            |
  |                          |-- Start conversion -------->|
  |                          |                            |
  |<-- Agent: JavaAnalyzer --|                            |
  |     (0-25%)              |                            |
  |                          |                            |
  |<-- Agent: BedrockArch ---|                            |
  |     (25-50%)             |                            |
  |                          |                            |
  |<-- Agent: LogicTrans ----|                            |
  |     (50-75%)             |                            |
  |                          |                            |
  |<-- Agent: AssetConverter -|                            |
  |     (75-90%)             |                            |
  |                          |                            |
  |<-- Agent: Packaging -----|                            |
  |     (90-100%)            |                            |
  |                          |                            |
  |<-- Conversion Complete --|                            |
  |                          |                            |
  |-- GET /download -------->|                            |
  |<-- .mcaddon file --------|                            |
```

## WebSocket Protocol

### Connection

**Endpoint:** `WS /api/v1/conversions/{conversion_id}/ws`

Connect to this endpoint to receive real-time progress updates for a conversion.

**Example:**
```javascript
const ws = new WebSocket(`ws://localhost:8080/api/v1/conversions/${conversionId}/ws`);

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  console.log('Received:', message);
};
```

### Message Format

All messages from server follow this structure:

```json
{
  "type": "message_type",
  "data": {
    "agent": "AgentName",
    "status": "in_progress",
    "progress": 45,
    "message": "Human-readable message",
    "timestamp": "2025-02-12T10:30:00Z",
    "details": {}
  }
}
```

### Message Types

#### 1. Connection Established

Sent immediately after WebSocket connection is accepted.

```json
{
  "type": "connection_established",
  "data": {
    "conversion_id": "uuid-v4",
    "message": "Connected to conversion progress stream",
    "timestamp": "2025-02-12T10:30:00Z"
  }
}
```

#### 2. Agent Progress

Sent when an agent's status changes.

```json
{
  "type": "agent_progress",
  "data": {
    "agent": "JavaAnalyzerAgent",
    "status": "in_progress",
    "progress": 45,
    "message": "Analyzing Java AST...",
    "timestamp": "2025-02-12T10:30:00Z",
    "details": {
      "files_processed": 15,
      "total_files": 33
    }
  }
}
```

**Agent Status Values:**
- `queued`: Agent is waiting to start
- `in_progress`: Agent is actively processing
- `completed`: Agent finished successfully
- `failed`: Agent encountered an error
- `skipped`: Agent was not needed

#### 3. Conversion Complete

Sent when entire conversion finishes successfully.

```json
{
  "type": "conversion_complete",
  "data": {
    "agent": "ConversionWorkflow",
    "status": "completed",
    "progress": 100,
    "message": "Conversion completed successfully",
    "timestamp": "2025-02-12T10:45:00Z",
    "details": {
      "download_url": "/api/v1/conversions/{id}/download"
    }
  }
}
```

#### 4. Conversion Failed

Sent when conversion encounters an error.

```json
{
  "type": "conversion_failed",
  "data": {
    "agent": "ConversionWorkflow",
    "status": "failed",
    "progress": 0,
    "message": "Conversion failed: Could not parse Java file",
    "timestamp": "2025-02-12T10:35:00Z",
    "details": {
      "error": "Could not parse Java file"
    }
  }
}
```

## REST API Endpoints

### 1. Create Conversion

**Endpoint:** `POST /api/v1/conversions`

**Request:** `multipart/form-data`
- `file`: Binary file (.jar or .zip)
- `options`: JSON string with conversion options

**Example:**
```bash
curl -X POST http://localhost:8080/api/v1/conversions \
  -F "file=@mod.jar" \
  -F 'options={"assumptions":"conservative","target_version":"1.20.0"}'
```

**Response:** `202 Accepted`
```json
{
  "conversion_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "estimated_time_seconds": 1800,
  "created_at": "2025-02-12T10:30:00Z"
}
```

### 2. Get Conversion Status

**Endpoint:** `GET /api/v1/conversions/{conversion_id}`

**Response:**
```json
{
  "conversion_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "progress": 45,
  "message": "JavaAnalyzerAgent is analyzing mod structure...",
  "created_at": "2025-02-12T10:30:00Z",
  "updated_at": "2025-02-12T10:35:00Z",
  "result_url": null,
  "error": null,
  "original_filename": "example_mod.jar"
}
```

### 3. List Conversions

**Endpoint:** `GET /api/v1/conversions?page=1&page_size=20&status=processing`

**Query Parameters:**
- `page`: Page number (default: 1)
- `page_size`: Items per page (default: 20, max: 100)
- `status`: Filter by status (optional)

**Response:**
```json
{
  "conversions": [...],
  "total": 42,
  "page": 1,
  "page_size": 20
}
```

### 4. Delete Conversion

**Endpoint:** `DELETE /api/v1/conversions/{conversion_id}`

**Response:** `204 No Content`

### 5. Download Result

**Endpoint:** `GET /api/v1/conversions/{conversion_id}/download`

**Response:** Binary file download (.mcaddon)

## Security Features

### File Upload Validation

1. **File Type Check**
   - Only `.jar` and `.zip` files allowed
   - Validation based on file extension

2. **File Size Limit**
   - Maximum 100MB per upload
   - Enforced during file read

3. **Filename Sanitization**
   - Removes path traversal attempts
   - Strips dangerous characters
   - Generates safe filename for storage

4. **UUID Assignment**
   - Each upload gets unique UUID
   - Original filename preserved in metadata
   - File stored with UUID-based name

### Rate Limiting

Rate limiting should be implemented at the middleware level (TODO).

## Integration with Conversion Workflow

### Broadcasting Progress

The conversion workflow (`simulate_ai_conversion()` in `main.py`) broadcasts progress through WebSocket:

```python
from websocket.progress_handler import ProgressHandler

# Agent starts
await ProgressHandler.broadcast_agent_start(
    conversion_id, "JavaAnalyzerAgent", "Starting analysis"
)

# Agent progress
await ProgressHandler.broadcast_agent_update(
    conversion_id, "JavaAnalyzerAgent", 50, "Halfway through analysis"
)

# Agent complete
await ProgressHandler.broadcast_agent_complete(
    conversion_id, "JavaAnalyzerAgent"
)

# Conversion complete
await ProgressHandler.broadcast_conversion_complete(
    conversion_id, download_url
)
```

### Agent Progress Stages

The conversion workflow simulates these agents:

1. **JavaAnalyzerAgent** (0-25%)
   - Analyzes Java mod structure
   - Parses dependencies
   - Identifies components

2. **BedrockArchitectAgent** (25-50%)
   - Designs conversion strategy
   - Maps Java to Bedrock equivalents
   - Plans architecture

3. **LogicTranslatorAgent** (50-75%)
   - Converts Java logic to JavaScript
   - Translates behaviors
   - Adapts game mechanics

4. **AssetConverterAgent** (75-90%)
   - Converts textures
   - Transforms models
   - Adapts sounds

5. **PackagingAgent** (90-100%)
   - Creates manifests
   - Packages into .mcaddon
   - Finalizes output

## Testing

### Running Tests

```bash
cd backend
pytest tests/test_websocket_integration.py -v
```

### Test Coverage

Tests cover:
- WebSocket connection management
- Message broadcasting
- Multi-client scenarios
- Progress message serialization
- API endpoint functionality
- Error handling
- Security validation

## Client Implementation Example

### React Component Example

```typescript
import { useEffect, useState } from 'react';
import { WebSocket } from 'fastapi-websocket-pusher';

interface ConversionProgress {
  agent: string;
  status: string;
  progress: number;
  message: string;
  timestamp: string;
}

export function ConversionProgress({ conversionId }: { conversionId: string }) {
  const [progress, setProgress] = useState<ConversionProgress | null>(null);

  useEffect(() => {
    const ws = new WebSocket(
      `ws://localhost:8080/api/v1/conversions/${conversionId}/ws`
    );

    ws.onopen = () => {
      console.log('Connected to conversion progress');
    };

    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);

      if (message.type === 'agent_progress') {
        setProgress(message.data);
      } else if (message.type === 'conversion_complete') {
        console.log('Conversion complete!', message.data);
      } else if (message.type === 'conversion_failed') {
        console.error('Conversion failed', message.data);
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    ws.onclose = () => {
      console.log('Disconnected from conversion progress');
    };

    return () => {
      ws.close();
    };
  }, [conversionId]);

  if (!progress) {
    return <div>Connecting...</div>;
  }

  return (
    <div>
      <h3>{progress.agent}</h3>
      <p>Status: {progress.status}</p>
      <div style={{ width: '100%', backgroundColor: '#e0e0e0' }}>
        <div
          style={{
            width: `${progress.progress}%`,
            backgroundColor: '#4caf50',
            height: '20px'
          }}
        />
      </div>
      <p>{progress.message}</p>
    </div>
  );
}
```

## Performance Considerations

### Connection Management

- Active connections tracked per conversion
- Automatic cleanup on disconnect
- Efficient broadcast to multiple clients
- No memory leaks from abandoned connections

### Scalability

- Stateless design allows horizontal scaling
- Redis cache for fast status retrieval
- Database as source of truth
- WebSocket connections can be distributed

### Resource Limits

Consider setting these limits in production:
- Max connections per conversion: 10
- Max total connections: 1000
- Connection timeout: 30 minutes
- Message size limit: 1KB

## Future Enhancements

### Planned Features

1. **Authentication**
   - User-specific connections
   - Private conversion tracking
   - Access control

2. **Bi-directional Communication**
   - Client can control conversion
   - Pause/resume support
   - Cancellation through WebSocket

3. **Progress History**
   - Store progress events
   - Replay capability
   - Debugging support

4. **Advanced Filtering**
   - Subscribe to specific agents
   - Filter by progress threshold
   - Custom event types

### Open Questions

1. Should we use `fastapi-websocket-pusher` or custom implementation?
2. How to handle WebSocket reconnection gracefully?
3. Should progress events be persisted to database?
4. How to distribute WebSocket connections across multiple servers?

## Troubleshooting

### Common Issues

**Issue:** WebSocket connection fails
- **Solution:** Check CORS settings, ensure WebSocket upgrade is allowed

**Issue:** Progress not updating
- **Solution:** Verify conversion job exists, check background task execution

**Issue:** Multiple clients not receiving updates
- **Solution:** Check connection manager, verify broadcast is called correctly

**Issue:** File upload rejected
- **Solution:** Verify file type (.jar or .zip), check file size < 100MB

## References

- [FastAPI WebSocket Documentation](https://fastapi.tiangolo.com/advanced/websockets/)
- [WebSocket Protocol RFC](https://tools.ietf.org/html/rfc6455)
- [Multipart Form Data](https://tools.ietf.org/html/rfc7578)
