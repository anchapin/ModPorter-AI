## 2025-02-18 - Accessibility for Expandable Content
**Learning:** Adding `aria-expanded` and `aria-controls` to toggle buttons is crucial for screen readers to understand the relationship between the button and the content it reveals.
**Action:** When implementing show/hide functionality, always verify that the trigger element has these attributes.

## 2025-02-21 - Inline Confirmation Focus Management
**Learning:** When replacing an action button with an inline confirmation dialog, focus is lost unless manually managed. Adding `autoFocus` to the "Cancel" button is a simple, effective way to restore focus and prevent accidental confirmation.
**Action:** Always use `autoFocus` on the safe/cancel option in inline confirmation flows.

## 2025-03-20 - Icon-Only Button Accessibility
**Learning:** Icon-only buttons (like a `✕` for "remove") need explicit aria labels, and the visual symbol itself should be hidden from screen readers using `<span aria-hidden="true">`.
**Action:** Always wrap visual symbols in `aria-hidden` spans and provide a descriptive `aria-label` to the parent `<button>` element.
