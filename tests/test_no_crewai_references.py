"""Regression guard for the LangChain/LangGraph migration (issue #1201).

After the legacy multi-agent framework was removed, no tracked source
file should reference its name. Historical archives and the CHANGELOG
entry recording the migration are exempt; everything else is in scope.
"""

from __future__ import annotations

import subprocess
from pathlib import Path


# The literal token is built from two halves so this guard does not
# trip on its own source.
_NEEDLE = b"crew" + b"ai"

_EXEMPT_PREFIXES = (
    "docs/archive/",
    ".planning/archives/",
)
_EXEMPT_FILES = {
    "CHANGELOG.md",
    "tests/test_no_crewai_references.py",  # this very file
}


def test_no_legacy_framework_references_in_tracked_files():
    """No tracked source file may reference the legacy framework name."""
    proc = subprocess.run(
        ["git", "ls-files"],
        capture_output=True,
        text=True,
        check=True,
        cwd=Path(__file__).resolve().parent.parent,
    )
    paths = proc.stdout.splitlines()
    offenders = []
    for path in paths:
        if path in _EXEMPT_FILES:
            continue
        if any(path.startswith(prefix) for prefix in _EXEMPT_PREFIXES):
            continue
        try:
            data = (Path(__file__).resolve().parent.parent / path).read_bytes()
        except (OSError, IsADirectoryError):
            continue
        if _NEEDLE in data.lower():
            offenders.append(path)

    assert not offenders, "Legacy framework references remain in: " + ", ".join(offenders)
