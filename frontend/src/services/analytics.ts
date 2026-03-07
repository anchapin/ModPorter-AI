/**
 * Analytics service for tracking user behavior and usage.
 * Provides a unified interface for tracking events in the frontend.
 */

import { API_BASE_URL } from './api';

// Event type constants
export const AnalyticsEventType = {
  // Page views
  PAGE_VIEW: 'page_view',
  LANDING_PAGE: 'landing_page',
  CONVERSION_PAGE: 'conversion_page',
  DASHBOARD_PAGE: 'dashboard_page',
  HISTORY_PAGE: 'history_page',

  // Conversion events
  CONVERSION_START: 'conversion_start',
  CONVERSION_COMPLETE: 'conversion_complete',
  CONVERSION_FAIL: 'conversion_fail',
  CONVERSION_CANCEL: 'conversion_cancel',
  CONVERSION_DOWNLOAD: 'conversion_download',

  // Upload events
  FILE_UPLOAD_START: 'file_upload_start',
  FILE_UPLOAD_COMPLETE: 'file_upload_complete',
  FILE_UPLOAD_FAIL: 'file_upload_fail',

  // User actions
  BUTTON_CLICK: 'button_click',
  LINK_CLICK: 'link_click',
  FORM_SUBMIT: 'form_submit',
  FEEDBACK_SUBMIT: 'feedback_submit',

  // Export events
  EXPORT_START: 'export_start',
  EXPORT_COMPLETE: 'export_complete',

  // Navigation events
  NAVIGATE: 'navigate',
} as const;

// Event category constants
export const AnalyticsEventCategory = {
  NAVIGATION: 'navigation',
  CONVERSION: 'conversion',
  UPLOAD: 'upload',
  FEEDBACK: 'feedback',
  EXPORT: 'export',
  USER_ACTION: 'user_action',
} as const;

// Generate a unique session ID
const generateSessionId = (): string => {
  const stored = sessionStorage.getItem('analytics_session_id');
  if (stored) return stored;

  const newSessionId = `sess_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  sessionStorage.setItem('analytics_session_id', newSessionId);
  return newSessionId;
};

// Get or generate user ID
const getUserId = (): string | undefined => {
  // For now, we'll use a generated anonymous ID
  // In the future, this could be tied to actual user accounts
  let userId = localStorage.getItem('analytics_user_id');
  if (!userId) {
    userId = `anon_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    localStorage.setItem('analytics_user_id', userId);
  }
  return userId;
};

export type AnalyticsEventType = (typeof AnalyticsEventType)[keyof typeof AnalyticsEventType];
export type AnalyticsEventCategory = (typeof AnalyticsEventCategory)[keyof typeof AnalyticsEventCategory];

export interface AnalyticsEvent {
  event_type: AnalyticsEventType;
  event_category: AnalyticsEventCategory;
  user_id?: string;
  session_id?: string;
  conversion_id?: string;
  event_properties?: Record<string, unknown>;
}

export interface AnalyticsOptions {
  userId?: string;
  sessionId?: string;
  conversionId?: string;
  properties?: Record<string, unknown>;
}

/**
 * Track an analytics event.
 *
 * @param eventType - The type of event (e.g., 'page_view', 'conversion_start')
 * @param eventCategory - The category of event (e.g., 'navigation', 'conversion')
 * @param options - Optional additional data
 */
export const trackEvent = async (
  eventType: AnalyticsEventType,
  eventCategory: AnalyticsEventCategory,
  options: AnalyticsOptions = {}
): Promise<void> => {
  const { userId, sessionId, conversionId, properties } = options;

  const payload = {
    event_type: eventType,
    event_category: eventCategory,
    user_id: userId || getUserId(),
    session_id: sessionId || generateSessionId(),
    conversion_id: conversionId,
    event_properties: properties,
  };

  try {
    // Fire and forget - don't block the main thread
    fetch(`${API_BASE_URL}/analytics/events`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    }).catch((err) => {
      console.warn('[Analytics] Failed to track event:', err);
    });
  } catch (err) {
    console.warn('[Analytics] Failed to track event:', err);
  }
};

/**
 * Track a page view.
 *
 * @param page - The page path (e.g., '/', '/convert')
 * @param options - Optional additional data
 */
export const trackPageView = (
  page: string,
  options: Omit<AnalyticsOptions, 'properties'> = {}
): void => {
  trackEvent(AnalyticsEventType.PAGE_VIEW, AnalyticsEventCategory.NAVIGATION, {
    ...options,
    properties: {
      ...options.properties,
      page,
    },
  });
};

/**
 * Track a conversion event.
 *
 * @param eventType - The conversion event type (start, complete, fail, download)
 * @param conversionId - The conversion job ID
 * @param options - Optional additional data
 */
export const trackConversionEvent = async (
  eventType:
    | 'conversion_start'
    | 'conversion_complete'
    | 'conversion_fail'
    | 'conversion_cancel'
    | 'conversion_download',
  conversionId: string,
  options: Omit<AnalyticsOptions, 'conversionId'> = {}
): Promise<void> => {
  await trackEvent(eventType, AnalyticsEventCategory.CONVERSION, {
    ...options,
    conversionId,
  });
};

/**
 * Track a button click.
 *
 * @param buttonId - The button ID or name
 * @param page - The page where the click occurred
 * @param options - Optional additional data
 */
export const trackButtonClick = (
  buttonId: string,
  page: string,
  options: Omit<AnalyticsOptions, 'properties'> = {}
): void => {
  trackEvent(
    AnalyticsEventType.BUTTON_CLICK,
    AnalyticsEventCategory.USER_ACTION,
    {
      ...options,
      properties: {
        button_id: buttonId,
        page,
      },
    }
  );
};

/**
 * Track a file upload event.
 *
 * @param eventType - The upload event type (start, complete, fail)
 * @param fileName - The name of the uploaded file
 * @param fileSize - The size of the file in bytes
 * @param options - Optional additional data
 */
export const trackUploadEvent = async (
  eventType: 'file_upload_start' | 'file_upload_complete' | 'file_upload_fail',
  fileName: string,
  fileSize: number,
  options: AnalyticsOptions = {}
): Promise<void> => {
  await trackEvent(eventType, AnalyticsEventCategory.UPLOAD, {
    ...options,
    properties: {
      ...options.properties,
      file_name: fileName,
      file_size: fileSize,
    },
  });
};

/**
 * Track an export event.
 *
 * @param eventType - The export event type (start, complete)
 * @param format - The export format (e.g., 'mcaddon', 'zip')
 * @param options - Optional additional data
 */
export const trackExportEvent = async (
  eventType: 'export_start' | 'export_complete',
  format: string,
  options: AnalyticsOptions = {}
): Promise<void> => {
  await trackEvent(eventType, AnalyticsEventCategory.EXPORT, {
    ...options,
    properties: {
      ...options.properties,
      export_format: format,
    },
  });
};

/**
 * Get the current session ID.
 */
export const getSessionId = (): string => {
  return generateSessionId();
};

/**
 * Get or create an anonymous user ID.
 */
export const getUserIdValue = (): string => {
  return getUserId();
};
