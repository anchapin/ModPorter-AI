## 2025-02-18 - Accessibility for Expandable Content
**Learning:** Adding `aria-expanded` and `aria-controls` to toggle buttons is crucial for screen readers to understand the relationship between the button and the content it reveals.
**Action:** When implementing show/hide functionality, always verify that the trigger element has these attributes.

## 2026-02-24 - Focus Management on DOM Removal
**Learning:** When an interactive element (like a "Remove" button) is removed from the DOM, focus is lost to the `body`, disorienting keyboard users.
**Action:** Implement focus restoration logic using `useEffect` and `useRef` to move focus to a logical fallback element (e.g., the "Upload" button) immediately after the element is unmounted.
