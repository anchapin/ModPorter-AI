## 2026-03-03 - [Inline Confirmations]
**Learning:** Destructive actions with inline confirmations can cause accidental execution if keyboard focus isn't carefully managed.
**Action:** Always add `autoFocus` to the 'Cancel' or safe option button when rendering inline confirmation states to prevent accidental execution.

## 2026-02-24 - Focus Management on DOM Removal
**Learning:** When an interactive element (like a "Remove" button) is removed from the DOM, focus is lost to the `body`, disorienting keyboard users.
**Action:** Implement focus restoration logic using `useEffect` and `useRef` to move focus to a logical fallback element (e.g., the "Upload" button) immediately after the element is unmounted.
