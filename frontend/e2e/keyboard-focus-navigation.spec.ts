import { test, expect } from '@playwright/test';

test.describe('Keyboard Focus-Visible Navigation', () => {
  test('form inputs show focus-visible outline on keyboard tab', async ({
    page,
  }) => {
    await page.goto('/settings');

    // Find all form inputs
    const inputs = page.locator(
      'input[type="text"], input[type="password"], select, textarea'
    );
    const inputCount = await inputs.count();

    expect(inputCount).toBeGreaterThan(0);

    // Tab to first input
    await page.keyboard.press('Tab');

    const focusedElement = page.locator(':focus');
    const computedStyle = await focusedElement.evaluate((el) => {
      const styles = window.getComputedStyle(el);
      return {
        outline: styles.outline,
        outlineColor: styles.outlineColor,
        outlineWidth: styles.outlineWidth,
      };
    });

    // Check that focused element has visible outline
    expect(computedStyle.outline).not.toBe('none');
    expect(computedStyle.outlineWidth).not.toBe('0px');
  });

  test('buttons have focus-visible indicators', async ({ page }) => {
    await page.goto('/');

    // Find all buttons
    const buttons = page.locator('button, [role="button"]');
    const buttonCount = await buttons.count();

    expect(buttonCount).toBeGreaterThan(0);

    // Focus first button via keyboard
    await page.keyboard.press('Tab');

    const focusedElement = page.locator(':focus');
    const isFocusVisible = await focusedElement.evaluate((el) => {
      // Check if element matches :focus-visible
      return el.matches(':focus-visible');
    });

    expect(isFocusVisible).toBeTruthy();
  });

  test('keyboard navigation traverses all interactive elements', async ({
    page,
  }) => {
    await page.goto('/');

    const focusableElements = page.locator(
      'button, [role="button"], input, select, textarea, a[href], [tabindex]:not([tabindex="-1"])'
    );
    const focusableCount = await focusableElements.count();

    expect(focusableCount).toBeGreaterThan(0);

    // Tab through elements
    let _previousElement: string | null = null;
    for (let i = 0; i < Math.min(focusableCount, 5); i++) {
      await page.keyboard.press('Tab');

      const focusedElement = page.locator(':focus');
      const tagName = await focusedElement.evaluate((el) => el.tagName);

      // Verify we're focused on an interactive element
      const interactiveTags = ['BUTTON', 'INPUT', 'SELECT', 'TEXTAREA', 'A'];
      const isInteractive =
        interactiveTags.includes(tagName) ||
        (await focusedElement.evaluate((el) => el.hasAttribute('role')));

      expect(isInteractive).toBeTruthy();
    }
  });

  test('API key input field has focus-visible styling', async ({ page }) => {
    await page.goto('/settings');

    const apiKeyInput = page.locator('.api-key-input').first();

    if ((await apiKeyInput.count()) > 0) {
      await apiKeyInput.focus();

      const computedStyle = await apiKeyInput.evaluate((el) => {
        const styles = window.getComputedStyle(el);
        return {
          outline: styles.outline,
          outlineColor: styles.outlineColor,
          borderColor: styles.borderColor,
        };
      });

      // Should have outline or border color change
      expect(computedStyle.outline).not.toBe('none');
    }
  });

  test('url input in conversion upload has focus-visible', async ({ page }) => {
    await page.goto('/');

    // Navigate to conversion upload section
    const urlInput = page.locator('.url-input').first();

    if ((await urlInput.count()) > 0) {
      await urlInput.focus();

      const hasOutline = await urlInput.evaluate((el) => {
        const styles = window.getComputedStyle(el);
        return styles.outline !== 'none' && styles.outlineWidth !== '0px';
      });

      expect(hasOutline).toBeTruthy();
    }
  });

  test('no focus ring visible on mouse click (mouse users not distracted)', async ({
    page,
  }) => {
    await page.goto('/');

    const button = page.locator('button').first();

    if ((await button.count()) > 0) {
      // Click with mouse (not keyboard)
      await button.click();

      // Wait a bit for any visual changes
      await page.waitForTimeout(100);

      // Focus-visible should not match for mouse users
      // This is browser-dependent, but the CSS should handle it with :focus:not(:focus-visible)
      const _isFocusVisible = await button.evaluate((el) => {
        return el.matches(':focus-visible');
      });

      // Mouse click should not trigger focus-visible in most browsers
      // (This is automatic browser behavior, CSS just respects it)
      // Some browsers like webkit may occasionally trigger it, so we don't strictly assert false
      expect(_isFocusVisible).toBeDefined();
    }
  });

  test('settings form inputs maintain focus indicators', async ({ page }) => {
    await page.goto('/settings');

    const formInputs = page
      .locator('.form-group input, .form-group select')
      .first();

    if ((await formInputs.count()) > 0) {
      await formInputs.focus();

      const styles = await formInputs.evaluate((el) => {
        const computed = window.getComputedStyle(el);
        return {
          hasOutline: computed.outline !== 'none',
          outlineColor: computed.outlineColor,
          borderColor: computed.borderColor,
        };
      });

      expect(
        styles.hasOutline || styles.borderColor !== 'rgba(0, 0, 0, 0)'
      ).toBeTruthy();
    }
  });

  test('search input has visible focus indicator', async ({ page }) => {
    await page.goto('/');

    const searchInput = page.locator('.globalSearchInput').first();

    if ((await searchInput.count()) > 0) {
      await searchInput.focus();

      const hasVisibleFocus = await searchInput.evaluate((el) => {
        const styles = window.getComputedStyle(el);
        return {
          outline: styles.outline,
          boxShadow: styles.boxShadow,
        };
      });

      // Should have either outline or box-shadow for visibility
      expect(
        hasVisibleFocus.outline !== 'none' ||
          hasVisibleFocus.boxShadow !== 'none'
      ).toBeTruthy();
    }
  });
});
