
## 2024-05-18 - Missing ARIA label on emoji icon-only links
**Learning:** Icon-only elements like the Settings emoji (⚙️) in navigation bars are completely inaccessible to screen readers without an `aria-label`, and confusing without a hover `title`. Emojis are often announced by screen readers unpredictably or skipped.
**Action:** Always wrap the emoji/icon in `<span aria-hidden="true">` and provide a clear `aria-label` and `title` on the parent interactive element.
