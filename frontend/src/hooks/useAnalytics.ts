/**
 * Analytics React hook for easy integration with React components.
 */

import { useCallback, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import {
  trackEvent,
  trackPageView,
  trackButtonClick,
  trackConversionEvent,
  trackUploadEvent,
  trackExportEvent,
  AnalyticsEventType,
  AnalyticsEventCategory,
  AnalyticsOptions,
  getSessionId,
  getUserIdValue,
} from '../services/analytics';

export type {
  AnalyticsEventType,
  AnalyticsEventCategory,
  AnalyticsOptions,
};

export {
  trackEvent,
  trackPageView,
  trackButtonClick,
  trackConversionEvent,
  trackUploadEvent,
  trackExportEvent,
  getSessionId,
  getUserIdValue,
};

/**
 * Hook for automatic page view tracking.
 * Tracks page views automatically when the route changes.
 *
 * @param enabled - Whether to enable auto-tracking (default: true)
 */
export const usePageViewTracking = (enabled: boolean = true) => {
  const location = useLocation();

  useEffect(() => {
    if (enabled) {
      trackPageView(location.pathname);
    }
  }, [location.pathname, enabled]);
};

/**
 * Hook for tracking button clicks.
 * Returns a click handler that tracks the button click.
 *
 * @param buttonId - The button ID or name
 * @param additionalProperties - Additional properties to track
 */
export const useButtonClickTracking = (
  buttonId: string,
  additionalProperties?: Record<string, unknown>
) => {
  const location = useLocation();

  return useCallback(
    (_event?: React.MouseEvent) => {
      trackButtonClick(buttonId, location.pathname, {
        properties: additionalProperties,
      });
    },
    [buttonId, location.pathname, additionalProperties]
  );
};

/**
 * Hook for tracking conversion events.
 * Provides functions to track conversion start, complete, fail, and download.
 */
export const useConversionTracking = () => {
  const sessionId = getSessionId();
  const userId = getUserIdValue();

  const trackStart = useCallback(
    (conversionId: string, properties?: Record<string, unknown>) => {
      trackConversionEvent('conversion_start', conversionId, {
        userId,
        sessionId,
        properties,
      });
    },
    [userId, sessionId]
  );

  const trackComplete = useCallback(
    (conversionId: string, properties?: Record<string, unknown>) => {
      trackConversionEvent('conversion_complete', conversionId, {
        userId,
        sessionId,
        properties,
      });
    },
    [userId, sessionId]
  );

  const trackFail = useCallback(
    (conversionId: string, properties?: Record<string, unknown>) => {
      trackConversionEvent('conversion_fail', conversionId, {
        userId,
        sessionId,
        properties,
      });
    },
    [userId, sessionId]
  );

  const trackDownload = useCallback(
    (conversionId: string, properties?: Record<string, unknown>) => {
      trackConversionEvent('conversion_download', conversionId, {
        userId,
        sessionId,
        properties,
      });
    },
    [userId, sessionId]
  );

  return {
    trackStart,
    trackComplete,
    trackFail,
    trackDownload,
  };
};

/**
 * Hook for tracking file uploads.
 * Provides functions to track upload start, complete, and fail.
 */
export const useUploadTracking = () => {
  const sessionId = getSessionId();
  const userId = getUserIdValue();

  const trackStart = useCallback(
    (fileName: string, fileSize: number) => {
      trackUploadEvent('file_upload_start', fileName, fileSize, {
        userId,
        sessionId,
      });
    },
    [userId, sessionId]
  );

  const trackComplete = useCallback(
    (fileName: string, fileSize: number) => {
      trackUploadEvent('file_upload_complete', fileName, fileSize, {
        userId,
        sessionId,
      });
    },
    [userId, sessionId]
  );

  const trackFail = useCallback(
    (fileName: string, fileSize: number) => {
      trackUploadEvent('file_upload_fail', fileName, fileSize, {
        userId,
        sessionId,
      });
    },
    [userId, sessionId]
  );

  return {
    trackStart,
    trackComplete,
    trackFail,
  };
};

/**
 * Hook for tracking export events.
 * Provides functions to track export start and complete.
 */
export const useExportTracking = () => {
  const sessionId = getSessionId();
  const userId = getUserIdValue();

  const trackStart = useCallback(
    (format: string, conversionId?: string) => {
      trackExportEvent('export_start', format, {
        userId,
        sessionId,
        conversionId,
      });
    },
    [userId, sessionId]
  );

  const trackComplete = useCallback(
    (format: string, conversionId?: string) => {
      trackExportEvent('export_complete', format, {
        userId,
        sessionId,
        conversionId,
      });
    },
    [userId, sessionId]
  );

  return {
    trackStart,
    trackComplete,
  };
};

/**
 * Hook for custom event tracking.
 * Provides a flexible way to track any event.
 */
export const useAnalytics = () => {
  const sessionId = getSessionId();
  const userId = getUserIdValue();

  const track = useCallback(
    (
      eventType: AnalyticsEventType,
      eventCategory: AnalyticsEventCategory,
      options?: AnalyticsOptions
    ) => {
      trackEvent(eventType, eventCategory, {
        userId: options?.userId || userId,
        sessionId: options?.sessionId || sessionId,
        conversionId: options?.conversionId,
        properties: options?.properties,
      });
    },
    [userId, sessionId]
  );

  return {
    track,
    sessionId,
    userId,
  };
};
