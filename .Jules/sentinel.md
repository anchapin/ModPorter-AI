## 2024-05-18 - [Insecure Deserialization in Caching]
**Vulnerability:** Insecure deserialization using `pickle.load` in `ai-engine/utils/conversion_cache.py`.
**Learning:** The caching mechanism was using `pickle` which allows arbitrary code execution if a malicious payload is supplied. This was present in a performance optimization utility intended to cache conversion results.
**Prevention:** Use safer serialization formats like `json` instead of `pickle` when the cache is loaded from disk. Also, ensure file read/write modes are set appropriately for text files.## 2024-05-24 - Information Leakage in HTTP 500 Errors
**Vulnerability:** FastAPIs `HTTPException` exposed Python `str(e)` in the error response payload on 500 Server Errors, which leaked internal traces or potential file paths to the end user.
**Learning:** Returning exception strings directly to the client can result in accidental information disclosure. This repository specifically uses Pydantic/FastAPI, making it easy to leak via the `detail` parameter.
**Prevention:** Instead, log the actual exception context using `logger.error(f"{e}", exc_info=True)` and return a generic string (e.g. "An internal server error occurred") in the HTTP exception `detail` parameter.
