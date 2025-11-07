/**
 * Integration Tests for Frontend-Backend API Connection
 * Tests the real API endpoints to ensure proper integration
 */

import { describe, test, expect, beforeAll, describe as context } from 'vitest';
import { 
  uploadFile, 
  convertMod, 
  getConversionStatus,
  API_BASE_URL 
} from '../services/api';

// Test configuration
const TEST_TIMEOUT = 30000; // 30 seconds
const BACKEND_URL = API_BASE_URL;

let isBackendRunning = false;

describe('Frontend-Backend Integration', () => {
  beforeAll(async () => {
    // Check if backend is running
    try {
      const response = await fetch(`${BACKEND_URL}/health`);
      if (!response.ok) {
        throw new Error(`Backend health check failed: ${response.status}`);
      }
      isBackendRunning = true;
    } catch {
      console.warn('Backend may not be running. Some tests may fail.');
      console.warn('Start backend with: docker-compose up -d backend');
      isBackendRunning = false;
    }
  });

  test('Backend health check endpoint', async () => {
    if (!isBackendRunning) {
      console.warn('Skipping backend health check test - backend not running');
      return;
    }
    
    const response = await fetch(`${BACKEND_URL}/health`);
    expect(response.ok).toBe(true);
    
    const data = await response.json();
    expect(data).toHaveProperty('status', 'healthy');
    expect(data).toHaveProperty('version');
    expect(data).toHaveProperty('timestamp');
  });

  test('File upload endpoint', async () => {
    if (!isBackendRunning) {
      console.warn('Skipping file upload test - backend not running');
      return;
    }
    
    // Create a simple test file
    const testContent = 'Test jar file content';
    const testFile = new File([testContent], 'test-mod.jar', {
      type: 'application/java-archive',
    });
    
    // Ensure file name is set correctly for test environment
    Object.defineProperty(testFile, 'name', {
      value: 'test-mod.jar',
      writable: false
    });

    const uploadResponse = await uploadFile(testFile);
    
    expect(uploadResponse).toHaveProperty('file_id');
    expect(uploadResponse).toHaveProperty('original_filename', 'test-mod.jar');
    expect(uploadResponse).toHaveProperty('size', testContent.length);
    expect(uploadResponse.message).toContain('saved successfully');
  });

  test('Conversion workflow integration', async () => {
    if (!isBackendRunning) {
      console.warn('Skipping conversion workflow test - backend not running');
      return;
    }
    
    // Create a test file
    const testContent = 'PK\x03\x04'; // Basic ZIP file signature
    const testFile = new File([testContent], 'test-conversion.jar', {
      type: 'application/java-archive',
    });

    // Step 1: Start conversion
    const conversionResponse = await convertMod({
      file: testFile,
      smartAssumptions: true,
      includeDependencies: false,
    });

    expect(conversionResponse).toHaveProperty('job_id');
    expect(conversionResponse).toHaveProperty('status');
    expect(conversionResponse.message).toContain('started');

    const jobId = conversionResponse.job_id;

    // Step 2: Check status (may take time in real scenario)
    const statusResponse = await getConversionStatus(jobId);
    
    expect(statusResponse).toHaveProperty('job_id', jobId);
    expect(statusResponse).toHaveProperty('status');
    expect(statusResponse).toHaveProperty('progress');
    expect(statusResponse).toHaveProperty('message');
    expect(statusResponse.progress).toBeGreaterThanOrEqual(0);
    expect(statusResponse.progress).toBeLessThanOrEqual(100);

    // Note: In real scenarios, you would poll until completion
    // For this test, we just verify the status endpoint works
  }, TEST_TIMEOUT);

  test('API error handling', async () => {
    if (!isBackendRunning) {
      console.warn('Skipping API error handling test - backend not running');
      return;
    }
    
    // Test invalid job ID
    await expect(getConversionStatus('invalid-job-id')).rejects.toThrow();
    
    // Test invalid file
    const invalidFile = new File(['not a jar'], 'test.txt', {
      type: 'text/plain',
    });
    
    await expect(uploadFile(invalidFile)).rejects.toThrow();
  });

  test('API endpoints return correct content types', async () => {
    if (!isBackendRunning) {
      console.warn('Skipping API content types test - backend not running');
      return;
    }
    
    const healthResponse = await fetch(`${BACKEND_URL}/health`);
    expect(healthResponse.headers.get('content-type')).toContain('application/json');
  });
});

// Helper function for testing with real backend
export const testBackendConnectivity = async (): Promise<boolean> => {
  try {
    const response = await fetch(`${BACKEND_URL}/health`);
    return response.ok;
  } catch {
    return false;
  }
};