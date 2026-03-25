
## 2026-02-19 - [Frontend Download Optimization]
**Learning:** Using `fetch` + `blob` to download large files (500MB+) in browser JavaScript causes significant memory spikes and potential crashes.
**Action:** Always prefer direct link downloads (creating a hidden `<a>` tag) for large file downloads. Implemented `triggerDownload` utility in `api.ts` to handle this centrally with backend compatibility checks.

## 2026-02-19 - [O(N) Categorization Optimization]
**Learning:** Calculating category totals using `.filter(condition).length` inside `.map(categories)` on every render cycle causes O(M*N) time complexity and massive unnecessary intermediate array allocations, degrading rendering performance for large lists of features.
**Action:** Always calculate aggregated categorical counts using a single O(N) pass `.reduce()` or loop wrapped in a `useMemo` block to memoize the statistics.
