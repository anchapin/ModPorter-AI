
## 2026-02-19 - [Frontend Download Optimization]
**Learning:** Using `fetch` + `blob` to download large files (500MB+) in browser JavaScript causes significant memory spikes and potential crashes.
**Action:** Always prefer direct link downloads (creating a hidden `<a>` tag) for large file downloads. Implemented `triggerDownload` utility in `api.ts` to handle this centrally with backend compatibility checks.

## 2026-03-18 - O(N) aggregation over O(N*M) filters
**Learning:** In React components with dynamically generated filter lists, using `.filter().length` inside a `.map()` results in O(N*M) time complexity, leading to sluggish renders with larger datasets.
**Action:** Use `.reduce()` or a single loop inside `useMemo` to pre-calculate category counts in an O(N) pass instead.

## 2026-03-19 - [Avoid reduce and some for hot loops in React]
**Learning:** Using chained array methods like `.reduce` and multiple `.some` calls inside `useMemo` hooks can cause unnecessary allocations and performance degradation due to closures and object creations, especially when checking nested or multiple arrays.
**Action:** Use simple `for` loops inside `useMemo` to combine multiple conditions, breaking early and avoiding callback allocations for faster single-pass validation or aggregation.

## 2026-03-19 - [Avoid O(N*M) lookups inside list renders]
**Learning:** Passing a callback that performs `.filter` on a full array down to child components that iterate over lists (like `FormBuilder` iterating over `fields` and calling `getFieldErrors(field.name)`) results in O(N*M) time complexity.
**Action:** Replace callback filters with a single pass O(M) `.reduce` or loop inside a `useMemo` to construct a grouped hash map by ID, turning child component lookups into O(1).
## 2024-05-14 - Optimize array filtering with Set and Map
**Learning:** Found an `O(N*M)` performance bottleneck in `VisualEditor.tsx` where array filtering inside a callback (`fields.filter((field) => category.fields.includes(field.name))`) was occurring on every render.
**Action:** Replaced it with a pre-computed `Map` using `useMemo` and an inner `Set` to provide `O(1)` lookups, significantly improving rendering performance for forms with many fields and categories.
