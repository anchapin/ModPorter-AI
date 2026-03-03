
## 2026-02-19 - [Frontend Download Optimization]
**Learning:** Using `fetch` + `blob` to download large files (500MB+) in browser JavaScript causes significant memory spikes and potential crashes.
**Action:** Always prefer direct link downloads (creating a hidden `<a>` tag) for large file downloads. Implemented `triggerDownload` utility in `api.ts` to handle this centrally with backend compatibility checks.

## 2025-05-23 - Avoid Reading Files for Size Validation in Async Python
**Learning:** Iterating over `UploadFile.file` (a `SpooledTemporaryFile`) to check file size is a synchronous operation that blocks the event loop, causing severe performance degradation (e.g., 1s block for 50MB file).
**Action:** Always use `file.file.seek(0, 2)` and `file.file.tell()` to determine size in O(1) time without reading content. Ensure to reset the file pointer with `await file.seek(0)` afterwards.
