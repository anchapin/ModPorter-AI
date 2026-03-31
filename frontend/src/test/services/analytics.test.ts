/**
 * Tests for analytics service
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { trackEvent, trackPageView, trackConversionEvent } from '../../services/analytics';

describe('Analytics Service', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    global.fetch = vi.fn();
  });

  describe('trackPageView', () => {
    it('should track page view function exists', () => {
      // trackPageView exists and is a function
      expect(trackPageView).toBeDefined();
      expect(typeof trackPageView).toBe('function');
    });
  });

  describe('trackEvent', () => {
    it('should track custom event', async () => {
      (global.fetch as any).mockResolvedValue({ ok: true });
      
      await trackEvent('click', 'button', { buttonId: 'submit' });
      
      expect(global.fetch).toHaveBeenCalled();
    });
  });

  describe('trackConversionEvent', () => {
    it('should track conversion with file info', async () => {
      (global.fetch as any).mockResolvedValue({ ok: true });
      
      await trackConversionEvent('conv-123', 'jar', 1024);
      
      expect(global.fetch).toHaveBeenCalled();
    });
  });
});