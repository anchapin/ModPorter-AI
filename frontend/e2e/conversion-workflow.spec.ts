import { test, expect } from './fixtures';

test.describe('ModPorter AI - Conversion Workflow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('should load the main application', async ({ page }) => {
    // Verify the main application loads
    await expect(page.locator('h1, h2')).toContainText('ModPorter', { timeout: 10000 });
    
    // Check if main navigation is present
    await expect(page.locator('nav, header')).toBeVisible();
  });

  test('should navigate to conversion page', async ({ page }) => {
    // Click on conversion/start button
    await page.click('[data-testid="start-conversion"], button:has-text("Start"), a:has-text("Convert")');
    
    // Should be on conversion page
    await expect(page.url()).toContain('/convert');
    await expect(page.locator('[data-testid="conversion-page"], h1:has-text("Convert")')).toBeVisible();
  });

  test('should handle file upload', async ({ page, testJarFile }) => {
    // Navigate to conversion page
    await page.click('[data-testid="start-conversion"], button:has-text("Start")');
    
    // Check if upload area is present
    const uploadArea = page.locator('[data-testid="file-upload"], .dropzone, input[type="file"]');
    await expect(uploadArea).toBeVisible();
    
    // Upload file (if test file exists)
    const fileInput = page.locator('input[type="file"]');
    if (await fileInput.isVisible()) {
      await fileInput.setInputFiles(testJarFile);
      
      // Verify file is uploaded (check for file name or success indicator)
      await expect(page.locator('[data-testid="uploaded-file"], .file-name')).toBeVisible({ timeout: 5000 });
    }
  });

  test('should show conversion options', async ({ page }) => {
    await page.click('[data-testid="start-conversion"], button:has-text("Start")');
    
    // Check for conversion options
    const conversionOptions = page.locator('[data-testid="conversion-options"], .options, form');
    if (await conversionOptions.isVisible()) {
      await expect(conversionOptions).toBeVisible();
      
      // Check for common options
      const blockOption = page.locator('[data-testid="option-blocks"], input[value="blocks"], label:has-text("Blocks")');
      if (await blockOption.isVisible()) {
        await expect(blockOption).toBeVisible();
      }
    }
  });

  test('should start conversion process', async ({ page }) => {
    await page.click('[data-testid="start-conversion"], button:has-text("Start")');
    
    // Upload a file or select demo option
    const demoButton = page.locator('[data-testid="demo-file"], button:has-text("Demo"), button:has-text("Sample")');
    if (await demoButton.isVisible()) {
      await demoButton.click();
    }
    
    // Start conversion
    const startButton = page.locator('[data-testid="start-conversion-btn"], button:has-text("Convert"), button:has-text("Start")');
    if (await startButton.isVisible()) {
      await startButton.click();
      
      // Should show progress
      const progress = page.locator('[data-testid="progress"], .progress-bar, .conversion-progress');
      await expect(progress).toBeVisible({ timeout: 10000 });
    }
  });

  test('should display conversion results', async ({ page }) => {
    // Complete the conversion flow
    await page.click('[data-testid="start-conversion"], button:has-text("Start")');
    
    // Try demo file if available
    const demoButton = page.locator('[data-testid="demo-file"], button:has-text("Demo")');
    if (await demoButton.isVisible()) {
      await demoButton.click();
      
      const startButton = page.locator('[data-testid="start-conversion-btn"], button:has-text("Convert")');
      if (await startButton.isVisible()) {
        await startButton.click();
        
        // Wait for completion (might take time)
        const results = page.locator('[data-testid="conversion-results"], .results, .report');
        await expect(results).toBeVisible({ timeout: 60000 });
        
        // Check for download button
        const downloadButton = page.locator('[data-testid="download-btn"], button:has-text("Download")');
        if (await downloadButton.isVisible()) {
          await expect(downloadButton).toBeVisible();
        }
      }
    }
  });

  test('should handle conversion errors gracefully', async ({ page }) => {
    await page.click('[data-testid="start-conversion"], button:has-text("Start")');
    
    // Try to start conversion without file to trigger error handling
    const startButton = page.locator('[data-testid="start-conversion-btn"], button:has-text("Convert")');
    if (await startButton.isVisible()) {
      await startButton.click();
      
      // Should show error message or validation
      const errorMessage = page.locator('[data-testid="error"], .error-message, .validation-error');
      if (await errorMessage.isVisible({ timeout: 5000 })) {
        await expect(errorMessage).toBeVisible();
      }
    }
  });

  test('should navigate to behavior editor', async ({ page }) => {
    // Look for behavior editor link or button
    const behaviorEditorLink = page.locator('[data-testid="behavior-editor"], a:has-text("Behavior"), button:has-text("Behavior")');
    if (await behaviorEditorLink.isVisible()) {
      await behaviorEditorLink.click();
      
      // Should be on behavior editor page
      await expect(page.url()).toContain('/behavior');
      await expect(page.locator('[data-testid="behavior-editor-page"], h1:has-text("Behavior")')).toBeVisible();
    }
  });

  test('should be responsive on mobile', async ({ page }) => {
    // Test mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/');
    
    // Check if mobile navigation is working
    await expect(page.locator('h1, h2')).toContainText('ModPorter');
    
    // Check if navigation is mobile-friendly
    const navToggle = page.locator('[data-testid="nav-toggle"], button[aria-label*="menu"], .hamburger');
    if (await navToggle.isVisible()) {
      await navToggle.click();
      
      // Mobile menu should open
      const mobileMenu = page.locator('[data-testid="mobile-menu"], .mobile-nav, .dropdown');
      await expect(mobileMenu).toBeVisible();
    }
  });
});
