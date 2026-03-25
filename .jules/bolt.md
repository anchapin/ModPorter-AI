
## 2026-02-19 - [Frontend Download Optimization]
**Learning:** Using `fetch` + `blob` to download large files (500MB+) in browser JavaScript causes significant memory spikes and potential crashes.
**Action:** Always prefer direct link downloads (creating a hidden `<a>` tag) for large file downloads. Implemented `triggerDownload` utility in `api.ts` to handle this centrally with backend compatibility checks.

## 2026-03-20 - Optimize FormBuilder summary calculation
**Learning:** Calculating metrics like filled fields, required fields, and errors using multiple inline `.filter(...).length` statements creates unnecessary intermediate array allocations (O(3N)) on every render.
**Action:** When calculating aggregate statistics or category counts for rendering, use a single O(N) pass with a loop or `.reduce()` inside `useMemo` instead of multiple inline `.filter().length` calls. Ensure any intermediate arrays passed as dependencies to `useMemo` (like a filtered list of fields) are also memoized, otherwise their changing references will break the cache on every render.
