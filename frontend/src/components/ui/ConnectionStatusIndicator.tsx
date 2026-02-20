/**
 * Connection Status Indicator Component
 * Displays WebSocket connection status with visual feedback
 */

import React from 'react';
import './ConnectionStatusIndicator.css';

export type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'error';

export interface ConnectionStatusIndicatorProps {
  status: ConnectionStatus;
  usingWebSocket?: boolean;
  error?: string | null;
  showLabel?: boolean;
  showTooltip?: boolean;
  size?: 'small' | 'medium' | 'large';
  className?: string;
  onClick?: () => void;
}

/**
 * Get status display information
 */
const getStatusInfo = (status: ConnectionStatus, usingWebSocket: boolean) => {
  if (status === 'connected') {
    return {
      label: usingWebSocket ? 'Real-time updates active' : 'Connected',
      tooltip: usingWebSocket
        ? 'Connected via WebSocket - Real-time updates'
        : 'Connected - Updates active',
      icon: '●',
      className: 'connected'
    };
  }

  if (status === 'connecting') {
    return {
      label: 'Connecting...',
      tooltip: 'Establishing connection...',
      icon: '○',
      className: 'connecting'
    };
  }

  if (status === 'error') {
    return {
      label: 'Connection Error',
      tooltip: 'Connection failed - Using fallback polling',
      icon: '✕',
      className: 'error'
    };
  }

  if (usingWebSocket) {
    return {
      label: 'Disconnected',
      tooltip: 'WebSocket disconnected - Using fallback polling',
      icon: '○',
      className: 'disconnected-websocket'
    };
  }

  return {
    label: 'Using fallback polling',
    tooltip: 'Real-time connection unavailable - Using polling',
    icon: '○',
    className: 'polling'
  };
};

/**
 * Connection Status Indicator Component
 */
export const ConnectionStatusIndicator: React.FC<ConnectionStatusIndicatorProps> = ({
  status,
  usingWebSocket = false,
  error = null,
  showLabel = true,
  showTooltip = true,
  size = 'medium',
  className = '',
  onClick
}) => {
  const statusInfo = getStatusInfo(status, usingWebSocket);

  const handleClick = () => {
    if (onClick) {
      onClick();
    }
  };

  return (
    <div
      className={`connection-status-indicator ${statusInfo.className} size-${size} ${onClick ? 'clickable' : ''} ${className}`}
      onClick={handleClick}
      title={showTooltip ? statusInfo.tooltip : undefined}
    >
      <div className="indicator-icon">{statusInfo.icon}</div>

      {showLabel && (
        <div className="indicator-content">
          <span className="indicator-label">{statusInfo.label}</span>

          {error && status === 'error' && (
            <span className="indicator-error">{error}</span>
          )}
        </div>
      )}

      {status === 'connecting' && (
        <div className="indicator-pulse" />
      )}
    </div>
  );
};

export default ConnectionStatusIndicator;
