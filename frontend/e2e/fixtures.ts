import { test as base, expect } from '@playwright/test';

// Extend the base test with fixtures following Playwright naming conventions
export const test = base.extend<{
  page: void; // Type annotation for page fixture override
  authenticatedPage: void; // Type annotation for authenticated page fixture
  testJarFile: string; // Type annotation for testJarFile fixture
}>({
  // Custom page fixture with common setup
  page: async ({ page }, use) => {
    // Set up common page configurations
    await page.setViewportSize({ width: 1280, height: 720 });
    
    // Add common error handling
    page.on('pageerror', (error) => {
      console.error('Page error:', error);
    });
    
    page.on('requestfailed', (request) => {
      console.error('Request failed:', request.url(), request.failure());
    });
    
    await use(page);
  },
  
  // Authenticated page fixture (if needed)
  authenticatedPage: async ({ page }, use) => {
    // Implement authentication logic here
    // await page.goto('/login');
    // await page.fill('[data-testid="username"]', 'testuser');
    // await page.fill('[data-testid="password"]', 'testpass');
    // await page.click('[data-testid="login-button"]');
    // await page.waitForURL('/');
    
    await use(page);
  },
  
  // Test data fixtures
  testJarFile: async (_params, use) => {
    // Create or load a test JAR file for conversion testing
    const testFilePath = './e2e/fixtures/test-mod.jar';
    await use(testFilePath);
  },
});

export { expect };
