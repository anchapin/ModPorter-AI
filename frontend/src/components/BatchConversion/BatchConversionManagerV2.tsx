/**
 * Enhanced Batch Conversion Manager v2
 * Implements Phase 2.5.4: Batch Conversion Automation
 * 
 * Features:
 * - Batch upload interface with drag-drop
 * - Intelligent queue management
 * - Priority-based processing
 * - Batch progress tracking
 * - Per-item error handling
 * 
 * Success Criteria:
 * - 100 mods in <1 hour
 * - Queue efficiency >90%
 * - Per-mod tracking accuracy 100%
 */

import React, { useState, useCallback, useEffect, useRef } from 'react';
import {
  useSuccessNotification,
  useErrorNotification,
} from '../NotificationSystem';
import { API_BASE_URL } from '../../services/api';
import './BatchConversionManager.css';

// Types
export interface BatchItemV2 {
  itemId: string;
  filename: string;
  file: File;
  status: 'pending' | 'queued' | 'processing' | 'completed' | 'failed' | 'retrying';
  progress: number;
  priority: 'vip' | 'high' | 'normal' | 'low';
  error?: {
    type: string;
    message: string;
    recoverable: boolean;
  };
  startedAt?: string;
  completedAt?: string;
  resultPath?: string;
}

export interface BatchStatusV2 {
  batchId: string;
  status: string;
  totalItems: number;
  completedItems: number;
  failedItems: number;
  queuedItems: number;
  processingItems: number;
  progress: number;
  efficiency?: number;
  items: BatchItemV2[];
}

interface BatchConversionManagerV2Props {
  onComplete?: (batchId: string, results: BatchItemV2[]) => void;
}

export const BatchConversionManagerV2: React.FC<BatchConversionManagerV2Props> = ({
  onComplete,
}) => {
  const [batchId, setBatchId] = useState<string | null>(null);
  const [items, setItems] = useState<BatchItemV2[]>([]);
  const [isConverting, setIsConverting] = useState(false);
  const [isPolling, setIsPolling] = useState(false);
  const [queueStats, setQueueStats] = useState<any>(null);
  const [priority, setPriority] = useState<'vip' | 'high' | 'normal' | 'low'>('normal');
  const wsRef = useRef<WebSocket | null>(null);
  
  const successNotification = useSuccessNotification();
  const errorNotification = useErrorNotification();

  // Poll batch status
  const pollBatchStatus = useCallback(async () => {
    if (!batchId) return;
    
    try {
      const response = await fetch(`${API_BASE_URL}/batch/v2/${batchId}/status`);
      if (!response.ok) throw new Error('Failed to get batch status');
      
      const status: BatchStatusV2 = await response.json();
      
      // Update items
      setItems(status.items.map(item => ({
        itemId: item.itemId,
        filename: item.filename,
        file: items.find(i => i.filename === item.filename)?.file || new File([], item.filename),
        status: item.status as any,
        progress: item.progress,
        priority: item.priority >= 100 ? 'vip' : item.priority >= 75 ? 'high' : item.priority >= 25 ? 'low' : 'normal',
        error: item.error,
        startedAt: item.startedAt,
        completedAt: item.completedAt,
        resultPath: item.resultPath,
      })));
      
      // Check if completed
      if (status.status === 'completed' || status.status === 'partial' || status.status === 'failed') {
        setIsConverting(false);
        setIsPolling(false);
        
        if (status.status === 'completed') {
          successNotification(`Batch completed: ${status.completedItems} mods converted`);
          onComplete?.(batchId, items);
        } else if (status.status === 'partial') {
          errorNotification(`Batch partial: ${status.completedItems} succeeded, ${status.failedItems} failed`);
        }
      }
    } catch (err) {
      console.error('Poll error:', err);
    }
  }, [batchId, items, successNotification, errorNotification, onComplete]);

  // Poll queue stats
  const pollQueueStats = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/batch/v2/queue/stats`);
      if (!response.ok) return;
      
      const stats = await response.json();
      setQueueStats(stats);
    } catch (err) {
      // Silently fail
    }
  }, []);

  // Setup polling and WebSocket
  useEffect(() => {
    if (isPolling && batchId) {
      // Poll status every 2 seconds
      const statusInterval = setInterval(pollBatchStatus, 2000);
      
      // Poll queue stats every 5 seconds
      const statsInterval = setInterval(pollQueueStats, 5000);
      
      // Try WebSocket connection
      try {
        const ws = new WebSocket(`${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}${API_BASE_URL.replace('/api/v2', '').replace('http', 'ws')}/batch/v2/ws/${batchId}`);
        ws.onmessage = (event) => {
          const data = JSON.parse(event.data);
          if (data.type === 'update') {
            // Update specific item progress
            setItems(prev => prev.map(item => 
              item.itemId === data.data.itemId 
                ? { ...item, progress: data.data.progress, status: data.data.status as any }
                : item
            ));
          }
        };
        wsRef.current = ws;
      } catch (err) {
        console.log('WebSocket not available, using polling');
      }
      
      return () => {
        clearInterval(statusInterval);
        clearInterval(statsInterval);
        if (wsRef.current) {
          wsRef.current.close();
        }
      };
    }
  }, [isPolling, batchId, pollBatchStatus, pollQueueStats]);

  // Handle file selection
  const handleFileSelect = useCallback(
    (files: FileList | null) => {
      if (!files) return;

      const newItems: BatchItemV2[] = Array.from(files)
        .filter((file) => {
          const ext = file.name.toLowerCase().split('.').pop();
          return ext === 'jar' || ext === 'zip' || ext === 'tar';
        })
        .map((file) => ({
          itemId: crypto.randomUUID(),
          filename: file.name,
          file,
          status: 'pending' as const,
          progress: 0,
          priority: priority,
        }));

      if (newItems.length === 0) {
        errorNotification('No valid files. Supported: .jar, .zip, .tar.gz');
        return;
      }

      setItems((prev) => [...prev, ...newItems]);

      if (newItems.length > 0) {
        successNotification(`Added ${newItems.length} file(s) to batch`);
      }
    },
    [priority, successNotification, errorNotification]
  );

  // Remove item
  const removeItem = useCallback((itemId: string) => {
    setItems((prev) => prev.filter((item) => item.itemId !== itemId));
  }, []);

  // Clear all
  const clearAll = useCallback(() => {
    setItems([]);
    setBatchId(null);
    setIsConverting(false);
    setIsPolling(false);
  }, []);

  // Start batch conversion
  const startBatchConversion = useCallback(async () => {
    const pendingItems = items.filter((i) => i.status === 'pending');
    if (pendingItems.length === 0) return;

    // Validate batch size
    if (pendingItems.length > 100) {
      errorNotification('Maximum 100 mods per batch');
      return;
    }

    setIsConverting(true);

    try {
      // Create FormData for file upload
      const formData = new FormData();
      pendingItems.forEach((item) => {
        formData.append('files', item.file);
      });
      formData.append('user_id', 'default_user');
      formData.append('priority', priority);

      // Upload batch
      const uploadResponse = await fetch(`${API_BASE_URL}/batch/v2/upload`, {
        method: 'POST',
        body: formData,
      });

      if (!uploadResponse.ok) {
        throw new Error('Upload failed');
      }

      const uploadResult = await uploadResponse.json();
      const newBatchId = uploadResult.batch_id;
      setBatchId(newBatchId);

      // Start processing
      const processResponse = await fetch(`${API_BASE_URL}/batch/v2/${newBatchId}/process`, {
        method: 'POST',
      });

      if (!processResponse.ok) {
        throw new Error('Failed to start processing');
      }

      // Start polling
      setIsPolling(true);
      successNotification(`Batch started: ${pendingItems.length} mods queued`);

    } catch (err: any) {
      setIsConverting(false);
      errorNotification(err.message || 'Batch conversion failed');
    }
  }, [items, priority, successNotification, errorNotification]);

  // Retry failed item
  const retryItem = useCallback(async (itemId: string) => {
    if (!batchId) return;

    try {
      const response = await fetch(`${API_BASE_URL}/batch/v2/${batchId}/item/${itemId}/retry`, {
        method: 'POST',
      });

      if (!response.ok) throw new Error('Retry failed');

      setItems(prev => prev.map(item => 
        item.itemId === itemId 
          ? { ...item, status: 'queued' as const, error: undefined }
          : item
      ));
      
      successNotification('Item queued for retry');
    } catch (err) {
      errorNotification('Failed to retry item');
    }
  }, [batchId, successNotification, errorNotification]);

  // Cancel item
  const cancelItem = useCallback(async (itemId: string) => {
    if (!batchId) return;

    try {
      const response = await fetch(`${API_BASE_URL}/batch/v2/${batchId}/item/${itemId}`, {
        method: 'DELETE',
      });

      if (!response.ok) throw new Error('Cancel failed');

      setItems(prev => prev.map(item => 
        item.itemId === itemId 
          ? { ...item, status: 'failed' as const }
          : item
      ));
    } catch (err) {
      errorNotification('Failed to cancel item');
    }
  }, [batchId, errorNotification]);

  // Calculate stats
  const stats = items.reduce((acc, item) => {
    if (item.status === 'pending' || item.status === 'queued') acc.pending++;
    else if (item.status === 'processing') acc.processing++;
    else if (item.status === 'completed') acc.completed++;
    else if (item.status === 'failed' || item.status === 'retrying') acc.failed++;
    return acc;
  }, { pending: 0, processing: 0, completed: 0, failed: 0 });

  const overallProgress = items.length > 0
    ? items.reduce((sum, item) => sum + item.progress, 0) / items.length
    : 0;

  return (
    <div className="batch-conversion-manager-v2">
      <div className="batch-header">
        <h2>Batch Conversion v2</h2>
        <p>Process up to 100 mods with intelligent queue management</p>
        
        {/* Queue Stats */}
        {queueStats && (
          <div className="queue-stats">
            <span>Queue: {queueStats.queue_size}</span>
            <span>Workers: {queueStats.concurrent_jobs}/{queueStats.max_concurrent}</span>
            <span>Efficiency: {queueStats.efficiency?.toFixed(1)}%</span>
          </div>
        )}
      </div>

      {/* File Drop Zone */}
      <div className="drop-zone">
        <input
          type="file"
          id="batch-file-input-v2"
          multiple
          accept=".jar,.zip,.tar.gz"
          onChange={(e) => handleFileSelect(e.target.files)}
          disabled={isConverting}
        />
        <label htmlFor="batch-file-input-v2" className="drop-zone-label">
          <div className="drop-icon">📁</div>
          <p>Drag & drop mod files here or click to select</p>
          <span className="supported-formats">
            Supported: .jar, .zip, .tar.gz (Max 100 files, 500MB each)
          </span>
        </label>
      </div>

      {/* Controls */}
      <div className="batch-controls">
        <div className="priority-control">
          <label>Priority:</label>
          <select
            value={priority}
            onChange={(e) => setPriority(e.target.value as any)}
            disabled={isConverting}
          >
            <option value="low">Low</option>
            <option value="normal">Normal</option>
            <option value="high">High</option>
            <option value="vip">VIP</option>
          </select>
        </div>

        <div className="action-buttons">
          {stats.pending > 0 && !isConverting && (
            <button
              className="start-button primary"
              onClick={startBatchConversion}
            >
              Start Batch ({stats.pending})
            </button>
          )}

          {isConverting && (
            <button className="processing-button" disabled>
              Processing... ({overallProgress.toFixed(0)}%)
            </button>
          )}

          {!isConverting && items.length > 0 && (
            <button className="clear-button" onClick={clearAll}>
              Clear All
            </button>
          )}
        </div>
      </div>

      {/* File List */}
      {items.length > 0 && (
        <div className="file-list">
          {/* Overall Progress */}
          {isConverting && (
            <div className="overall-progress">
              <div className="progress-bar large">
                <div
                  className="progress-fill"
                  style={{ width: `${overallProgress * 100}%` }}
                />
              </div>
              <span className="progress-text">
                {stats.completed}/{items.length} completed
                {stats.failed > 0 && ` • ${stats.failed} failed`}
              </span>
            </div>
          )}

          {/* Item List */}
          <div className="file-items">
            {items.map((item) => (
              <div key={item.itemId} className={`file-item ${item.status}`}>
                <div className="file-icon">
                  {item.status === 'pending' && '📄'}
                  {item.status === 'queued' && '⏳'}
                  {item.status === 'processing' && '⚙️'}
                  {item.status === 'completed' && '✅'}
                  {item.status === 'failed' && '❌'}
                  {item.status === 'retrying' && '🔄'}
                </div>
                
                <div className="file-info">
                  <div className="file-name-row">
                    <span className="filename">{item.filename}</span>
                    <span className={`priority-badge ${item.priority}`}>
                      {item.priority}
                    </span>
                  </div>
                  
                  {/* Progress bar */}
                  {(item.status === 'processing' || item.status === 'queued') && (
                    <div className="progress-bar">
                      <div
                        className="progress-fill"
                        style={{ width: `${item.progress * 100}%` }}
                      />
                    </div>
                  )}
                  
                  {/* Status text */}
                  <div className="status-text">
                    {item.status === 'pending' && 'Waiting to upload'}
                    {item.status === 'queued' && 'In queue'}
                    {item.status === 'processing' && `Processing... ${(item.progress * 100).toFixed(0)}%`}
                    {item.status === 'completed' && 'Completed'}
                    {item.status === 'failed' && item.error?.message}
                    {item.status === 'retrying' && `Retrying... (${item.progress * 100}%)`}
                  </div>
                  
                  {/* Error details */}
                  {item.error && item.status === 'failed' && (
                    <div className="error-details">
                      <span className="error-type">{item.error.type}</span>
                      {item.error.recoverable && (
                        <button 
                          className="retry-button"
                          onClick={() => retryItem(item.itemId)}
                        >
                          Retry
                        </button>
                      )}
                      <button 
                        className="cancel-button"
                        onClick={() => cancelItem(item.itemId)}
                      >
                        Cancel
                      </button>
                    </div>
                  )}
                </div>
                
                {/* Remove button */}
                {item.status === 'pending' && !isConverting && (
                  <button
                    className="remove-button"
                    onClick={() => removeItem(item.itemId)}
                  >
                    ✕
                  </button>
                )}
              </div>
            ))}
          </div>

          {/* Summary */}
          <div className="batch-summary">
            <span className="pending">{stats.pending} pending</span>
            <span className="queued">{items.filter(i => i.status === 'queued').length} queued</span>
            <span className="processing">{stats.processing} processing</span>
            <span className="completed">{stats.completed} completed</span>
            <span className="failed">{stats.failed} failed</span>
          </div>
        </div>
      )}
    </div>
  );
};

export default BatchConversionManagerV2;
