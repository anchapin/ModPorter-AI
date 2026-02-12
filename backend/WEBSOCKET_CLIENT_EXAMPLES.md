"""
WebSocket Client Examples for ModPorter-AI

This file provides practical examples for connecting to and using
the WebSocket API from various client implementations.
"""

# ============================================================================
# 1. Python Client Example
# ============================================================================

import asyncio
import websockets
import json
from typing import Optional

class ConversionProgressClient:
    """WebSocket client for tracking conversion progress."""

    def __init__(self, conversion_id: str, ws_url: str = "ws://localhost:8080"):
        self.conversion_id = conversion_id
        self.ws_url = ws_url
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.connected = False

    async def connect(self):
        """Connect to the WebSocket server."""
        uri = f"{self.ws_url}/api/v1/conversions/{self.conversion_id}/ws"
        try:
            self.ws = await websockets.connect(uri)
            self.connected = True
            print(f"✓ Connected to conversion {self.conversion_id}")
            return True
        except Exception as e:
            print(f"✗ Connection failed: {e}")
            return False

    async def listen(self):
        """Listen for progress updates."""
        if not self.connected or not self.ws:
            print("Not connected!")
            return

        try:
            async for message in self.ws:
                data = json.loads(message)
                self._handle_message(data)
        except websockets.exceptions.ConnectionClosed:
            print("Connection closed")
        except Exception as e:
            print(f"Error listening for messages: {e}")

    def _handle_message(self, data: dict):
        """Handle incoming WebSocket message."""
        msg_type = data.get("type")
        payload = data.get("data", {})

        if msg_type == "connection_established":
            print(f"✓ {payload.get('message')}")
        elif msg_type == "agent_progress":
            agent = payload.get("agent")
            status = payload.get("status")
            progress = payload.get("progress")
            message = payload.get("message")
            print(f"[{progress}%] {agent}: {message} ({status})")
        elif msg_type == "conversion_complete":
            print(f"✓ Conversion complete!")
            download_url = payload.get("details", {}).get("download_url")
            if download_url:
                print(f"  Download: {self.ws_url.replace('ws://', 'http://')}{download_url}")
        elif msg_type == "conversion_failed":
            error = payload.get("details", {}).get("error", "Unknown error")
            print(f"✗ Conversion failed: {error}")

    async def close(self):
        """Close the WebSocket connection."""
        if self.ws:
            await self.ws.close()
            self.connected = False
            print("Connection closed")


# Usage
async def main():
    """Example usage of the WebSocket client."""
    # Connect to a conversion
    client = ConversionProgressClient("your-conversion-id-here")

    if await client.connect():
        # Listen for progress updates
        await client.listen()

    # Connection will close automatically on disconnect/error

# Run with: python -m asyncio main.py


# ============================================================================
# 2. JavaScript/Browser Client Example
# ============================================================================

"""
HTML/JavaScript example for browser WebSocket connection:

```html
<!DOCTYPE html>
<html>
<head>
    <title>Conversion Progress</title>
    <style>
        .progress-bar {
            width: 100%;
            height: 30px;
            background-color: #f0f0f0;
            border-radius: 5px;
            overflow: hidden;
        }
        .progress-fill {
            height: 100%;
            background-color: #4caf50;
            transition: width 0.3s ease;
        }
        .log {
            max-height: 300px;
            overflow-y: auto;
            font-family: monospace;
            font-size: 12px;
            padding: 10px;
            background: #f5f5f5;
            border: 1px solid #ddd;
        }
    </style>
</head>
<body>
    <h1>Conversion Progress</h1>

    <div>
        <label>Conversion ID:</label>
        <input type="text" id="conversionId" placeholder="Enter conversion ID">
        <button onclick="connect()">Connect</button>
        <button onclick="disconnect()">Disconnect</button>
    </div>

    <div id="progressSection" style="display: none;">
        <h2>Progress</h2>
        <div class="progress-bar">
            <div id="progressFill" class="progress-fill" style="width: 0%"></div>
        </div>
        <p id="progressText">0%</p>
        <p id="agentStatus">Waiting for updates...</p>
    </div>

    <h3>Log</h3>
    <div id="log" class="log"></div>

    <script>
        let ws = null;
        const API_BASE = 'http://localhost:8080';

        function log(message) {
            const logDiv = document.getElementById('log');
            const entry = document.createElement('div');
            entry.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
            logDiv.appendChild(entry);
            logDiv.scrollTop = logDiv.scrollHeight;
        }

        function connect() {
            const conversionId = document.getElementById('conversionId').value;
            if (!conversionId) {
                alert('Please enter a conversion ID');
                return;
            }

            const wsUrl = `ws://localhost:8080/api/v1/conversions/${conversionId}/ws`;
            log(`Connecting to ${wsUrl}...`);

            ws = new WebSocket(wsUrl);

            ws.onopen = () => {
                log('✓ Connected');
                document.getElementById('progressSection').style.display = 'block';
            };

            ws.onmessage = (event) => {
                const message = JSON.parse(event.data);
                handleMessage(message);
            };

            ws.onerror = (error) => {
                log(`✗ Error: ${error}`);
            };

            ws.onclose = () => {
                log('Connection closed');
            };
        }

        function disconnect() {
            if (ws) {
                ws.close();
                ws = null;
                log('Disconnected');
            }
        }

        function handleMessage(message) {
            const type = message.type;
            const data = message.data;

            if (type === 'connection_established') {
                log(`✓ ${data.message}`);
            }
            else if (type === 'agent_progress') {
                const agent = data.agent;
                const status = data.status;
                const progress = data.progress;
                const msg = data.message;

                // Update progress bar
                document.getElementById('progressFill').style.width = `${progress}%`;
                document.getElementById('progressText').textContent = `${progress}%`;
                document.getElementById('agentStatus').textContent =
                    `${agent}: ${msg}`;

                log(`[${progress}%] ${agent} - ${msg} (${status})`);

                // Check if complete
                if (status === 'completed') {
                    document.getElementById('progressFill').style.backgroundColor = '#4caf50';
                }
            }
            else if (type === 'conversion_complete') {
                log('✓ Conversion completed successfully!');
                const downloadUrl = data.details?.download_url;
                if (downloadUrl) {
                    const fullUrl = `${API_BASE}${downloadUrl}`;
                    log(`Download: ${fullUrl}`);

                    // Add download button
                    const downloadBtn = document.createElement('button');
                    downloadBtn.textContent = 'Download .mcaddon';
                    downloadBtn.onclick = () => window.open(fullUrl);
                    document.getElementById('progressSection').appendChild(downloadBtn);
                }
            }
            else if (type === 'conversion_failed') {
                const error = data.details?.error || 'Unknown error';
                log(`✗ Conversion failed: ${error}`);
                document.getElementById('progressFill').style.backgroundColor = '#f44336';
            }
        }
    </script>
</body>
</html>
```
"""


# ============================================================================
# 3. Node.js Client Example
# ============================================================================

"""
Node.js example using the `ws` package:

```javascript
// npm install ws

const WebSocket = require('ws');

class ConversionProgressClient {
  constructor(conversionId, wsUrl = 'ws://localhost:8080') {
    this.conversionId = conversionId;
    this.wsUrl = wsUrl;
    this.ws = null;
  }

  connect() {
    const uri = `${this.wsUrl}/api/v1/conversions/${this.conversionId}/ws`;

    this.ws = new WebSocket(uri);

    this.ws.on('open', () => {
      console.log(`✓ Connected to conversion ${this.conversionId}`);
    });

    this.ws.on('message', (data) => {
      const message = JSON.parse(data);
      this.handleMessage(message);
    });

    this.ws.on('error', (error) => {
      console.error('✗ WebSocket error:', error);
    });

    this.ws.on('close', () => {
      console.log('Connection closed');
    });
  }

  handleMessage(message) {
    const type = message.type;
    const data = message.data;

    if (type === 'connection_established') {
      console.log(`✓ ${data.message}`);
    }
    else if (type === 'agent_progress') {
      const { agent, status, progress, message: msg } = data;
      console.log(`[${progress}%] ${agent}: ${msg} (${status})`);
    }
    else if (type === 'conversion_complete') {
      console.log('✓ Conversion complete!');
      const downloadUrl = data.details?.download_url;
      if (downloadUrl) {
        const fullUrl = this.wsUrl.replace('ws://', 'http://') + downloadUrl;
        console.log(`  Download: ${fullUrl}`);
      }
    }
    else if (type === 'conversion_failed') {
      const error = data.details?.error || 'Unknown error';
      console.error(`✗ Conversion failed: ${error}`);
    }
  }

  close() {
    if (this.ws) {
      this.ws.close();
    }
  }
}

// Usage
const client = new ConversionProgressClient('your-conversion-id');
client.connect();

// Keep process running
process.on('SIGINT', () => {
  client.close();
  process.exit(0);
});
```
"""


# ============================================================================
# 4. React Hook Example
# ============================================================================

"""
React custom hook for WebSocket connection:

```typescript
import { useEffect, useState, useCallback, useRef } from 'react';
import { WebSocket } from 'fastapi-websocket-pusher';

interface ConversionProgress {
  agent: string;
  status: string;
  progress: number;
  message: string;
  timestamp: string;
  details?: Record<string, any>;
}

interface WebSocketMessage {
  type: string;
  data: ConversionProgress;
}

interface UseConversionProgressOptions {
  onProgress?: (progress: ConversionProgress) => void;
  onComplete?: (downloadUrl: string) => void;
  onError?: (error: string) => void;
}

export function useConversionProgress(
  conversionId: string | null,
  options: UseConversionProgressOptions = {}
) {
  const [connected, setConnected] = useState(false);
  const [currentProgress, setCurrentProgress] = useState<ConversionProgress | null>(null);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  const { onProgress, onComplete, onError } = options;

  useEffect(() => {
    if (!conversionId) return;

    const wsUrl = `ws://localhost:8080/api/v1/conversions/${conversionId}/ws`;
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log('WebSocket connected');
      setConnected(true);
      setError(null);
    };

    ws.onmessage = (event) => {
      const message: WebSocketMessage = JSON.parse(event.data);

      if (message.type === 'agent_progress') {
        setCurrentProgress(message.data);
        onProgress?.(message.data);
      }
      else if (message.type === 'conversion_complete') {
        const downloadUrl = message.data.details?.download_url || '';
        onComplete?.(downloadUrl);
      }
      else if (message.type === 'conversion_failed') {
        const errorMessage = message.data.details?.error || 'Unknown error';
        setError(errorMessage);
        onError?.(errorMessage);
      }
    };

    ws.onerror = (event) => {
      console.error('WebSocket error:', event);
      setError('Connection error');
    };

    ws.onclose = () => {
      console.log('WebSocket disconnected');
      setConnected(false);
    };

    wsRef.current = ws;

    return () => {
      ws.close();
    };
  }, [conversionId, onProgress, onComplete, onError]);

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
    }
  }, []);

  return {
    connected,
    currentProgress,
    error,
    disconnect,
  };
}

// Usage in component:
export function ConversionProgressTracker({ conversionId }: { conversionId: string }) {
  const { connected, currentProgress, error } = useConversionProgress(
    conversionId,
    {
      onProgress: (progress) => {
        console.log(`Progress: ${progress.progress}% - ${progress.message}`);
      },
      onComplete: (downloadUrl) => {
        console.log('Download ready:', downloadUrl);
        // Trigger download or show button
      },
      onError: (error) => {
        console.error('Conversion failed:', error);
      },
    }
  );

  return (
    <div>
      <h3>Conversion Progress</h3>
      {connected ? (
        <span className="badge badge-success">Connected</span>
      ) : (
        <span className="badge badge-warning">Disconnected</span>
      )}

      {currentProgress && (
        <div>
          <p>Agent: {currentProgress.agent}</p>
          <p>Status: {currentProgress.status}</p>
          <div className="progress">
            <div
              className="progress-bar"
              role="progressbar"
              style={{ width: `${currentProgress.progress}%` }}
            >
              {currentProgress.progress}%
            </div>
          </div>
          <p className="text-muted">{currentProgress.message}</p>
        </div>
      )}

      {error && (
        <div className="alert alert-danger">
          <strong>Error:</strong> {error}
        </div>
      )}
    </div>
  );
}
```
"""


# ============================================================================
# 5. Command Line Testing
# ============================================================================

"""
Simple command-line testing using websocat:

```bash
# Install websocat
# cargo install websocat  (Rust)
# or brew install websocat  (macOS)

# Connect to WebSocket
websocat ws://localhost:8080/api/v1/conversions/{conversion_id}/ws

# You'll see messages like:
# {"type":"connection_established","data":{"conversion_id":"...","message":"Connected...","timestamp":"..."}}
# {"type":"agent_progress","data":{"agent":"JavaAnalyzerAgent","status":"in_progress","progress":10,"message":"Parsing Java AST...","timestamp":"..."}}
```
"""
