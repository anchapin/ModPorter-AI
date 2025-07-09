import { submitFeedback } from './api';
import type { FeedbackCreatePayload, FeedbackResponse } from '../types/api';

// Mock the global fetch function
global.fetch = jest.fn();

// Helper to cast mock fetch
const mockFetch = fetch as jest.Mock;

describe('API Service - Feedback', () => {
  beforeEach(() => {
    // Reset the mock before each test
    mockFetch.mockClear();
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

    it('should submit feedback successfully', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockSuccessResponse,
        status: 200,
      } as Response);

      const result = await submitFeedback(mockPayload);

      expect(mockFetch).toHaveBeenCalledTimes(1);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringMatching(/\/api\/v1\/feedback$/), // Checks if URL ends with /api/v1/feedback
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(mockPayload),
        }
      );
      expect(result).toEqual(mockSuccessResponse);
    });

    it('should throw ApiError on API error response (e.g., 400, 500)', async () => {
      const errorDetail = 'Invalid feedback data';
      mockFetch.mockResolvedValueOnce({
        ok: false,
        json: async () => ({ detail: errorDetail }),
        status: 400,
      } as Response);

      await expect(submitFeedback(mockPayload)).rejects.toThrow(errorDetail);

      expect(mockFetch).toHaveBeenCalledTimes(1);
    });

    it('should throw ApiError with default message if detail is missing on API error', async () => {
        mockFetch.mockResolvedValueOnce({
          ok: false,
          json: async () => ({}), // No detail in error response
          status: 500,
        } as Response);

        await expect(submitFeedback(mockPayload)).rejects.toThrow('Failed to submit feedback');
        expect(mockFetch).toHaveBeenCalledTimes(1);
      });

    it('should throw an error on network failure', async () => {
      const networkError = new TypeError('Failed to fetch'); // Simulate network error
      mockFetch.mockRejectedValueOnce(networkError);

      // The ApiError class might not be thrown for a raw network error,
      // depends on how submitFeedback handles it. If it re-throws, test for that.
      // The current implementation of submitFeedback would likely let this bubble up or catch and throw its own.
      // Based on the structure of other functions in api.ts, it's likely an ApiError is not thrown here,
      // but the original network error or a generic one.
      // For now, let's assume it throws the network error or a generic error message.
      // The provided api.ts doesn't wrap fetch in a try/catch that would create an ApiError for network issues.
      // It relies on response.ok. So, a TypeError "Failed to fetch" is expected.
      await expect(submitFeedback(mockPayload)).rejects.toThrow(networkError.message);

      expect(mockFetch).toHaveBeenCalledTimes(1);
    });

    it('should handle non-JSON error responses from API', async () => {
        mockFetch.mockResolvedValueOnce({
          ok: false,
          json: async () => { throw new Error('Not JSON'); }, // Simulate response.json() failing
          text: async () => 'Server Error Text', // Fallback if .json() fails
          status: 500,
        } as any); // Using 'any' because .json() is intentionally broken for this test

        // The ApiError constructor in api.ts tries response.json().catch(),
        // which would lead to 'Unknown error submitting feedback' if .json() fails badly
        // or it might use the status code. Let's test the expected behavior.
        // The current ApiError in api.ts has: await response.json().catch(() => ({ detail: 'Unknown error submitting feedback' }));
        await expect(submitFeedback(mockPayload)).rejects.toThrow('Unknown error submitting feedback');
        expect(mockFetch).toHaveBeenCalledTimes(1);
      });
  });
});
