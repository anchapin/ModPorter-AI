/**
 * Batch Conversion Manager
 * Allows uploading and converting multiple mod files at once
 */

import React, { useState, useCallback } from 'react';
import {
  useSuccessNotification,
  useErrorNotification,
} from '../NotificationSystem';
import {
  convertMod,
  getConversionStatus,
  triggerDownload,
} from '../../services/api';
import './BatchConversionManager.css';

export interface BatchConversionItem {
  id: string;
  filename: string;
  file: File;
  status: 'pending' | 'uploading' | 'converting' | 'completed' | 'failed';
  progress: number;
  jobId?: string;
  error?: string;
  resultUrl?: string;
}

interface BatchConversionManagerProps {
  onComplete?: (jobIds: string[]) => void;
}

export const BatchConversionManager: React.FC<BatchConversionManagerProps> = ({
  onComplete,
}) => {
  const [items, setItems] = useState<BatchConversionItem[]>([]);
  const [isConverting, setIsConverting] = useState(false);
  const [maxConcurrent, setMaxConcurrent] = useState(3);
  const successNotification = useSuccessNotification();
  const errorNotification = useErrorNotification();

  // Handle file selection
  const handleFileSelect = useCallback(
    (files: FileList | null) => {
      if (!files) return;

      const newItems: BatchConversionItem[] = Array.from(files)
        .filter((file) => {
          const ext = file.name.toLowerCase().split('.').pop();
          return ext === 'jar' || ext === 'zip' || ext === 'mcaddon';
        })
        .map((file) => ({
          id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
          filename: file.name,
          file,
          status: 'pending' as const,
          progress: 0,
        }));

      setItems((prev) => [...prev, ...newItems]);

      if (newItems.length > 0) {
        successNotification(`Added ${newItems.length} file(s) to batch`);
      }
    },
    [successNotification]
  );

  // Remove item from batch
  const removeItem = useCallback((id: string) => {
    setItems((prev) => prev.filter((item) => item.id !== id));
  }, []);

  // Clear all items
  const clearAll = useCallback(() => {
    setItems([]);
    setIsConverting(false);
  }, []);

  // Start batch conversion
  const startBatchConversion = useCallback(async () => {
    const pendingItems = items.filter((i) => i.status === 'pending');
    if (pendingItems.length === 0) return;

    setIsConverting(true);
    const completedJobIds: string[] = [];
    const failedIds: string[] = [];

    // Process in batches
    for (let i = 0; i < pendingItems.length; i += maxConcurrent) {
      const batch = pendingItems.slice(i, i + maxConcurrent);

      await Promise.all(
        batch.map(async (item) => {
          try {
            // Inline conversion logic to avoid dependency issue
            setItems((prev) =>
              prev.map((x) =>
                x.id === item.id
                  ? { ...x, status: 'converting' as const, progress: 20 }
                  : x
              )
            );
            const conversionResponse = await convertMod({
              file: item.file,
              smartAssumptions: true,
              includeDependencies: false,
            });
            const jobId = conversionResponse.job_id;
            setItems((prev) =>
              prev.map((x) =>
                x.id === item.id ? { ...x, jobId, progress: 40 } : x
              )
            );

            // Poll for completion
            let completed = false;
            let attempts = 0;
            while (!completed && attempts < 300) {
              await new Promise((resolve) => setTimeout(resolve, 1000));
              const status = await getConversionStatus(jobId);
              setItems((prev) =>
                prev.map((x) =>
                  x.id === item.id
                    ? {
                        ...x,
                        progress: 40 + Math.floor((status.progress / 100) * 50),
                      }
                    : x
                )
              );
              if (status.status === 'completed') {
                completed = true;
                setItems((prev) =>
                  prev.map((x) =>
                    x.id === item.id
                      ? {
                          ...x,
                          status: 'completed' as const,
                          progress: 100,
                          resultUrl: `/api/v1/conversions/${jobId}/download`,
                        }
                      : x
                  )
                );
              } else if (status.status === 'failed') {
                throw new Error(status.error || 'Conversion failed');
              }
              attempts++;
            }
            if (!completed) throw new Error('Conversion timed out');
            completedJobIds.push(jobId);
          } catch {
            failedIds.push(item.id);
          }
        })
      );
    }

    setIsConverting(false);

    if (completedJobIds.length > 0) {
      successNotification(
        `Batch conversion completed: ${completedJobIds.length} succeeded`
      );
      onComplete?.(completedJobIds);
    }

    if (failedIds.length > 0) {
      errorNotification(`Batch conversion failed: ${failedIds.length} failed`);
    }
  }, [
    items,
    maxConcurrent,
    successNotification,
    errorNotification,
    onComplete,
  ]);

  // Download all completed conversions as ZIP
  const downloadAll = useCallback(async () => {
    const completed = items.filter((i) => i.status === 'completed' && i.jobId);

    for (const item of completed) {
      try {
        // ⚡ Bolt optimization: Use triggerDownload to prevent large memory spikes from blob allocation
        await triggerDownload(item.jobId!);
      } catch (error) {
        console.error(`Failed to download ${item.filename}:`, error);
      }
    }
  }, [items]);

  // ⚡ Bolt optimization: Single pass instead of multiple filter().length calls to avoid O(3N) time complexity and intermediate array allocations
  const { pendingCount, completedCount, failedCount } = items.reduce(
    (acc, item) => {
      if (item.status === 'pending') acc.pendingCount++;
      else if (item.status === 'completed') acc.completedCount++;
      else if (item.status === 'failed') acc.failedCount++;
      return acc;
    },
    { pendingCount: 0, completedCount: 0, failedCount: 0 }
  );

  return (
    <div className="batch-conversion-manager">
      <div className="batch-header">
        <h2>Batch Conversion</h2>
        <p>Convert multiple mod files at once</p>
      </div>

      {/* File Drop Zone */}
      <div className="drop-zone">
        <input
          type="file"
          id="batch-file-input"
          multiple
          accept=".jar,.zip,.mcaddon"
          onChange={(e) => handleFileSelect(e.target.files)}
          disabled={isConverting}
        />
        <label htmlFor="batch-file-input" className="drop-zone-label">
          <div className="drop-icon">📁</div>
          <p>Drag & drop files here or click to select</p>
          <span className="supported-formats">
            Supported: .jar, .zip, .mcaddon
          </span>
        </label>
      </div>

      {/* File List */}
      {items.length > 0 && (
        <div className="file-list">
          <div className="file-list-header">
            <span>{items.length} file(s) queued</span>
            {!isConverting && (
              <button className="clear-button" onClick={clearAll}>
                Clear All
              </button>
            )}
          </div>

          <div className="file-items">
            {items.map((item) => (
              <div key={item.id} className={`file-item ${item.status}`}>
                <div className="file-icon">
                  {item.status === 'pending' && '📄'}
                  {item.status === 'uploading' && '⬆️'}
                  {item.status === 'converting' && '⚙️'}
                  {item.status === 'completed' && '✅'}
                  {item.status === 'failed' && '❌'}
                </div>
                <div className="file-info">
                  <span className="filename">{item.filename}</span>
                  {item.status === 'converting' && (
                    <div className="progress-bar">
                      <div
                        className="progress-fill"
                        style={{ width: `${item.progress}%` }}
                      />
                    </div>
                  )}
                  {item.status === 'failed' && item.error && (
                    <span className="error-text">{item.error}</span>
                  )}
                </div>
                {item.status === 'pending' && !isConverting && (
                  <button
                    className="remove-button"
                    onClick={() => removeItem(item.id)}
                  >
                    ✕
                  </button>
                )}
              </div>
            ))}
          </div>

          {/* Controls */}
          <div className="batch-controls">
            <div className="concurrency-control">
              <label>
                Max concurrent conversions:
                <select
                  value={maxConcurrent}
                  onChange={(e) => setMaxConcurrent(Number(e.target.value))}
                  disabled={isConverting}
                >
                  <option value={1}>1</option>
                  <option value={2}>2</option>
                  <option value={3}>3</option>
                  <option value={5}>5</option>
                </select>
              </label>
            </div>

            <div className="action-buttons">
              {pendingCount > 0 && !isConverting && (
                <button
                  className="start-button primary"
                  onClick={startBatchConversion}
                >
                  Start Batch ({pendingCount})
                </button>
              )}

              {isConverting && (
                <button className="processing-button" disabled>
                  Processing...
                </button>
              )}

              {completedCount > 0 && !isConverting && (
                <button
                  className="download-button secondary"
                  onClick={downloadAll}
                >
                  Download All ({completedCount})
                </button>
              )}
            </div>
          </div>

          {/* Summary */}
          <div className="batch-summary">
            <span className="pending">{pendingCount} pending</span>
            <span className="completed">{completedCount} completed</span>
            <span className="failed">{failedCount} failed</span>
          </div>
        </div>
      )}
    </div>
  );
};

export default BatchConversionManager;
