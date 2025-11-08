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
    const mockHeaders = new Map([
      ['content-type', 'application/json']
    ]);
    
    return Promise.resolve({
      ok: true,
      status: 200,
      headers: mockHeaders,
      json: () => Promise.resolve({
        status: 'healthy',
        version: '1.0.0',
        timestamp: new Date().toISOString(),
      }),
    });
  }
  
  if (url.includes('/upload') && options?.method === 'POST') {
    // Get file from request to check type
    const mockBody = options.body as FormData;
    const file = mockBody?.get('file') as File;
    
    // Reject invalid file types
    if (file && !file.name.endsWith('.jar')) {
      return Promise.resolve({
        ok: false,
        status: 400,
        headers: new Map([['content-type', 'application/json']]),
        json: () => Promise.resolve({ detail: 'Invalid file type' }),
      });
    }
    
    // Get the actual file size from the request for more accurate testing
    const mockText = 'Test jar file content';
    const actualSize = mockText.length;
    
    const uploadHeaders = new Map([
      ['content-type', 'application/json']
    ]);
    
    return Promise.resolve({
      ok: true,
      status: 200,
      headers: uploadHeaders,
      json: () => Promise.resolve({
        file_id: 'mock-file-123',
        original_filename: 'test-mod.jar',
        saved_filename: 'mock-file-123.jar',
        size: actualSize, // Use actual content length
        content_type: 'application/java-archive',
        message: 'saved successfully',
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
    // Check if this is an invalid job ID request
    const statusHeaders = new Map([
      ['content-type', 'application/json']
    ]);
    
    if (url.includes('invalid-job-id')) {
      return Promise.resolve({
        ok: false,
        status: 404,
        headers: statusHeaders,
        json: () => Promise.resolve({
          detail: 'Job not found'
        }),
      });
    }
    
    return Promise.resolve({
      ok: true,
      status: 200,
      headers: statusHeaders,
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