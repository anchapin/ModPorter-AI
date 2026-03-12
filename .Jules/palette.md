## 2025-02-18 - Accessibility for Expandable Content
**Learning:** Adding `aria-expanded` and `aria-controls` to toggle buttons is crucial for screen readers to understand the relationship between the button and the content it reveals.
**Action:** When implementing show/hide functionality, always verify that the trigger element has these attributes.

## 2025-02-21 - Inline Confirmation Focus Management
**Learning:** When replacing an action button with an inline confirmation dialog, focus is lost unless manually managed. Adding `autoFocus` to the "Cancel" button is a simple, effective way to restore focus and prevent accidental confirmation.
**Action:** Always use `autoFocus` on the safe/cancel option in inline confirmation flows.

## 2025-02-23 - Focus Styles for Custom Checkboxes
**Learning:** For custom checkboxes built with an invisible `input[type='checkbox']` (opacity 0) and an adjacent visual `.checkmark`, default browser focus rings won't show. Keyboard users lose visual context unless focus-visible styles are explicitly applied to the adjacent visual element.
**Action:** When creating visually hidden inputs with custom proxy elements, always add `:focus-visible` styles to the proxy element using a sibling combinator (e.g., `input:focus-visible + .checkmark`).
