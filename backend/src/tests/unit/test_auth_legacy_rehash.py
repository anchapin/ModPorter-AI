"""
Unit tests for the rehash-on-next-use migration path for legacy SHA-256 /
scrypt API keys (issue #1428).

Covers both ``security.auth.verify_api_key`` (async, DB-aware — does the
actual rehash + commit) and ``core.auth.AuthManager.verify_api_key_with_rehash``
(pure primitive — returns the new bcrypt hash for the caller to persist).

The bcrypt fast-path must remain byte-identical to the post-#1425 behaviour:
no extra DB write, no metric increment, no log line.
"""

import hashlib
import logging
from types import SimpleNamespace
from typing import Any, Optional

import bcrypt
import pytest

from core.auth import (
    BCRYPT_HASH_PREFIXES,
    AuthManager,
    _is_bcrypt_hash,
    _matches_legacy_scrypt,
    _matches_legacy_sha256,
    needs_rehash,
    verify_api_key_with_rehash,
)
from security.auth import (
    SECRET_KEY,
    hash_api_key,
    verify_api_key,
)
from security.auth import (
    _matches_legacy_scrypt as sec_matches_legacy_scrypt,
)
from security.auth import (
    _matches_legacy_sha256 as sec_matches_legacy_sha256,
)


# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------


class _ScalarResult:
    """Mimic the slice of the SQLAlchemy ``Result`` API used by verify_api_key."""

    def __init__(self, rows: list[Any]):
        self._rows = rows

    def all(self) -> list[Any]:
        return list(self._rows)

    def scalar_one_or_none(self) -> Optional[Any]:
        return self._rows[0] if self._rows else None

    def scalars(self) -> "_ScalarResult":
        return self


class _FakeAsyncSession:
    """
    Async session double that yields canned ``execute`` results in order.

    First call -> APIKey candidates (a list).
    Second call -> User row(s) for the matched candidate.
    Third+ calls -> repeats the user-row result (used by the
    "rehashed key verifies on next call" test which authenticates twice
    against the same fake).
    """

    def __init__(self, candidates: list[Any], users: list[Any]):
        self._candidates = candidates
        self._users = users
        self.execute_calls = 0
        self.commit_calls = 0
        self.rollback_calls = 0
        self.commit_should_raise: Optional[Exception] = None

    async def execute(self, _stmt: Any) -> _ScalarResult:
        self.execute_calls += 1
        # On every odd call (1st, 3rd, ...) we return candidates so the test
        # can re-run the verifier; on even calls we return users.
        if self.execute_calls % 2 == 1:
            return _ScalarResult(self._candidates)
        return _ScalarResult(self._users)

    async def commit(self) -> None:
        self.commit_calls += 1
        if self.commit_should_raise is not None:
            raise self.commit_should_raise

    async def rollback(self) -> None:
        self.rollback_calls += 1


def _legacy_sha256_hash(plain: str) -> str:
    """Replicate the pre-#1414 ``core.auth.hash_api_key`` output exactly."""
    return hashlib.sha256(plain.encode()).hexdigest()


def _legacy_scrypt_hash(plain: str) -> str:
    """Replicate the pre-#1414 ``security.auth.hash_api_key`` output exactly."""
    return hashlib.scrypt(
        plain.encode(),
        salt=SECRET_KEY.encode(),
        n=16384,
        r=8,
        p=1,
        dklen=32,
    ).hex()


# ===========================================================================
# security.auth.verify_api_key — async DB-aware verifier (#1428 main flow)
# ===========================================================================


@pytest.mark.unit
@pytest.mark.asyncio
class TestSecurityAuthLegacyRehash:
    """End-to-end behaviour of the rehash-on-next-use flow."""

    async def test_legacy_sha256_key_verifies_and_upgrades_to_bcrypt(self):
        """A pre-#1414 SHA-256 hash matches, gets rehashed, and persists."""
        plain = "mpk_legacy-sha256-key-payload"
        record = SimpleNamespace(
            key_hash=_legacy_sha256_hash(plain),
            user_id="user-sha",
        )
        user = SimpleNamespace(id="user-sha")
        db = _FakeAsyncSession([record], [user])

        result = await verify_api_key(db, plain)

        assert result is user
        # The row was rehashed and committed exactly once.
        assert db.commit_calls == 1
        assert db.rollback_calls == 0
        # New hash is bcrypt and verifies against the original plaintext.
        assert record.key_hash.startswith(BCRYPT_HASH_PREFIXES)
        assert bcrypt.checkpw(plain.encode("utf-8"), record.key_hash.encode("utf-8"))

    async def test_legacy_scrypt_key_verifies_and_upgrades_to_bcrypt(self):
        """A pre-#1414 scrypt hash matches, gets rehashed, and persists."""
        plain = "mpk_legacy-scrypt-key-payload"
        record = SimpleNamespace(
            key_hash=_legacy_scrypt_hash(plain),
            user_id="user-scrypt",
        )
        user = SimpleNamespace(id="user-scrypt")
        db = _FakeAsyncSession([record], [user])

        result = await verify_api_key(db, plain)

        assert result is user
        assert db.commit_calls == 1
        assert db.rollback_calls == 0
        assert record.key_hash.startswith(BCRYPT_HASH_PREFIXES)
        assert bcrypt.checkpw(plain.encode("utf-8"), record.key_hash.encode("utf-8"))

    async def test_bcrypt_key_passes_through_unchanged(self):
        """Bcrypt-format hashes hit the fast-path: no commit, no rollback."""
        plain = "mpk_modern-bcrypt-key-payload"
        original_hash = hash_api_key(plain)
        record = SimpleNamespace(key_hash=original_hash, user_id="user-bcrypt")
        user = SimpleNamespace(id="user-bcrypt")
        db = _FakeAsyncSession([record], [user])

        result = await verify_api_key(db, plain)

        assert result is user
        # Byte-identical to pre-#1428 behaviour: no DB writes whatsoever.
        assert db.commit_calls == 0
        assert db.rollback_calls == 0
        # Stored hash is untouched (still the exact original bcrypt string).
        assert record.key_hash == original_hash

    async def test_wrong_key_against_legacy_hash_returns_false_no_upgrade(self):
        """A mismatched key against a legacy-format row must NOT trigger a write."""
        legitimate = "mpk_legitimate-legacy-key"
        attacker = "mpk_attacker-guessed-this"
        record = SimpleNamespace(
            key_hash=_legacy_sha256_hash(legitimate),
            user_id="user-legit",
        )
        db = _FakeAsyncSession([record], [])

        result = await verify_api_key(db, attacker)

        assert result is None
        # No rehash, no rollback — just a candidate fetch.
        assert db.commit_calls == 0
        assert db.rollback_calls == 0
        assert db.execute_calls == 1
        # Stored hash is unchanged (still the legacy SHA-256 hex string).
        assert record.key_hash == _legacy_sha256_hash(legitimate)

    async def test_wrong_key_against_legacy_scrypt_no_upgrade(self):
        """Same as above but against a scrypt-format row."""
        legitimate = "mpk_legitimate-scrypt-key"
        attacker = "mpk_attacker-guessed-this2"
        record = SimpleNamespace(
            key_hash=_legacy_scrypt_hash(legitimate),
            user_id="user-legit",
        )
        db = _FakeAsyncSession([record], [])

        result = await verify_api_key(db, attacker)

        assert result is None
        assert db.commit_calls == 0
        assert record.key_hash == _legacy_scrypt_hash(legitimate)

    async def test_rehashed_key_verifies_on_next_call(self):
        """After a successful rehash, the same key authenticates via the bcrypt fast-path."""
        plain = "mpk_two-call-upgrade-flow"
        record = SimpleNamespace(
            key_hash=_legacy_sha256_hash(plain),
            user_id="user-twice",
        )
        user = SimpleNamespace(id="user-twice")
        db = _FakeAsyncSession([record], [user])

        # First call: legacy match → rehash + commit.
        first = await verify_api_key(db, plain)
        assert first is user
        assert db.commit_calls == 1
        rehashed = record.key_hash
        assert rehashed.startswith(BCRYPT_HASH_PREFIXES)

        # Second call: stored hash is now bcrypt → fast-path, no extra commit.
        second = await verify_api_key(db, plain)
        assert second is user
        assert db.commit_calls == 1, "second call must NOT trigger another rehash"
        assert record.key_hash == rehashed, "stored hash must not change on bcrypt fast-path"

    async def test_legacy_match_succeeds_even_if_persist_fails(self):
        """If db.commit() raises, auth still succeeds and the session is rolled back.

        Rationale: a transient DB hiccup must not lock a previously-valid
        legacy key out. The next call simply retries the rehash.
        """
        plain = "mpk_legacy-but-broken-db"
        record = SimpleNamespace(
            key_hash=_legacy_sha256_hash(plain),
            user_id="user-broken",
        )
        user = SimpleNamespace(id="user-broken")
        db = _FakeAsyncSession([record], [user])
        db.commit_should_raise = RuntimeError("simulated commit failure")

        result = await verify_api_key(db, plain)

        assert result is user
        assert db.commit_calls == 1
        assert db.rollback_calls == 1

    async def test_legacy_rehash_emits_log_and_metric(self, caplog):
        """Successful rehash logs ``legacy_api_key_rehashed`` and increments the counter."""
        from services.metrics import legacy_api_key_rehashed_total

        plain = "mpk_metric-and-log-check"
        record = SimpleNamespace(
            key_hash=_legacy_sha256_hash(plain),
            user_id="user-metric",
        )
        user = SimpleNamespace(id="user-metric")
        db = _FakeAsyncSession([record], [user])

        before = legacy_api_key_rehashed_total.labels(old_format="sha256")._value.get()

        with caplog.at_level(logging.INFO, logger="security.auth"):
            await verify_api_key(db, plain)

        after = legacy_api_key_rehashed_total.labels(old_format="sha256")._value.get()
        assert after - before == 1

        log_msgs = [r.getMessage() for r in caplog.records]
        assert "legacy_api_key_rehashed" in log_msgs

    async def test_unknown_format_candidate_is_skipped(self):
        """A candidate with garbage in key_hash must not raise and must not match."""
        plain = "mpk_real-key-after-garbage-row"
        garbage = SimpleNamespace(key_hash="this-is-definitely-not-a-hash", user_id="garbage")
        good = SimpleNamespace(key_hash=hash_api_key(plain), user_id="user-good")
        user = SimpleNamespace(id="user-good")
        db = _FakeAsyncSession([garbage, good], [user])

        result = await verify_api_key(db, plain)

        assert result is user
        # The garbage row must not have been "rehashed" — its key_hash is
        # untouched and no commit fired on its behalf.
        assert garbage.key_hash == "this-is-definitely-not-a-hash"
        assert db.commit_calls == 0


# ===========================================================================
# core.auth — pure verification primitive (no DB)
# ===========================================================================


@pytest.mark.unit
class TestCoreAuthLegacyRehash:
    """``AuthManager.verify_api_key_with_rehash`` returns a (matched, new_hash) tuple."""

    def test_bcrypt_match_returns_no_new_hash(self):
        manager = AuthManager()
        plain = "mpk_modern-bcrypt-key"
        stored = manager.hash_api_key(plain)

        matched, new_hash = manager.verify_api_key_with_rehash(plain, stored)

        assert matched is True
        assert new_hash is None

    def test_bcrypt_mismatch_returns_false_and_no_new_hash(self):
        manager = AuthManager()
        plain = "mpk_modern-bcrypt-key"
        stored = manager.hash_api_key(plain)

        matched, new_hash = manager.verify_api_key_with_rehash("mpk_wrong-key", stored)

        assert matched is False
        assert new_hash is None

    def test_legacy_sha256_match_returns_bcrypt_new_hash(self):
        manager = AuthManager()
        plain = "mpk_legacy-sha256-payload"
        stored = _legacy_sha256_hash(plain)

        matched, new_hash = manager.verify_api_key_with_rehash(plain, stored)

        assert matched is True
        assert new_hash is not None
        assert new_hash.startswith(BCRYPT_HASH_PREFIXES)
        assert bcrypt.checkpw(plain.encode("utf-8"), new_hash.encode("utf-8"))

    def test_legacy_scrypt_match_returns_bcrypt_new_hash(self):
        manager = AuthManager()
        plain = "mpk_legacy-scrypt-payload"
        stored = _legacy_scrypt_hash(plain)

        matched, new_hash = manager.verify_api_key_with_rehash(plain, stored)

        assert matched is True
        assert new_hash is not None
        assert new_hash.startswith(BCRYPT_HASH_PREFIXES)
        assert bcrypt.checkpw(plain.encode("utf-8"), new_hash.encode("utf-8"))

    def test_legacy_mismatch_returns_no_new_hash(self):
        manager = AuthManager()
        legitimate = "mpk_legitimate-key"
        attacker = "mpk_guess-attempt"
        stored = _legacy_sha256_hash(legitimate)

        matched, new_hash = manager.verify_api_key_with_rehash(attacker, stored)

        assert matched is False
        assert new_hash is None

    def test_garbage_stored_hash_returns_false_no_raise(self):
        manager = AuthManager()
        for garbage in ("", "not-a-hash", "x" * 64, "$2b$broken"):
            matched, new_hash = manager.verify_api_key_with_rehash("mpk_anything", garbage)
            assert matched is False
            assert new_hash is None

    def test_none_inputs_return_false_no_raise(self):
        manager = AuthManager()
        assert manager.verify_api_key_with_rehash(None, "x") == (False, None)
        assert manager.verify_api_key_with_rehash("x", None) == (False, None)
        assert manager.verify_api_key_with_rehash(None, None) == (False, None)

    def test_module_level_alias_works(self):
        """The module-level ``verify_api_key_with_rehash`` proxies to ``default_auth``."""
        plain = "mpk_alias-check-payload"
        stored = _legacy_sha256_hash(plain)
        matched, new_hash = verify_api_key_with_rehash(plain, stored)
        assert matched is True
        assert new_hash is not None
        assert bcrypt.checkpw(plain.encode("utf-8"), new_hash.encode("utf-8"))

    def test_needs_rehash_flags_legacy_only(self):
        plain = "mpk_needs-rehash-test"
        modern = AuthManager().hash_api_key(plain)
        sha256 = _legacy_sha256_hash(plain)
        scrypt = _legacy_scrypt_hash(plain)

        assert needs_rehash(modern) is False
        assert needs_rehash(sha256) is True
        assert needs_rehash(scrypt) is True
        # Garbage / non-string inputs are also flagged for replacement.
        assert needs_rehash("garbage") is True
        assert needs_rehash(None) is True


# ===========================================================================
# Backwards-compat: the existing bcrypt-only primitive must not change.
# ===========================================================================


@pytest.mark.unit
class TestBcryptPathByteIdentical:
    """``AuthManager.verify_api_key`` must remain bcrypt-only post-#1428."""

    def test_bcrypt_correct_key_still_true(self):
        manager = AuthManager()
        plain = "mpk_bcrypt-truth-table"
        assert manager.verify_api_key(plain, manager.hash_api_key(plain)) is True

    def test_bcrypt_wrong_key_still_false(self):
        manager = AuthManager()
        plain = "mpk_bcrypt-truth-table"
        assert manager.verify_api_key("mpk_wrong", manager.hash_api_key(plain)) is False

    def test_legacy_sha256_against_old_primitive_still_false(self):
        """Pre-#1428 callers of ``verify_api_key`` see legacy hashes as failures.

        This is intentional: the rehash-aware flow lives in
        ``verify_api_key_with_rehash`` so existing callers' contract is
        unchanged. Any caller that wants legacy support must opt in.
        """
        manager = AuthManager()
        plain = "mpk_was-legacy-payload"
        stored = _legacy_sha256_hash(plain)
        assert manager.verify_api_key(plain, stored) is False

    def test_legacy_scrypt_against_old_primitive_still_false(self):
        manager = AuthManager()
        plain = "mpk_was-legacy-payload"
        stored = _legacy_scrypt_hash(plain)
        assert manager.verify_api_key(plain, stored) is False

    def test_malformed_hash_against_old_primitive_still_false(self):
        manager = AuthManager()
        for garbage in ("", "x" * 64, "not-a-hash"):
            assert manager.verify_api_key("mpk_anything", garbage) is False


# ===========================================================================
# Constant-time legacy helpers — direct unit tests
# ===========================================================================


@pytest.mark.unit
class TestLegacyHelperPrimitives:
    """Both modules expose helpers; verify behaviour and constant-time guards."""

    def test_is_bcrypt_hash_recognises_known_prefixes(self):
        for prefix in BCRYPT_HASH_PREFIXES:
            assert _is_bcrypt_hash(prefix + "12$" + "a" * 53) is True
        # Negative cases.
        assert _is_bcrypt_hash("a" * 64) is False
        assert _is_bcrypt_hash("") is False
        assert _is_bcrypt_hash(None) is False
        assert _is_bcrypt_hash(b"$2b$12$abc") is False  # bytes, not str

    def test_matches_legacy_sha256_correctness(self):
        plain = "mpk_helper-sha-test"
        stored = _legacy_sha256_hash(plain)
        assert _matches_legacy_sha256(plain, stored) is True
        assert sec_matches_legacy_sha256(plain, stored) is True

        # Wrong key.
        assert _matches_legacy_sha256("mpk_other", stored) is False
        # Wrong stored.
        assert _matches_legacy_sha256(plain, "0" * 64) is False

    def test_matches_legacy_sha256_constant_time_on_garbage(self):
        """Malformed stored hash must not raise — just return False."""
        plain = "mpk_helper-sha-garbage"
        for stored in (None, "", "short", "x" * 13, 12345, b"bytes"):
            assert _matches_legacy_sha256(plain, stored) is False
            assert sec_matches_legacy_sha256(plain, stored) is False

    def test_matches_legacy_scrypt_correctness(self):
        plain = "mpk_helper-scrypt-test"
        stored = _legacy_scrypt_hash(plain)
        assert _matches_legacy_scrypt(plain, stored) is True
        assert sec_matches_legacy_scrypt(plain, stored) is True

        assert _matches_legacy_scrypt("mpk_other", stored) is False
        assert _matches_legacy_scrypt(plain, "0" * 64) is False

    def test_matches_legacy_scrypt_constant_time_on_garbage(self):
        plain = "mpk_helper-scrypt-garbage"
        for stored in (None, "", "short", 12345, b"bytes"):
            assert _matches_legacy_scrypt(plain, stored) is False
            assert sec_matches_legacy_scrypt(plain, stored) is False
