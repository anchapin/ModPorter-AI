/**
 * Conversion History Component - Enhanced
 * Shows user's previous conversions with status, download options, and management features
 * Fetches from API and supports filtering/search
 */

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  triggerDownload,
  listConversions,
  billingAPI,
  downloadConversionReport,
  UsageInfo,
  SubscriptionStatus,
} from '../../services/api';
import './ConversionHistory.css';
import { ConversionHistoryItem, ConversionHistoryItemFromAPI } from './types';
import ConversionHistoryItemRow from './ConversionHistoryItem';

interface ConversionHistoryProps {
  className?: string;
  maxItems?: number;
  onStartNewConversion?: () => void;
}

interface UsageStats {
  tier: string;
  conversions_this_month: number;
  remaining: number;
  monthly_limit: number;
  should_upgrade: boolean;
  upgrade_message: string | null;
}

export const ConversionHistory: React.FC<ConversionHistoryProps> = ({
  className = '',
  maxItems = 50,
  onStartNewConversion,
}) => {
  const [history, setHistory] = useState<ConversionHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedItems, setSelectedItems] = useState<Set<string>>(new Set());
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [usageStats, setUsageStats] = useState<UsageStats | null>(null);
  const [subscriptionStatus, setSubscriptionStatus] =
    useState<SubscriptionStatus | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalItems, setTotalItems] = useState(0);
  const pageSize = 20;

  // Confirmation states
  const [confirmClear, setConfirmClear] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);

  // Reset confirmDelete when selection is cleared
  useEffect(() => {
    if (selectedItems.size === 0) {
      setConfirmDelete(false);
    }
  }, [selectedItems.size]);

  // Load conversion history from API
  const loadHistory = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await listConversions({
        page: currentPage,
        page_size: pageSize,
      });

      setTotalItems(response.total);

      // Map API response to component format
      const mappedHistory: ConversionHistoryItem[] = response.conversions.map(
        (item: ConversionHistoryItemFromAPI) => ({
          job_id: item.conversion_id,
          original_filename: item.original_filename || 'Unknown',
          status: item.status as ConversionHistoryItem['status'],
          created_at: item.created_at,
          completed_at: item.updated_at,
          error_message: item.error,
          complexity_tier: item.complexity_tier,
          features_converted: item.features_converted || [],
          features_skipped: item.features_skipped || [],
          warnings: item.warnings || [],
          options: {},
        })
      );

      setHistory(mappedHistory);
    } catch (err) {
      console.error('Failed to load conversion history:', err);
      // Fallback to localStorage if API fails
      const storedHistory = localStorage.getItem(
        'modporter_conversion_history'
      );
      const parsedHistory: ConversionHistoryItem[] = storedHistory
        ? JSON.parse(storedHistory)
        : [];
      setHistory(parsedHistory.slice(0, maxItems));
      setError('Failed to load from server, showing cached data');
    } finally {
      setLoading(false);
    }
  }, [currentPage, maxItems]);

  // Load usage stats
  const loadUsageStats = useCallback(async () => {
    try {
      const usage = await billingAPI.getUsageInfo();
      setUsageStats({
        tier: usage.tier,
        conversions_this_month: usage.web_conversions,
        remaining: usage.remaining,
        monthly_limit: usage.monthly_limit,
        should_upgrade: usage.should_upgrade,
        upgrade_message: usage.upgrade_message,
      });
    } catch (err) {
      console.error('Failed to load usage stats:', err);
    }
  }, []);

  // Load subscription status
  const loadSubscriptionStatus = useCallback(async () => {
    try {
      const subscription = await billingAPI.getSubscriptionStatus();
      setSubscriptionStatus(subscription);
    } catch (err) {
      console.error('Failed to load subscription status:', err);
    }
  }, []);

  useEffect(() => {
    loadHistory();
    loadUsageStats();
    loadSubscriptionStatus();
  }, [loadHistory, loadUsageStats, loadSubscriptionStatus, currentPage]);

  // Filter history based on search and status
  const filteredHistory = useMemo(() => {
    let result = [...history];

    // Apply search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      result = result.filter(
        (item) =>
          item.original_filename.toLowerCase().includes(query) ||
          item.job_id.toLowerCase().includes(query)
      );
    }

    // Apply status filter
    if (statusFilter !== 'all') {
      result = result.filter((item) => item.status === statusFilter);
    }

    return result;
  }, [history, searchQuery, statusFilter]);

  // Add new conversion to history
  const addToHistory = useCallback(
    (item: ConversionHistoryItem) => {
      setHistory((prevHistory) => {
        const updatedHistory = [item, ...prevHistory].slice(0, maxItems);
        return updatedHistory;
      });
    },
    [maxItems]
  );

  // Update existing conversion status
  const updateConversionStatus = useCallback(
    (jobId: string, updates: Partial<ConversionHistoryItem>) => {
      setHistory((prevHistory) => {
        const updatedHistory = prevHistory.map((item) =>
          item.job_id === jobId ? { ...item, ...updates } : item
        );
        return updatedHistory;
      });
    },
    []
  );

  // Download conversion result
  const downloadConversion = useCallback(async (jobId: string) => {
    try {
      await triggerDownload(jobId);
    } catch (err) {
      console.error('Download failed:', err);
      setError('Failed to download file');
    }
  }, []);

  // Download conversion report
  const downloadReport = useCallback(
    async (jobId: string, format: 'json' | 'html' | 'csv' = 'json') => {
      try {
        await downloadConversionReport(jobId, format);
      } catch (err) {
        console.error('Report download failed:', err);
        setError('Failed to download report');
      }
    },
    []
  );

  // Delete conversion from history (local only - API delete is not implemented)
  const deleteConversion = useCallback((jobId: string) => {
    setHistory((prevHistory) => {
      const updatedHistory = prevHistory.filter(
        (item) => item.job_id !== jobId
      );
      return updatedHistory;
    });

    setSelectedItems((prev) => {
      if (!prev.has(jobId)) return prev;
      const updated = new Set(prev);
      updated.delete(jobId);
      return updated;
    });
  }, []);

  // Clear all history (local only)
  const clearAllHistory = useCallback(() => {
    setHistory([]);
    setSelectedItems(new Set());
    setConfirmClear(false);
  }, []);

  // Toggle item selection
  const toggleSelection = useCallback((jobId: string) => {
    setSelectedItems((prev) => {
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
    setHistory((currentHistory) => {
      const newHistory = currentHistory.filter(
        (item) => !selectedItems.has(item.job_id)
      );
      return newHistory;
    });
    setSelectedItems(new Set());
    setConfirmDelete(false);
  }, [selectedItems]);

  // Expose methods for parent components
  React.useImperativeHandle(
    React.useRef(),
    () => ({
      addToHistory,
      updateConversionStatus,
      loadHistory,
    }),
    [addToHistory, updateConversionStatus, loadHistory]
  );

  const formatTierDisplay = (tier: string) => {
    return tier.charAt(0).toUpperCase() + tier.slice(1);
  };

  if (loading) {
    return (
      <div
        className={`conversion-history loading ${className}`}
        role="status"
        aria-label="Loading history"
      >
        <div className="loading-spinner">
          <span aria-hidden="true">⏳</span> Loading conversion history...
        </div>
      </div>
    );
  }

  return (
    <div className={`conversion-history ${className}`}>
      {/* Usage Stats Header */}
      {usageStats && (
        <div className="usage-stats-bar">
          <div className="usage-stat">
            <span className="usage-label">Plan:</span>
            <span className="usage-value tier-{usageStats.tier}">
              {formatTierDisplay(usageStats.tier)}
            </span>
          </div>
          <div className="usage-stat">
            <span className="usage-label">This Month:</span>
            <span className="usage-value">
              {usageStats.conversions_this_month}
              {usageStats.monthly_limit !== -1 &&
                ` / ${usageStats.monthly_limit}`}
            </span>
          </div>
          {usageStats.monthly_limit !== -1 && (
            <div className="usage-stat">
              <span className="usage-label">Remaining:</span>
              <span className="usage-value">{usageStats.remaining}</span>
            </div>
          )}
          {usageStats.should_upgrade && usageStats.upgrade_message && (
            <a href="/billing?upgrade=true" className="upgrade-link">
              <span aria-hidden="true">⚡</span> Upgrade
            </a>
          )}
        </div>
      )}

      <div className="history-header">
        <h3>
          <span className="history-icon">
            <span aria-hidden="true">📋</span>
          </span>
          Conversion History
          {filteredHistory.length > 0 && (
            <span className="count">({filteredHistory.length})</span>
          )}
        </h3>

        {/* Search and Filter Controls */}
        <div className="history-controls">
          <input
            type="search"
            className="search-input"
            placeholder="Search conversions..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            aria-label="Search conversions"
          />
          <select
            className="status-filter"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            aria-label="Filter by status"
          >
            <option value="all">All Status</option>
            <option value="completed">Completed</option>
            <option value="processing">Processing</option>
            <option value="failed">Failed</option>
            <option value="queued">Queued</option>
          </select>
        </div>

        {filteredHistory.length > 0 && (
          <div className="history-actions">
            {selectedItems.size > 0 &&
              (confirmDelete ? (
                <div
                  className="confirm-actions"
                  role="alertdialog"
                  aria-label="Confirm delete selected"
                >
                  <span className="confirm-text">
                    Delete {selectedItems.size} items?
                  </span>
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
                    autoFocus
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
                  <span aria-hidden="true">🗑️</span> Delete Selected (
                  {selectedItems.size})
                </button>
              ))}

            {confirmClear ? (
              <div
                className="confirm-actions"
                role="alertdialog"
                aria-label="Confirm clear all history"
              >
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
                  autoFocus
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
                <span aria-hidden="true">🧹</span> Clear All
              </button>
            )}
          </div>
        )}
      </div>

      {error && (
        <div className="error-message" role="alert">
          <span aria-hidden="true">⚠️</span> {error}
        </div>
      )}

      {filteredHistory.length === 0 ? (
        <div className="empty-history" role="status">
          <div className="empty-icon" aria-hidden="true">
            📭
          </div>
          <p>No conversions yet</p>
          <p className="empty-subtitle">
            {searchQuery || statusFilter !== 'all'
              ? 'No conversions match your filters'
              : 'Your conversion history will appear here'}
          </p>
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
        <>
          <div className="history-list">
            {filteredHistory.map((item) => (
              <ConversionHistoryItemRow
                key={item.job_id}
                item={item}
                isSelected={selectedItems.has(item.job_id)}
                onToggle={toggleSelection}
                onDelete={deleteConversion}
                onDownload={downloadConversion}
                onDownloadReport={downloadReport}
              />
            ))}
          </div>

          {totalItems > pageSize && (
            <div className="pagination">
              <button
                className="pagination-btn"
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                disabled={currentPage === 1}
                aria-label="Previous page"
              >
                <span aria-hidden="true">‹</span> Prev
              </button>
              <span className="pagination-info">
                Page {currentPage} of {Math.ceil(totalItems / pageSize)}
              </span>
              <button
                className="pagination-btn"
                onClick={() =>
                  setCurrentPage((p) =>
                    Math.min(Math.ceil(totalItems / pageSize), p + 1)
                  )
                }
                disabled={currentPage >= Math.ceil(totalItems / pageSize)}
                aria-label="Next page"
              >
                Next <span aria-hidden="true">›</span>
              </button>
            </div>
          )}
        </>
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
    }
  };

  const updateConversion = (
    jobId: string,
    updates: Partial<ConversionHistoryItem>
  ) => {
    if (historyRef?.updateConversionStatus) {
      historyRef.updateConversionStatus(jobId, updates);
    }
  };

  return {
    setHistoryRef,
    addConversion,
    updateConversion,
  };
};

export default ConversionHistory;
