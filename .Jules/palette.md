## 2025-02-18 - Accessibility for Expandable Content
**Learning:** Adding `aria-expanded` and `aria-controls` to toggle buttons is crucial for screen readers to understand the relationship between the button and the content it reveals.
**Action:** When implementing show/hide functionality, always verify that the trigger element has these attributes.

## 2025-02-21 - Inline Confirmation Focus Management
**Learning:** When replacing an action button with an inline confirmation dialog, focus is lost unless manually managed. Adding `autoFocus` to the "Cancel" button is a simple, effective way to restore focus and prevent accidental confirmation.
**Action:** Always use `autoFocus` on the safe/cancel option in inline confirmation flows.

## 2026-02-25 - Custom Checkbox Focus States
**Learning:** When using `opacity: 0` to hide native checkboxes for custom styling, the default focus ring is lost, making keyboard navigation impossible. We must explicitly target the custom visual element (e.g., `input:focus-visible + .checkmark`) to restore focus indicators.
**Action:** Always check keyboard navigation (Tab key) on custom form controls to ensure focus is visible.
