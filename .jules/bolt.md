
## 2026-02-19 - [Frontend Download Optimization]
**Learning:** Using `fetch` + `blob` to download large files (500MB+) in browser JavaScript causes significant memory spikes and potential crashes.
**Action:** Always prefer direct link downloads (creating a hidden `<a>` tag) for large file downloads. Implemented `triggerDownload` utility in `api.ts` to handle this centrally with backend compatibility checks.

## 2026-02-23 - [React Component Re-render Optimization]
**Learning:** High-frequency state updates (like upload progress bars updating at 10Hz) can cause expensive re-renders of the entire parent component tree.
**Action:** Extract static or less frequently changing UI sections into separate components wrapped with `React.memo` to isolate them from the rapid state updates.
