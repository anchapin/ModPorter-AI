## 2024-05-18 - [Insecure Deserialization in Caching]
**Vulnerability:** Insecure deserialization using `pickle.load` in `ai-engine/utils/conversion_cache.py`.
**Learning:** The caching mechanism was using `pickle` which allows arbitrary code execution if a malicious payload is supplied. This was present in a performance optimization utility intended to cache conversion results.
**Prevention:** Use safer serialization formats like `json` instead of `pickle` when the cache is loaded from disk. Also, ensure file read/write modes are set appropriately for text files.
## 2024-03-15 - [Insecure Randomness for ID Generation]
**Vulnerability:** Using `Math.random().toString(36).substr(2, 9)` to generate identifiers in the frontend application.
**Learning:** This approach uses an insecure random number generator (`Math.random()`) which produces predictable values and could lead to identifier collisions. While not always directly exploitable for privilege escalation in all frontend contexts, predictable identifiers can cause unexpected state behavior, allow session correlation, or permit brute-forcing of component/session states.
**Prevention:** Always use standard, cryptographically secure ID generation like `crypto.randomUUID()` when creating unique identifiers (session IDs, toast IDs, DOM element IDs, etc.) to ensure randomness and global uniqueness.
