"""
Real-service integration tests for CacheService refresh-token blocklist.

These exercise the LIVE Redis behavior of the methods added in PR #1423 /
issue #1418, which the unit tests can only mock:

* ``add_refresh_token``                 -- TTL and hashed-key shape.
* ``is_refresh_token_valid``            -- positive and revoked-token paths.
* ``revoke_refresh_token``              -- per-token removal.
* ``revoke_all_user_refresh_tokens``    -- pattern-scan revocation.

Run with::

    USE_REAL_SERVICES=1 pytest backend/src/tests/integration/test_real_redis_refresh_tokens.py -v
"""

from __future__ import annotations

import asyncio
import hashlib
import urllib.parse
import uuid

import pytest

pytestmark = [pytest.mark.real_service, pytest.mark.asyncio]

# Use a dedicated Redis logical DB for these tests so concurrent xdist workers
# running ``test_real_redis_rate_limiter.py`` (which calls ``FLUSHDB`` on its
# fixture's teardown against db 0) cannot wipe our blocklist mid-test.
_REFRESH_TOKEN_TEST_DB = 9


def _redis_url_with_db(base_url: str, db: int) -> str:
    """Return ``base_url`` re-pointed at logical Redis database ``db``."""
    parsed = urllib.parse.urlparse(base_url)
    return parsed._replace(path=f"/{db}").geturl()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def real_cache_service(real_redis_url):
    """Yield a :class:`CacheService` connected to live Redis on an isolated db.

    Isolation strategy:
      * a dedicated logical Redis DB (``_REFRESH_TOKEN_TEST_DB``) so other
        integration tests' ``FLUSHDB`` calls cannot wipe our keys in-flight;
      * per-test UUID ``user_id`` prefixes plus short TTLs on every key, so
        leftover data from a previous run cannot poison the next.

    A single ``FLUSHDB`` runs on session teardown via the autouse fixture
    below.
    """
    from services.cache import CacheService

    isolated_url = _redis_url_with_db(real_redis_url, _REFRESH_TOKEN_TEST_DB)
    service = CacheService(redis_url=isolated_url, disable_redis=False)

    # Sanity-check we are actually wired to a real Redis (the fixture is
    # auto-skipped without USE_REAL_SERVICES, but ping confirms reachability).
    try:
        await service._client.ping()
    except Exception as exc:  # pragma: no cover - defensive
        pytest.skip(f"Redis at {isolated_url} not reachable: {exc}")

    yield service

    try:
        await service._client.close()
    except Exception:
        pass


# NOTE: There is intentionally no FLUSHDB teardown here. With xdist running
# different test classes from this module on different workers, a module-scoped
# teardown still races the other workers' in-flight tests. Per-test isolation
# is guaranteed by:
#   * unique UUID user_ids per test (no cross-test key collision), and
#   * short TTLs (<= 120s) on every key written by these tests
# so any leftover keys self-evict well before the next CI run.


def _expected_key(user_id: str, token: str) -> str:
    """Compute the Redis key the way ``CacheService`` does."""
    from services.cache import CacheService

    token_hash = hashlib.sha256(token.encode()).hexdigest()
    return f"{CacheService.REFRESH_TOKEN_PREFIX}{user_id}:{token_hash}"


# ---------------------------------------------------------------------------
# add_refresh_token
# ---------------------------------------------------------------------------


class TestAddRefreshTokenLiveRedis:
    async def test_add_refresh_token_persists_under_hashed_key(self, real_cache_service):
        """Stored key uses ``rt:<user_id>:<sha256(token)>`` and value is "1"."""
        user_id = f"user-{uuid.uuid4()}"
        token = "tok-abc-123"

        await real_cache_service.add_refresh_token(user_id, token, ttl_seconds=60)

        key = _expected_key(user_id, token)
        value = await real_cache_service._client.get(key)
        assert value == "1", f"expected sentinel '1', got {value!r}"

    async def test_add_refresh_token_does_not_store_plaintext_token(self, real_cache_service):
        """The raw token must never appear in any Redis key."""
        user_id = f"user-{uuid.uuid4()}"
        token = "PLAINTEXT-LEAK-CANARY"

        await real_cache_service.add_refresh_token(user_id, token, ttl_seconds=60)

        all_keys = await real_cache_service._client.keys(
            f"{real_cache_service.REFRESH_TOKEN_PREFIX}{user_id}:*"
        )
        assert all_keys, "expected at least one rt:<user>:* key"
        for k in all_keys:
            assert token not in k, f"plaintext token leaked into key: {k}"

    async def test_add_refresh_token_sets_ttl(self, real_cache_service):
        """The key carries the TTL we requested (with a generous slack)."""
        user_id = f"user-{uuid.uuid4()}"
        token = "tok-with-ttl"

        await real_cache_service.add_refresh_token(user_id, token, ttl_seconds=120)

        key = _expected_key(user_id, token)
        ttl = await real_cache_service._client.ttl(key)
        # Redis returns seconds; some clients return -1 for "no expiry" and -2
        # for "missing key". We want a positive TTL bounded by the request.
        assert 0 < ttl <= 120, f"TTL out of expected range: {ttl}"

    async def test_add_refresh_token_short_ttl_expires_key(self, real_cache_service):
        """A small TTL really removes the key after it elapses."""
        user_id = f"user-{uuid.uuid4()}"
        token = "tok-short-lived"

        await real_cache_service.add_refresh_token(user_id, token, ttl_seconds=1)
        assert await real_cache_service.is_refresh_token_valid(user_id, token) is True

        # Sleep a touch past the TTL; keep the wait short to avoid slow CI.
        await asyncio.sleep(1.5)

        assert await real_cache_service.is_refresh_token_valid(user_id, token) is False

    async def test_different_tokens_for_same_user_yield_distinct_keys(self, real_cache_service):
        """Hashed-key collisions: two distinct tokens => two distinct keys."""
        user_id = f"user-{uuid.uuid4()}"
        token_a = "device-a-token"
        token_b = "device-b-token"

        await real_cache_service.add_refresh_token(user_id, token_a, ttl_seconds=60)
        await real_cache_service.add_refresh_token(user_id, token_b, ttl_seconds=60)

        key_a = _expected_key(user_id, token_a)
        key_b = _expected_key(user_id, token_b)
        assert key_a != key_b

        # Both must exist independently.
        keys = await real_cache_service._client.keys(
            f"{real_cache_service.REFRESH_TOKEN_PREFIX}{user_id}:*"
        )
        assert sorted(keys) == sorted([key_a, key_b])

    async def test_re_adding_same_token_refreshes_ttl(self, real_cache_service):
        """Re-adding the same token replaces the value and resets TTL."""
        user_id = f"user-{uuid.uuid4()}"
        token = "tok-renewed"

        await real_cache_service.add_refresh_token(user_id, token, ttl_seconds=2)
        await asyncio.sleep(1.2)  # let the original TTL drop
        await real_cache_service.add_refresh_token(user_id, token, ttl_seconds=60)

        key = _expected_key(user_id, token)
        ttl = await real_cache_service._client.ttl(key)
        assert ttl > 30, f"TTL was not refreshed by re-adding token; got {ttl} (expected >30)"


# ---------------------------------------------------------------------------
# is_refresh_token_valid
# ---------------------------------------------------------------------------


class TestIsRefreshTokenValidLiveRedis:
    async def test_unknown_token_is_invalid(self, real_cache_service):
        user_id = f"user-{uuid.uuid4()}"
        assert await real_cache_service.is_refresh_token_valid(user_id, "never-added") is False

    async def test_added_token_is_valid(self, real_cache_service):
        user_id = f"user-{uuid.uuid4()}"
        token = "tok-valid"

        await real_cache_service.add_refresh_token(user_id, token, ttl_seconds=60)

        assert await real_cache_service.is_refresh_token_valid(user_id, token) is True

    async def test_other_user_cannot_read_my_token(self, real_cache_service):
        """The user_id is part of the key namespace - no cross-user lookup."""
        user_a = f"user-a-{uuid.uuid4()}"
        user_b = f"user-b-{uuid.uuid4()}"
        shared_token = "same-string-different-owners"

        await real_cache_service.add_refresh_token(user_a, shared_token, 60)

        assert await real_cache_service.is_refresh_token_valid(user_a, shared_token) is True
        assert await real_cache_service.is_refresh_token_valid(user_b, shared_token) is False


# ---------------------------------------------------------------------------
# revoke_refresh_token
# ---------------------------------------------------------------------------


class TestRevokeRefreshTokenLiveRedis:
    async def test_revoke_removes_only_targeted_token(self, real_cache_service):
        user_id = f"user-{uuid.uuid4()}"
        token_keep = "device-keep"
        token_revoke = "device-revoke"

        await real_cache_service.add_refresh_token(user_id, token_keep, 60)
        await real_cache_service.add_refresh_token(user_id, token_revoke, 60)

        await real_cache_service.revoke_refresh_token(user_id, token_revoke)

        assert await real_cache_service.is_refresh_token_valid(user_id, token_keep) is True
        assert await real_cache_service.is_refresh_token_valid(user_id, token_revoke) is False

    async def test_revoke_unknown_token_is_a_no_op(self, real_cache_service):
        """Revoking a token that was never stored must not raise."""
        user_id = f"user-{uuid.uuid4()}"
        await real_cache_service.revoke_refresh_token(user_id, "ghost-token")

        # And subsequent ``is_refresh_token_valid`` still reports invalid.
        assert await real_cache_service.is_refresh_token_valid(user_id, "ghost-token") is False


# ---------------------------------------------------------------------------
# revoke_all_user_refresh_tokens (pattern-scan revocation)
# ---------------------------------------------------------------------------


class TestRevokeAllUserRefreshTokensLiveRedis:
    async def test_revoke_all_clears_every_token_for_user(self, real_cache_service):
        """Pattern ``rt:<user>:*`` deletes every device key for that user."""
        user_id = f"user-{uuid.uuid4()}"
        tokens = [f"device-{i}" for i in range(5)]
        for t in tokens:
            await real_cache_service.add_refresh_token(user_id, t, ttl_seconds=60)

        # Sanity: all five exist before the sweep.
        before = await real_cache_service._client.keys(
            f"{real_cache_service.REFRESH_TOKEN_PREFIX}{user_id}:*"
        )
        assert len(before) == 5

        await real_cache_service.revoke_all_user_refresh_tokens(user_id)

        after = await real_cache_service._client.keys(
            f"{real_cache_service.REFRESH_TOKEN_PREFIX}{user_id}:*"
        )
        assert after == [], f"expected zero keys, got {after}"

        for t in tokens:
            assert await real_cache_service.is_refresh_token_valid(user_id, t) is False

    async def test_revoke_all_does_not_affect_other_users(self, real_cache_service):
        """Pattern is anchored on ``rt:<user>:`` -- other users are untouched."""
        target = f"user-target-{uuid.uuid4()}"
        bystander = f"user-bystander-{uuid.uuid4()}"

        await real_cache_service.add_refresh_token(target, "tok1", 60)
        await real_cache_service.add_refresh_token(target, "tok2", 60)
        await real_cache_service.add_refresh_token(bystander, "tok-by", 60)

        await real_cache_service.revoke_all_user_refresh_tokens(target)

        # Target user purged.
        target_keys = await real_cache_service._client.keys(
            f"{real_cache_service.REFRESH_TOKEN_PREFIX}{target}:*"
        )
        assert target_keys == []

        # Bystander still has their token.
        assert await real_cache_service.is_refresh_token_valid(bystander, "tok-by") is True

    async def test_revoke_all_when_user_has_no_tokens_is_a_no_op(self, real_cache_service):
        """Should not raise even if there are zero matching keys."""
        user_id = f"user-noop-{uuid.uuid4()}"
        await real_cache_service.revoke_all_user_refresh_tokens(user_id)

    async def test_user_id_with_colon_does_not_leak_via_pattern_match(self, real_cache_service):
        """``user_id`` segments containing ``:`` must not let one user's
        revocation match another user's keys.

        The blocklist key shape is ``rt:<user_id>:<hash>``; if user_id is
        ``alice`` then ``rt:alice:*`` must not match ``rt:alice-evil:<hash>``
        (i.e. the trailing ``:`` is significant).
        """
        alice = f"alice-{uuid.uuid4()}"
        evil = f"{alice}-evil"

        await real_cache_service.add_refresh_token(alice, "alice-token", 60)
        await real_cache_service.add_refresh_token(evil, "evil-token", 60)

        await real_cache_service.revoke_all_user_refresh_tokens(alice)

        assert await real_cache_service.is_refresh_token_valid(alice, "alice-token") is False
        # The look-alike user must still be valid.
        assert await real_cache_service.is_refresh_token_valid(evil, "evil-token") is True
