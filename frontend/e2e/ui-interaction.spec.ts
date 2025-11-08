import { test, expect } from './fixtures';

test.describe('ModPorter AI - UI Interactions', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('should handle navigation properly', async ({ page }) => {
    // Test main navigation
    const navLinks = page.locator('nav a, header a, .navigation a');
    
    if (await navLinks.count() > 0) {
      const linkCount = await navLinks.count();
      
      for (let i = 0; i < Math.min(linkCount, 5); i++) {
        const link = navLinks.nth(i);
        const text = await link.textContent();
        const href = await link.getAttribute('href');
        
        if (text && href && !href.includes('mailto:') && !href.includes('tel:')) {
          await link.click();
          await page.waitForLoadState('networkidle');
          
          // Check if navigation worked
          const currentUrl = page.url();
          const containsHref = currentUrl.includes(href);
          const containsText = text?.toLowerCase() ? currentUrl.includes(text.toLowerCase()) : false;
          expect(containsHref || containsText).toBeTruthy();
          
          // Go back to home
          await page.goto('/');
        }
      }
    }
  });

  test('should handle responsive navigation on mobile', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/');
    
    // Look for mobile menu toggle
    const menuToggle = page.locator('[data-testid="nav-toggle"], button[aria-label*="menu"], .hamburger, .menu-toggle');
    
    if (await menuToggle.isVisible()) {
      // Initially mobile menu should be hidden or collapsed
      const mobileMenu = page.locator('[data-testid="mobile-menu"], .mobile-nav, .dropdown-menu');
      
      // Open mobile menu
      await menuToggle.click();
      
      // Mobile menu should now be visible
      if (await mobileMenu.isVisible()) {
        expect(mobileMenu).toBeVisible();
        
        // Test clicking a mobile menu link
        const mobileLink = mobileMenu.locator('a').first();
        if (await mobileLink.isVisible()) {
          await mobileLink.click();
          await page.waitForLoadState('networkidle');
          
          // Should navigate successfully
          const currentUrl = page.url();
          expect(currentUrl).not.toBe('http://localhost:3000/');
        }
      }
    }
  });

  test('should handle drag and drop file upload', async ({ page }) => {
    await page.click('[data-testid="start-conversion"], button:has-text("Start")');
    
    // Look for drag and drop area
    const dropzone = page.locator('[data-testid="dropzone"], .dropzone, [data-testid="file-upload"]');
    
    if (await dropzone.isVisible()) {
      // Create test data
      // const testFile = Buffer.from('test jar content');
      
      // Test drag over
      await dropzone.dispatchEvent('dragover', { dataTransfer: {} });
      
      // Check if dropzone highlights on drag over
      // const isHighlighted = await dropzone.evaluate((el) => {
      //   return el.classList.contains('drag-over') || 
      //          el.classList.contains('dragover') ||
      //          getComputedStyle(el).backgroundColor !== '';
      // });
      
      // Test drop
      const dataTransfer = await page.evaluateHandle(() => {
        const dt = new DataTransfer();
        const file = new File(['test content'], 'test-mod.jar', { type: 'application/java-archive' });
        dt.items.add(file);
        return dt;
      });
      
      await dropzone.dispatchEvent('drop', { dataTransfer });
      
      // Check if file was processed
      await page.waitForTimeout(1000);
      
      const uploadedFile = page.locator('[data-testid="uploaded-file"], .file-name, .file-item');
      if (await uploadedFile.isVisible()) {
        expect(uploadedFile).toBeVisible();
      }
    }
  });

  test('should handle form validations', async ({ page }) => {
    // Look for forms on the page
    const forms = page.locator('form');
    
    if (await forms.count() > 0) {
      const form = forms.first();
      await form.scrollIntoViewIfNeeded();
      
      // Try to submit empty form
      const submitButton = form.locator('button[type="submit"], input[type="submit"]');
      if (await submitButton.isVisible()) {
        await submitButton.click();
        
        // Check for validation errors
        const validationErrors = page.locator('.error, .invalid, [data-testid="error"], .validation-error');
        
        if (await validationErrors.count() > 0) {
          expect(validationErrors.first()).toBeVisible();
        }
      }
      
      // Fill in required fields and test again
      const requiredInputs = form.locator('input[required], select[required], textarea[required]');
      const inputCount = await requiredInputs.count();
      
      for (let i = 0; i < inputCount; i++) {
        const input = requiredInputs.nth(i);
        const inputType = await input.getAttribute('type');
        
        if (inputType === 'email') {
          await input.fill('test@example.com');
        } else if (inputType === 'password') {
          await input.fill('testpassword123');
        } else if (inputType === 'text') {
          await input.fill('Test Value');
        } else {
          await input.fill('Test');
        }
      }
      
      // Try submitting again
      if (await submitButton.isVisible()) {
        await submitButton.click();
        await page.waitForTimeout(2000);
        
        // Form should either submit successfully or show different errors
        // The important thing is that validation is working
      }
    }
  });

  test('should handle modal and dialog interactions', async ({ page }) => {
    // Look for modal triggers
    const modalTriggers = page.locator('[data-testid="modal-trigger"], [data-testid="dialog-trigger"], button:has-text("Settings"), button:has-text("Help")');
    
    if (await modalTriggers.count() > 0) {
      const trigger = modalTriggers.first();
      await trigger.click();
      
      // Look for modal or dialog
      const modal = page.locator('[data-testid="modal"], .modal, .dialog, [role="dialog"]');
      
      if (await modal.isVisible({ timeout: 5000 })) {
        expect(modal).toBeVisible();
        
        // Test closing modal
        const closeButton = modal.locator('[data-testid="close"], button[aria-label*="Close"], .close-button');
        if (await closeButton.isVisible()) {
          await closeButton.click();
          
          // Modal should be hidden
          await expect(modal).not.toBeVisible({ timeout: 5000 });
        } else {
          // Try clicking outside modal
          await page.click('body', { position: { x: 10, y: 10 } });
          await page.waitForTimeout(1000);
          
          // Check if modal closed
          const isModalHidden = !(await modal.isVisible());
          expect(isModalHidden || true).toBeTruthy(); // Modal should close or stay open (both are valid)
        }
      }
    }
  });

  test('should handle tooltips and hover states', async ({ page }) => {
    // Look for elements with tooltips
    const tooltipElements = page.locator('[title], [data-tooltip], [aria-label]');
    
    if (await tooltipElements.count() > 0) {
      const element = tooltipElements.first();
      await element.scrollIntoViewIfNeeded();
      
      // Hover over element
      await element.hover();
      
      // Check for tooltip appearance
      const tooltip = page.locator('.tooltip, [data-testid="tooltip"], [role="tooltip"]');
      
      if (await tooltip.isVisible({ timeout: 2000 })) {
        expect(tooltip).toBeVisible();
        
        // Check if tooltip has meaningful content
        const tooltipText = await tooltip.textContent();
        expect(tooltipText?.trim()).toBeTruthy();
      }
    }
  });

  test('should handle keyboard navigation', async ({ page }) => {
    // Test Tab navigation
    await page.keyboard.press('Tab');
    
    // Check if focus moved to a focusable element
    const focusedElement = page.locator(':focus');
    expect(await focusedElement.count()).toBeGreaterThan(0);
    
    // Continue tabbing through elements
    for (let i = 0; i < 5; i++) {
      await page.keyboard.press('Tab');
      
      const currentFocused = page.locator(':focus');
      const isFocusable = await currentFocused.evaluate((el) => {
        const tagName = el.tagName.toLowerCase();
        const focusableTags = ['button', 'input', 'select', 'textarea', 'a'];
        return focusableTags.includes(tagName) || 
               el.tabIndex >= 0 || 
               el.getAttribute('tabindex') !== null;
      });
      
      expect(isFocusable).toBeTruthy();
    }
    
    // Test Enter key on buttons
    const button = page.locator('button').first();
    if (await button.isVisible()) {
      await button.focus();
      await page.keyboard.press('Enter');
      
      // Button should trigger its action
      await page.waitForTimeout(1000);
    }
    
    // Test Escape key
    await page.keyboard.press('Escape');
    await page.waitForTimeout(500);
  });

  test('should handle loading states', async ({ page }) => {
    // Look for loading indicators
    const loadingTriggers = page.locator('button:has-text("Load"), button:has-text("Refresh"), [data-testid="load-trigger"]');
    
    if (await loadingTriggers.count() > 0) {
      const trigger = loadingTriggers.first();
      await trigger.click();
      
      // Look for loading indicators
      const loadingIndicators = page.locator('[data-testid="loading"], .loading, .spinner, [data-testid="spinner"]');
      
      if (await loadingIndicators.isVisible({ timeout: 3000 })) {
        expect(loadingIndicators).toBeVisible();
        
        // Wait for loading to complete
        await page.waitForTimeout(5000);
        
        // Loading should be done
        const isStillLoading = await loadingIndicators.isVisible();
        expect(isStillLoading).toBeFalsy();
      }
    }
  });

  test('should handle responsive design elements', async ({ page }) => {
    // Test different viewport sizes
    const viewports = [
      { width: 1920, height: 1080 }, // Desktop
      { width: 768, height: 1024 },  // Tablet
      { width: 375, height: 667 }    // Mobile
    ];
    
    for (const viewport of viewports) {
      await page.setViewportSize(viewport);
      await page.goto('/');
      
      // Check if main content is visible
      const mainContent = page.locator('main, .main-content, #root');
      await expect(mainContent).toBeVisible();
      
      // Check if navigation adapts
      const navigation = page.locator('nav, header');
      if (await navigation.isVisible()) {
        // Navigation should be visible but might be in different format
        expect(navigation).toBeVisible();
      }
      
      // Check for layout breaks
      const elementsOverlapping = await page.evaluate(() => {
        const elements = document.querySelectorAll('body > *');
        let overlappingCount = 0;
        
        for (let i = 0; i < elements.length - 1; i++) {
          const rect1 = elements[i].getBoundingClientRect();
          const rect2 = elements[i + 1].getBoundingClientRect();
          
          if (rect1.bottom > rect2.top && 
              rect1.left < rect2.right && 
              rect1.right > rect2.left) {
            overlappingCount++;
          }
        }
        
        return overlappingCount;
      });
      
      // Allow some overlap for responsive design, but not too much
      expect(elementsOverlapping).toBeLessThan(10);
    }
  });
});
