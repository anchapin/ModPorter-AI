# Outstanding follow-ups after PR #1448 (consolidation) merged

GitHub issues are not in use on this repo, so this file serves as the
canonical tracker for items spawned during PR #1447 (typed
logic_translator) and PR #1448 (ai_engine/ ↔ ai-engine/ consolidation).

**Last updated:** 2026-05-15 — typed-args migration COMPLETE; cleanup wave merging: **PR #1460** ✅ MERGED (Item 2), **PR #1461** ✅ MERGED (Items 4+5), **PR #1462** open (Item 9 ruff). G-tag still blocked until 2026-05-15T17:21Z (~15h).

## Status legend
- 🚨 **URGENT** — actively breaking something or blocking other work
- 🎯 **NEXT** — the natural next sequenced task
- 🔁 **PARALLEL** — independent of the critical path
- ⏳ **DEFERRED** — needs a decision before starting
- 🐛 **CLEANUP** — drive-by, low priority
- ✅ **DONE** — landed (or PR open and ready)

---

## Cumulative deliverables across sessions

| PR | Title | Status |
|---|---|---|
| #1447 | refactor(ai-engine): convert logic_translator tools to typed args_schema | ✅ MERGED (`0067e9ea`) |
| #1448 | refactor(ai-engine): consolidate ai_engine/ namespace into ai-engine/ | ✅ MERGED (`aa9bb446`) |
| #1449 | fix(ai-engine): mmsd.premium_client._parse_output mismatched JSON as JS | ✅ MERGED (`8ccf85a0`) |
| #1450 | fix(backend): make ai-engine reachable from backend process for non-colliding imports | ✅ Open — Agent-2 revised (append vs prepend), Agent-3 fixed CI test isolation |
| #1451 | refactor(ai-engine): convert steering_tools to typed args_schema (A2.5) | ✅ MERGED (`f964aa08`) |
| #1452 | chore(ai-engine): reconcile chromadb pin | ✅ Open, ready |
| #1453 | refactor(ai-engine): convert QA validator tools to typed args_schema (A3) | ✅ Open, ready (Agent-3) |
| #1454 | chore(ai-engine): fix F841 + format drift in test_integration.py | ✅ Open, ready (Agent-3) |
| (local) | refactor(ai-engine): convert bedrock_architect + bedrock_builder tools to typed args_schema (A4a) | ✅ Local commit on `feature/1201-typed-bedrock-architect-builder` (`28f0deae`); 14 tools, 72 new tests + 25 baseline pass unchanged |
| (local) | refactor(ai-engine): convert packaging_agent tools to typed args_schema (A4b) + Item 9 F401 cleanup + latent-logger fix | ✅ Local commit on `feature/1201-typed-packaging-agent` (`eb5b97b7`); 13 tools, 60 new tests + 28 baseline pass unchanged |
| (local) | refactor(ai-engine): convert recipe converter tools to typed args_schema (A5) + recipe_converter.py shim F401 cleanup | ✅ Local commit on `feature/1201-typed-recipe-converter` (`225cfffe`); 4 tools, 27 new tests + 94 baseline pass unchanged |
| (local) | refactor(ai-engine): convert java_analyzer tools to typed args_schema (A6 — last A-slice) + 4 F401 cleanup in test_java_analyzer_comprehensive.py | ✅ Local commit on `feature/1201-typed-java-analyzer-tools` (`862f9ece`); 6 tools, 39 new tests + 5 baseline updated to .invoke({...}) shape pass |
| #1459 | chore(repo): re-run skeleton generator + persist PLUR Memory in CLAUDE_MD (E) | ✅ **MERGED** 2026-05-15T01:39Z as squash commit `33846a06` on `main`. PR #1459. 3 source commits: `d8188a31` regen, `c335e25b` PLUR durability, `05607580` post-rebase refresh (+287/-50 in `ai-engine/SKELETON.md` after typed-class symbols from merged A4a-A6 became canonical). Verified idempotent. |

## Critical path (typed-args migration)

| ID | Item | Status | Notes |
|---|---|---|---|
| ~~A2.5~~ | `agents/logic_translator/steering_tools.py` (6 wrappers) | ✅ MERGED PR #1451 | 6 typed BaseTool subclasses + 22 tests |
| ~~A3~~ | `agents/qa/__init__.py` (6 wrappers) | ✅ PR #1453 | 6 typed BaseTool subclasses + 26 tests including 3 explicit deprecation-alias guards |
| ~~A4a~~ | `bedrock_architect.py` (10) + `bedrock_builder.py` (4) | ✅ Local commit `28f0deae` on `feature/1201-typed-bedrock-architect-builder` | 14 typed BaseTool subclasses + 72 new tests; 978/978 unit tests pass **Pushed 2026-05-14, PR #1455** (mergeable, base `main`). |
| ~~A4b~~ | `packaging_agent.py` (13) | ✅ Local commit `eb5b97b7` on `feature/1201-typed-packaging-agent` | 13 typed BaseTool subclasses + 60 new tests; folded in Item 9 F401 cleanup (ManifestGenerator, PackagingCoordinator) AND drive-by `logger = __name__` → `logger = logging.getLogger(__name__)` fix **Pushed 2026-05-14, PR #1456** (mergeable, base `main`). |
| ~~A5~~ | `recipe/__init__.py` (4) + `recipe_converter.py` (drive-by F401) | ✅ Local commit `225cfffe` on `feature/1201-typed-recipe-converter` | 4 typed BaseTool subclasses + 27 new tests; legacy `tool_func.run(<json_string>)` shape from `tests/test_recipe_converter.py` continues to work **Pushed 2026-05-14, PR #1457** (mergeable, base `main`). |
| ~~A6~~ | `java_analyzer/tools.py` (6) | ✅ Local commit `862f9ece` on `feature/1201-typed-java-analyzer-tools` | 6 typed BaseTool subclasses + 39 new tests; 5 baseline tests updated `.func(<str>)` → `.invoke({"mod_data": <str>})`; 4 pre-existing F401s in test file cleaned up as drive-by **Pushed 2026-05-14, PR #1458** (mergeable, base `main`). **CI fix `6dea74bd`**: 3 baseline tests in `test_agents_unit.py` (2) and `test_java_analyzer_coverage.py` (1) still expected pre-A6 `.func` / `str(t)` surfaces and were missed by the A6 commit; updated to `.invoke({...})` and `t.name`. 104/104 java_analyzer tests now pass locally. |
| ~~E~~ | Re-run skeleton generator | ✅ **MERGED** 2026-05-15T01:39Z (PR #1459 → squash `33846a06`) | After A4a-A6 all merged on `main`, rebased E (clean), re-ran generator, captured the additional +287/-50 in `ai-engine/SKELETON.md` as commit `05607580` on top. PLUR Memory durability fix shipped as commit `c335e25b` on the same branch. Verified idempotent. |

## Parallel lanes

| ID | Item | Status | Notes |
|---|---|---|---|
| ~~B+C~~ | chromadb pin reconciliation | ✅ PR #1452 | All 3 sources now agree on `>=1.5.8,<2.0`. |
| D | OTel tracing audit | ⏳ DEFERRED | Default to OTel-bridge (preserves Jaeger/Prometheus). LangSmith requires explicit approval. Independent of A-slices. |

## Timed

| ID | Item | Status | Notes |
|---|---|---|---|
| G | Push `langchain-cutover-complete` tag | ⏳ blocked until 2026-05-15T17:21Z (~19h from this writing) | SHA `d7b8941d` re-verified. **Runbook: `.planning/notes/2026-05-15-g-tag-runbook.md`** |

## Spawned by PR #1447 (typed logic_translator)

| # | Item | Status | Notes |
|---|---|---|---|
| 1 | Pydantic AIMessage discriminator bug | ❌ CANNOT REPRODUCE | Verified in P1 on both `main` and PR branch. 939 unit tests pass under `--cov`. Closed without action. |
| ~~2~~ | `rag_evaluator.py` broken — imports missing `agents.knowledge_base_agent` | ✅ **MERGED PR #1460** (`ca6dc392`) | Deletion path: 0 importers, wrong class name (`RagEvaluator` vs production `RAGEvaluator`), orphan JSON fixture had generic non-Minecraft placeholder content. 3 docs repointed at production `evaluation/rag_evaluator.py`. 78 RAG tests still pass. |
| ~~3~~ | `test_integration.py:159` F841 + format drift | ✅ PR #1454 | Pitfall #10. F841 fixed by removing unused `chain` assignment. Format drift fixed via `ruff format`. |
| ~~4~~ | Broken `get_extended_tools` / `get_block_generation_tools` helpers in `logic_translator/tools.py` | ✅ **MERGED PR #1461** (`ccba4c28`) | Both deleted (-7 + -10 lines). Confirmed `get_extended_tools` references 5 attributes that don't exist on `LogicTranslatorAgent` — would AttributeError on first call. Zero in-repo callers. |
| ~~5~~ | Dead `@staticmethod`-only pseudo-tools in `logic_translator/tools.py` | ✅ **MERGED PR #1461** (`ccba4c28`) | All 6 deleted (folded into the same PR as Item 4 because `get_extended_tools` referenced 5 of them). 227 passed, 0 failed across the logic_translator + recipe + agents test surface. |
| 6 | ~2,000 lines of duplicate business logic in `LogicTranslatorTools` | 🐛 CLEANUP | Mirrors `LogicTranslatorAgent`. Unreachable from typed wrappers. Biggest win, biggest risk — wait for stable surface. |

## Spawned by PR #1448 (consolidation)

| # | Item | Status | Notes |
|---|---|---|---|
| ~~7~~ | Fix `mmsd.premium_client._parse_output` parser bug | ✅ MERGED PR #1449 | Word-boundary fix on the JS-fence regex + 2 regression tests. |
| 8 | Dead `mmsd.*` / `knowledge.*` / `utils.*` / `search.*` imports in `backend/` | ⚠️ PARTIAL via PR #1450 | Safe non-colliding `mmsd.*` and `knowledge.*` paths fixed. `search.*` and `utils.*` direct imports intentionally left for Item 11 because they depend on colliding `schemas.*` / `utils.*` packages. Helper appends rather than prepends to avoid shadowing. CI tests fixed by Agent-3. |
| ~~9~~ | Pre-existing ruff warnings | ✅ **PR #1456 + #1462** | packaging_agent.py F401s landed in PR #1456 (A4b). PR #1462 cleans up the remaining named files: 1 F401 in fewshot_enhancer_agent.py (CI-visible) + 11 fixes in test_agent_orchestration_comprehensive.py (repo-local — `tests/` is excluded from ai-engine's ruff scan). Global error count 98→97. |
| 10 | Optional Phase 4 — full directory rename `ai-engine/` → `ai_engine/` | ⏳ DEFERRED | Requires Dockerfile, compose, CI, scripts, docs updates. Symbolic win vs operational cost. |

## Spawned during follow-up sessions

| # | Item | Status | Notes |
|---|---|---|---|
| 11 | **Namespace collision** — backend AND ai-engine both have `utils/`, `models/`, `schemas/`, `services/` as regular packages with `__init__.py`. PR #1450 review confirmed sys.path prepending is unsafe; helper now appends only for non-colliding imports. | 🚨 ARCHITECTURAL | 13+ import sites in `backend/src/` (api/embeddings.py, api/comparison.py, api/rag.py, services/cache.py, services/batch_queuing.py, services/resource/*.py, etc.) hit this wall. **Strategic fix: HTTP-based decoupling — backend should call AI Engine via its FastAPI endpoints (port 8001 in production), not direct imports.** Full rewrite. Separate effort. |
| 12 | `multimodal_search_engine.py` had `logger.warning(...)` called before `logger = logging.getLogger(__name__)` was defined | ✅ via PR #1450 | Pre-existing latent bug, surfaced during smoke testing. Fixed as drive-by. |

---

## Recommended execution order (from here)

1. ~~Merge PR #1449~~ ✅ MERGED
2. ~~Merge PR #1451~~ ✅ MERGED as `f964aa08`
3. ~~Merge PR #1452~~ ✅ MERGED as `b38e688b`
4. **Merge PRs #1450, #1453, #1454** (3 PRs ready, all small, no overlap)
5. ~~**A4a** (`bedrock_architect.py` + `bedrock_builder.py`)~~ ✅ Local commit `28f0deae` — needs push + PR
6. ~~**A4b** (`packaging_agent.py` — fold in F401 cleanup [Item 9])~~ ✅ Local commit `eb5b97b7` — needs push + PR (Item 9 closed in same commit)
7. ~~**A5** (recipe family)~~ ✅ Local commit `225cfffe` — needs push + PR
8. ~~**A6** (`java_analyzer/tools.py`)~~ ✅ Local commit `862f9ece` — needs push + PR
9. ~~**E** (skeleton regenerate)~~ ✅ **MERGED** 2026-05-15T01:39Z as PR #1459 (squash `33846a06`) — typed-args migration is now complete
10. **G-tag push** at 2026-05-15T17:21Z (use runbook) — see "G-tag readiness" below
11. **D** (OTel tracing audit) — independent, can interleave anywhere
12. ~~**Item 2** (rag_evaluator.py broken import)~~ ✅ MERGED as PR #1460 (`ca6dc392`)
13. ~~**Items 4, 5**~~ ✅ MERGED as PR #1461 (`ccba4c28`, -122 lines). **Item 6** (~2000-line dedupe) deferred to its own dedicated PR — typed-args surface is now stable enough to attempt it
14. ~~**Item 9 ruff cleanup**~~ ✅ **PR #1462** open (fewshot_enhancer_agent + test_agent_orchestration_comprehensive)
14. **Item 11** (namespace collision / HTTP-boundary refactor) — dedicated milestone

## Local commits ready to push + PR

| Branch | SHA | Slice | Files | Tests |
|---|---|---|---|---|
| `feature/1201-typed-bedrock-architect-builder` | `28f0deae` | A4a | bedrock_architect.py, bedrock_builder.py, tests/unit/test_bedrock_architect_builder_typed.py | 72 new + 25 baseline |
| `feature/1201-typed-packaging-agent` | `eb5b97b7` | A4b + Item 9 + logger fix | packaging_agent.py, tests/unit/test_packaging_agent_typed.py | 60 new + 28 baseline |
| `feature/1201-typed-recipe-converter` | `225cfffe` | A5 + recipe_converter.py F401 fix | agents/recipe/__init__.py, agents/recipe_converter.py, tests/unit/test_recipe_typed.py | 27 new + 94 baseline |
| `feature/1201-typed-java-analyzer-tools` | `862f9ece` | A6 + drive-by F401 cleanup in test file | agents/java_analyzer/tools.py, tests/unit/test_java_analyzer_tools_typed.py, tests/unit/test_java_analyzer_comprehensive.py | 39 new + 5 baseline (updated .func() → .invoke({...})) |
| ~~`feature/1201-skeleton-regen-post-A6`~~ DELETED | merged as `33846a06` | E (PR #1459) | CLAUDE.md, ARCHITECTURE.md, .cursorrules, ai-engine/SKELETON.md, backend/SKELETON.md, frontend/SKELETON.md, scripts/portkit_skeletonize.py | doc/script-only |

Recommended PR landing order: **A4a → A4b → A5 → A6 → E**. Each branch is independent (disjoint file sets within ai-engine/agents/), so they can also land in parallel; only E should land last because it regenerates skeletons that reflect the post-A6 surface.

## G-tag readiness (item 4 from the previous session's critical-path)

* **Tag SHA**: `d7b8941d67c73ddc7f05ef9e39fe44344ddbad2f` (verified in PR #1448 P1)
* **Earliest push time**: `2026-05-15T17:21:00Z`
* **Runbook**: `.planning/notes/2026-05-15-g-tag-runbook.md`
* **Status as of this writing (2026-05-14T23:30Z)**: ⏳ ~18h until window opens. Cannot push yet.
* **Pre-push checklist** (run at the window):
  1. `git fetch --all --tags`
  2. `git show d7b8941d --stat | head -5` — confirm SHA still resolves to PR #1445
  3. `git log d7b8941d -1 --format='%s' | grep -F '#1445'` — exit 0 expected
  4. `git tag -l langchain-cutover-complete` — should print nothing
  5. Manual: Sentry/Grafana/Prometheus/app-logs check for new langgraph/langchain regressions in the soak window
  6. If clean: `git tag -a langchain-cutover-complete d7b8941d... -m "..."` then `git push origin langchain-cutover-complete`

## Items now closed (cumulative session result)

| Item | Resolution |
|---|---|
| A4a | ✅ Local commit `28f0deae` (this session) |
| A4b | ✅ Local commit `eb5b97b7` (this session) |
| A5 | ✅ Local commit `225cfffe` (this session) |
| A6 | ✅ Local commit `862f9ece` (this session) |
| E | ✅ **MERGED** as PR #1459 (`33846a06`) — 2026-05-15T01:39Z |
| Item 9 — F401 in packaging_agent.py | ✅ Folded into A4b commit `eb5b97b7` |
| Item 12 (analogue) — `logger = __name__` latent bug in packaging_agent.py | ✅ Drive-by fix folded into A4b commit `eb5b97b7` (same flavor as PR #1450's multimodal_search_engine.py fix) |
| F401s in test_java_analyzer_comprehensive.py | ✅ Drive-by fix folded into A6 commit `862f9ece` |
| F401 in recipe_converter.py shim (`tool` import unused) | ✅ Drive-by fix folded into A5 commit `225cfffe` |
