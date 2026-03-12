
## 2026-02-19 - [Frontend Download Optimization]
**Learning:** Using `fetch` + `blob` to download large files (500MB+) in browser JavaScript causes significant memory spikes and potential crashes.
**Action:** Always prefer direct link downloads (creating a hidden `<a>` tag) for large file downloads. Implemented `triggerDownload` utility in `api.ts` to handle this centrally with backend compatibility checks.

## 2025-05-23 - Avoid Reading Files for Size Validation in Async Python
**Learning:** Iterating over `UploadFile.file` (a `SpooledTemporaryFile`) to check file size is a synchronous operation that blocks the event loop, causing severe performance degradation (e.g., 1s block for 50MB file).
**Action:** Always use `file.file.seek(0, 2)` and `file.file.tell()` to determine size in O(1) time without reading content. Ensure to reset the file pointer with `await file.seek(0)` afterwards.

## 2025-06-25 - Avoid `String.prototype.localeCompare` for Technical/ISO String Sorting
**Learning:** While `localeCompare` is semantically correct for alphabetizing localized strings, it carries significant overhead (invoking the Internationalization API). In V8, sorting 10,000 ISO date strings using `localeCompare` takes ~200ms, whereas standard string operators (`a > b ? 1 : a < b ? -1 : 0`) take ~10ms (a 20x improvement).
**Action:** Always use standard operators (`>`, `<`) when sorting ISO 8601 date strings or technical identifiers (like Minecraft resource IDs/names) where strict locale-awareness is not required.

## 2026-03-05 - [React Initial State Optimization]
**Learning:** Initializing state from `localStorage` inside a `useEffect` hook causes a double render and a visible layout shift because the component first renders with empty/loading state, and then immediately re-renders after the effect reads the data.
**Action:** Always use lazy initialization (`useState(() => { return readFromLocalStorage(); })`) for state derived from synchronous storage APIs to ensure the component renders with data on the very first paint, avoiding layout shifts and flashes of loading states.

## 2026-03-06 - [Array Aggregation Optimization]
**Learning:** Calculating multiple aggregate statistics from an array (e.g., status counts) using multiple `.filter(condition).length` calls results in O(k * N) time complexity (where k is the number of stats) and creates multiple intermediate arrays, causing unnecessary memory allocation and CPU cycles during frequent React renders.
**Action:** Always use a single O(N) pass, such as `Array.reduce()` or a standard `for` loop, to calculate multiple aggregates simultaneously, avoiding intermediate array creation and redundant iteration.
