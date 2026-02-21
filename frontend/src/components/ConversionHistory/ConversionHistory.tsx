/**
 * Conversion History Component - Day 5 Enhancement
 * Shows user's previous conversions with status, download options, and management features
 */

import React, { useState, useEffect, useCallback } from 'react';
import { triggerDownload } from '../../services/api';
import './ConversionHistory.css';
import { ConversionHistoryItem } from './types';
import ConversionHistoryItemRow from './ConversionHistoryItem';

interface ConversionHistoryProps {
  className?: string;
  maxItems?: number;
  onStartNewConversion?: () => void;
}

export const ConversionHistory: React.FC<ConversionHistoryProps> = ({ 
  className = '',
  maxItems = 50,
  onStartNewConversion
}) => {
  // Lazy initialization of history from localStorage
  const [history, setHistory] = useState<ConversionHistoryItem[]>(() => {
    try {
      const storedHistory = localStorage.getItem('modporter_conversion_history');
      if (!storedHistory) return [];
      const parsedHistory: ConversionHistoryItem[] = JSON.parse(storedHistory);
      // Sort by creation date (newest first) using string comparison for ISO dates
      return parsedHistory.sort((a, b) =>
        (b.created_at || '').localeCompare(a.created_at || '')
      ).slice(0, maxItems);
    } catch (err) {
      console.error('Failed to load conversion history:', err);
      return [];
    }
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedItems, setSelectedItems] = useState<Set<string>>(new Set());

  // Confirmation states
  const [confirmClear, setConfirmClear] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const isMountedRef = React.useRef(false);

  // Reset confirmDelete when selection is cleared
  useEffect(() => {
    if (selectedItems.size === 0) {
      setConfirmDelete(false);
    }
  }, [selectedItems.size]);

  // Load conversion history from localStorage
  const loadHistory = useCallback(() => {
    try {
      setLoading(true);
      
      // For MVP, use localStorage to store conversion history
      const storedHistory = localStorage.getItem('modporter_conversion_history');
      const parsedHistory: ConversionHistoryItem[] = storedHistory ? JSON.parse(storedHistory) : [];
      
      // Sort by creation date (newest first)
      // Optimization: String comparison for ISO dates
      const sortedHistory = parsedHistory.sort((a, b) => 
        (b.created_at || '').localeCompare(a.created_at || '')
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
  }, [maxItems]);

  // Only load history on subsequent updates (e.g. maxItems change), skip initial mount
  useEffect(() => {
    if (isMountedRef.current) {
      loadHistory();
    } else {
      isMountedRef.current = true;
    }
  }, [loadHistory]);

  // Sync state to localStorage whenever history changes
  // This ensures deletions and updates are persisted without side effects in updaters
  useEffect(() => {
    if (!loading) {
      localStorage.setItem('modporter_conversion_history', JSON.stringify(history));
    }
  }, [history, loading]);

  // Add new conversion to history
  const addToHistory = useCallback((item: ConversionHistoryItem) => {
    setHistory(prevHistory => {
      const updatedHistory = [item, ...prevHistory].slice(0, maxItems);
      // LocalStorage sync handled by useEffect
      return updatedHistory;
    });
  }, [maxItems]);

  // Update existing conversion status
  const updateConversionStatus = useCallback((jobId: string, updates: Partial<ConversionHistoryItem>) => {
    setHistory(prevHistory => {
      const updatedHistory = prevHistory.map(item =>
        item.job_id === jobId ? { ...item, ...updates } : item
      );
      // LocalStorage sync handled by useEffect
      return updatedHistory;
    });
  }, []);

  // Download conversion result
  const downloadConversion = useCallback(async (jobId: string) => {
    try {
      await triggerDownload(jobId);
    } catch (err) {
      console.error('Download failed:', err);
      setError('Failed to download file');
    }
  }, []);

  // Delete conversion from history
  const deleteConversion = useCallback((jobId: string) => {
    setHistory(prevHistory => {
      const updatedHistory = prevHistory.filter(item => item.job_id !== jobId);
      return updatedHistory;
    });

    setSelectedItems(prev => {
      if (!prev.has(jobId)) return prev;
      const updated = new Set(prev);
      updated.delete(jobId);
      return updated;
    });
  }, []);

  // Clear all history
  const clearAllHistory = useCallback(() => {
    setHistory([]);
    setSelectedItems(new Set());
    setConfirmClear(false);
    // LocalStorage sync handled by useEffect
  }, []);

  // Toggle item selection
  const toggleSelection = useCallback((jobId: string) => {
    setSelectedItems(prev => {
      const updated = new Set(prev);
      if (updated.has(jobId)) {
        updated.delete(jobId);
      } else {
        updated.add(jobId);
      }
      return updated;
    });
  }, []);

  // Delete selected items
  const deleteSelected = useCallback(() => {
    setHistory(currentHistory => {
      const newHistory = currentHistory.filter(item => !selectedItems.has(item.job_id));
      return newHistory;
    });
    setSelectedItems(new Set());
    setConfirmDelete(false);
  }, [selectedItems]);

  // Expose methods for parent components
  React.useImperativeHandle(React.useRef(), () => ({
    addToHistory,
    updateConversionStatus,
    loadHistory
  }), [addToHistory, updateConversionStatus, loadHistory]);

  if (loading) {
    return (
      <div className={`conversion-history loading ${className}`} role="status" aria-label="Loading history">
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
              confirmDelete ? (
                <div className="confirm-actions" role="alertdialog" aria-label="Confirm delete selected">
                    <span className="confirm-text">Delete {selectedItems.size} items?</span>
                    <button
                      className="delete-selected-btn"
                      onClick={deleteSelected}
                      aria-label="Yes, delete selected items"
                    >
                      Yes
                    </button>
                    <button
                      className="cancel-btn"
                      onClick={() => setConfirmDelete(false)}
                      aria-label="Cancel delete"
                    >
                      No
                    </button>
                </div>
              ) : (
                <button
                  className="delete-selected-btn"
                  onClick={() => setConfirmDelete(true)}
                  title={`Delete ${selectedItems.size} selected items`}
                  aria-label={`Delete ${selectedItems.size} selected items`}
                >
                  🗑️ Delete Selected ({selectedItems.size})
                </button>
              )
            )}

            {confirmClear ? (
                <div className="confirm-actions" role="alertdialog" aria-label="Confirm clear all history">
                    <span className="confirm-text">Clear all?</span>
                    <button
                      className="clear-all-btn"
                      onClick={clearAllHistory}
                      aria-label="Yes, clear all history"
                    >
                      Yes
                    </button>
                    <button
                      className="cancel-btn"
                      onClick={() => setConfirmClear(false)}
                      aria-label="Cancel clear all"
                    >
                      No
                    </button>
                </div>
            ) : (
              <button 
                className="clear-all-btn"
                onClick={() => setConfirmClear(true)}
                title="Clear all history"
                aria-label="Clear all history"
              >
                🧹 Clear All
              </button>
            )}
          </div>
        )}
      </div>

      {error && (
        <div className="error-message" role="alert">
          ⚠️ {error}
        </div>
      )}

      {history.length === 0 ? (
        <div className="empty-history" role="status">
          <div className="empty-icon" aria-hidden="true">📭</div>
          <p>No conversions yet</p>
          <p className="empty-subtitle">Your conversion history will appear here</p>
          {onStartNewConversion && (
            <button
              className="start-new-btn"
              onClick={onStartNewConversion}
              aria-label="Start a new conversion"
            >
              Start New Conversion
            </button>
          )}
        </div>
      ) : (
        <div className="history-list">
          {history.map((item) => (
            <ConversionHistoryItemRow
              key={item.job_id}
              item={item}
              isSelected={selectedItems.has(item.job_id)}
              onToggle={toggleSelection}
              onDelete={deleteConversion}
              onDownload={downloadConversion}
            />
          ))}
        </div>
      )}
    </div>
  );
};

// Create a hook for managing conversion history from other components
// eslint-disable-next-line react-refresh/only-export-components
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
