## 2026-02-16 - SSRF Prevention Pattern
**Vulnerability:** Server-Side Request Forgery (SSRF) in file download functionality.
**Learning:** `httpx` (and `requests`) follow redirects by default, potentially bypassing initial URL validation if a redirect leads to a private IP. Blocking DNS resolution via `socket.getaddrinfo` is effective but requires handling IPv6 scope IDs and fail-secure logic.
**Prevention:**
1. Validate URL scheme (http/https).
2. Resolve hostname to IP(s) and check against private/loopback ranges.
3. Disable automatic redirect following (`follow_redirects=False`).
4. Manually handle redirects, re-validating the URL at each hop.
5. Sanitize URLs before logging to avoid leaking sensitive tokens.

## 2026-02-16 - Zip Slip Prevention in Addon Export
**Vulnerability:** Zip Slip vulnerability in `addon_exporter.py` allowing directory traversal via malicious filenames in exported zip archives.
**Learning:** Using `os.path.join` with unsanitized user input inside `zipfile` operations can lead to files being written outside the intended directory upon extraction. Even if the path doesn't escape the zip root, `../` segments can be dangerous.
**Prevention:**
1. Sanitize all filenames used in `zipfile` operations using `os.path.basename` to strip directory components.
2. Restrict filenames to a safe allowlist (alphanumeric, `._-`).
3. Apply sanitization consistently across all file types (textures, sounds, models, etc.).

## 2026-02-16 - Rate Limiter Race Condition
**Vulnerability:** Race condition in `RateLimitMiddleware` where a shared `RateLimiter` instance's configuration was modified per-request.
**Learning:** In asynchronous frameworks like FastAPI/Starlette, middleware runs concurrently. Modifying shared state (like a singleton service's configuration) based on request attributes leads to isolation violations, where one request's settings bleed into others.
**Prevention:**
1. Never modify shared service state in middleware.
2. Pass request-specific configuration as arguments to service methods (e.g. `override_config`).
3. Use immutable configuration objects where possible or deep copy if modification is needed locally.
