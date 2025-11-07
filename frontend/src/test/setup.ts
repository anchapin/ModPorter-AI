// Polyfills first
import { TextEncoder, TextDecoder } from 'util';
global.TextEncoder = TextEncoder;
global.TextDecoder = TextDecoder;

// Comprehensive Web Stream API polyfills for Node.js compatibility
const { TransformStream, WritableStream } = require('node:stream/web');
global.TransformStream = TransformStream;
global.WritableStream = WritableStream;

import '@testing-library/jest-dom';

// Temporarily disable MSW due to Node.js compatibility issues
// import { setupServer } from 'msw/node';
import { handlers, resetConversionState } from './msw-handlers'; // Assuming handlers are in this path
import { beforeAll, afterEach, afterAll } from 'vitest';

// Setup requests interception using the given handlers.
export const server = setupServer(...handlers);

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

// Establish API mocking before all tests.
// beforeAll(() => server.listen());

// Reset any request handlers that we may add during the tests,
// so they don't affect other tests.
afterEach(() => {
  server.resetHandlers();
  resetConversionState(); // Reset our mock server's internal state
});

// Clean up after the tests are finished.
// afterAll(() => server.close());