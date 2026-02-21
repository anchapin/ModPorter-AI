import React, { memo, useState } from 'react';
import { ConversionHistoryItem as IConversionHistoryItem } from './types';
import { formatDate, formatFileSize, getStatusColor, getStatusIcon } from './utils';
import './ConversionHistory.css';

interface ConversionHistoryItemProps {
  item: IConversionHistoryItem;
  isSelected: boolean;
  onToggle: (jobId: string) => void;
  onDelete: (jobId: string) => void;
  onDownload: (jobId: string, filename: string) => void;
}

export const ConversionHistoryItem = memo(({
  item,
  isSelected,
  onToggle,
  onDelete,
  onDownload
}: ConversionHistoryItemProps) => {
  const [showConfirm, setShowConfirm] = useState(false);

  return (
    <div
      className={`history-item ${isSelected ? 'selected' : ''}`}
    >
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
        {item.status === 'completed' && !showConfirm && (
          <button
            className="download-btn"
            onClick={() => onDownload(item.job_id, item.original_filename)}
            title="Download converted file"
            aria-label={`Download ${item.original_filename}`}
          >
            ⬇️ Download
          </button>
        )}

        {showConfirm ? (
           <div className="confirm-delete-group" role="group" aria-label="Confirm deletion">
             <button
                className="confirm-yes-btn"
                onClick={() => onDelete(item.job_id)}
                aria-label="Confirm deletion"
                title="Confirm deletion"
             >
               ✓
             </button>
             <button
                className="confirm-no-btn"
                onClick={() => setShowConfirm(false)}
                aria-label="Cancel deletion"
                title="Cancel deletion"
                autoFocus
             >
               ✕
             </button>
           </div>
        ) : (
            <button
              className="delete-btn"
              onClick={() => setShowConfirm(true)}
              title="Remove from history"
              aria-label={`Remove ${item.original_filename} from history`}
            >
              🗑️
            </button>
        )}
      </div>
    </div>
  );
});

ConversionHistoryItem.displayName = 'ConversionHistoryItem';

export default ConversionHistoryItem;
