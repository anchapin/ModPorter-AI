## 2024-06-13 - [Accessibility] Screen readers pronouncing decorative emojis
**Learning:** Screen readers often misinterpret standalone emojis (e.g., ⬇️, 🗑️) inside buttons, reading them literally, which creates redundant or confusing announcements when a descriptive `aria-label` is already present.
**Action:** Always wrap non-informational emojis or text-based icons in `<span aria-hidden="true">` when the parent interactive element already has a sufficiently descriptive label.

## 2025-03-30 - [Accessibility] Screen readers pronouncing missing aria-labels on tooltips
**Learning:** Even if a Tooltip provides visual context, icon-only buttons (like `IconButton`) must still have an explicit `aria-label` for screen readers, as the tooltip title alone might not always be reliably announced by all screen readers across different browsers.
**Action:** Always provide `aria-label` directly on icon-only interactive elements, even when wrapping them in a UI tooltip.
