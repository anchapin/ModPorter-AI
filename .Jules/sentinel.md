## 2024-05-18 - [Insecure Deserialization in Caching]
**Vulnerability:** Insecure deserialization using `pickle.load` in `ai-engine/utils/conversion_cache.py`.
**Learning:** The caching mechanism was using `pickle` which allows arbitrary code execution if a malicious payload is supplied. This was present in a performance optimization utility intended to cache conversion results.
**Prevention:** Use safer serialization formats like `json` instead of `pickle` when the cache is loaded from disk. Also, ensure file read/write modes are set appropriately for text files.## $(date +%Y-%m-%d) - Comparison API Information Exposure
**Vulnerability:** Information Exposure Through an Error Message (CWE-209). FastAPI HTTPExceptions in `backend/src/api/comparison.py` were directly exposing raw exception messages (`str(e)`) to the client, potentially leaking sensitive backend details and stack traces.
**Learning:** Exception handling in public APIs must sanitize error details. Direct passing of `str(e)` in `detail=...` reveals internal logic, which is an anti-pattern.
**Prevention:** Always log the actual error detail locally with `logger.error(..., exc_info=True)` and return a generic, safe error message (e.g., "An unexpected error occurred during comparison") to the client.
## $(date +%Y-%m-%d) - Pip Resolution Exhaustion via Deprecated Dependencies
**Vulnerability:** Dependency exhaustion (DoS) during build due to conflicting unbounded constraints on `opentelemetry` vs `opentelemetry-exporter-jaeger`.
**Learning:** `pip`'s dependency resolver will backtrack forever if a deprecated specific-version package (`opentelemetry-exporter-jaeger==1.21.0`) fundamentally conflicts with an unbounded peer (`opentelemetry-api>=1.24.0`).
**Prevention:** Remove obsolete/deprecated components completely rather than pinning them to ancient versions while newer core SDKs move forward, preventing build-time lockups.
