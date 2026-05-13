"""Unit tests for ``security.path_sanitization``.

Issue #1429.

Coverage areas:

- ``safe_path_segment``: traversal tokens, separators, control chars,
  non-strings, empty/None inputs, accepted patterns.
- ``safe_join``: containment guarantees, traversal attempts via ``..``,
  absolute paths outside allow-list, symlink escape, empty parts.
- ``validate_uuid``: valid UUID-strings, ``uuid.UUID`` instances, malformed
  strings, ``None``, non-string objects.
- ``sanitize_for_log``: CR/LF escaping, ASCII control chars, ``None``,
  truncation of oversized values, idempotent behaviour for safe values.
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path

import pytest

from security.path_sanitization import (
    LOG_TRUNCATION_MARKER,
    MAX_LOG_VALUE_LEN,
    PathSanitizationError,
    safe_join,
    safe_path_segment,
    sanitize_for_log,
    validate_uuid,
)


# ---------------------------------------------------------------------------
# safe_path_segment
# ---------------------------------------------------------------------------


class TestSafePathSegment:
    """Allow-list validation for individual path segments."""

    @pytest.mark.parametrize(
        "value",
        [
            "file.txt",
            "abc-DEF_123",
            "1234abcd-5678-90ef-1234-567890abcdef",
            "chunk_0001",
            "report.html",
            "a",
        ],
    )
    def test_accepts_safe_segments(self, value):
        assert safe_path_segment(value) == value

    @pytest.mark.parametrize("value", ["", None])
    def test_rejects_empty_or_none(self, value):
        with pytest.raises(PathSanitizationError):
            safe_path_segment(value)

    @pytest.mark.parametrize("value", [".", ".."])
    def test_rejects_reserved_traversal_tokens(self, value):
        with pytest.raises(PathSanitizationError, match="Reserved"):
            safe_path_segment(value)

    @pytest.mark.parametrize(
        "value",
        [
            "../etc/passwd",
            "..\\windows",
            "..",
            "foo/bar",
            "foo\\bar",
            "/abs/path",
            "C:\\Users",
            "with space",
            "with\ttab",
            "new\nline",
            "carriage\rreturn",
            "null\x00byte",
            "esc\x1bseq",
            "del\x7fchar",
            "URL%2eencoded",
            "smart‐dash",  # non-ASCII
            "emoji😀",
        ],
    )
    def test_rejects_unsafe_segments(self, value):
        with pytest.raises(PathSanitizationError):
            safe_path_segment(value)

    def test_rejects_non_string_input(self):
        with pytest.raises(PathSanitizationError, match="must be a string"):
            safe_path_segment(123)
        with pytest.raises(PathSanitizationError, match="must be a string"):
            safe_path_segment(b"file.txt")
        with pytest.raises(PathSanitizationError, match="must be a string"):
            safe_path_segment(Path("file.txt"))


# ---------------------------------------------------------------------------
# safe_join
# ---------------------------------------------------------------------------


class TestSafeJoin:
    """End-to-end containment tests for ``safe_join``."""

    def test_joins_simple_segments(self, tmp_path):
        result = safe_join(tmp_path, "chunks", "chunk_0001")
        assert result == (tmp_path / "chunks" / "chunk_0001").resolve()
        assert str(result).startswith(str(tmp_path.resolve()))

    def test_returns_absolute_resolved_path(self, tmp_path):
        result = safe_join(tmp_path, "a")
        assert result.is_absolute()

    def test_does_not_require_path_to_exist(self, tmp_path):
        # Defines the canonical location for a future write; the file does
        # not yet exist on disk.
        result = safe_join(tmp_path, "future_file.zip")
        assert not result.exists()
        assert result.parent == tmp_path.resolve()

    def test_rejects_traversal_segment(self, tmp_path):
        with pytest.raises(PathSanitizationError):
            safe_join(tmp_path, "..", "etc")

    def test_rejects_dot_dot_in_segment(self, tmp_path):
        with pytest.raises(PathSanitizationError):
            safe_join(tmp_path, "..\\..\\etc\\passwd")

    def test_rejects_absolute_path_in_segment(self, tmp_path):
        with pytest.raises(PathSanitizationError):
            safe_join(tmp_path, "/etc/passwd")

    def test_rejects_path_separators_in_segment(self, tmp_path):
        with pytest.raises(PathSanitizationError):
            safe_join(tmp_path, "chunks/chunk_0001")

    def test_rejects_empty_parts_list(self, tmp_path):
        with pytest.raises(PathSanitizationError, match="at least one"):
            safe_join(tmp_path)

    def test_rejects_empty_segment(self, tmp_path):
        with pytest.raises(PathSanitizationError):
            safe_join(tmp_path, "")

    def test_rejects_none_segment(self, tmp_path):
        with pytest.raises(PathSanitizationError):
            safe_join(tmp_path, None)

    def test_rejects_control_char_segment(self, tmp_path):
        with pytest.raises(PathSanitizationError):
            safe_join(tmp_path, "chunk\x00.bin")

    def test_rejects_symlink_escape(self, tmp_path):
        # Create a legitimate base dir and a symlink that points outside it.
        # safe_join should refuse to follow the symlink to escape the root.
        base = tmp_path / "base"
        base.mkdir()
        outside = tmp_path / "outside"
        outside.mkdir()
        link = base / "link"
        try:
            link.symlink_to(outside, target_is_directory=True)
        except (OSError, NotImplementedError):
            pytest.skip("Symlink creation not permitted on this platform")

        with pytest.raises(PathSanitizationError):
            # The segment "link" is allow-listed by name, but resolve()
            # follows it, and the resulting absolute path is outside ``base``.
            safe_join(base, "link", "secret")

    def test_accepts_string_base(self, tmp_path):
        result = safe_join(str(tmp_path), "ok")
        assert result == (tmp_path / "ok").resolve()

    def test_uuid_str_is_accepted_segment(self, tmp_path):
        # The most common real-world usage: the UUID-string from a Pydantic
        # ``UUID`` parameter.
        upload_id = "1234abcd-5678-90ef-1234-567890abcdef"
        result = safe_join(tmp_path, "chunks", upload_id)
        assert result.parent.name == "chunks"


# ---------------------------------------------------------------------------
# validate_uuid
# ---------------------------------------------------------------------------


class TestValidateUuid:
    def test_accepts_canonical_uuid_string(self):
        s = "12345678-1234-5678-1234-567812345678"
        result = validate_uuid(s)
        assert isinstance(result, uuid.UUID)
        assert str(result) == s

    def test_accepts_uuid_instance(self):
        u = uuid.uuid4()
        assert validate_uuid(u) is u

    def test_accepts_hex_uuid(self):
        # uuid.UUID accepts the 32-char hex form too.
        assert isinstance(validate_uuid("12345678123456781234567812345678"), uuid.UUID)

    def test_rejects_none(self):
        with pytest.raises(PathSanitizationError, match="required"):
            validate_uuid(None)

    def test_rejects_empty_string(self):
        with pytest.raises(PathSanitizationError, match="required"):
            validate_uuid("")
        with pytest.raises(PathSanitizationError, match="required"):
            validate_uuid("   ")

    @pytest.mark.parametrize(
        "value",
        [
            "not-a-uuid",
            "12345678-1234-5678-1234",  # too short
            "../../etc/passwd",
            "abcdefgh-1234-5678-1234-567812345678",  # non-hex
            123,
            object(),
        ],
    )
    def test_rejects_invalid_inputs(self, value):
        with pytest.raises(PathSanitizationError):
            validate_uuid(value)


# ---------------------------------------------------------------------------
# sanitize_for_log
# ---------------------------------------------------------------------------


class TestSanitizeForLog:
    def test_simple_string_passes_through(self):
        assert sanitize_for_log("hello") == "hello"

    def test_uuid_passes_through(self):
        u = uuid.uuid4()
        assert sanitize_for_log(u) == str(u)

    def test_none_becomes_marker(self):
        assert sanitize_for_log(None) == "<none>"

    def test_escapes_newline(self):
        out = sanitize_for_log("line1\nline2")
        assert "\n" not in out
        assert "\\n" in out

    def test_escapes_carriage_return(self):
        out = sanitize_for_log("a\rb")
        assert "\r" not in out
        assert "\\r" in out

    def test_log_forgery_attempt_is_neutralised(self):
        # Classic CWE-117 payload: terminate the legitimate line and forge
        # a new one with a fake "INFO" level.
        attack = "Guest\r\nINFO: User name: Admin"
        out = sanitize_for_log(attack)
        assert "\r\n" not in out
        assert "\\r\\n" in out

    @pytest.mark.parametrize("ch", ["\x00", "\x07", "\x1b", "\x7f"])
    def test_replaces_other_control_chars(self, ch):
        out = sanitize_for_log(f"a{ch}b")
        assert ch not in out
        assert "?" in out

    def test_truncates_oversize_values(self):
        long = "x" * (MAX_LOG_VALUE_LEN + 50)
        out = sanitize_for_log(long)
        assert out.endswith(LOG_TRUNCATION_MARKER)
        assert len(out) == MAX_LOG_VALUE_LEN + len(LOG_TRUNCATION_MARKER)

    def test_respects_custom_max_len(self):
        out = sanitize_for_log("0123456789", max_len=4)
        assert out == "0123" + LOG_TRUNCATION_MARKER

    def test_handles_non_string_value(self):
        assert sanitize_for_log(42) == "42"
        assert sanitize_for_log(3.14) == "3.14"

    def test_handles_unrepresentable_object(self):
        class Boom:
            def __str__(self):
                raise RuntimeError("nope")

        out = sanitize_for_log(Boom())
        assert "<unrepresentable" in out
        assert "Boom" in out


# ---------------------------------------------------------------------------
# Cross-cutting: realistic end-to-end usage matching the api/ call sites
# ---------------------------------------------------------------------------


class TestRealisticUsage:
    """Smoke tests that mirror how ``conversions.py`` invokes the helpers."""

    def test_upload_chunks_dir_pattern(self, tmp_path):
        upload_id = uuid.uuid4()
        chunks_dir = safe_join(tmp_path, "chunks", str(upload_id))
        chunks_dir.mkdir(parents=True)
        chunk_path = safe_join(chunks_dir, f"chunk_{1:04d}")
        chunk_path.write_bytes(b"data")
        assert chunk_path.exists()
        assert chunk_path.parent == chunks_dir

    def test_download_path_pattern(self, tmp_path):
        # Caller already validated the conversion_id as UUID and confirmed
        # ownership.
        conv_id = "00000000-0000-4000-8000-000000000001"
        validated = validate_uuid(conv_id)
        artifact = safe_join(tmp_path, f"{validated}_converted.mcaddon")
        artifact.write_bytes(b"x")
        assert artifact.exists()

    def test_download_rejects_path_separator_in_id(self, tmp_path):
        with pytest.raises(PathSanitizationError):
            safe_join(tmp_path, "../etc/passwd_converted.mcaddon")

    def test_log_line_with_tainted_websocket_text(self):
        attacker = "ping\r\nERROR: forged"
        line = (
            f"WS message for conv {sanitize_for_log('aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee')}: "
            f"{sanitize_for_log(attacker)}"
        )
        assert "\n" not in line
        assert "ERROR:" in line  # text retained, but on a single line
        assert "\\r\\n" in line


# Sanity check that the module path is importable with the project's
# ``pythonpath = src`` pytest config (declared in backend/pytest.ini).
def test_module_is_importable_via_src_layout():
    import security.path_sanitization as mod

    assert mod.__name__ == "security.path_sanitization"
    assert os.path.isfile(mod.__file__)
