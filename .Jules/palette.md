## 2025-02-18 - Accessibility for Expandable Content
**Learning:** Adding `aria-expanded` and `aria-controls` to toggle buttons is crucial for screen readers to understand the relationship between the button and the content it reveals.
**Action:** When implementing show/hide functionality, always verify that the trigger element has these attributes.

## 2025-02-21 - Inline Confirmation Focus Management
**Learning:** When replacing an action button with an inline confirmation dialog, focus is lost unless manually managed. Adding `autoFocus` to the "Cancel" button is a simple, effective way to restore focus and prevent accidental confirmation.
**Action:** Always use `autoFocus` on the safe/cancel option in inline confirmation flows.

## 2025-03-21 - Hide decorative emojis from screen readers in Conversion Assets
**Learning:** Decorative emojis in buttons and UI elements (like 🔄 or ⏳) are read aloud by screen readers by default, which can cause confusion and clutter the audio output, detracting from the actual button label (e.g., "clockwise vertical arrows Refresh").
**Action:** Always wrap purely decorative emojis in `<span aria-hidden="true">` to ensure a cleaner, more accessible experience for screen reader users.
