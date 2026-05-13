"""
Path and log sanitization helpers.

Provides defense-in-depth against:
- ``py/path-injection`` (CWE-22, CWE-23, CWE-36, CWE-73, CWE-99)
- ``py/log-injection`` (CWE-117)

These helpers use **allow-list** validation (regex-restricted character sets)
so that downstream CodeQL flow analysis recognises them as effective
sanitizers when called between a user-controlled source and a filesystem or
logging sink.

Issue #1429: triage CodeQL alerts in ``conversions.py`` and
``behavioral_testing.py`` after the auth changes in PR #1426 added new
taint sources.
"""

from __future__ import annotations

import re
import uuid
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Maximum length of a sanitised log value. Defends against log-flooding from
#: oversized user inputs that pass other checks.
MAX_LOG_VALUE_LEN = 256

#: Marker appended when a log value is truncated.
LOG_TRUNCATION_MARKER = "...[truncated]"

# Allow-list for individual filesystem-path segments accepted by ``safe_join``.
# Allows letters, digits, underscore, dot, hyphen. Forbids '/', '\\', ':',
# whitespace and every control character. The standalone tokens '.' and '..'
# are rejected separately by ``safe_path_segment``.
_SAFE_PATH_SEGMENT_RE = re.compile(r"^[A-Za-z0-9._-]+$")

# Whitespace + control characters (0x00-0x1F, 0x7F) replaced inside log
# values. ``\r`` and ``\n`` are escaped earlier so this regex never sees
# them in the form that would create a forged log line.
_LOG_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class PathSanitizationError(ValueError):
    """Raised when input cannot be safely used as a filesystem path."""


# ---------------------------------------------------------------------------
# UUID validation
# ---------------------------------------------------------------------------


def validate_uuid(value: object) -> uuid.UUID:
    """Validate that ``value`` is a UUID and return it as :class:`uuid.UUID`.

    Accepts an existing :class:`uuid.UUID` or any string that
    :class:`uuid.UUID` can parse (canonical, hex, urn, braced).

    Raises:
        PathSanitizationError: if ``value`` is None / empty / not a UUID.
    """
    if value is None:
        raise PathSanitizationError("UUID value is required")
    if isinstance(value, uuid.UUID):
        return value
    text = str(value).strip()
    if not text:
        raise PathSanitizationError("UUID value is required")
    try:
        return uuid.UUID(text)
    except (ValueError, AttributeError, TypeError) as exc:
        raise PathSanitizationError("Value is not a valid UUID") from exc


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------


def safe_path_segment(segment: object) -> str:
    r"""Return ``segment`` unchanged if it is a safe single path component.

    A "safe segment" matches ``[A-Za-z0-9._-]+`` and is not the reserved
    relative-traversal token ``.`` or ``..``. This excludes path separators
    (``/`` and ``\\``), drive prefixes (``C:``), null bytes, newlines and
    every other ASCII control character.

    Raises:
        PathSanitizationError: if ``segment`` is None / empty / not a string
            / contains disallowed characters / is a reserved token.
    """
    if segment is None:
        raise PathSanitizationError("Path segment is required")
    if not isinstance(segment, str):
        raise PathSanitizationError(f"Path segment must be a string, got {type(segment).__name__}")
    if not segment:
        raise PathSanitizationError("Path segment must be non-empty")
    if segment in (".", ".."):
        raise PathSanitizationError(f"Reserved path segment: {segment!r}")
    if not _SAFE_PATH_SEGMENT_RE.match(segment):
        raise PathSanitizationError(f"Path segment contains disallowed characters: {segment!r}")
    return segment


def safe_join(base: str | Path, *parts: str) -> Path:
    """Securely join ``parts`` onto ``base`` and verify containment.

    Each part must individually satisfy :func:`safe_path_segment`. The
    final resolved path is then checked to be located inside the resolved
    ``base`` directory; any escape (via symlink, ``..``, absolute prefix
    or other trick) raises :class:`PathSanitizationError`.

    The base directory is resolved with ``Path.resolve()`` (which follows
    symlinks). The result is **not** required to exist on disk -- callers
    typically write to or create the returned path -- so ``strict=False``
    is used.

    Args:
        base: The allow-listed root directory. Must be an existing directory
            for symlink resolution to be meaningful, but this is not
            enforced here.
        *parts: One or more path segments. Each is validated independently.

    Returns:
        The resolved :class:`pathlib.Path`, guaranteed to be inside ``base``.

    Raises:
        PathSanitizationError: if any part is unsafe or the resolved path
            escapes ``base``.
    """
    if not parts:
        raise PathSanitizationError("safe_join requires at least one path part")
    base_path = Path(base).resolve()
    cleaned = [safe_path_segment(part) for part in parts]
    candidate = base_path.joinpath(*cleaned).resolve()
    try:
        candidate.relative_to(base_path)
    except ValueError as exc:  # pragma: no cover - exercised by tests
        raise PathSanitizationError(
            f"Resolved path escapes base directory: {candidate!r} not under {base_path!r}"
        ) from exc
    return candidate


# ---------------------------------------------------------------------------
# Log helpers
# ---------------------------------------------------------------------------


def sanitize_for_log(value: object, *, max_len: int = MAX_LOG_VALUE_LEN) -> str:
    r"""Return a string representation of ``value`` safe to embed in a log line.

    Specifically:

    * ``None`` becomes the literal ``"<none>"``.
    * Carriage return / newline are escaped as the two-char sequences
      ``\\r`` / ``\\n`` so an attacker cannot forge new log lines.
    * Other ASCII control characters (NUL, BEL, ESC, DEL, ...) are replaced
      with ``?``.
    * Values longer than ``max_len`` characters are truncated and marked
      with :data:`LOG_TRUNCATION_MARKER`.

    The output is always a ``str`` and never raises.

    Args:
        value: Any object; ``str(value)`` is used as the starting point.
        max_len: Maximum length of the returned string (excluding marker).
            Defaults to :data:`MAX_LOG_VALUE_LEN`.
    """
    if value is None:
        return "<none>"
    try:
        text = str(value)
    except Exception:  # noqa: BLE001 - defensive: never raise from logging
        text = f"<unrepresentable {type(value).__name__}>"
    text = text.replace("\r", "\\r").replace("\n", "\\n")
    text = _LOG_CONTROL_CHARS_RE.sub("?", text)
    if len(text) > max_len:
        text = text[:max_len] + LOG_TRUNCATION_MARKER
    return text


__all__ = [
    "LOG_TRUNCATION_MARKER",
    "MAX_LOG_VALUE_LEN",
    "PathSanitizationError",
    "safe_join",
    "safe_path_segment",
    "sanitize_for_log",
    "validate_uuid",
]
