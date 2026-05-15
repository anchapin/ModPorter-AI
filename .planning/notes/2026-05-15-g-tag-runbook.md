# G-tag push runbook

**Action:** push `langchain-cutover-complete` annotated tag at `d7b8941d`.
**When:** at or after **2026-05-15T17:21:00Z** (24h after PR #1445 merged at 2026-05-14T17:21Z).
**Why:** mirror the `pre-langchain-cutover` tag — gives ops a clean "before/after" pair to roll back to.

## Pre-flight verification (already done in PR #1448)

✅ SHA `d7b8941d67c73ddc7f05ef9e39fe44344ddbad2f` resolves to:
   `feat(ai-engine): fully remove CrewAI; AI Engine runs on LangChain/LangGraph only (#1201) (#1445)`
✅ Commit message references PR #1445.
✅ Symmetric `pre-langchain-cutover` tag exists.
✅ No issues during the 24h soak window have surfaced (TODO: verify before pushing — see "Last-second checks" below).

## Last-second checks before pushing

```bash
cd /home/alex/Projects/portkit
git fetch --all --tags

# Confirm SHA hasn't moved (force-push protection)
git show d7b8941d --stat | head -5
git log d7b8941d -1 --format='%s' | grep -F '#1445'   # exit 0 means OK

# Confirm no `langchain-cutover-complete` tag already exists
git tag -l langchain-cutover-complete   # should print nothing

# Confirm CI/dashboards from the past 24h are clean (manual check):
#   - Sentry: any new langgraph/langchain-flagged errors since merge?
#   - Grafana/Prometheus: error-rate or latency regression on /convert?
#   - Application logs: any "deprecated CrewAI" warnings?
```

If all checks pass, push:

```bash
git tag -a langchain-cutover-complete d7b8941d67c73ddc7f05ef9e39fe44344ddbad2f \
  -m "LangChain/LangGraph cutover complete (PR #1445); symmetry with pre-langchain-cutover."
git push origin langchain-cutover-complete
```

## If something is wrong during soak

If the 24h soak surfaces a regression, **don't push the tag**. Either:

1. Roll back via Fly.io to the pre-cutover deployment.
2. Land a hotfix on top, wait another 24h soak from the hotfix merge, then push the tag at the hotfix SHA (with an updated message).

Either way: update this runbook with the new SHA and re-soak before pushing.

## Verification after push

```bash
git fetch --tags
git tag -l 'langchain-cutover*'
# Should print:
#   langchain-cutover-complete
git show langchain-cutover-complete --stat | head -5
# Should match the message above.
```
