## 2024-06-13 - [Accessibility] Screen readers pronouncing decorative emojis
**Learning:** Screen readers often misinterpret standalone emojis (e.g., ⬇️, 🗑️) inside buttons, reading them literally, which creates redundant or confusing announcements when a descriptive `aria-label` is already present.
**Action:** Always wrap non-informational emojis or text-based icons in `<span aria-hidden="true">` when the parent interactive element already has a sufficiently descriptive label.
## 2025-04-03 - Improved Notification Close Button Accessibility and Focus Styles
**Learning:** Decorative characters like "✕" inside buttons that already have `aria-label` attributes can cause redundant or confusing announcements for screen reader users. Additionally, using the `:focus` pseudo-class for buttons triggers focus outlines even on mouse clicks, which can add unnecessary visual noise.
**Action:** When implementing icon-only buttons with decorative characters, wrap the visual character in `<span aria-hidden="true">` to rely entirely on the `aria-label`. Use `:focus-visible` instead of `:focus` for interactive elements to ensure focus outlines appear only during keyboard navigation.

## 2024-04-12 - Ensure secondary actions have focus states
**Learning:** Secondary UI elements like cancel buttons in confirmation dialogues often get missed when styling keyboard focus states, breaking keyboard accessibility for secondary paths.
**Action:** Whenever styling focus states for primary action buttons, always verify that adjacent secondary or cancel buttons also have explicit `:focus-visible` styles applied.
## 2024-04-15 - [Accessibility] Improve screen reader experience on decorative icons
**Learning:** Screen readers often misinterpret standalone emojis (e.g., 📥) and non-informational icons inside interactive elements or purely decorative blocks, reading them literally which can be redundant or confusing. Furthermore, if a button only contains an icon/emoji without descriptive text, it must have an `aria-label`.
**Action:** When adding icons/emojis, explicitly wrap them in `<span aria-hidden="true">` when they are decorative or when the parent element has a descriptive label or `aria-label`. Ensure interactive elements without text labels have clear `aria-label` attributes.
