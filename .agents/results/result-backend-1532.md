# Security Evaluation: JWT Algorithm for Enterprise Scale

## Issue: #1532 - security(backend): evaluate RS256 JWT algorithm for enterprise scale

---

## Current JWT Algorithm

**Algorithm:** `HS256` (HMAC with SHA-256)
**Location:** `backend/src/security/auth.py` and `backend/src/core/auth.py`

Both modules define `ALGORITHM = "HS256"` as a hardcoded constant at module load time.

---

## Analysis: HS256 vs RS256 for Enterprise Scale

### HS256 (Symmetric - Current)

**Pros:**
- Fast signing and verification (~3x faster than RSA)
- Simple key management: single shared secret
- Lower computational overhead for token validation
- No certificate management complexity

**Cons:**
- **Key distribution problem**: Every service that needs to verify tokens needs the same secret. If any verifier service is compromised, attacker can forge valid tokens
- Secret rotation is complex: all services must update simultaneously
- Not suitable for multi-party/partner integrations where you don't want partners to be able to forge tokens

### RS256 (Asymmetric - Recommended for Enterprise)

**Pros:**
- **Superior key management**: Private key stays only on auth server; public key can be widely distributed
- Compromise of a verifier service only exposes the public key - cannot forge tokens
- Natural fit for microservice architectures: each service only needs the public key
- Supports key rotation without service downtime
- Industry standard for enterprise OAuth2/OpenID Connect deployments

**Cons:**
- ~3x slower signing (not verification) - negligible for typical workloads
- Requires RSA key pair generation and management
- Slightly more complex setup

### Other Algorithms Considered

| Algorithm | Type | Recommendation |
|-----------|------|----------------|
| HS256 | Symmetric | Default for backwards compatibility |
| HS384 | Symmetric | OK if HS256 feel insufficient |
| HS512 | Symmetric | Avoid - unnecessarily slow, no security benefit |
| RS256 | Asymmetric | **Recommended for enterprise** |
| RS384 | Asymmetric | OK if RSA-2048 required, otherwise RS256 |
| RS512 | Asymmetric | Avoid - unnecessarily slow, no security benefit |

---

## Code Changes Implemented

### 1. `backend/src/security/auth.py`

**Changes:**
- Added `JWT_ALGORITHM` environment variable support (defaults to HS256)
- Added RSA key loading for RS256 support via `RSA_PRIVATE_KEY`/`RSA_PUBLIC_KEY` env vars or `RSA_PRIVATE_KEY_FILE`/`RSA_PUBLIC_KEY_FILE` file paths
- Added `_get_signing_key()` and `_get_verification_key()` helper functions to handle key selection based on algorithm
- Updated `create_access_token()`, `create_refresh_token()`, `verify_token()`, and `get_token_expiry()` to use the correct keys

**Key Selection Logic:**
```python
def _get_signing_key() -> str:
    if ALGORITHM.startswith("RS"):
        return _RSA_PRIVATE_KEY  # Private key for signing
    return SECRET_KEY  # Symmetric key for HS256

def _get_verification_key() -> str:
    if ALGORITHM.startswith("RS"):
        return _RSA_PUBLIC_KEY  # Public key for verification
    return SECRET_KEY  # Same secret for HS256
```

### 2. `backend/src/core/auth.py`

**Changes:**
- Added `os` import (was missing after refactoring)
- Added same `JWT_ALGORITHM` environment variable support
- Added RSA key loading with file fallback support
- Updated `AuthManager` class to use `algorithm=None` default and pull from module-level `ALGORITHM`
- Added `_get_signing_key()` and `_get_verification_key()` methods to `AuthManager`
- Updated `create_access_token()`, `create_refresh_token()`, `verify_token()`, and `get_token_expiry()` in `AuthManager` to use correct keys

---

## Configuration for Enterprise Deployment

### Option 1: Environment Variables

```bash
# Use RS256 for enterprise
export JWT_ALGORITHM=RS256
export RSA_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\nMIIEvg...\n-----END PRIVATE KEY-----"
export RSA_PUBLIC_KEY="-----BEGIN PUBLIC KEY-----\nMIIBIjAN...\n-----END PUBLIC KEY-----"
```

### Option 2: File-based (Kubernetes Secrets, mounted certs)

```bash
export JWT_ALGORITHM=RS256
export RSA_PRIVATE_KEY_FILE=/run/secrets/rsa_private_key.pem
export RSA_PUBLIC_KEY_FILE=/run/secrets/rsa_public_key.pem
```

### Option 3: Backwards Compatible (HS256 - current default)

```bash
# No changes required - HS256 works as before
export SECRET_KEY=your-256-bit-secret
```

---

## Security Comparison

| Aspect | HS256 | RS256 |
|--------|-------|-------|
| Token Signing | Shared secret | Private key (auth server only) |
| Token Verification | Shared secret | Public key (any service) |
| Compromise of Verifier | Attacker can forge tokens | Attacker can only verify, cannot forge |
| Key Rotation | Complex (all services must update) | Simple (update auth server, public key propagates) |
| Performance | Faster signing | Slower signing but acceptable |
| Enterprise Readiness | Basic | **Recommended** |

---

## Acceptance Criteria Checklist

- [x] **Current algorithm identified**: HS256 (symmetric)
- [x] **Analysis complete**: RS256 recommended for enterprise due to superior key management
- [x] **Code changes implemented**: Both `security.auth` and `core.auth` updated
- [x] **Backwards compatible**: HS256 still works without any changes
- [x] **RS256 support added**: Via environment variables or files
- [x] **Tests pass**: 14 tests in `test_security_auth_coverage.py`, 23 in `test_core_api_extra_coverage.py`
- [x] **Consistent with codebase**: Follows same patterns as existing BYOK key vault

---

## Files Changed

1. `backend/src/security/auth.py` - JWT algorithm selection and RSA key support
2. `backend/src/core/auth.py` - JWT algorithm selection and RSA key support (AuthManager class)

---

## Recommendations

1. **Default to HS256 for now**: Maintains backwards compatibility
2. **Migrate to RS256 for production enterprise deployment**: Set `JWT_ALGORITHM=RS256` and provide RSA keys
3. **Consider ES256 (ECDSA)** for future: Better performance than RSA while maintaining asymmetric benefits
4. **Document key rotation procedure**: For enterprise IT teams managing secrets