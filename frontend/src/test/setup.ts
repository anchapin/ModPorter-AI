// Apply polyfills immediately before any other imports
(() => {
  const { TextEncoder, TextDecoder } = require('util');
  global.TextEncoder = TextEncoder;
  global.TextDecoder = TextDecoder;

  // Use web-streams-polyfill for better MSW compatibility
  try {
    const { TransformStream, WritableStream, ReadableStream } = require('web-streams-polyfill');
    global.TransformStream = TransformStream;
    global.WritableStream = WritableStream;
    global.ReadableStream = ReadableStream;
  } catch (e) {
    console.warn('web-streams-polyfill not available, trying node:stream/web:', e);
    // Fallback to Node.js native implementation
    try {
      const { TransformStream, WritableStream, ReadableStream } = require('node:stream/web');
      global.TransformStream = TransformStream;
      global.WritableStream = WritableStream;
      global.ReadableStream = ReadableStream;
    } catch (nodeError) {
      console.warn('Both polyfills failed, using minimal implementations:', nodeError);
      // Minimal fallback implementations
      global.TransformStream = class TransformStream {
        constructor() {}
      };
      global.WritableStream = class WritableStream {
        constructor() {}
      };
      global.ReadableStream = class ReadableStream {
        constructor() {}
      };
    }
  }
})();

import '@testing-library/jest-dom';

// Mock environment variables
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => {},
  }),
});

// Mock fetch implementation to replace MSW
const mockResponses = new Map<string, any>();

const mockFetch = vi.fn((url: string, options?: RequestInit) => {
  console.log('Mock fetch called:', url, options?.method);
  
  // Store request for debugging
  mockFetch.lastRequest = { url, options };
  
  // Return mock response based on URL pattern
  if (url.includes('/health')) {
    return Promise.resolve({
      ok: true,
      status: 200,
      json: () => Promise.resolve({
        status: 'healthy',
        version: '1.0.0',
        timestamp: new Date().toISOString(),
      }),
    });
  }
  
  if (url.includes('/upload') && options?.method === 'POST') {
    return Promise.resolve({
      ok: true,
      status: 200,
      json: () => Promise.resolve({
        file_id: 'mock-file-123',
        original_filename: 'test-mod.jar',
        saved_filename: 'mock-file-123.jar',
        size: 1024,
        content_type: 'application/java-archive',
        message: 'File uploaded successfully',
      }),
    });
  }
  
  if (url.includes('/convert') && options?.method === 'POST') {
    return Promise.resolve({
      ok: true,
      status: 200,
      json: () => Promise.resolve({
        job_id: 'mock-job-123',
        status: 'pending',
        message: 'Conversion started',
        progress: 0,
        overallSuccessRate: 0,
        convertedMods: [],
        failedMods: [],
        smartAssumptionsApplied: [],
        detailedReport: { stage: 'Pending', progress: 0, logs: [], technicalDetails: {} },
      }),
    });
  }
  
  if (url.includes('/status')) {
    return Promise.resolve({
      ok: true,
      status: 200,
      json: () => Promise.resolve({
        job_id: 'mock-job-123',
        status: 'completed',
        progress: 100,
        message: 'Conversion completed',
        stage: 'Completed',
        overallSuccessRate: 100,
        convertedMods: [{ name: 'Test Mod', version: '1.0', status: 'success', features: [], warnings: [] }],
        failedMods: [],
        smartAssumptionsApplied: [],
        detailedReport: { stage: 'Completed', progress: 100, logs: [], technicalDetails: {} },
      }),
    });
  }
  
  if (url.includes('/download')) {
    return Promise.resolve({
      ok: true,
      status: 200,
      blob: () => Promise.resolve(new Blob(['mock file content'], { type: 'application/octet-stream' })),
      headers: new Map([['Content-Disposition', 'attachment; filename="converted.mcaddon"']]),
    });
  }
  
  if (url.includes('/feedback') && options?.method === 'POST') {
    return Promise.resolve({
      ok: true,
      status: 200,
      json: () => Promise.resolve({
        message: 'Feedback submitted successfully',
      }),
    });
  }
  
  // Default response
  return Promise.resolve({
    ok: false,
    status: 404,
    json: () => Promise.resolve({ detail: 'Not found' }),
  });
});

// Replace global fetch
global.fetch = mockFetch;

export const server = {
  listen: () => {
    console.log('Test setup: Fetch mocking enabled');
  },
  resetHandlers: () => {
    mockFetch.mockClear();
  },
  close: () => {
    vi.restoreAllMocks();
  },
  use: () => {},
  // Expose the mock for testing
  _getMock: () => mockFetch,
};

console.log('Test setup: Using fetch mocking instead of MSW');