
## 2026-02-19 - [Frontend Download Optimization]
**Learning:** Using `fetch` + `blob` to download large files (500MB+) in browser JavaScript causes significant memory spikes and potential crashes.
**Action:** Always prefer direct link downloads (creating a hidden `<a>` tag) for large file downloads. Implemented `triggerDownload` utility in `api.ts` to handle this centrally with backend compatibility checks.

## 2026-03-21 - Optimize Recipe Validation Lookup
**Learning:** Frequent array scans (`.some()`) inside nested validation loops cause unnecessary CPU overhead, especially with large datasets like item libraries.
**Action:** Always pre-compute a `Set` for O(1) lookups before entering loops that validate items against a known library.
