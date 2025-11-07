// Polyfills first
import { TextEncoder, TextDecoder } from 'util';
global.TextEncoder = TextEncoder;
global.TextDecoder = TextDecoder;

// Comprehensive Web Stream API polyfills for Node.js compatibility
// Note: Using require due to Node.js compatibility issues with esm imports
// eslint-disable-next-line @typescript-eslint/no-require-imports
const { TransformStream, WritableStream } = require('node:stream/web');
global.TransformStream = TransformStream;
global.WritableStream = WritableStream;

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

// MSW setup disabled temporarily due to Node.js compatibility issues
// Will be re-enabled once Web Stream API polyfills are resolved
console.log('Test setup: MSW disabled due to Node.js compatibility issues');