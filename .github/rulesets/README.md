# Repository Rulesets — codified

This directory codifies the GitHub repository rulesets that protect this repo's
branches, so that future changes go through normal PR review instead of being
silent UI edits. It exists because of [Issue #1472][i1472]: the GitHub Rulesets
API rejected updates to the `Main` ruleset due to stale Integration bypass
actors that the API could no longer validate, and there was no codified record
of what the desired state actually was.

[i1472]: https://github.com/anchapin/portkit/issues/1472

## Files

| File | Purpose |
|---|---|
| [`main.json`](./main.json) | Desired state of the `Main` ruleset (protects the default branch). The single source of truth. |
| [`sync.py`](./sync.py) | CLI tool: `normalize` (sanitize raw API output), `diff` (compare on-disk vs. live), `apply` (push on-disk to GitHub). |
| [`../workflows/ruleset-drift.yml`](../workflows/ruleset-drift.yml) | Scheduled drift detector (opt-in via `vars.ENABLE_RULESET_DRIFT_CHECK`). |

## What each `main.json` field means

The on-disk JSON is the **deterministic, intent-only** form: every field that
varies per fetch (`id`, `node_id`, `created_at`, `updated_at`, `_links`,
`current_user_can_bypass`, `source`, `source_type`) is stripped, and every list
whose order does not affect enforcement is sorted. This means a fresh export
will diff cleanly against the committed file when the live state matches.

Currently committed state (matches the resolution recorded in #1472):

- **Target**: default branch (`~DEFAULT_BRANCH`)
- **Required status check**: `PR Gates`
- **Pull-request rule**: 1 approving review required, dismiss stale reviews on
  push, require thread resolution, all merge methods allowed
- **Other rules**: deletion / non-fast-forward / creation blocked, Copilot code
  review (off by default, off for drafts)
- **Bypass actors**: `RepositoryRole#5` (Admin role) with `bypass_mode: always`
  — no GitHub Apps. This is the same single bypass that #1472 settled on after
  the stale Integration actors were removed.

## How to change the ruleset (the ONLY supported workflow)

1. **Edit `main.json` in a PR.** Make the change you want — add a required
   check, raise the approval count, add or remove bypass actors, etc.
2. **Open the PR.** Reviewers can see exactly what's changing because the file
   is normalized and stable.
3. **Merge.** A repo admin runs `apply` from a checkout of `main`:

   ```bash
   python3 .github/rulesets/sync.py apply .github/rulesets/main.json
   ```

   Add `--dry-run` to print the request body without sending. Requires `gh auth`
   to a token with `repo` admin scope on `anchapin/portkit`.

> [!IMPORTANT]
> `apply` is **not** automated in CI. Pushing rulesets needs admin scope on the
> repo, and we do not want a workflow with that scope running on every merge to
> `main`. Manual application is intentional and friction-light.

## How to detect drift

Drift = "someone edited the ruleset directly in the GitHub UI without updating
this file". Two ways to catch it:

### Local one-off check

```bash
python3 .github/rulesets/sync.py diff .github/rulesets/main.json
```

Exit codes: `0` in sync, `1` drift detected (prints unified diff), `2` ruleset
of that name not found on GitHub.

### Scheduled GitHub Actions check (opt-in)

The workflow [`ruleset-drift.yml`](../workflows/ruleset-drift.yml) runs the same
`diff` weekly and on `workflow_dispatch`. It is **opt-in** — schedule runs are
gated on the repo variable `ENABLE_RULESET_DRIFT_CHECK == 'true'` so it doesn't
add noise until someone wants the alert. Manual dispatch always runs.

To enable: Settings → Secrets and variables → Actions → Variables → set
`ENABLE_RULESET_DRIFT_CHECK = true`.

## How to bootstrap a new ruleset file

If GitHub adds a new ruleset and we want to codify it:

```bash
# 1. Find the ID
gh api repos/anchapin/portkit/rulesets

# 2. Fetch the raw JSON
gh api repos/anchapin/portkit/rulesets/<id> > /tmp/raw.json

# 3. Normalize it into the repo
python3 .github/rulesets/sync.py normalize \
    --from-file /tmp/raw.json \
    --output .github/rulesets/<short-name>.json

# 4. Commit + open a PR
```

## Limitations and intentional non-features

- **`sync.py` only handles a single ruleset per file by name.** `apply` looks up
  the existing ruleset on GitHub by `name` and either `PUT`s an update or
  `POST`s a create. It does **not** delete rulesets that exist on GitHub but
  not on disk — drift in that direction is detected by `diff` but never acted
  on automatically.
- **The numeric ruleset ID is intentionally not stored on disk.** It is volatile
  (changes if the ruleset is deleted and recreated) and would create spurious
  diffs.
- **There is no Terraform or Probot.** The repo doesn't otherwise manage GitHub
  resources as code. A 280-line Python script + JSON is the smallest tool that
  solves the original problem (no codified record of the ruleset).
