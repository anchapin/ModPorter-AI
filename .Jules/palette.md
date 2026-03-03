## 2025-02-18 - Accessibility for Expandable Content
**Learning:** Adding `aria-expanded` and `aria-controls` to toggle buttons is crucial for screen readers to understand the relationship between the button and the content it reveals.
**Action:** When implementing show/hide functionality, always verify that the trigger element has these attributes.
## 2026-03-03 - [Inline Confirmations]
**Learning:** Destructive actions with inline confirmations can cause accidental execution if keyboard focus isn't carefully managed.
**Action:** Always add `autoFocus` to the 'Cancel' or safe option button when rendering inline confirmation states to prevent accidental execution.
