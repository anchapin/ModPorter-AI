"""
Regression tests for ``security.auth.verify_api_key`` after the bcrypt
migration in issue #1414.

These tests use a fake async DB that yields canned ``execute`` results,
so we can exercise the prefix-narrow + ``bcrypt.checkpw`` candidate loop
without spinning up a real database.
"""

from types import SimpleNamespace
from typing import Any

import pytest

from security.auth import hash_api_key, verify_api_key


class _ScalarResult:
    """Mimic the slice of the SQLAlchemy ``Result`` API used by verify_api_key."""

    def __init__(self, rows: list[Any]):
        self._rows = rows

    def all(self) -> list[Any]:
        return list(self._rows)

    def scalar_one_or_none(self) -> Any | None:
        return self._rows[0] if self._rows else None

    def scalars(self) -> "_ScalarResult":
        return self


class _FakeAsyncSession:
    """
    Two-call fake: the first ``execute`` returns API-key candidates,
    the second returns the User row matched against the winning candidate.
    """

    def __init__(self, candidates: list[Any], users: list[Any]):
        self._candidates = candidates
        self._users = users
        self.execute_calls = 0

    async def execute(self, _stmt: Any) -> _ScalarResult:
        self.execute_calls += 1
        if self.execute_calls == 1:
            return _ScalarResult(self._candidates)
        return _ScalarResult(self._users)


@pytest.mark.unit
@pytest.mark.asyncio
class TestSecurityAuthVerifyApiKey:
    """Behavioural tests for ``security.auth.verify_api_key`` candidate loop."""

    async def test_returns_user_for_correct_key_single_candidate(self):
        plain = "mpk_test-key-single-candidate"
        candidate = SimpleNamespace(key_hash=hash_api_key(plain), user_id="user-1")
        user = SimpleNamespace(id="user-1")
        db = _FakeAsyncSession([candidate], [user])

        result = await verify_api_key(db, plain)

        assert result is user
        # one query for candidates, one for the user
        assert db.execute_calls == 2

    async def test_returns_user_when_correct_key_is_not_first_candidate(self):
        """If multiple keys share a prefix, the loop must keep checking."""
        plain = "mpk_real-key-second-in-list"
        wrong = SimpleNamespace(key_hash=hash_api_key("mpk_some-other-key"), user_id="user-x")
        right = SimpleNamespace(key_hash=hash_api_key(plain), user_id="user-1")
        user = SimpleNamespace(id="user-1")
        db = _FakeAsyncSession([wrong, right], [user])

        result = await verify_api_key(db, plain)

        assert result is user

    async def test_returns_none_when_no_candidate_matches(self):
        plain = "mpk_a-key-that-no-row-stores"
        wrong = SimpleNamespace(key_hash=hash_api_key("mpk_completely-different"), user_id="x")
        db = _FakeAsyncSession([wrong], [])

        result = await verify_api_key(db, plain)

        assert result is None
        # Only the candidate query runs; we never look the user up.
        assert db.execute_calls == 1

    async def test_returns_none_when_no_candidates_for_prefix(self):
        plain = "mpk_no-rows-at-all"
        db = _FakeAsyncSession([], [])

        assert await verify_api_key(db, plain) is None
        assert db.execute_calls == 1

    async def test_returns_none_for_empty_or_short_input(self):
        db = _FakeAsyncSession([], [])

        assert await verify_api_key(db, "") is None
        assert await verify_api_key(db, "abc") is None
        # Short-circuit: no DB calls at all.
        assert db.execute_calls == 0

    async def test_returns_none_for_none_input(self):
        db = _FakeAsyncSession([], [])

        assert await verify_api_key(db, None) is None
        assert db.execute_calls == 0

    async def test_skips_candidate_with_legacy_hash_format(self):
        """A legacy SHA-256 / scrypt hex hash must not raise, just be skipped."""
        plain = "mpk_real-key-after-legacy-row"
        legacy = SimpleNamespace(key_hash="a" * 64, user_id="legacy")
        good = SimpleNamespace(key_hash=hash_api_key(plain), user_id="user-1")
        user = SimpleNamespace(id="user-1")
        db = _FakeAsyncSession([legacy, good], [user])

        result = await verify_api_key(db, plain)

        assert result is user
