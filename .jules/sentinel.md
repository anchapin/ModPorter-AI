## 2026-02-16 - SSRF Prevention Pattern
**Vulnerability:** Server-Side Request Forgery (SSRF) in file download functionality.
**Learning:** `httpx` (and `requests`) follow redirects by default, potentially bypassing initial URL validation if a redirect leads to a private IP. Blocking DNS resolution via `socket.getaddrinfo` is effective but requires handling IPv6 scope IDs and fail-secure logic.
**Prevention:**
1. Validate URL scheme (http/https).
2. Resolve hostname to IP(s) and check against private/loopback ranges.
3. Disable automatic redirect following (`follow_redirects=False`).
4. Manually handle redirects, re-validating the URL at each hop.
5. Sanitize URLs before logging to avoid leaking sensitive tokens.
