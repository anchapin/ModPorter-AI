import React, { memo, useState } from 'react';
import { ConversionHistoryItem as IConversionHistoryItem } from './types';
import {
  formatDate,
  formatFileSize,
  getStatusColor,
  getStatusIcon,
} from './utils';
import './ConversionHistory.css';

interface ConversionHistoryItemProps {
  item: IConversionHistoryItem;
  isSelected: boolean;
  onToggle: (jobId: string) => void;
  onDelete: (jobId: string) => void;
  onDownload: (jobId: string, filename: string) => void;
  onDownloadReport?: (jobId: string) => void;
}

export const ConversionHistoryItem = memo(
  ({
    item,
    isSelected,
    onToggle,
    onDelete,
    onDownload,
    onDownloadReport,
  }: ConversionHistoryItemProps) => {
    const [showConfirm, setShowConfirm] = useState(false);

    return (
      <div className={`history-item ${isSelected ? 'selected' : ''}`}>
        <div className="item-checkbox">
          <input
            type="checkbox"
            checked={isSelected}
            onChange={() => onToggle(item.job_id)}
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
              <span
                className="status"
                style={{ color: getStatusColor(item.status) }}
              >
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
                  <span className="option-tag">
                    <span aria-hidden="true">🧠</span> Smart Assumptions
                  </span>
                )}
                {item.options.includeDependencies && (
                  <span className="option-tag">
                    <span aria-hidden="true">📦</span> Dependencies
                  </span>
                )}
                {item.options.modUrl && (
                  <span className="option-tag">
                    <span aria-hidden="true">🔗</span> URL Source
                  </span>
                )}
              </div>
            )}

            {item.error_message && (
              <div className="error-detail">
                <span aria-hidden="true">⚠️</span> {item.error_message}
              </div>
            )}

            {(item.complexity_tier || item.warnings?.length > 0) && (
              <div className="item-details">
                {item.complexity_tier && (
                  <span className={`tier-badge tier-${item.complexity_tier}`}>
                    {item.complexity_tier.charAt(0).toUpperCase() +
                      item.complexity_tier.slice(1)}
                  </span>
                )}
                {item.warnings && item.warnings.length > 0 && (
                  <span
                    className="warnings-badge"
                    title={item.warnings.join(', ')}
                  >
                    <span aria-hidden="true">⚠️</span> {item.warnings.length}
                  </span>
                )}
              </div>
            )}

            {item.features_converted && item.features_converted.length > 0 && (
              <div className="features-summary">
                <span className="features-label">Converted:</span>
                <span className="features-list">
                  {item.features_converted.slice(0, 3).join(', ')}
                  {item.features_converted.length > 3 &&
                    ` +${item.features_converted.length - 3} more`}
                </span>
              </div>
            )}

            {item.features_skipped && item.features_skipped.length > 0 && (
              <div className="features-skipped">
                <span className="features-label">Skipped:</span>
                <span className="features-list">
                  {item.features_skipped.slice(0, 3).join(', ')}
                  {item.features_skipped.length > 3 &&
                    ` +${item.features_skipped.length - 3} more`}
                </span>
              </div>
            )}
          </div>
        </div>

        <div className="item-actions">
          {item.status === 'completed' && !showConfirm && (
            <>
              <button
                className="download-btn"
                onClick={() => onDownload(item.job_id, item.original_filename)}
                title="Download converted file"
                aria-label={`Download ${item.original_filename}`}
              >
                <span aria-hidden="true">⬇️</span> Download
              </button>
              {onDownloadReport && (
                <button
                  className="report-btn"
                  onClick={() => onDownloadReport(item.job_id)}
                  title="Download conversion report"
                  aria-label={`Download report for ${item.original_filename}`}
                >
                  <span aria-hidden="true">📄</span> Report
                </button>
              )}
            </>
          )}

          {showConfirm ? (
            <div
              className="confirm-delete-group"
              role="group"
              aria-label="Confirm deletion"
            >
              <button
                className="confirm-yes-btn"
                onClick={() => onDelete(item.job_id)}
                aria-label="Confirm deletion"
                title="Confirm deletion"
              >
                <span aria-hidden="true">✓</span>
              </button>
              <button
                className="confirm-no-btn"
                onClick={() => setShowConfirm(false)}
                aria-label="Cancel deletion"
                title="Cancel deletion"
                autoFocus
              >
                <span aria-hidden="true">✕</span>
              </button>
            </div>
          ) : (
            <button
              className="delete-btn"
              onClick={() => setShowConfirm(true)}
              title="Remove from history"
              aria-label={`Remove ${item.original_filename} from history`}
            >
              <span aria-hidden="true">🗑️</span>
            </button>
          )}
        </div>
      </div>
    );
  }
);

ConversionHistoryItem.displayName = 'ConversionHistoryItem';

export default ConversionHistoryItem;
