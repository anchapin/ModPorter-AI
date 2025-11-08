import { test, expect } from './fixtures';

test.describe('ModPorter AI - API Integration', () => {
  const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8080';

  test.beforeEach(async ({ page }) => {
    // Set up API request interception
    await page.route('**/api/**', (route) => {
      // Continue with the request but log it
      console.log('API Request:', route.request().method(), route.request().url());
      route.continue();
    });
  });

  test('should handle health check endpoint', async ({ page }) => {
    const response = await page.goto(`${API_BASE_URL}/api/health`);
    
    if (response) {
      const status = response.status();
      expect(status).toBe(200);
      
      const body = await response.text();
      const isHealthy = body.includes('healthy') || body.includes('ok');
      expect(isHealthy).toBe(true);
    }
  });

  test('should handle conversion API requests', async ({ page }) => {
    await page.goto('/');
    
    // Start conversion process to trigger API calls
    const startButton = page.locator('[data-testid="start-conversion"], button:has-text("Start")');
    if (await startButton.isVisible()) {
      await startButton.click();
      
      // Monitor API requests during conversion
      const apiRequests = [];
      
      page.on('request', (request) => {
        if (request.url().includes('/api/')) {
          apiRequests.push({
            method: request.method(),
            url: request.url(),
            postData: request.postData()
          });
        }
      });
      
      // Try demo file
      const demoButton = page.locator('[data-testid="demo-file"], button:has-text("Demo")');
      if (await demoButton.isVisible()) {
        await demoButton.click();
        
        const convertButton = page.locator('[data-testid="start-conversion-btn"], button:has-text("Convert")');
        if (await convertButton.isVisible()) {
          await convertButton.click();
          
          // Wait for some API calls to be made
          await page.waitForTimeout(3000);
          
          // Verify API calls were made
          const conversionRequests = apiRequests.filter(req => 
            req.url.includes('/api/convert') || 
            req.url.includes('/api/conversion') ||
            req.url.includes('/api/upload')
          );
          
          expect(conversionRequests.length).toBeGreaterThan(0);
          
          // Check request methods and structure
          conversionRequests.forEach(req => {
            expect(['POST', 'PUT', 'GET']).toContain(req.method);
          });
        }
      }
    }
  });

  test('should handle API error responses gracefully', async ({ page }) => {
    // Mock API error response
    await page.route('**/api/convert', (route) => {
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Internal Server Error' })
      });
    });
    
    await page.goto('/');
    await page.click('[data-testid="start-conversion"], button:has-text("Start")');
    
    // Try to trigger conversion
    const demoButton = page.locator('[data-testid="demo-file"], button:has-text("Demo")');
    if (await demoButton.isVisible()) {
      await demoButton.click();
      
      const convertButton = page.locator('[data-testid="start-conversion-btn"], button:has-text("Convert")');
      if (await convertButton.isVisible()) {
        await convertButton.click();
        
        // Should show error message
        const errorMessage = page.locator('[data-testid="error"], .error-message, .api-error');
        await expect(errorMessage).toBeVisible({ timeout: 10000 });
      }
    }
  });

  test('should handle file upload API', async ({ page }) => {
    await page.goto('/');
    await page.click('[data-testid="start-conversion"], button:has-text("Start")');
    
    // Monitor upload requests
    let uploadRequest = null;
    
    page.on('request', (request) => {
      if (request.url().includes('/api/upload') || request.url().includes('/api/file')) {
        uploadRequest = request;
      }
    });
    
    // Try to upload a file
    const fileInput = page.locator('input[type="file"]');
    if (await fileInput.isVisible()) {
      // Create a test file buffer
      const testFile = Buffer.from('test jar content');
      await fileInput.setInputFiles({
        name: 'test-mod.jar',
        mimeType: 'application/java-archive',
        buffer: testFile
      });
      
      // Wait for upload request
      await page.waitForTimeout(2000);
      
      if (uploadRequest) {
        expect(uploadRequest.method()).toBe('POST');
        expect(uploadRequest.postData()).toBeTruthy();
      }
    }
  });

  test('should handle behavior editor API calls', async ({ page }) => {
    // Navigate to behavior editor
    const behaviorLink = page.locator('[data-testid="behavior-editor"], a:has-text("Behavior")');
    if (await behaviorLink.isVisible()) {
      await behaviorLink.click();
      
      // Monitor behavior API requests
      const behaviorRequests = [];
      
      page.on('request', (request) => {
        if (request.url().includes('/api/behavior') || 
            request.url().includes('/api/templates') ||
            request.url().includes('/api/logic')) {
          behaviorRequests.push({
            method: request.method(),
            url: request.url()
          });
        }
      });
      
      // Wait for page to load
      await page.waitForTimeout(2000);
      
      // Check for behavior API calls
      if (behaviorRequests.length > 0) {
        behaviorRequests.forEach(req => {
          expect(['GET', 'POST', 'PUT', 'DELETE']).toContain(req.method());
        });
      }
    }
  });

  test('should handle real-time updates via websockets', async ({ page }) => {
    await page.goto('/');
    await page.click('[data-testid="start-conversion"], button:has-text("Start")');
    
    // Monitor WebSocket connections
    const wsConnections = [];
    
    page.on('websocket', (ws) => {
      wsConnections.push(ws.url());
      console.log('WebSocket connected:', ws.url());
    });
    
    // Start a conversion to potentially trigger WebSocket connections
    const demoButton = page.locator('[data-testid="demo-file"], button:has-text("Demo")');
    if (await demoButton.isVisible()) {
      await demoButton.click();
      
      const convertButton = page.locator('[data-testid="start-conversion-btn"], button:has-text("Convert")');
      if (await convertButton.isVisible()) {
        await convertButton.click();
        
        // Wait for potential WebSocket connection
        await page.waitForTimeout(5000);
        
        // WebSocket connections are optional, so we just log if any are found
        if (wsConnections.length > 0) {
          console.log('WebSocket connections found:', wsConnections);
        }
      }
    }
  });

  test('should handle authentication API if present', async ({ page }) => {
    // Look for login/signup functionality
    const loginButton = page.locator('[data-testid="login"], button:has-text("Login"), a:has-text("Login")');
    const signupButton = page.locator('[data-testid="signup"], button:has-text("Sign Up"), a:has-text("Sign")');
    
    if (await loginButton.isVisible() || await signupButton.isVisible()) {
      const authButton = await loginButton.isVisible() ? loginButton : signupButton;
      await authButton.click();
      
      // Monitor auth API requests
      const authRequests = [];
      
      page.on('request', (request) => {
        if (request.url().includes('/api/auth') || 
            request.url().includes('/api/login') ||
            request.url().includes('/api/signup')) {
          authRequests.push({
            method: request.method(),
            url: request.url()
          });
        }
      });
      
      // Wait for auth page to load
      await page.waitForTimeout(2000);
      
      // Check if auth form is present
      const authForm = page.locator('form');
      if (await authForm.isVisible()) {
        // Try to fill in test credentials (this might fail, but we're testing the API flow)
        const emailInput = page.locator('input[type="email"], input[name="email"]');
        const passwordInput = page.locator('input[type="password"], input[name="password"]');
        
        if (await emailInput.isVisible()) {
          await emailInput.fill('test@example.com');
        }
        
        if (await passwordInput.isVisible()) {
          await passwordInput.fill('testpassword');
        }
        
        const submitButton = page.locator('button[type="submit"], button:has-text("Login"), button:has-text("Sign Up")');
        if (await submitButton.isVisible()) {
          await submitButton.click();
          
          // Wait for auth request
          await page.waitForTimeout(3000);
          
          if (authRequests.length > 0) {
            authRequests.forEach(req => {
              expect(['POST']).toContain(req.method());
            });
          }
        }
      }
    }
  });
});
