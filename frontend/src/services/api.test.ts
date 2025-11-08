import { submitFeedback } from './api';
import type { FeedbackCreatePayload, FeedbackResponse } from '../types/api';
import { beforeEach, describe, test, expect, vi, afterEach } from 'vitest';
import { server } from '../test/setup';

describe('API Service - Feedback', () => {
  beforeEach(() => {
    // Reset MSW handlers
    server.resetHandlers();
    
    // Mock fetch since MSW is disabled
    global.fetch = vi.fn();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('submitFeedback', () => {
    const mockPayload: FeedbackCreatePayload = {
      job_id: 'job-123-uuid',
      feedback_type: 'thumbs_up',
      comment: 'Looks great!',
      user_id: 'user-789',
    };

    const mockSuccessResponse: FeedbackResponse = {
      id: 'feedback-abc-uuid',
      job_id: 'job-123-uuid',
      feedback_type: 'thumbs_up',
      comment: 'Looks great!',
      user_id: 'user-789',
      created_at: new Date().toISOString(),
    };

    test('should submit feedback successfully', async () => {
      const mockFetch = vi.mocked(global.fetch);
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockSuccessResponse,
      } as Response);

      const result = await submitFeedback(mockPayload);
      expect(result).toEqual(mockSuccessResponse);
      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/feedback',
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(mockPayload),
        }
      );
    });

    test('should throw ApiError on API error response (e.g., 400, 500)', async () => {
      const errorDetail = 'Invalid feedback data';
      const mockFetch = vi.mocked(global.fetch);
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: async () => ({ detail: errorDetail }),
      } as Response);

      await expect(submitFeedback(mockPayload)).rejects.toThrow(errorDetail);
    });

    test('should throw ApiError with default message if detail is missing on API error', async () => {
        const mockFetch = vi.mocked(global.fetch);
        mockFetch.mockResolvedValueOnce({
          ok: false,
          status: 500,
          json: async () => ({}),
        } as Response);

        await expect(submitFeedback(mockPayload)).rejects.toThrow('Failed to submit feedback');
      });

    test('should throw an error on network failure', async () => {
      const mockFetch = vi.mocked(global.fetch);
      mockFetch.mockRejectedValueOnce(new Error('Network error'));

      await expect(submitFeedback(mockPayload)).rejects.toThrow('Network error');
    });

    test('should handle non-JSON error responses from API', async () => {
        const mockFetch = vi.mocked(global.fetch);
        mockFetch.mockResolvedValueOnce({
          ok: false,
          status: 500,
          json: async () => {
            throw new Error('Invalid JSON');
          },
        } as Response);

        await expect(submitFeedback(mockPayload)).rejects.toThrow('Unknown error submitting feedback');
      });
  });
});
