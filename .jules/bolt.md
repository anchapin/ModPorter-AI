## 2026-02-19 - [Frontend Download Optimization]
**Learning:** Using `fetch` + `blob` to download large files (500MB+) in browser JavaScript causes significant memory spikes and potential crashes.
**Action:** Always prefer direct link downloads (creating a hidden `<a>` tag) for large file downloads. Implemented `triggerDownload` utility in `api.ts` to handle this centrally with backend compatibility checks.

## 2026-02-26 - [React Component Extraction for Frequent Updates]
**Learning:** Embedding static UI sections (like configuration options) within a component that updates frequently (e.g., upload progress every 100ms) causes unnecessary re-renders of the static parts.
**Action:** Extract static or stable UI sections into separate `React.memo` components to isolate them from high-frequency state updates in the parent component.
