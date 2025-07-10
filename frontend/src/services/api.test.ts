import { submitFeedback } from './api';
import type { FeedbackCreatePayload, FeedbackResponse } from '../types/api';
import { vi, beforeEach, afterEach, describe, test, expect } from 'vitest';
import { server } from '../test/setup';
import { http, HttpResponse } from 'msw';

describe('API Service - Feedback', () => {
  beforeEach(() => {
    // Reset MSW handlers
    server.resetHandlers();
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
      server.use(
        http.post('http://localhost:8080/api/v1/feedback', () => {
          return HttpResponse.json(mockSuccessResponse);
        })
      );

      const result = await submitFeedback(mockPayload);
      expect(result).toEqual(mockSuccessResponse);
    });

    test('should throw ApiError on API error response (e.g., 400, 500)', async () => {
      const errorDetail = 'Invalid feedback data';
      server.use(
        http.post('http://localhost:8080/api/v1/feedback', () => {
          return HttpResponse.json({ detail: errorDetail }, { status: 400 });
        })
      );

      await expect(submitFeedback(mockPayload)).rejects.toThrow(errorDetail);
    });

    test('should throw ApiError with default message if detail is missing on API error', async () => {
        server.use(
          http.post('http://localhost:8080/api/v1/feedback', () => {
            return HttpResponse.json({}, { status: 500 });
          })
        );

        await expect(submitFeedback(mockPayload)).rejects.toThrow('Failed to submit feedback');
      });

    test('should throw an error on network failure', async () => {
      server.use(
        http.post('http://localhost:8080/api/v1/feedback', () => {
          return HttpResponse.error();
        })
      );

      await expect(submitFeedback(mockPayload)).rejects.toThrow();
    });

    test('should handle non-JSON error responses from API', async () => {
        server.use(
          http.post('http://localhost:8080/api/v1/feedback', () => {
            return new HttpResponse('Server Error Text', { status: 500 });
          })
        );

        await expect(submitFeedback(mockPayload)).rejects.toThrow('Unknown error submitting feedback');
      });
  });
});
