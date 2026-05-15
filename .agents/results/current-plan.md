# PortKit Backlog — 2026-05-15 oma-pm Review

**Session ID**: `pm-20260515T081734`
**Repo**: anchapin/portkit
**Open issues at start**: 0 (all recent work closed)
**Recent context**: M5 beta launch, B2B 67% conversion coverage, post-CrewAI removal, post-CI consolidation
**Sources reviewed**: `README.md`, `ARCHITECTURE.md`, `docs/SCALABILITY-ASSESSMENT.md`, `docs/GAP-ANALYSIS-v2.5.md`, `docs/PRD.md`, `docs/ROADMAP.md`, `docs/ENTERPRISE-ROADMAP.md`, `docs/ENHANCEMENT-FEATURES.md`, `docs/ci/coverage-policy.md`, `.planning/STATE.md`, `NEXT_SESSION_PROMPT.md`, `INVESTIGATION_NEXT_SESSION.md`, dependabot alerts (4 open dompurify CVEs + 7 backend image CVEs), code-scanning alerts (4 open CodeQL alerts), recent merge history (last 30 commits)

---

## Goal

Refill the open backlog after the recent close-out batch. Cover four categories:

1. **Security / CVE remediation** — open dependabot + Trivy + CodeQL alerts (must triage soon)
2. **Horizontal-scaling P0 blockers** — documented in `SCALABILITY-ASSESSMENT.md` but not yet ticketed
3. **Beta → GA stability** — rate limits, AI-engine isolation, CDN, replicas
4. **B2B conversion coverage levers** — Create recipes, embedding upgrade, coverage ratchet
5. **Platform / Enterprise enablement** — webhooks, frontend coverage gate

## ISO framing (lightweight)

| Concern | ISO lens | Application here |
|---|---|---|
| Project structure | ISO 21500 | 3 priority tiers, dependencies surfaced explicitly, parallelizable scopes |
| Risk prioritization | ISO 31000 | P0 = production blocker / unpatched CVE; P1 = beta stability; P2 = coverage / DX |
| Governance & ownership | ISO 38500 | Each issue carries a `scope` (directory prefix) so reviewers can validate boundaries; security CVEs are owned by the security label, scaling P0s by infrastructure |

---

## Backlog (21 issues across 3 tiers)

### Tier 1 — P0 (parallelizable, no dependencies on other tier-1 items)

| # | Title | Scope | Labels |
|---|-------|-------|--------|
| 1 | Bump `dompurify` ≥ 3.4.0 to remediate 4 open XSS / prototype-pollution CVEs | `frontend/` | bug, security, frontend, P1, dependencies |
| 2 | Bump `wheel` ≥ 0.46.2 in backend image (CVE-2026-24049 privilege-escalation) | `backend/Dockerfile` | bug, security, backend, P1, dependencies, docker |
| 3 | Bump `jaraco.context` ≥ 6.1.0 in backend image (CVE-2026-23949 Zip Slip) | `backend/Dockerfile` | bug, security, backend, P1, dependencies, docker |
| 4 | Bump `pip` ≥ 25.3 in backend image (CVE-2025-8869 + CVE-2026-1703 + CVE-2026-6357) | `backend/Dockerfile` | bug, security, backend, P2, dependencies, docker |
| 5 | Migrate `conversion_jobs_db` from in-memory dict to Redis/Postgres | `backend/src/main.py`, `backend/src/services/`, `backend/src/db/` | enhancement, backend, scalability, P1, infrastructure, architecture |
| 6 | Replace local Docker volumes with Tigris/S3 object storage | `backend/src/`, `ai-engine/`, `docker-compose.prod.yml`, `fly.toml` | enhancement, backend, ai-engine, scalability, P1, infrastructure |
| 7 | Make `/api/v1/conversions` rate limits per-authenticated-user (not per-IP) | `backend/src/security/`, `backend/src/api/conversions.py` | bug, backend, api, security, P2 |
| 8 | Fix CodeQL `js/log-injection` alerts in `websocket.ts` and `ConversionProgress.tsx` (alerts #76, #77, #78) | `frontend/src/services/websocket.ts`, `frontend/src/components/ConversionProgress/` | bug, security, frontend, P2 |
| 9 | Fix CodeQL `js/xss-through-dom` alert in `ConversionAssetsUpload.tsx` (alert #75) | `frontend/src/components/ConversionAssets/` | bug, security, frontend, P1 |
| 10 | Fix CodeQL `js/tainted-format-string` alert in `frontend/src/services/api.ts` (alert #74) | `frontend/src/services/api.ts` | bug, security, frontend, P2 |

### Tier 2 — P1 / P2 (beta-to-GA + B2B coverage levers)

| # | Title | Scope | Labels |
|---|-------|-------|--------|
| 11 | Extract AI Engine to its own Fly.io app (`portkit-ai-engine`) for independent vertical scaling | `fly.toml`, `Dockerfile.fly`, `ai-engine/`, `docker-compose.prod.yml` | enhancement, ai-engine, infrastructure, scalability, P2, architecture |
| 12 | Add Fly.io auto-scale config (`[[services.concurrency]]` + `max_machines_running`) | `fly.toml`, `fly-staging.toml` | enhancement, infrastructure, scalability, P2 |
| 13 | Replace hardcoded Celery `--concurrency=4` with `--autoscale=8,2` | `fly.toml`, `backend/src/services/celery_config.py` | enhancement, backend, infrastructure, scalability, P2, performance |
| 14 | Close coverage gap on the remaining 1,661 unconverted Create recipes (top B2B lever) | `ai-engine/agents/recipe_converter.py`, `ai-engine/converters/` | enhancement, ai-engine, conversion, conversion-quality, P2, component:recipe-conversion |
| 15 | Upgrade embedding model `text-embedding-ada-002` → `text-embedding-3-large` for RAG | `ai-engine/search/`, `ai-engine/services/rag_service.py`, `backend/src/db/` | enhancement, ai-engine, P3, optimization |

### Tier 3 — P2 / P3 (platform / enterprise / DX)

| # | Title | Scope | Labels |
|---|-------|-------|--------|
| 16 | Deploy frontend SPA to a CDN (Vercel / Cloudflare Pages / Tigris static) | `frontend/`, `nginx-fly.conf`, `fly.toml` | enhancement, frontend, infrastructure, scalability, P3 |
| 17 | Add Postgres read replica + route SELECT-only endpoints to `readonly_database_url` | `backend/src/db/base.py`, `backend/src/db/`, `fly.toml` | enhancement, backend, database, infrastructure, scalability, P3 |
| 18 | Ratchet backend coverage floor 40% → 50% (M1 promotion criterion is sustained ≥55%) | `.github/workflows/pr.yml`, `backend/` | enhancement, backend, ci/cd, testing, tech-debt, quality-assurance, P3 |
| 19 | Ratchet AI Engine coverage floor 65% → 70% (M1 promotion criterion is sustained ≥75%) | `.github/workflows/pr.yml`, `ai-engine/` | enhancement, ai-engine, ci/cd, testing, tech-debt, quality-assurance, P3 |
| 20 | Add an enforced frontend coverage gate (currently `vitest run` runs without `--coverage`) | `.github/workflows/pr.yml`, `frontend/vitest.config.ts` | enhancement, frontend, ci/cd, testing, P3 |
| 21 | Add webhook notifications for batch conversion completion (Enterprise Phase 1 deliverable) | `backend/src/api/`, `backend/src/services/`, `backend/src/db/models.py` | enhancement, backend, api, P3 |

---

## Dependencies (minimal — most run in parallel)

```
6  (object storage) ──► 11 (AI Engine extract)        # AI Engine needs shared storage to be standalone
5  (Redis job state) ──► 12 (auto-scale)              # Don't enable HA scale before state is shared
14 (Create recipes) ──► (no blocker, parallelizable)
21 (webhooks) ──► 5 (DB-backed jobs)                  # Webhooks query persisted job state
```

All other items are independent.

## Acceptance contracts

Every issue body uses the project's existing AI-triage convention:

```
> *This was generated by AI during triage.*

## Problem
…
## Evidence
…
## Expected outcome
…
## Suggested implementation
…
## Acceptance criteria
- testable bullets
```

## Verification (what "done" looks like for this PM session)

- [x] 21 issues filed in anchapin/portkit with consistent labels and scope tags
- [x] Plan artifact at `.agents/results/current-plan.md`
- [x] JSON plan at `.agents/results/plan-pm-20260515T081734.json`
- [x] Dependencies surfaced; nothing in Tier 1 blocks itself
- [x] Each item is single-agent-completable, has measurable acceptance criteria, and bundles security + testing

---

## Filed issues (anchapin/portkit)

| Plan ID | GitHub | Title | Tier |
|---|---|---|---|
| 1 | [#1481](https://github.com/anchapin/portkit/issues/1481) | security(frontend): bump dompurify >= 3.4.0 | T1 / P1 |
| 2 | [#1484](https://github.com/anchapin/portkit/issues/1484) | security(backend): bump wheel >= 0.46.2 | T1 / P1 |
| 3 | [#1483](https://github.com/anchapin/portkit/issues/1483) | security(backend): bump jaraco.context >= 6.1.0 | T1 / P1 |
| 4 | [#1482](https://github.com/anchapin/portkit/issues/1482) | security(backend): bump pip >= 26.1 | T1 / P2 |
| 5 | [#1487](https://github.com/anchapin/portkit/issues/1487) | scaling(backend): migrate conversion_jobs_db to Redis/Postgres | T1 / P1 |
| 6 | [#1485](https://github.com/anchapin/portkit/issues/1485) | scaling(infra): replace local Docker volumes with Tigris/S3 | T1 / P1 |
| 7 | [#1486](https://github.com/anchapin/portkit/issues/1486) | rate-limits(backend): per-authenticated-user limits | T1 / P2 |
| 8 | [#1490](https://github.com/anchapin/portkit/issues/1490) | security(frontend): CodeQL js/log-injection (#76,#77,#78) | T1 / P2 |
| 9 | [#1488](https://github.com/anchapin/portkit/issues/1488) | security(frontend): CodeQL js/xss-through-dom (#75) | T1 / P1 |
| 10 | [#1489](https://github.com/anchapin/portkit/issues/1489) | security(frontend): CodeQL js/tainted-format-string (#74) | T1 / P2 |
| 11 | [#1493](https://github.com/anchapin/portkit/issues/1493) | scaling(infra): extract AI Engine to its own Fly.io app | T2 / P2 |
| 12 | [#1491](https://github.com/anchapin/portkit/issues/1491) | scaling(infra): Fly.io auto-scale config | T2 / P2 |
| 13 | [#1492](https://github.com/anchapin/portkit/issues/1492) | scaling(infra): Celery --autoscale=8,2 | T2 / P2 |
| 14 | [#1495](https://github.com/anchapin/portkit/issues/1495) | feat(ai-engine): close 1,661 Create recipes gap | T2 / P2 epic |
| 15 | [#1496](https://github.com/anchapin/portkit/issues/1496) | feat(ai-engine): upgrade RAG embeddings to text-embedding-3-large | T2 / P3 |
| 16 | [#1494](https://github.com/anchapin/portkit/issues/1494) | scaling(frontend): deploy SPA to CDN | T3 / P3 |
| 17 | [#1498](https://github.com/anchapin/portkit/issues/1498) | scaling(backend): Postgres read replica + readonly routing | T3 / P3 |
| 18 | [#1499](https://github.com/anchapin/portkit/issues/1499) | ci: ratchet backend coverage 40% → 50% | T3 / P3 |
| 19 | [#1497](https://github.com/anchapin/portkit/issues/1497) | ci: ratchet AI Engine coverage 65% → 70% | T3 / P3 |
| 20 | [#1500](https://github.com/anchapin/portkit/issues/1500) | ci: enforced frontend coverage gate | T3 / P3 |
| 21 | [#1501](https://github.com/anchapin/portkit/issues/1501) | feat(backend): webhook notifications for batch completion | T3 / P3 |

## Summary

- **21 issues filed**, all using the project's existing AI-triage convention and label vocabulary.
- **Tier 1 (P1/P2 — 10 issues)**: 4 security CVE bumps + 4 CodeQL fixes + 2 scaling P0 blockers + per-user rate limits.
- **Tier 2 (P2/P3 — 5 issues)**: AI engine isolation, Fly auto-scale, Celery autoscale, Create recipes (top B2B lever), embedding upgrade.
- **Tier 3 (P3 — 6 issues)**: CDN, read replica, three coverage ratchets, enterprise webhooks.
- All Tier 1 items are independently parallelizable except the scaling P0 pair (#1487 + #1485) which together unlock the rest of the scaling track.
