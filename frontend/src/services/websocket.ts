/**
 * WebSocket Service for Real-time Conversion Progress
 * Handles WebSocket connection, reconnection, and message parsing
 */

import { ConversionStatus } from '../types/api';

export type WebSocketMessageHandler = (data: ConversionStatus) => void;
export type WebSocketStatusHandler = (
  status: 'connecting' | 'connected' | 'disconnected' | 'error'
) => void;

export class ConversionWebSocket {
  private ws: WebSocket | null = null;
  private url: string;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000; // Start with 1 second
  private maxReconnectDelay = 30000; // Max 30 seconds
  private reconnectTimeout: ReturnType<typeof setTimeout> | null = null;
  private intentionalClose = false;

  private messageHandlers: Set<WebSocketMessageHandler> = new Set();
  private statusHandlers: Set<WebSocketStatusHandler> = new Set();

  constructor(private jobId: string) {
    // Determine WebSocket URL based on environment
    // Priority: VITE_API_BASE_URL > derived from VITE_API_URL > default

    // In development with Vite proxy:
    // - Set VITE_API_BASE_URL to empty string (use proxy)
    // - Set VITE_API_URL to include /api/v1 path

    let apiBase: string;

    if (import.meta.env.VITE_API_BASE_URL) {
      // Explicit base URL provided (e.g., https://api.portkit.cloud)
      apiBase = import.meta.env.VITE_API_BASE_URL;
    } else if (import.meta.env.VITE_API_URL) {
      // Derive from full API URL (e.g., http://localhost:8000/api/v1 -> http://localhost:8000)
      apiBase = import.meta.env.VITE_API_URL.replace(/\/api\/v1$/, '');
    } else {
      // Development with Vite proxy: use relative URL
      // The proxy handles /api/* and /ws/* routes
      apiBase = '';
    }

    // Convert http/https to ws/wss for WebSocket
    this.url =
      apiBase.replace(/^http:/, 'ws:').replace(/^https:/, 'wss:') +
      `/api/v1/conversions/${this.jobId}/ws`;
  }

  /**
   * Connect to WebSocket
   */
  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      console.log('[WebSocket] Already connected');
      return;
    }

    this.notifyStatusHandlers('connecting');
    this.intentionalClose = false;

    try {
      this.ws = new WebSocket(this.url);

      this.ws.onopen = () => {
        console.log('[WebSocket] Connected successfully');
        this.reconnectAttempts = 0;
        this.reconnectDelay = 1000;
        this.notifyStatusHandlers('connected');
      };

      this.ws.onmessage = (event) => {
        try {
          const rawData = JSON.parse(event.data);
          console.log('[WebSocket] Raw message received:', rawData);

          // Handle wrapped format from backend: { type: "agent_progress", data: {...} }
          // or connection confirmation: { type: "connection_established", data: {...} }
          let data;
          if (rawData.type && rawData.data) {
            // Extract relevant fields from the wrapped format
            const progressData = rawData.data;

            // Map agent status to conversion status
            const statusMap: Record<string, string> = {
              queued: 'queued',
              in_progress: 'preprocessing',
              completed: 'completed',
              failed: 'failed',
              skipped: 'cancelled',
            };
            const mappedStatus =
              statusMap[progressData.status] || progressData.status;

            data = {
              job_id: progressData.conversion_id || this.jobId,
              status: mappedStatus,
              progress: progressData.progress || 0,
              message: progressData.message || '',
              stage: progressData.agent || null,
              created_at: progressData.timestamp || new Date().toISOString(),
              error: progressData.details?.error || null,
            };

            // Handle terminal messages
            if (rawData.type === 'conversion_complete') {
              data.status = 'completed';
              data.progress = 100;
              data.message =
                progressData.message || 'Conversion completed successfully';
            } else if (rawData.type === 'conversion_failed') {
              data.status = 'failed';
              data.message = progressData.message || 'Conversion failed';
              data.error = progressData.details?.error || data.message;
            }
          } else {
            // Direct format (legacy or direct ConversionStatus)
            data = rawData as ConversionStatus;
          }

          console.log('[WebSocket] Parsed message:', data);
          this.notifyMessageHandlers(data);
        } catch (error) {
          console.error('[WebSocket] Failed to parse message:', error);
        }
      };

      this.ws.onclose = (event) => {
        console.log(
          `[WebSocket] Connection closed: ${event.code} - ${event.reason}`
        );

        if (!this.intentionalClose) {
          this.notifyStatusHandlers('disconnected');
          this.attemptReconnect();
        }
      };

      this.ws.onerror = (error) => {
        console.error('[WebSocket] Error:', error);
        this.notifyStatusHandlers('error');
      };
    } catch (error) {
      console.error(
        '[WebSocket] Failed to create WebSocket connection:',
        error
      );
      this.notifyStatusHandlers('error');
    }
  }

  /**
   * Disconnect from WebSocket
   */
  disconnect(): void {
    this.intentionalClose = true;

    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }

    if (this.ws) {
      this.ws.close(1000, 'User disconnected');
      this.ws = null;
    }
  }

  /**
   * Attempt to reconnect with exponential backoff
   */
  private attemptReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('[WebSocket] Max reconnection attempts reached');
      return;
    }

    this.reconnectAttempts++;
    const delay = Math.min(
      this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1),
      this.maxReconnectDelay
    );

    console.log(
      `[WebSocket] Attempting reconnect ${this.reconnectAttempts}/${this.maxReconnectAttempts} in ${delay}ms`
    );

    this.reconnectTimeout = setTimeout(() => {
      this.connect();
    }, delay);
  }

  /**
   * Register a message handler
   */
  onMessage(handler: WebSocketMessageHandler): () => void {
    this.messageHandlers.add(handler);
    return () => this.messageHandlers.delete(handler);
  }

  /**
   * Register a status handler
   */
  onStatus(handler: WebSocketStatusHandler): () => void {
    this.statusHandlers.add(handler);
    return () => this.statusHandlers.delete(handler);
  }

  /**
   * Notify all message handlers
   */
  private notifyMessageHandlers(data: ConversionStatus): void {
    this.messageHandlers.forEach((handler) => {
      try {
        handler(data);
      } catch (error) {
        console.error('[WebSocket] Error in message handler:', error);
      }
    });
  }

  /**
   * Notify all status handlers
   */
  private notifyStatusHandlers(
    status: 'connecting' | 'connected' | 'disconnected' | 'error'
  ): void {
    this.statusHandlers.forEach((handler) => {
      try {
        handler(status);
      } catch (error) {
        console.error('[WebSocket] Error in status handler:', error);
      }
    });
  }

  /**
   * Get connection state
   */
  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  /**
   * Clean up resources
   */
  destroy(): void {
    this.disconnect();
    this.messageHandlers.clear();
    this.statusHandlers.clear();
  }
}

/**
 * Factory function to create a WebSocket connection
 */
export const createConversionWebSocket = (
  jobId: string
): ConversionWebSocket => {
  return new ConversionWebSocket(jobId);
};
