# Coverage Policy & Ratchet Plan

> **Status**: active as of 2026-05.
> **Owners**: CI / Platform.
> **Source of truth for thresholds**: [`.github/workflows/pr.yml`](../../.github/workflows/pr.yml) (`env.COVERAGE_FLOOR_BACKEND`, `env.COVERAGE_FLOOR_AI_ENGINE`).

This document explains **why** the CI-enforced coverage floors do not match the
"80%+" target stated in `AGENTS.md` historically, and **how** we close that gap
over time without flipping coverage from a useful signal into a blocker that
gets routinely bypassed.

---

## TL;DR

| Component   | Enforced floor (CI-blocking) | Aspirational target |
|-------------|------------------------------|---------------------|
| `backend`   | **40%**                      | 80%                 |
| `ai-engine` | **65%**                      | 80%                 |
| `frontend`  | not enforced (vitest run, no `--coverage` gate) | 80% |

The floors are the **minimum** a PR must keep coverage at to merge. They are
not the goal — they are the worst we are willing to ship today. The ratchet
plan below moves them upward toward the 80% target on a predictable cadence.

---

## Why a floor instead of a single target?

A single hard target of 80% has historically led to one of three outcomes in
this repo:

1. **The number is bypassed.** Reviewers wave PRs through with
   `--cov-fail-under=0`-style overrides because the threshold is unrealistic
   for the current code shape. Coverage stops being a gate.
2. **PRs add throwaway tests** to satisfy the percentage without exercising
   real behaviour. Coverage goes up; quality does not.
3. **Coverage-improvement work gets blocked** because the very PR that adds
   tests to a previously-untested module temporarily *lowers* the global
   percentage (denominator grows faster than the numerator on the first
   commit), so the gate fails.

A **floor + ratchet** model avoids all three: the floor is set just below
current measured coverage, so ordinary PRs pass; the ratchet schedule
documents exactly when and how the floor moves up; lowering the floor is
deliberately friction-heavy so it is not the path of least resistance.

---

## Current enforced thresholds

These are the values enforced today in CI via `pytest --cov-fail-under`:

```yaml
# .github/workflows/pr.yml
env:
  COVERAGE_FLOOR_BACKEND: '40'      # backend/src
  COVERAGE_FLOOR_AI_ENGINE: '65'    # ai-engine
```

If a PR drops coverage below these, the `backend-tests` / `ai-engine-tests`
job fails, which fails the `PR Gates` aggregator, which blocks merge.

---

## Ratchet milestones

The plan is to walk the floors upward in fixed steps, re-evaluating actual
coverage between each step. **The milestones below are the *target floors*,
not the dates** — we promote when the codebase is sustainably above the next
milestone, not on a calendar.

### Backend (`backend/src`)

| Milestone | Floor | Promotion criterion (see "Cadence") |
|-----------|-------|-------------------------------------|
| M0 (today)| 40%   | baseline                            |
| M1        | 50%   | sustained ≥55% on `main` for ≥4 weeks |
| M2        | 60%   | sustained ≥65% on `main` for ≥4 weeks |
| M3        | 70%   | sustained ≥75% on `main` for ≥4 weeks |
| M4        | 80%   | sustained ≥82% on `main` for ≥4 weeks; matches `AGENTS.md` target |

### AI engine (`ai-engine`)

| Milestone | Floor | Promotion criterion |
|-----------|-------|---------------------|
| M0 (today)| 65%   | baseline            |
| M1        | 70%   | sustained ≥75% on `main` for ≥4 weeks |
| M2        | 75%   | sustained ≥80% on `main` for ≥4 weeks |
| M3        | 80%   | sustained ≥82% on `main` for ≥4 weeks; matches `AGENTS.md` target |

### Frontend (`frontend`)

Frontend tests run in CI (`pnpm run test:ci`) but coverage is not gated.
A future ratchet for the frontend will be added once a baseline is
established; until then the 80% target is purely aspirational for the
frontend. Tracking issue: TBD.

---

## Cadence

> **Rule of thumb**: raise the floor by **+10 percentage points (pp)** at most
> **once per quarter**, and only when measured coverage on `main` has been
> **≥5pp above the next milestone for at least 4 consecutive weeks**.

Concretely:

- Once per quarter, the on-call maintainer (or anyone) opens an issue titled
  `coverage: ratchet review YYYY-Qn` and pastes the last 4 weeks of coverage
  numbers from the `backend-coverage` and `ai-engine-coverage` artifacts on
  `main`.
- If both numbers comfortably clear the next milestone, open the bump PR (see
  below).
- If only one component clears, bump only that one.
- If neither clears, no change — file follow-up issues for the gap modules.

The +10pp / 4-week buffer rule prevents thrashing: a single lucky PR cannot
ratchet the floor; the floor only moves when the team has *durably* improved
coverage and would not regress on a routine refactor.

---

## How to propose a raise

1. Open a PR that:
   - Bumps the value of `COVERAGE_FLOOR_BACKEND` and/or
     `COVERAGE_FLOOR_AI_ENGINE` in `.github/workflows/pr.yml`.
   - Updates the "Current enforced thresholds" section above to match.
   - Strikes through (or replaces) the relevant row in the milestone table
     with a "✅ promoted YYYY-MM-DD" note.
   - Optionally updates `AGENTS.md` if the new floor reaches the 80% target.
2. CI must be green on that PR with the new, higher floor — that is the
   verification that the codebase actually sustains the new floor today.
3. Reviewer: confirms the milestone criterion is met (link to the 4-week
   coverage history in the PR description).
4. Merge. The next PR onward enforces the new floor.

A raise PR is **scope `chore(ci)` or `chore(docs,ci)`**. It does not need
new tests; the test work that produced the higher coverage should already be
on `main`.

---

## How to lower (rare)

Lowering a floor is intentionally rare and high-friction. It is appropriate
in cases such as:

- A large module is **deleted** (denominator shrinks; numerator
  proportionally less, so percentage drops) and we cannot land replacement
  tests in the same PR.
- A **legitimate refactor** introduces a previously-untested integration
  layer that we plan to test in a follow-up PR with a tracking issue.
- A **flaky** coverage measurement is causing repeated false-negative gate
  failures on otherwise-correct PRs (in this case, fix the flake instead if
  at all possible).

To lower:

1. Open a PR that:
   - Lowers the value in `.github/workflows/pr.yml`.
   - Updates the "Current enforced thresholds" table above.
   - Adds a dated entry to the **"Lowering log"** section below explaining
     the reason and the tracking issue for restoring the floor.
2. PR description must include:
   - The reason (link to the deletion/refactor PR or flake report).
   - A concrete plan and target date for restoring the previous floor.
   - Explicit reviewer sign-off from a CODEOWNER for `.github/workflows/`.
3. Open a follow-up issue labelled `ci`, `coverage`, and `tech-debt`
   referencing the lowered floor and the restoration target. Link it from
   the lowering log entry.

### Lowering log

_(empty — no floors have been lowered)_

---

## How a PR currently fails the gate

The relevant CI lines (paraphrased) are:

```bash
# backend
python -m pytest src/tests/unit/ \
  --cov=src --cov-report=xml --cov-report=term \
  --cov-fail-under=${COVERAGE_FLOOR_BACKEND}

# ai-engine
python -m pytest tests/ \
  --cov=. --cov-report=xml \
  --cov-fail-under=${COVERAGE_FLOOR_AI_ENGINE}
```

If total coverage falls below the floor, `pytest` exits non-zero, the job
fails, and the `PR Gates` aggregator (`pr-gates` job in `pr.yml`) reports
failure to the branch-protection check, blocking merge.

---

## What this policy is *not*

- **Not a per-file rule.** A new file at 0% coverage will not fail the gate
  on its own; only the aggregate percentage matters. Reviewers should still
  push back on PRs that add untested code.
- **Not a per-PR diff rule.** Diff coverage (Option C in the original RFC)
  is intentionally not used today because it is sensitive to renames /
  whitespace / vendored code in this repo. We may revisit if/when a stable
  diff-coverage tool is wired in.
- **Not a substitute for code review.** Coverage is a floor on test
  *execution*, not on test *quality*. A reviewer can still block a PR that
  has high coverage but weak assertions.

---

## Cross-references

- `.github/workflows/pr.yml` — where the floors are enforced.
- `AGENTS.md` — repository contributor guide; testing section links here.
- `pytest.ini` — project-wide pytest defaults (parallelism, markers).
- `backend/coverage.xml` / `ai-engine/coverage.xml` — per-run coverage
  artifacts uploaded by the `backend-tests` and `ai-engine-tests` jobs.
