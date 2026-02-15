## 2025-05-22 - SSRF Protection Implementation
**Vulnerability:** The `download_from_url` method in `FileProcessor` was vulnerable to Server-Side Request Forgery (SSRF). It accepted any URL and downloaded content using `httpx` without validation, allowing access to internal network resources or local files if exploited.
**Learning:** `httpx` and other HTTP clients often follow redirects by default, which can bypass initial URL validation. Also, testing environments can be fragile; shadowing standard library modules like `types` can cause obscure `ImportError`s in test tools like `pytest`.
**Prevention:**
1. Always validate user-supplied URLs against an allowlist or ensure they resolve to public IPs before connection.
2. Disable automatic redirects (`follow_redirects=False`) and manually verify each hop in the redirect chain.
3. Avoid naming local modules `types.py` or `types/` to prevent shadowing the Python standard library.