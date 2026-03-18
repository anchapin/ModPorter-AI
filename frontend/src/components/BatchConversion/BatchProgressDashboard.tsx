/**
 * Batch Progress Dashboard Component
 * Task 1.5.2.3: Build batch progress dashboard
 * 
 * Features:
 * - Overall progress bar
 * - Per-mod status
 * - Completed/Failed/Queued counts
 * - Real-time updates
 * - ETA calculation
 */

import React, { useEffect, useState, useRef, useCallback } from 'react';
import {
  useSuccessNotification,
  useErrorNotification,
} from '../NotificationSystem';
import { API_BASE_URL } from '../../services/api';
import './BatchProgressDashboard.css';

export interface BatchItemProgress {
  itemId: string;
  filename: string;
  status: 'pending' | 'queued' | 'processing' | 'completed' | 'failed' | 'retrying';
  progress: number;
  error?: {
    type: string;
    message: string;
    recoverable: boolean;
  };
  startedAt?: string;
  completedAt?: string;
}

export interface BatchProgressDashboardProps {
  batchId: string;
  items: BatchItemProgress[];
  onComplete?: (batchId: string) => void;
  onError?: (error: string) => void;
}

interface EtaData {
  estimatedSeconds: number;
  averageTimePerItem: number;
  completedCount: number;
  remainingCount: number;
}

export const BatchProgressDashboard: React.FC<BatchProgressDashboardProps> = ({
  batchId,
  items,
  onComplete,
  onError,
}) => {
  const [isPolling, setIsPolling] = useState(true);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const completedTimesRef = useRef<Map<string, number>>(new Map());
  const startTimeRef = useRef<number>(Date.now());
  const [eta, setEta] = useState<EtaData | null>(null);
  
  const successNotification = useSuccessNotification();
  const errorNotification = useErrorNotification();

  // Calculate ETA based on completed items
  const calculateEta = useCallback(() => {
    if (items.length === 0) return null;

    const completed = items.filter(i => i.status === 'completed');
    const processing = items.filter(i => i.status === 'processing');
    const pending = items.filter(i => i.status === 'pending' || i.status === 'queued');
    
    if (completed.length === 0) {
      // Estimate based on total items and no data yet
      return {
        estimatedSeconds: items.length * 120, // 2 min average
        averageTimePerItem: 120,
        completedCount: 0,
        remainingCount: items.length,
      };
    }

    // Calculate average time per completed item
    let totalTime = 0;
    let count = 0;
    completed.forEach(item => {
      const completedTime = completedTimesRef.current.get(item.itemId);
      if (completedTime) {
        totalTime += completedTime;
        count++;
      }
    });

    const averageTimePerItem = count > 0 ? totalTime / count : 120;
    const remainingItems = processing.length + pending.length;
    
    return {
      estimatedSeconds: Math.round(remainingItems * averageTimePerItem),
      averageTimePerItem: Math.round(averageTimePerItem),
      completedCount: completed.length,
      remainingCount: remainingItems,
    };
  }, [items]);

  // Update ETA when items complete
  useEffect(() => {
    const now = Date.now();
    const elapsed = (now - startTimeRef.current) / 1000;
    
    items.forEach(item => {
      if (item.status === 'completed' && item.completedAt) {
        if (!completedTimesRef.current.has(item.itemId)) {
          completedTimesRef.current.set(item.itemId, elapsed);
        }
      }
    });
    
    setEta(calculateEta());
  }, [items, calculateEta]);

  // Format ETA as human readable
  const formatEta = (seconds: number): string => {
    if (seconds < 60) {
      return `${Math.round(seconds)} seconds`;
    }
    if (seconds < 3600) {
      const mins = Math.floor(seconds / 60);
      const secs = Math.round(seconds % 60);
      return `${mins}m ${secs}s`;
    }
    const hours = Math.floor(seconds / 3600);
    const mins = Math.round((seconds % 3600) / 60);
    return `${hours}h ${mins}m`;
  };

  // Calculate overall progress
  const overallProgress = items.length > 0
    ? items.reduce((sum, item) => sum + item.progress, 0) / items.length
    : 0;

  // Calculate stats
  const stats = items.reduce((acc, item) => {
    if (item.status === 'pending' || item.status === 'queued') acc.pending++;
    else if (item.status === 'processing') acc.processing++;
    else if (item.status === 'completed') acc.completed++;
    else if (item.status === 'failed' || item.status === 'retrying') acc.failed++;
    return acc;
  }, { pending: 0, processing: 0, completed: 0, failed: 0 });

  // Check for completion
  useEffect(() => {
    const isComplete = 
      items.length > 0 && 
      (stats.completed + stats.failed === items.length);
    
    if (isComplete) {
      setIsPolling(false);
      
      if (stats.failed === 0) {
        successNotification(`Batch completed: ${stats.completed} mods converted`);
        onComplete?.(batchId);
      } else if (stats.completed > 0) {
        errorNotification(`Batch partial: ${stats.completed} succeeded, ${stats.failed} failed`);
      } else {
        errorNotification(`Batch failed: All ${stats.failed} mods failed`);
        onError?.(`All ${stats.failed} mods failed`);
      }
    }
  }, [stats, items.length, batchId, successNotification, errorNotification, onComplete, onError]);

  // Poll for updates
  useEffect(() => {
    if (!isPolling || !batchId) return;

    const pollStatus = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/batch/v2/${batchId}/status`);
        if (!response.ok) return;
        
        setLastUpdate(new Date());
      } catch (err) {
        console.error('Poll error:', err);
      }
    };

    const interval = setInterval(pollStatus, 3000);
    return () => clearInterval(interval);
  }, [isPolling, batchId]);

  // Get status color
  const getStatusColor = (status: string): string => {
    switch (status) {
      case 'completed': return 'var(--success-color)';
      case 'failed': return 'var(--error-color)';
      case 'processing': return 'var(--primary-color)';
      case 'queued': return 'var(--warning-color)';
      default: return 'var(--text-secondary)';
    }
  };

  return (
    <div className="batch-progress-dashboard">
      {/* Header */}
      <div className="dashboard-header">
        <h3>Batch Progress</h3>
        <span className="batch-id">Batch: {batchId.slice(0, 8)}...</span>
      </div>

      {/* Overall Progress */}
      <div className="overall-progress-section">
        <div className="progress-header">
          <span>Overall Progress</span>
          <span className="progress-percent">{Math.round(overallProgress * 100)}%</span>
        </div>
        <div className="progress-bar large">
          <div 
            className="progress-fill"
            style={{ width: `${overallProgress * 100}%` }}
          />
        </div>
        
        {/* ETA Display */}
        {eta && eta.remainingCount > 0 && (
          <div className="eta-display">
            <span className="eta-icon">⏱️</span>
            <span>Estimated time remaining: {formatEta(eta.estimatedSeconds)}</span>
            <span className="eta-detail">
              (avg {eta.averageTimePerItem}s per mod, {eta.remainingCount} remaining)
            </span>
          </div>
        )}
        
        {eta && eta.remainingCount === 0 && (
          <div className="eta-display complete">
            <span className="eta-icon">✅</span>
            <span>All conversions complete!</span>
          </div>
        )}
      </div>

      {/* Stats Cards */}
      <div className="stats-grid">
        <div className="stat-card pending">
          <div className="stat-icon">⏳</div>
          <div className="stat-value">{stats.pending + items.filter(i => i.status === 'queued').length}</div>
          <div className="stat-label">Queued</div>
        </div>
        
        <div className="stat-card processing">
          <div className="stat-icon">⚙️</div>
          <div className="stat-value">{stats.processing}</div>
          <div className="stat-label">Processing</div>
        </div>
        
        <div className="stat-card completed">
          <div className="stat-icon">✅</div>
          <div className="stat-value">{stats.completed}</div>
          <div className="stat-label">Completed</div>
        </div>
        
        <div className="stat-card failed">
          <div className="stat-icon">❌</div>
          <div className="stat-value">{stats.failed}</div>
          <div className="stat-label">Failed</div>
        </div>
      </div>

      {/* Per-Mod Status */}
      <div className="per-mod-status">
        <h4>Mod Status</h4>
        <div className="mod-list">
          {items.map((item) => (
            <div 
              key={item.itemId} 
              className={`mod-item ${item.status}`}
            >
              <div 
                className="mod-status-indicator"
                style={{ backgroundColor: getStatusColor(item.status) }}
              />
              <div className="mod-info">
                <span className="mod-filename">{item.filename}</span>
                <span className="mod-status-text">
                  {item.status === 'pending' && 'Waiting in queue'}
                  {item.status === 'queued' && 'Queued for processing'}
                  {item.status === 'processing' && `Processing... ${Math.round(item.progress * 100)}%`}
                  {item.status === 'completed' && '✓ Completed'}
                  {item.status === 'failed' && `✗ Failed: ${item.error?.message || 'Unknown error'}`}
                  {item.status === 'retrying' && `🔄 Retrying...`}
                </span>
              </div>
              {item.status === 'processing' && (
                <div className="mod-progress">
                  <div className="progress-bar small">
                    <div 
                      className="progress-fill"
                      style={{ width: `${item.progress * 100}%` }}
                    />
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Last Update */}
      {lastUpdate && (
        <div className="last-update">
          Last updated: {lastUpdate.toLocaleTimeString()}
        </div>
      )}
    </div>
  );
};

export default BatchProgressDashboard;
