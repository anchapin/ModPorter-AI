"""Tests for backend.src.utils.ai_engine_path."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from utils import ai_engine_path as aep


@pytest.fixture(autouse=True)
def reset_state():
    """Each test gets a fresh memoization state and clean sys.path snapshot."""
    aep.reset_for_tests()
    original_path = list(sys.path)
    yield
    sys.path[:] = original_path
    aep.reset_for_tests()


class TestEnsureAiEnginePath:
    def test_returns_true_when_repo_layout_resolves(self):
        """In a real checkout, the repo-root-relative candidate should resolve."""
        # The repo root is reachable from this test file, so ai-engine/ exists.
        ok = aep.ensure_ai_engine_on_path()
        assert ok is True
        # The resolved dir should be on sys.path.
        assert aep._RESOLVED is not None
        assert str(aep._RESOLVED) in sys.path

    def test_idempotent_subsequent_calls(self):
        """A second call is a memoized no-op and returns True."""
        aep.ensure_ai_engine_on_path()
        snapshot = list(sys.path)
        result = aep.ensure_ai_engine_on_path()
        assert result is True
        assert sys.path == snapshot

    def test_env_override_takes_precedence(self, tmp_path, monkeypatch):
        """AI_ENGINE_PATH env var beats the production and repo-root candidates."""
        override = tmp_path / "custom-ai-engine"
        override.mkdir()
        monkeypatch.setenv("AI_ENGINE_PATH", str(override))
        aep.reset_for_tests()
        ok = aep.ensure_ai_engine_on_path()
        assert ok is True
        assert override == aep._RESOLVED
        assert str(override) in sys.path

    def test_does_not_duplicate_path_entry(self):
        """If the dir is already on sys.path, don't add it again."""
        aep.ensure_ai_engine_on_path()
        resolved = str(aep._RESOLVED)
        first_count = sys.path.count(resolved)
        # Force re-resolution
        aep.reset_for_tests()
        aep.ensure_ai_engine_on_path()
        assert sys.path.count(resolved) == first_count

    def test_appends_path_instead_of_prepending_to_avoid_shadowing(self, tmp_path):
        """ai-engine must not shadow backend packages such as utils/schemas/models."""
        backend_src = tmp_path / "backend-src"
        ai_engine = tmp_path / "ai-engine"
        backend_src.mkdir()
        ai_engine.mkdir()
        sys.path[:] = [str(backend_src)]

        with patch.object(aep, "_candidate_paths", return_value=[ai_engine]):
            aep.reset_for_tests()
            ok = aep.ensure_ai_engine_on_path()

        assert ok is True
        assert sys.path == [str(backend_src), str(ai_engine)]

    def test_returns_false_when_no_candidate_resolves(self, tmp_path, monkeypatch):
        """All candidates missing → returns False, doesn't crash, doesn't pollute sys.path."""
        # Override env var to point at a missing dir
        missing = tmp_path / "does-not-exist"
        monkeypatch.setenv("AI_ENGINE_PATH", str(missing))
        # Patch the production and repo-root candidates to also miss
        with patch.object(aep, "_candidate_paths", return_value=[missing]):
            aep.reset_for_tests()
            snapshot = list(sys.path)
            ok = aep.ensure_ai_engine_on_path()
            assert ok is False
            assert sys.path == snapshot

    def test_repeated_failure_does_not_relog(self, tmp_path, monkeypatch, caplog):
        """After a failed attempt, subsequent calls return False without re-logging."""
        missing = tmp_path / "does-not-exist"
        with patch.object(aep, "_candidate_paths", return_value=[missing]):
            aep.reset_for_tests()
            with caplog.at_level("WARNING"):
                aep.ensure_ai_engine_on_path()
            warn_count_first = sum(
                1 for r in caplog.records if "ai-engine directory not found" in r.message
            )
            caplog.clear()
            with caplog.at_level("WARNING"):
                aep.ensure_ai_engine_on_path()
            warn_count_second = sum(
                1 for r in caplog.records if "ai-engine directory not found" in r.message
            )
            assert warn_count_first == 1
            assert warn_count_second == 0


class TestCandidatePaths:
    def test_includes_production_path(self):
        candidates = aep._candidate_paths()
        assert Path("/app/ai-engine") in candidates

    def test_includes_repo_root_relative(self):
        """The repo-root candidate is parents[3] / 'ai-engine' from this file."""
        candidates = aep._candidate_paths()
        # The expected repo-root candidate
        here = Path(aep.__file__).resolve()
        expected = here.parents[3] / "ai-engine"
        assert expected in candidates

    def test_env_override_first_when_set(self, monkeypatch, tmp_path):
        custom = tmp_path / "custom"
        monkeypatch.setenv("AI_ENGINE_PATH", str(custom))
        candidates = aep._candidate_paths()
        assert candidates[0] == custom
