## 2024-06-13 - [Accessibility] Screen readers pronouncing decorative emojis
**Learning:** Screen readers often misinterpret standalone emojis (e.g., ⬇️, 🗑️) inside buttons, reading them literally, which creates redundant or confusing announcements when a descriptive `aria-label` is already present.
**Action:** Always wrap non-informational emojis or text-based icons in `<span aria-hidden="true">` when the parent interactive element already has a sufficiently descriptive label.
