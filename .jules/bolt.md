## 2025-02-28 - Optimize Iterations Over Log Entries

**Learning:** When performing multiple categorization operations over an array in React, especially inside `useMemo`, looping individually or repeatedly executing string functions (like `toLowerCase()`) over the same item multiple times creates an architectural performance bottleneck as the size of the array scales.
**Action:** Consolidate aggregate passes on the same array structure into a single pass using `Array.prototype.reduce`. Do not blindly string `.filter().length` together or repeat variable modifications inside `.forEach` when they could be reduced iteratively in O(n) combined overhead.
