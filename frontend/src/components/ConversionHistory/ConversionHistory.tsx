/**
 * Conversion History Component - Day 5 Enhancement
 * Shows user's previous conversions with status, download options, and management features
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { triggerDownload } from '../../services/api';
import './ConversionHistory.css';
import { ConversionHistoryItem } from './types';
import ConversionHistoryItemRow from './ConversionHistoryItem';

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

  // Load conversion history from localStorage
  const loadHistory = useCallback(async () => {
    try {
      setLoading(true);
      
      // For MVP, use localStorage to store conversion history
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
  }, [maxItems]);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  // Add new conversion to history
  const addToHistory = useCallback((item: ConversionHistoryItem) => {
    setHistory(prevHistory => {
      const updatedHistory = [item, ...prevHistory].slice(0, maxItems);
      localStorage.setItem('modporter_conversion_history', JSON.stringify(updatedHistory));
      return updatedHistory;
    });
  }, [maxItems]);

  // Update existing conversion status
  const updateConversionStatus = useCallback((jobId: string, updates: Partial<ConversionHistoryItem>) => {
    setHistory(prevHistory => {
      const updatedHistory = prevHistory.map(item =>
        item.job_id === jobId ? { ...item, ...updates } : item
      );
      localStorage.setItem('modporter_conversion_history', JSON.stringify(updatedHistory));
      return updatedHistory;
    });
  }, []);

  // Download conversion result
  const downloadConversion = useCallback(async (jobId: string, _filename: string) => {
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
      localStorage.setItem('modporter_conversion_history', JSON.stringify(updatedHistory));
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
    localStorage.removeItem('modporter_conversion_history');
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
    // We need the current selected items set to filter history
    // But we can't access state inside setHistory callback cleanly if we want to depend only on stable refs.
    // However, deleteSelected depends on selectedItems state anyway, so it will change when selection changes.
    // That is acceptable as it's attached to the "Delete Selected" button, NOT passed to individual rows.

    // Wait, deleteSelected is NOT passed to rows. So it doesn't need to be perfectly stable for rows.
    // Only toggleSelection, deleteConversion, downloadConversion need to be stable for rows.

    setHistory(currentHistory => {
      // Need access to current selectedItems.
      // Since we are inside a callback that depends on selectedItems, we can use it.
      // But wait, the callback below needs selectedItems from closure.
      return currentHistory.filter(item => !selectedItems.has(item.job_id));
    });

    // We also need to update localStorage with the result.
    // The setHistory updater function is pure-ish.
    // Better:
    const newHistory = history.filter(item => !selectedItems.has(item.job_id));
    setHistory(newHistory);
    localStorage.setItem('modporter_conversion_history', JSON.stringify(newHistory));
    setSelectedItems(new Set());
  }, [history, selectedItems]);
  // deleteSelected depends on history and selectedItems.
  // It's attached to the header button, so it's fine if it re-renders the header button.

  // Expose methods for parent components
  React.useImperativeHandle(React.useRef(), () => ({
    addToHistory,
    updateConversionStatus,
    loadHistory
  }), [addToHistory, updateConversionStatus, loadHistory]);

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
