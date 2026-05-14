"""Make the ai-engine package importable from the backend process.

The ai-engine and backend are deployed in the same Docker image but as separate
Python processes with separate PYTHONPATHs. The backend's PYTHONPATH does NOT
include /app/ai-engine, but several backend endpoints and Celery tasks
nonetheless import from the AI Engine's flat-top-level packages
(`mmsd.*`, `knowledge.*`, etc.) — historical decisions that bypass
the intended HTTP service boundary. Only non-colliding top-level packages are
safe to import this way; `utils.*`, `models.*`, `schemas.*`, and `services.*`
collide with backend packages and must be migrated to HTTP calls instead.

This helper appends ai-engine to sys.path on demand. It tries (in order):

1. ``$AI_ENGINE_PATH`` env var — explicit override
2. ``/app/ai-engine`` — production layout (Fly.io ``Dockerfile.fly`` copies
   ai-engine here)
3. Repo-root-relative path walking up from this file — local-dev / pytest layout

If none resolve to an existing directory, it returns False and lets the
caller's import raise its own ImportError (which carries a clearer message
than anything we could fabricate).

This is a tactical fix for the import-resolution bug surfaced by
PR #1448 (`refactor(ai-engine): consolidate ai_engine/ namespace`). The
strategic fix is to convert these direct imports into HTTP calls against
the AI Engine service running on a separate process. See
``.planning/notes/2026-05-14-followups.md`` Item 8.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# Memoize the resolved path so we only compute / log once per process.
_RESOLVED: Path | None = None
_RESOLVED_ATTEMPTED: bool = False


def _candidate_paths() -> list[Path]:
    """Yield candidate ai-engine directory locations in priority order."""
    candidates: list[Path] = []

    env_override = os.environ.get("AI_ENGINE_PATH")
    if env_override:
        candidates.append(Path(env_override))

    # Production layout (Fly.io Dockerfile.fly: COPY ai-engine/ /app/ai-engine/)
    candidates.append(Path("/app/ai-engine"))

    # Local-dev / pytest layout: walk up from backend/src/utils/ai_engine_path.py
    #   parent[0] = backend/src/utils/
    #   parent[1] = backend/src/
    #   parent[2] = backend/
    #   parent[3] = repo root
    here = Path(__file__).resolve()
    candidates.append(here.parents[3] / "ai-engine")

    return candidates


def ensure_ai_engine_on_path() -> bool:
    """Ensure the ai-engine package directory is on sys.path.

    Returns:
        True if a usable ai-engine directory was found and added (or was
        already present); False if no candidate resolved.

    Idempotent: safe to call multiple times. The first successful call
    memoizes the result; subsequent calls are O(1).
    """
    global _RESOLVED, _RESOLVED_ATTEMPTED

    if _RESOLVED is not None:
        return True

    if _RESOLVED_ATTEMPTED:
        # We tried before and failed; don't keep trying / re-logging.
        return False

    for candidate in _candidate_paths():
        if candidate.is_dir():
            candidate_str = str(candidate)
            if candidate_str not in sys.path:
                # Append instead of prepending. Prepending would let ai-engine
                # shadow backend packages with the same top-level names
                # (`utils`, `models`, `schemas`, `services`) for the remainder
                # of the worker process. Appending still makes non-colliding
                # packages such as `mmsd` and `knowledge` importable.
                sys.path.append(candidate_str)
                logger.info("ai-engine appended to sys.path: %s", candidate_str)
            else:
                logger.debug("ai-engine already on sys.path: %s", candidate_str)
            _RESOLVED = candidate
            return True

    _RESOLVED_ATTEMPTED = True
    logger.warning(
        "ai-engine directory not found at any candidate path: %s. "
        "Imports of non-colliding ai-engine packages from backend code will fail. "
        "Set AI_ENGINE_PATH env var to override.",
        [str(p) for p in _candidate_paths()],
    )
    return False


def reset_for_tests() -> None:
    """Clear memoized state. Test-only helper."""
    global _RESOLVED, _RESOLVED_ATTEMPTED
    _RESOLVED = None
    _RESOLVED_ATTEMPTED = False
