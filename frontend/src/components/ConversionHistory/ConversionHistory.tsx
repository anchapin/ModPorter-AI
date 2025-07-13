/**
 * Conversion History Component - Day 5 Enhancement
 * Shows user's previous conversions with status, download options, and management features
 */

import React, { useState, useEffect } from 'react';
import './ConversionHistory.css';

interface ConversionHistoryItem {
  job_id: string;
  original_filename: string;
  status: 'completed' | 'failed' | 'processing' | 'queued';
  created_at: string;
  completed_at?: string;
  file_size?: number;
  error_message?: string;
  options?: {
    smartAssumptions: boolean;
    includeDependencies: boolean;
    modUrl?: string;
  };
}

interface ConversionHistoryProps {
  className?: string;
  maxItems?: number;
}

export const ConversionHistory: React.FC<ConversionHistoryProps> = ({ 
  className = '',
  maxItems = 50 
}) => {
  const [history, setHistory] = useState<ConversionHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedItems, setSelectedItems] = useState<Set<string>>(new Set());

  const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8080/api/v1';

  // Load conversion history from localStorage for now
  // In production, this would come from the backend API
  useEffect(() => {
    loadHistory();
  }, []);

  const loadHistory = async () => {
    try {
      setLoading(true);
      
      // For MVP, use localStorage to store conversion history
      // In production, this would be an API call to the backend
      const storedHistory = localStorage.getItem('modporter_conversion_history');
      const parsedHistory: ConversionHistoryItem[] = storedHistory ? JSON.parse(storedHistory) : [];
      
      // Sort by creation date (newest first)
      const sortedHistory = parsedHistory.sort((a, b) => 
        new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      );
      
      setHistory(sortedHistory.slice(0, maxItems));
      setError(null);
    } catch (err) {
      console.error('Failed to load conversion history:', err);
      setError('Failed to load conversion history');
      setHistory([]);
    } finally {
      setLoading(false);
    }
  };

  // Add new conversion to history
  const addToHistory = (item: ConversionHistoryItem) => {
    const updatedHistory = [item, ...history];
    setHistory(updatedHistory.slice(0, maxItems));
    
    // Save to localStorage
    localStorage.setItem('modporter_conversion_history', JSON.stringify(updatedHistory));
  };

  // Update existing conversion status
  const updateConversionStatus = (jobId: string, updates: Partial<ConversionHistoryItem>) => {
    const updatedHistory = history.map(item => 
      item.job_id === jobId ? { ...item, ...updates } : item
    );
    setHistory(updatedHistory);
    localStorage.setItem('modporter_conversion_history', JSON.stringify(updatedHistory));
  };

  // Download conversion result
  const downloadConversion = async (jobId: string, filename: string) => {
    try {
      const response = await fetch(`${API_BASE_URL}/convert/${jobId}/download`);
      
      if (!response.ok) {
        throw new Error('Download failed');
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename.endsWith('.mcaddon') ? filename : `${filename}.mcaddon`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      console.error('Download failed:', err);
      setError('Failed to download file');
    }
  };

  // Delete conversion from history
  const deleteConversion = (jobId: string) => {
    const updatedHistory = history.filter(item => item.job_id !== jobId);
    setHistory(updatedHistory);
    localStorage.setItem('modporter_conversion_history', JSON.stringify(updatedHistory));
    setSelectedItems(prev => {
      const updated = new Set(prev);
      updated.delete(jobId);
      return updated;
    });
  };

  // Clear all history
  const clearAllHistory = () => {
    setHistory([]);
    setSelectedItems(new Set());
    localStorage.removeItem('modporter_conversion_history');
  };

  // Toggle item selection
  const toggleSelection = (jobId: string) => {
    setSelectedItems(prev => {
      const updated = new Set(prev);
      if (updated.has(jobId)) {
        updated.delete(jobId);
      } else {
        updated.add(jobId);
      }
      return updated;
    });
  };

  // Delete selected items
  const deleteSelected = () => {
    const updatedHistory = history.filter(item => !selectedItems.has(item.job_id));
    setHistory(updatedHistory);
    localStorage.setItem('modporter_conversion_history', JSON.stringify(updatedHistory));
    setSelectedItems(new Set());
  };

  // Format file size
  const formatFileSize = (bytes?: number): string => {
    if (!bytes) return 'Unknown size';
    const mb = bytes / (1024 * 1024);
    return `${mb.toFixed(2)} MB`;
  };

  // Format date
  const formatDate = (dateString: string): string => {
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
  };

  // Get status icon
  const getStatusIcon = (status: string): string => {
    switch (status) {
      case 'completed': return '✅';
      case 'failed': return '❌';
      case 'processing': return '⏳';
      case 'queued': return '⏸️';
      default: return '❓';
    }
  };

  // Get status color
  const getStatusColor = (status: string): string => {
    switch (status) {
      case 'completed': return '#4caf50';
      case 'failed': return '#f44336';
      case 'processing': return '#ff9800';
      case 'queued': return '#2196f3';
      default: return '#9e9e9e';
    }
  };

  // Expose methods for parent components
  React.useImperativeHandle(React.useRef(), () => ({
    addToHistory,
    updateConversionStatus,
    loadHistory
  }), [history]);

  if (loading) {
    return (
      <div className={`conversion-history loading ${className}`}>
        <div className="loading-spinner">⏳ Loading conversion history...</div>
      </div>
    );
  }

  return (
    <div className={`conversion-history ${className}`}>
      <div className="history-header">
        <h3>
          <span className="history-icon">📋</span>
          Conversion History
          {history.length > 0 && <span className="count">({history.length})</span>}
        </h3>
        
        {history.length > 0 && (
          <div className="history-actions">
            {selectedItems.size > 0 && (
              <button 
                className="delete-selected-btn"
                onClick={deleteSelected}
                title={`Delete ${selectedItems.size} selected items`}
              >
                🗑️ Delete Selected ({selectedItems.size})
              </button>
            )}
            <button 
              className="clear-all-btn"
              onClick={clearAllHistory}
              title="Clear all history"
            >
              🧹 Clear All
            </button>
          </div>
        )}
      </div>

      {error && (
        <div className="error-message">
          ⚠️ {error}
        </div>
      )}

      {history.length === 0 ? (
        <div className="empty-history">
          <div className="empty-icon">📭</div>
          <p>No conversions yet</p>
          <p className="empty-subtitle">Your conversion history will appear here</p>
        </div>
      ) : (
        <div className="history-list">
          {history.map((item) => (
            <div 
              key={item.job_id} 
              className={`history-item ${selectedItems.has(item.job_id) ? 'selected' : ''}`}
            >
              <div className="item-checkbox">
                <input
                  type="checkbox"
                  checked={selectedItems.has(item.job_id)}
                  onChange={() => toggleSelection(item.job_id)}
                  aria-label={`Select ${item.original_filename}`}
                />
              </div>

              <div className="item-icon">
                <span style={{ color: getStatusColor(item.status) }}>
                  {getStatusIcon(item.status)}
                </span>
              </div>

              <div className="item-content">
                <div className="item-main">
                  <div className="item-title">
                    <span className="filename">{item.original_filename}</span>
                    <span className="job-id">#{item.job_id.slice(0, 8)}</span>
                  </div>
                  
                  <div className="item-meta">
                    <span className="status" style={{ color: getStatusColor(item.status) }}>
                      {item.status.charAt(0).toUpperCase() + item.status.slice(1)}
                    </span>
                    <span className="date">{formatDate(item.created_at)}</span>
                    {item.file_size && (
                      <span className="size">{formatFileSize(item.file_size)}</span>
                    )}
                  </div>

                  {item.options && (
                    <div className="item-options">
                      {item.options.smartAssumptions && (
                        <span className="option-tag">🧠 Smart Assumptions</span>
                      )}
                      {item.options.includeDependencies && (
                        <span className="option-tag">📦 Dependencies</span>
                      )}
                      {item.options.modUrl && (
                        <span className="option-tag">🔗 URL Source</span>
                      )}
                    </div>
                  )}

                  {item.error_message && (
                    <div className="error-detail">
                      ⚠️ {item.error_message}
                    </div>
                  )}
                </div>
              </div>

              <div className="item-actions">
                {item.status === 'completed' && (
                  <button
                    className="download-btn"
                    onClick={() => downloadConversion(item.job_id, item.original_filename)}
                    title="Download converted file"
                  >
                    ⬇️ Download
                  </button>
                )}
                
                <button
                  className="delete-btn"
                  onClick={() => deleteConversion(item.job_id)}
                  title="Remove from history"
                >
                  🗑️
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

// Create a hook for managing conversion history from other components
export const useConversionHistory = () => {
  const [historyRef, setHistoryRef] = useState<any>(null);

  const addConversion = (conversion: ConversionHistoryItem) => {
    if (historyRef?.addToHistory) {
      historyRef.addToHistory(conversion);
    } else {
      // Fallback to localStorage if ref not available
      const storedHistory = localStorage.getItem('modporter_conversion_history');
      const history: ConversionHistoryItem[] = storedHistory ? JSON.parse(storedHistory) : [];
      const updatedHistory = [conversion, ...history];
      localStorage.setItem('modporter_conversion_history', JSON.stringify(updatedHistory));
    }
  };

  const updateConversion = (jobId: string, updates: Partial<ConversionHistoryItem>) => {
    if (historyRef?.updateConversionStatus) {
      historyRef.updateConversionStatus(jobId, updates);
    } else {
      // Fallback to localStorage
      const storedHistory = localStorage.getItem('modporter_conversion_history');
      const history: ConversionHistoryItem[] = storedHistory ? JSON.parse(storedHistory) : [];
      const updatedHistory = history.map(item => 
        item.job_id === jobId ? { ...item, ...updates } : item
      );
      localStorage.setItem('modporter_conversion_history', JSON.stringify(updatedHistory));
    }
  };

  return {
    setHistoryRef,
    addConversion,
    updateConversion
  };
};

export default ConversionHistory;