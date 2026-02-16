/**
 * Batch Conversion Manager
 * Allows uploading and converting multiple mod files at once
 */

import React, { useState, useCallback } from 'react';
import { useNotification } from '../NotificationSystem';
import { 
  uploadFile, 
  startConversion, 
  getConversionStatus, 
  downloadResult 
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
  onError?: (error: string) => void;
}

export const BatchConversionManager: React.FC<BatchConversionManagerProps> = ({
  onComplete,
  onError
}) => {
  const [items, setItems] = useState<BatchConversionItem[]>([]);
  const [isConverting, setIsConverting] = useState(false);
  const [maxConcurrent, setMaxConcurrent] = useState(3);
  const notification = useNotification();

  // Handle file selection
  const handleFileSelect = useCallback((files: FileList | null) => {
    if (!files) return;

    const newItems: BatchConversionItem[] = Array.from(files)
      .filter(file => {
        const ext = file.name.toLowerCase().split('.').pop();
        return ext === 'jar' || ext === 'zip' || ext === 'mcaddon';
      })
      .map(file => ({
        id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
        filename: file.name,
        file,
        status: 'pending' as const,
        progress: 0
      }));

    setItems(prev => [...prev, ...newItems]);
    
    if (newItems.length > 0) {
      notification.success(`Added ${newItems.length} file(s) to batch`);
    }
  }, [notification]);

  // Remove item from batch
  const removeItem = useCallback((id: string) => {
    setItems(prev => prev.filter(item => item.id !== id));
  }, []);

  // Clear all items
  const clearAll = useCallback(() => {
    setItems([]);
    setIsConverting(false);
  }, []);

  // Process a single conversion
  const processConversion = async (
    item: BatchConversionItem,
    index: number
  ): Promise<BatchConversionItem> => {
    try {
      // Update status to uploading
      setItems(prev => prev.map(i => 
        i.id === item.id ? { ...i, status: 'uploading', progress: 10 } : i
      ));

      // Upload file
      const { file_id } = await uploadFile(item.file);
      
      // Update status to converting
      setItems(prev => prev.map(i => 
        i.id === item.id ? { ...i, status: 'converting', progress: 30 } : i
      ));

      // Start conversion
      const { job_id } = await startConversion({
        file_id,
        original_filename: item.filename
      });

      // Update with job ID
      setItems(prev => prev.map(i => 
        i.id === item.id ? { ...i, jobId: job_id, progress: 50 } : i
      ));

      // Poll for completion
      let completed = false;
      let attempts = 0;
      const maxAttempts = 300; // 5 minutes max

      while (!completed && attempts < maxAttempts) {
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        const status = await getConversionStatus(job_id);
        
        setItems(prev => prev.map(i => 
          i.id === item.id ? { 
            ...i, 
            progress: 50 + Math.floor((status.progress / 100) * 40) 
          } : i
        ));

        if (status.status === 'completed') {
          completed = true;
          setItems(prev => prev.map(i => 
            i.id === item.id ? { 
              ...i, 
              status: 'completed',
              progress: 100,
              resultUrl: `/api/v1/conversions/${job_id}/download`
            } : i
          ));
        } else if (status.status === 'failed') {
          throw new Error(status.error || 'Conversion failed');
        }
        
        attempts++;
      }

      if (!completed) {
        throw new Error('Conversion timed out');
      }

      return items.find(i => i.id === item.id)!;
    } catch (error: any) {
      const errorMessage = error.message || 'Unknown error';
      setItems(prev => prev.map(i => 
        i.id === item.id ? { 
          ...i, 
          status: 'failed',
          error: errorMessage 
        } : i
      ));
      throw error;
    }
  };

  // Start batch conversion
  const startBatchConversion = useCallback(async () => {
    const pendingItems = items.filter(i => i.status === 'pending');
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
            const result = await processConversion(item, i);
            if (result.jobId) {
              completedJobIds.push(result.jobId);
            }
          } catch (error) {
            failedIds.push(item.id);
          }
        })
      );
    }

    setIsConverting(false);
    
    if (completedJobIds.length > 0) {
      notification.success(`Batch conversion completed: ${completedJobIds.length} succeeded`);
      onComplete?.(completedJobIds);
    }
    
    if (failedIds.length > 0) {
      notification.error(`Batch conversion failed: ${failedIds.length} failed`);
    }
  }, [items, maxConcurrent, notification, onComplete]);

  // Download all completed conversions as ZIP
  const downloadAll = useCallback(async () => {
    const completed = items.filter(i => i.status === 'completed' && i.jobId);
    
    for (const item of completed) {
      try {
        const { blob, filename } = await downloadResult(item.jobId!);
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      } catch (error) {
        console.error(`Failed to download ${item.filename}:`, error);
      }
    }
  }, [items]);

  const pendingCount = items.filter(i => i.status === 'pending').length;
  const completedCount = items.filter(i => i.status === 'completed').length;
  const failedCount = items.filter(i => i.status === 'failed').length;

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
            {items.map(item => (
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
