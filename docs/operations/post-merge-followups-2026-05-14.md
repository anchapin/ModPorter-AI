# Post-Merge Manual Follow-Ups — 2026-05-14 Parallel-Issue-Workflow Batch

This document records the manual actions a maintainer must perform **after**
the three PRs from the 2026-05-14 parallel-issue-workflow batch are merged. It
is point-in-time; future batches should add their own dated file rather than
overwriting this one.

## Batch summary

| Issue | PR | Branch | Scope | Auto-closes issue? |
| --- | --- | --- | --- | --- |
| [#1437](https://github.com/anchapin/portkit/issues/1437) | [#1440](https://github.com/anchapin/portkit/pull/1440) | `fix/1437-trivy-sarif-permission` | `.github/workflows/ai-quality-gates.yml` (+3 / −0) | ✅ Closes #1437 |
| [#1438](https://github.com/anchapin/portkit/issues/1438) | [#1441](https://github.com/anchapin/portkit/pull/1441) | `ops/1438-fly-token-rotation-runbook` | `docs/operations/fly-token-rotation.md` (+277 / −0) | ⚠️ Manual rotation still required; issue remains open until verified |
| [#1439](https://github.com/anchapin/portkit/issues/1439) | [#1442](https://github.com/anchapin/portkit/pull/1442) | `fix/1439-langchain-langchain-openai-conflict` | `ai-engine/requirements.txt` (+7 / −3) | ✅ Closes #1439 |

All three branches were forked from `main @ accf7329` and have disjoint write
sets, so they could be merged in any order without conflicts. The order below
was chosen for safety, not for technical dependency.

## Actual merge outcome

| Order | PR | Merge commit | Result |
| --- | --- | --- | --- |
| 1 | [#1440](https://github.com/anchapin/portkit/pull/1440) | `eabbe6b4` | Landed the Trivy SARIF permissions fix; [#1437](https://github.com/anchapin/portkit/issues/1437) is closed. |
| 2 | [#1441](https://github.com/anchapin/portkit/pull/1441) | `6f1d5f4a` | Landed the Fly.io token rotation runbook; [#1438](https://github.com/anchapin/portkit/issues/1438) remains open because credential rotation is still manual. |
| 3 | [#1442](https://github.com/anchapin/portkit/pull/1442) | `0519803b` | Landed the `langchain` / `langchain-openai` dependency fix after all CI gates passed; [#1439](https://github.com/anchapin/portkit/issues/1439) is closed. |
| 4 | [#1443](https://github.com/anchapin/portkit/pull/1443) | `68fa6bbd` | Landed this dated follow-up checklist. |

After #1441 merged, GitHub briefly marked #1438 closed because the PR body
contained an auto-linking phrase that matched GitHub's issue-closing keyword
parser. The issue was reopened with an explanatory comment and should remain
open until the token rotation is performed and verified.

## Merge order used (with rationale)

1. **#1440 first** — fully green at submission; small (+3 / −0), additive,
   and reverses the only pre-existing failure on `ai-quality-gates.yml`. Lowest
   blast radius of the three.
2. **#1441 next** — documentation-only (+277 / −0). Only one CI job
   (`ai-engine-test`) was outstanding at submission; that job exercises the
   ai-engine test image which is unaffected by a docs-only diff. Merging this
   second makes the runbook canonically available before the maintainer needs
   it to act on the items in this file.
3. **#1442 last and only after all 9 originally-pending CI jobs reported green**.
   The critical gates were `build-python-base`, `ai-engine-test`,
   `Tests + Coverage (70% min)`, `Integration Tests (ai-engine|backend|integration)`,
   `Mutation Testing - Python (ai-engine)`, `Mutation Testing - Frontend`, and
   `Trivy Dependency Scan`. The `langchain 0.11.x → 0.193.x` jump crossed an API
   boundary; `pip` resolver convergence (proven locally) was not treated as
   enough proof of runtime compatibility. These checks passed before #1442 was
   merged.

## Manual ops follow-ups still required after merges

These actions could not be automated by the workflow worker because they
require live production credentials and have irreversible side effects.

### From PR #1441 (Fly.io token rotation, blocks #1438 closure)

A maintainer with **Fly.io org access** AND **`anchapin/portkit` repo-secret
write access** must:

1. **Mint a new token.** Per-app deploy tokens are preferred for least
   privilege:
   ```bash
   fly tokens create deploy --app portkit-backend-staging --expiry 168h
   fly tokens create deploy --app portkit-backend         --expiry 168h
   ```
   Or, if the workflow refactor (see "Deferred follow-ups" below) hasn't
   landed yet, mint a single org token instead:
   ```bash
   fly tokens create org <org-slug>
   ```
2. **Verify the new token works** before storing it:
   ```bash
   read -s -p "Paste new token: " NEW_TOKEN; echo
   FLY_API_TOKEN="$NEW_TOKEN" fly auth whoami
   ```
3. **Store it in GitHub Actions secrets** (do not echo the token to shell
   history):
   ```bash
   gh secret set FLY_API_TOKEN --repo anchapin/portkit --body "$NEW_TOKEN"
   unset NEW_TOKEN
   ```
   If using per-app tokens AND the workflow refactor has landed:
   ```bash
   gh secret set FLY_API_TOKEN_STAGING --repo anchapin/portkit --body "$STAGING_TOKEN"
   gh secret set FLY_API_TOKEN_PROD    --repo anchapin/portkit --body "$PROD_TOKEN"
   ```
4. **Re-trigger the deploy workflow** and confirm `Deploy to Fly.io` gets past
   auth:
   ```bash
   gh workflow run fly-deploy.yml --repo anchapin/portkit --ref main
   gh run watch --repo anchapin/portkit
   ```
5. **Mark [#1438](https://github.com/anchapin/portkit/issues/1438) done** once the
   first post-rotation run reaches the deploy step. The issue should stay open
   until this verification step is done by hand.
6. **Update the runbook's `Last rotated:` line** in a small follow-up PR. The
   current value in `docs/operations/fly-token-rotation.md` is
   `_never (initial runbook)_`.

The full procedure is in `docs/operations/fly-token-rotation.md` (lands with
PR #1441); this section is a check-the-box checklist.

> Note: the separate `ai-engine` dependency-resolution failure from #1439 was
> fixed by PR #1442. If deploys still fail before any build output appears, the
> remaining blocker is the Fly.io token authentication issue tracked by #1438.

## Deferred follow-ups (separate future PRs)

These were intentionally scoped out of the batch above to keep each PR small
and reviewable. They should be tracked as new issues if not already.

### A. `fly-deploy.yml` per-app secret refactor

Currently `.github/workflows/fly-deploy.yml` reads only `secrets.FLY_API_TOKEN`,
so per-app deploy tokens cannot be used until the workflow is refactored to
select a different secret per matrix entry. The intended shape (sketched in
the runbook) is:

```yaml
matrix:
  include:
    - environment: staging
      app_name: portkit-backend-staging
      token_secret_name: FLY_API_TOKEN_STAGING
    - environment: production
      app_name: portkit-backend
      token_secret_name: FLY_API_TOKEN_PROD

- name: Deploy to Fly.io
  uses: superfly/flyctl-actions@master
  env:
    # Prefer per-app token; fall back to legacy single token for backward compat.
    FLY_API_TOKEN: ${{ secrets[matrix.token_secret_name] || secrets.FLY_API_TOKEN }}
  with:
    args: "deploy --app ${{ matrix.app_name }} --remote-only"
```

The `secrets[matrix.x]` dynamic-indexing syntax is not guaranteed to evaluate
in every GitHub Actions context; the refactor must be validated on a
short-lived branch in a real runner before being landed on `main`. If
dynamic indexing fails in practice, fall back to two explicit `Deploy to
Fly.io` steps with `if:` matrix-environment guards and static secret names.

### B. `chromadb` bump to unlock `langchain 1.x`

`ai-engine/requirements.txt` currently pins `langchain>=0.140.0,<0.201.0` because
`langchain 0.201+` (and all `1.x`) declares `chromadb~=1.1.0`, which is mutually
exclusive with the existing `chromadb==1.5.8` hard pin. To pick up bug fixes
and features in `langchain 1.x`:

1. Audit the codebase for `chromadb` API usage that may have changed between
   `1.5.8` and the current `langchain 1.x` constraint band.
2. Lower-bound `chromadb` to whatever `langchain 1.x` declares (currently
   `~=1.1.0` per PyPI metadata for `langchain 1.14.4`).
3. Re-run `pip install --dry-run -r ai-engine/requirements.txt` and the
   ai-engine test suite to confirm no second-order conflicts (e.g. with
   `embedchain`, `langchain-*`, or the `opentelemetry-exporter-*` stack the
   file already calls out).
4. Bump `langchain` to `1.x` in the same PR.

### C. Update the `langchain` major-line — codebase audit

PR #1442 jumped `langchain` from `0.11.x` to `0.193.2`. The Agent / Task / Crew
constructor surface that `ai-engine/orchestration/langgraph_pipeline.py` and
`ai-engine/agents/rag_agents.py` rely on was structurally compatible based on
the `langchain 0.193.2` wheel inspection that informed the version pick, and the
critical CI gates passed before merge. If future runtime issues appear around
`Agent.__init__()`, `Task.__init__()`, `Crew.__init__()`, or `Process`, handle
them in a focused follow-up PR that adapts the call sites rather than mixing
that work into credential-rotation follow-ups.

## Source

- Generated by: 2026-05-14 parallel-issue-workflow run, post-merge follow-up summary.
- Worker agents: Dewey (#1437), Lorentz (#1438), Franklin (#1439).
- Base commit for all three branches: `accf7329`.
