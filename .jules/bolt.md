
## 2026-02-19 - [Frontend Download Optimization]
**Learning:** Using `fetch` + `blob` to download large files (500MB+) in browser JavaScript causes significant memory spikes and potential crashes.
**Action:** Always prefer direct link downloads (creating a hidden `<a>` tag) for large file downloads. Implemented `triggerDownload` utility in `api.ts` to handle this centrally with backend compatibility checks.

## 2026-03-18 - O(N) aggregation over O(N*M) filters
**Learning:** In React components with dynamically generated filter lists, using `.filter().length` inside a `.map()` results in O(N*M) time complexity, leading to sluggish renders with larger datasets.
**Action:** Use `.reduce()` or a single loop inside `useMemo` to pre-calculate category counts in an O(N) pass instead.
