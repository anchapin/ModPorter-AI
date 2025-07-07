import '@testing-library/jest-dom';
import { setupServer } from 'msw/node';
import { handlers, resetConversionState } from './msw-handlers'; // Assuming handlers are in this path

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
beforeAll(() => server.listen());

// Reset any request handlers that we may add during the tests,
// so they don't affect other tests.
afterEach(() => {
  server.resetHandlers();
  resetConversionState(); // Reset our mock server's internal state
});

// Clean up after the tests are finished.
afterAll(() => server.close());