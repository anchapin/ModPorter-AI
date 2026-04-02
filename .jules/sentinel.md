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
## 2024-05-24 - [Hardcoded JWT Secret Key]
**Vulnerability:** A hardcoded `SECRET_KEY` ("your-secret-key-change-in-production") was used in `backend/src/security/auth.py` for signing JWT tokens.
**Learning:** Hardcoded cryptographic keys allow attackers who read the source code to forge valid JWT tokens, completely bypassing authentication.
**Prevention:** Always load secrets from environment variables or a secure secret management system using a utility like `get_secret` from `core.secrets`.

## 2024-05-24 - [Fail-Secure Missing Secrets]
**Vulnerability:** A hardcoded `SECRET_KEY` was used as a default, or the application might fall back to an insecure default if the secret was not available.
**Learning:** When removing hardcoded cryptographic secrets to use environment variables, the application must fail securely if the variable is unset. Falling back to an insecure default negates the purpose of externalized secrets.
**Prevention:** Raise an explicit error (e.g., `ValueError`) during initialization if critical cryptographic secrets are missing, rather than using fallback values.

## 2024-05-24 - [CRITICAL] Remove Hardcoded Fallback for JWT SECRET_KEY
**Vulnerability:** The application used a hardcoded fallback secret key (`"dev-secret-key-do-not-use-in-production-change-me"`) for JWT token generation and validation if the `SECRET_KEY` environment variable was missing.
**Learning:** Hardcoded cryptographic secrets are a severe vulnerability (CWE-798). If the environment variable isn't set properly, the application falls back to an insecure, easily guessable default in production, compromising all tokens.
**Prevention:** Never use default fallback values for cryptographic secrets. When removing hardcoded cryptographic secrets to use environment variables, ensure the application fails securely (e.g., raises a `ValueError`) if the variable is unset, rather than falling back to an insecure default. For testing, set dummy values in `conftest.py` before application imports.
