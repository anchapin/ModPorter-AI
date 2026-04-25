import { usePageViewTracking } from '../hooks/useAnalytics';

/**
 * PageViewTracker - Wrapper component that tracks page views.
 * Must be used inside a Router context.
 */
export const PageViewTracker = () => {
  usePageViewTracking(true);
  return null;
};
