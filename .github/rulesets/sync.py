#!/usr/bin/env python3
"""GitHub repository ruleset codification tool (Issue #1472).

Subcommands
-----------
* ``normalize`` — read a raw ruleset JSON (e.g. from ``gh api repos/.../rulesets/<id>``)
  on stdin or via ``--from-file`` and write a deterministic, intent-only form to
  stdout (or to ``--output``). Strips computed/volatile fields (``id``, ``node_id``,
  ``_links``, ``created_at``, ``updated_at``, ``current_user_can_bypass``,
  ``source``, ``source_type``) and sorts every list whose order is not semantically
  meaningful, so that ``git diff`` shows real intent only.

* ``diff`` — fetch the live ruleset by name from the GitHub API, normalize it,
  and ``diff`` it against the on-disk file. Exit 0 = in sync, 1 = drift detected,
  2 = ruleset of that name not found on GitHub.

* ``apply`` — push the on-disk file back to GitHub. Looks up the existing
  ruleset by name (so the on-disk file does not need to embed the volatile
  numeric ``id``); creates a new one if no match is found. Use ``--dry-run`` to
  print the request body without sending.

Auth: requires ``GH_TOKEN`` (or ``GITHUB_TOKEN``) with ``repo`` admin scope, or a
working ``gh auth`` session.

Why this exists: see Issue #1472 — the GitHub Rulesets UI silently rejects
ruleset-API updates when stale Integration bypass actors are present. Codifying
the ruleset to the repo lets future changes go through normal PR review and
makes drift visible.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Fields that vary per fetch but carry no intent. Stripping them keeps the
# on-disk JSON stable across re-exports.
# ---------------------------------------------------------------------------
_VOLATILE_TOP_LEVEL_FIELDS = frozenset(
    {
        "id",
        "node_id",
        "_links",
        "created_at",
        "updated_at",
        "current_user_can_bypass",
        "source",
        "source_type",
    }
)


def _sort_strings(values: list[str] | None) -> list[str]:
    return sorted(values) if values else []


def _sort_dicts_by_keys(
    values: list[dict[str, Any]] | None, keys: tuple[str, ...]
) -> list[dict[str, Any]]:
    if not values:
        return []
    return sorted(values, key=lambda d: tuple(json.dumps(d.get(k), sort_keys=True) for k in keys))


def _normalize_rules(rules: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """Sort rules deterministically and normalize their parameters."""
    if not rules:
        return []
    out: list[dict[str, Any]] = []
    for rule in rules:
        copy = json.loads(json.dumps(rule, sort_keys=True))
        params = copy.get("parameters")
        if isinstance(params, dict):
            # required_status_checks: sort the contexts list
            checks = params.get("required_status_checks")
            if isinstance(checks, list):
                params["required_status_checks"] = _sort_dicts_by_keys(
                    checks, ("context", "integration_id")
                )
            # allowed_merge_methods: sort
            merges = params.get("allowed_merge_methods")
            if isinstance(merges, list):
                params["allowed_merge_methods"] = _sort_strings(merges)
            # required_reviewers: sort
            reviewers = params.get("required_reviewers")
            if isinstance(reviewers, list):
                params["required_reviewers"] = _sort_dicts_by_keys(
                    reviewers, ("reviewer_type", "reviewer_id")
                )
        out.append(copy)
    out.sort(
        key=lambda r: (r.get("type", ""), json.dumps(r.get("parameters") or {}, sort_keys=True))
    )
    return out


def _normalize_conditions(conditions: dict[str, Any] | None) -> dict[str, Any]:
    if not conditions:
        return {}
    out = json.loads(json.dumps(conditions, sort_keys=True))
    ref = out.get("ref_name")
    if isinstance(ref, dict):
        ref["include"] = _sort_strings(ref.get("include"))
        ref["exclude"] = _sort_strings(ref.get("exclude"))
    return out


def _normalize_bypass_actors(actors: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    return _sort_dicts_by_keys(actors, ("actor_type", "actor_id", "bypass_mode"))


def normalize_ruleset(raw: dict[str, Any]) -> dict[str, Any]:
    """Return a deterministic, intent-only copy of ``raw``."""
    out: dict[str, Any] = {}
    for k, v in raw.items():
        if k in _VOLATILE_TOP_LEVEL_FIELDS:
            continue
        out[k] = v
    out["conditions"] = _normalize_conditions(out.get("conditions"))
    out["rules"] = _normalize_rules(out.get("rules"))
    out["bypass_actors"] = _normalize_bypass_actors(out.get("bypass_actors"))
    return out


# ---------------------------------------------------------------------------
# GitHub API plumbing — uses the `gh` CLI so we get auth handling for free.
# ---------------------------------------------------------------------------
def _gh(
    *args: str, input_bytes: bytes | None = None, check: bool = True
) -> subprocess.CompletedProcess[bytes]:
    if shutil.which("gh") is None:
        raise SystemExit("error: the `gh` CLI is required (install from https://cli.github.com/)")
    return subprocess.run(
        ["gh", *args],
        input=input_bytes,
        capture_output=True,
        check=check,
    )


def _list_rulesets(repo: str) -> list[dict[str, Any]]:
    res = _gh("api", f"repos/{repo}/rulesets")
    return json.loads(res.stdout.decode("utf-8") or "[]")


def _get_ruleset(repo: str, ruleset_id: int) -> dict[str, Any]:
    res = _gh("api", f"repos/{repo}/rulesets/{ruleset_id}")
    return json.loads(res.stdout.decode("utf-8"))


def _find_ruleset_id_by_name(repo: str, name: str) -> int | None:
    for rs in _list_rulesets(repo):
        if rs.get("name") == name:
            return int(rs["id"])
    return None


def _fetch_normalized(repo: str, name: str) -> dict[str, Any] | None:
    ruleset_id = _find_ruleset_id_by_name(repo, name)
    if ruleset_id is None:
        return None
    return normalize_ruleset(_get_ruleset(repo, ruleset_id))


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------
def cmd_normalize(args: argparse.Namespace) -> int:
    if args.from_file:
        raw = json.loads(Path(args.from_file).read_text())
    else:
        raw = json.loads(sys.stdin.read())
    normalized = normalize_ruleset(raw)
    text = json.dumps(normalized, indent=2, sort_keys=True) + "\n"
    if args.output:
        Path(args.output).write_text(text)
    else:
        sys.stdout.write(text)
    return 0


def cmd_diff(args: argparse.Namespace) -> int:
    on_disk_text = Path(args.file).read_text()
    on_disk = json.loads(on_disk_text)
    name = on_disk.get("name")
    if not name:
        sys.stderr.write(f"error: {args.file} is missing a top-level 'name' field\n")
        return 2
    live = _fetch_normalized(args.repo, name)
    if live is None:
        sys.stderr.write(f"error: no ruleset named {name!r} found on {args.repo}\n")
        return 2
    on_disk_norm = normalize_ruleset(on_disk)
    a = json.dumps(on_disk_norm, indent=2, sort_keys=True).splitlines(keepends=True)
    b = json.dumps(live, indent=2, sort_keys=True).splitlines(keepends=True)
    if a == b:
        print(f"in sync: {args.repo} ruleset {name!r} matches {args.file}")
        return 0
    import difflib

    diff = difflib.unified_diff(
        a, b, fromfile=f"a/{args.file}", tofile=f"b/live ({args.repo}::{name})"
    )
    sys.stdout.writelines(diff)
    sys.stderr.write(f"\ndrift detected: {args.repo} ruleset {name!r} differs from {args.file}\n")
    return 1


def cmd_apply(args: argparse.Namespace) -> int:
    on_disk = json.loads(Path(args.file).read_text())
    name = on_disk.get("name")
    if not name:
        sys.stderr.write(f"error: {args.file} is missing a top-level 'name' field\n")
        return 2
    body = normalize_ruleset(on_disk)
    body_bytes = json.dumps(body).encode("utf-8")

    ruleset_id = _find_ruleset_id_by_name(args.repo, name)
    if ruleset_id is None:
        method = "POST"
        endpoint = f"repos/{args.repo}/rulesets"
        action = f"create new ruleset {name!r}"
    else:
        method = "PUT"
        endpoint = f"repos/{args.repo}/rulesets/{ruleset_id}"
        action = f"update ruleset {name!r} (id={ruleset_id})"

    if args.dry_run:
        print(f"[dry-run] would {action} via {method} {endpoint}")
        print(f"[dry-run] body ({len(body_bytes)} bytes):")
        print(json.dumps(body, indent=2, sort_keys=True))
        return 0

    print(f"applying: {action} via {method} {endpoint}")
    res = _gh(
        "api",
        "--method",
        method,
        endpoint,
        "--input",
        "-",
        input_bytes=body_bytes,
        check=False,
    )
    if res.returncode != 0:
        sys.stderr.write(res.stderr.decode("utf-8"))
        return res.returncode
    print(res.stdout.decode("utf-8"))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_norm = sub.add_parser("normalize", help="strip volatile fields and sort lists")
    p_norm.add_argument("--from-file", help="read raw JSON from this file (default: stdin)")
    p_norm.add_argument("--output", help="write to this file (default: stdout)")
    p_norm.set_defaults(func=cmd_normalize)

    repo_default = os.environ.get("GITHUB_REPOSITORY", "anchapin/portkit")

    p_diff = sub.add_parser("diff", help="diff on-disk ruleset against the live one on GitHub")
    p_diff.add_argument("file", help="path to the on-disk ruleset JSON")
    p_diff.add_argument(
        "--repo", default=repo_default, help=f"OWNER/REPO (default: {repo_default})"
    )
    p_diff.set_defaults(func=cmd_diff)

    p_apply = sub.add_parser("apply", help="push the on-disk ruleset to GitHub")
    p_apply.add_argument("file", help="path to the on-disk ruleset JSON")
    p_apply.add_argument(
        "--repo", default=repo_default, help=f"OWNER/REPO (default: {repo_default})"
    )
    p_apply.add_argument(
        "--dry-run", action="store_true", help="print the request body without sending"
    )
    p_apply.set_defaults(func=cmd_apply)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
