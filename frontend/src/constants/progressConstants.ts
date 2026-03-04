/**
 * Progress Context Constants
 * Centralized constants for progress tracking functionality
 */

export const PROGRESS_STORAGE_KEY = 'conversion_progress';
export const CONNECTION_STATUS = {
  DISCONNECTED: 'disconnected' as const,
  CONNECTING: 'connecting' as const,
  CONNECTED: 'connected' as const,
  ERROR: 'error' as const,
} as const;

export const MEMORY_LEAK_DETECTION_CONFIG = {
  MAX_UPDATES_PER_MINUTE: 10,
  MAX_STORED_CONVERSIONS: 50,
  CLEANUP_INTERVAL_MS: 60000, // 1 minute
} as const;

export const ERROR_MESSAGES = {
  NETWORK_ERROR: 'Network error - Unable to connect to conversion service',
  STORAGE_ERROR: 'Unable to access local storage',
  PARSE_ERROR: 'Failed to parse conversion data',
  CONNECTION_LOST: 'Connection to conversion service lost',
} as const;
