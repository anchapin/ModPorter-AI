
import { 
  uploadFile, 
  getConversionStatus, 
  convertMod, 
  getAddonDetails 
} from './api';
import { beforeEach, describe, test, expect, vi, afterEach } from 'vitest';

describe('API Service - Comprehensive', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    global.fetch = vi.fn();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('uploadFile', () => {
    test('should upload file successfully', async () => {
      const mockFile = new File(['test content'], 'test.jar', { type: 'application/java-archive' });
      const mockResponse = { filename: 'test.jar', file_id: 'file-123' };
      
      const mockFetch = vi.mocked(global.fetch);
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      } as Response);

      const result = await uploadFile(mockFile);
      expect(result).toEqual(mockResponse);
      expect(mockFetch).toHaveBeenCalledWith(expect.stringContaining('/upload'), expect.objectContaining({
        method: 'POST',
        body: expect.any(FormData),
      }));
    });
  });

  describe('getConversionStatus', () => {
    test('should get status successfully', async () => {
      const jobId = 'job-123';
      const apiResponse = { 
        conversion_id: jobId, 
        status: 'completed', 
        progress: 100,
        message: 'Done',
        created_at: '2026-01-01'
      };
      
      const mockFetch = vi.mocked(global.fetch);
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => apiResponse,
      } as Response);

      const result = await getConversionStatus(jobId);
      expect(result).toEqual({
        job_id: jobId,
        status: 'completed',
        progress: 100,
        message: 'Done',
        created_at: '2026-01-01',
        error: undefined,
        stage: 'completed'
      });
    });
  });

  describe('convertMod', () => {
    test('should start conversion successfully using unified endpoint', async () => {
      const mockFile = new File(['test'], 'test.jar');
      const params = { file: mockFile, target_version: '1.20.0' };
      const apiResponse = { conversion_id: 'job-123', status: 'queued', estimated_time_seconds: 60 };
      
      const mockFetch = vi.mocked(global.fetch);
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => apiResponse,
      } as Response);

      const result = await convertMod(params);
      expect(result.job_id).toBe('job-123');
      expect(result.status).toBe('queued');
      expect(mockFetch).toHaveBeenCalledWith(expect.stringContaining('/conversions'), expect.objectContaining({
        method: 'POST',
        body: expect.any(FormData),
      }));
    });
  });

  describe('getAddonDetails', () => {
    test('should get addon details successfully', async () => {
      const addonId = 'addon-123';
      const mockResponse = { id: addonId, name: 'My Addon' };
      
      const mockFetch = vi.mocked(global.fetch);
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      } as Response);

      const result = await getAddonDetails(addonId);
      expect(result).toEqual(mockResponse);
      expect(mockFetch).toHaveBeenCalledWith(expect.stringContaining(`/addons/${addonId}`));
    });
  });
});
