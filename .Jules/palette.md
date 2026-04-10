## 2024-06-13 - [Accessibility] Screen readers pronouncing decorative emojis
**Learning:** Screen readers often misinterpret standalone emojis (e.g., ⬇️, 🗑️) inside buttons, reading them literally, which creates redundant or confusing announcements when a descriptive `aria-label` is already present.
**Action:** Always wrap non-informational emojis or text-based icons in `<span aria-hidden="true">` when the parent interactive element already has a sufficiently descriptive label.
## 2025-04-03 - Improved Notification Close Button Accessibility and Focus Styles
**Learning:** Decorative characters like "✕" inside buttons that already have `aria-label` attributes can cause redundant or confusing announcements for screen reader users. Additionally, using the `:focus` pseudo-class for buttons triggers focus outlines even on mouse clicks, which can add unnecessary visual noise.
**Action:** When implementing icon-only buttons with decorative characters, wrap the visual character in `<span aria-hidden="true">` to rely entirely on the `aria-label`. Use `:focus-visible` instead of `:focus` for interactive elements to ensure focus outlines appear only during keyboard navigation.
