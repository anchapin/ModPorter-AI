# PortKit — Development Roadmap

**Last Updated:** 2026-04-20 (v16 audit — 1:46am ET)
**Status:** M1–M4 ✅ | M5 In Progress (beta launch) | 8/8 PASS ✅ | B2B 67.0% 🆕
**Repo:** [anchapin/portkit](https://github.com/anchapin/portkit) | Rebranded to PortKit ✅ (#1114)
**Target:** Public launch at portkit.cloud by June 22, 2026

---

## Executive Summary

PortKit converts Minecraft Java mods to Bedrock add-ons. Positioned as a **B2B conversion accelerator** targeting Marketplace creators.

**B2B readiness: 67.0%** (v16, 8/8 PASS). M1–M4 all complete. The 4-cycle ceiling at 66.4% was broken in v16 by #1119 (Create custom recipe converters): Create recipes 36% → 40%, aggregate recipes 41.7% → 45.0%. ~126 of 750 Create custom recipes now convert (~21% of custom types). Remaining Create recipe coverage (1,661 unconverted) is the top remaining lever for B2B growth.

**Pipeline state**: tree-sitter (Java 17+) ✅ | minecraft-data 1152 items ✅ | confidence scoring ✅ | semantic chunking ✅ | java_analyzer 6-module package ✅ | Celery task queues ✅ | texture/model converter subpackages ✅ | Create recipe converters (milling/crushing/deploying/splashing/compacting) ✅ | DPC multi-candidate consistency selection ✅

---

## Conversion Audit History

| Cycle | Date | Mods | Textures | Models | Recipes | Sound | Lang | B2B est. | Key Changes |
|-------|------|------|----------|--------|---------|-------|------|-----------|-------------|
| v1 | Apr 8 | 8 | ~0% | 0% | 0% | 0% | 0% | ~5% | Baseline |
| v2 | Apr 9 | 8 | 54.8% | 0.2% | 0% | 0% | 0% | ~25% | Bulk texture extraction |
| v5 | Apr 11 | 8 | 54.7% | 82.3% | 25.8% | 0% | 0% | ~46% | Model+recipe converters wired |
| v6 | Apr 15 | 30 | 68.7% | 68.3% | 40.2% | 0% | 0% | ~49% | NeoForge fix, 30-mod set |
| v7 | Apr 16 | 8 | 54.7% | 82.3% | 25.8% | ~100% | 89.3% | ~63% 🎯 | Sound+lang, loot tables, spawn rules |
| v9 | Apr 18 00:06 | 8 | 54.7% | 82.3% | 26.6% | ~100% | 89.3% | 63.4% | Cooking recipe fix +27 |
| v10 | Apr 18 10:15 | 8 | 54.7% | 82.3% | 28.5% | ~100% | 89.3% | 63.7% | Cutting board fix +72 |
| v11 | Apr 18 19:16 | 7/8 ⚠️ | 54.7%* | 82.3%* | 32.1%* | ~100%* | 89.3%* | ~64.4%* | Collision fix +138; Create crash P0 |
| v12 | Apr 18 20:48 | 8/8 ✅ | 54.7% | 82.3% | 41.7% | ~100% | 89.3% | 66.4% 🎯 | Create restored; recipe +509 total |
| v13 | Apr 19 00:51 | 8/8 ✅ | 54.7% | 82.3% | 41.7% | ~100% | 89.3% | 66.4% | Non-std JAR ✅, rebrand ✅, M4 ✅ |
| v14 | Apr 19 13:33 | 8/8 ✅ | 54.7% | 82.3% | 41.7% | ~100% | 89.3% | 66.4% | tree-sitter ✅, item map 1152 ✅, confidence scoring ✅ |
| v15 | Apr 19 19:53 | 8/8 ✅ | 54.7% | 82.3% | 41.7% | ~100% | 89.3% | 66.4% | semantic chunking ✅, java_analyzer split ✅, Celery ✅ |
| **v16** | **Apr 20 01:46** | **8/8 ✅** | **54.7%** | **82.3%** | **45.0% 🆕** | **~100%** | **89.3%** | **67.0% 🆕** | **Create recipe converters ✅ (+127), DPC consistency ✅, texture/model split ✅** |

\* v11 adjusted (Create excluded due to crash)

**v16 B2B breakdown:**
| Asset Type | Coverage | Weight | Contribution | Delta v15 |
|------------|----------|--------|-------------|-----------|
| Texture | 54.7% | 25% | 13.7% | — |
| Model | 82.3% | 30% | 24.7% | — |
| Recipe | **45.0%** | 20% | **9.0%** | **+0.7pp** |
| Sound | ~100% | 10% | 10.0% | — |
| Localization | 89.3% | 10% | 8.9% | — |
| Entity | ~15% | 5% | 0.8% | — |
| **Total** | | | **67.0%** | **+0.6pp** |

---

## Ceiling Analysis (Updated v16)

### Recipe — 45.0% (was 41.7%; next lever: improve Create recipe converter coverage)
- **Create ceiling partially broken**: 750 custom recipes → ~126 now convert (milling/crushing/deploying/splashing/compacting mapped to Bedrock shapeless/shaped approximations). Create recipe coverage 36% → 40%.
- **1,661 Create recipes still unconverted** (~60% of Create's total). Root cause to investigate: edge cases in Create recipe JSON format, `compacting` type coverage, result multi-output handling, and recipes that require machine-specific mechanics with no Bedrock approximation.
- **ImmersiveEngineering** (8 crusher recipes in Farmer's Delight): not yet covered — similar pattern to Create custom types.
- **Standard ceiling (excl. Create customs)**: ~47–50% — FD cooking_pot, cutting board, iron chests remain the reference floor.

### Texture — 54.7% (structural — unchanged)
- JEI 0% (GUI-only), JourneyMap 7% (minimap UI): correct, not bugs.
- Create 49%, Supplementaries 62%: room to grow via expanded block state and entity texture path handling.

### Model — 82.3% (structural — unchanged)
- Solid baseline. Minor drag from Create custom parent paths.

---

## Milestone Status

### ✅ M1 — M4 Complete
### 🔄 M5 — Beta Launch
All prerequisites complete. Beta onboarding, conversion quality tuning, and confidence score UI are active.

### ⏳ M6-M7 — Beta Feedback + Public Launch (Jun 22)

---

## Open Issues (7 total — 0 open PRs)

### Conversion Quality / AI Engine
| Issue | Labels | Priority |
|-------|--------|----------|
| **New** | File: Create recipe converter edge cases + remaining coverage | **🥇 #1 — 1,661 Create recipes still unconverted; converters in but ~21% hit rate** |
| [#994](https://github.com/anchapin/portkit/issues/994) Upgrade embedding model ada-002 → text-embedding-3 | enhancement, ai-engine | 🥉 #3 — quality lever for Java→Bedrock mapping retrieval |
| [#996](https://github.com/anchapin/portkit/issues/996) Diffusion LoRA for texture pairs | post-launch | — |
| [#997](https://github.com/anchapin/portkit/issues/997) Fine-tune open-weights LLM | post-launch | — |

### Refactor / Tech Debt
| Issue | Labels | Priority |
|-------|--------|----------|
| [#1097](https://github.com/anchapin/portkit/issues/1097) Consolidate 5 backend error-handling files | backend, refactor | 🥈 #2 — beta stability; last medium-priority open debt |
| [#1101](https://github.com/anchapin/portkit/issues/1101) Remove dead BM25 fallback | ai-engine, refactor | — |
| [#1102](https://github.com/anchapin/portkit/issues/1102) Consolidate 4 backend report files | backend, ai-engine, refactor | — |

### Post-Launch Enhancements
| Issue | Note |
|-------|------|
| [#1048](https://github.com/anchapin/portkit/issues/1048) IDE/Plugin ecosystem (bridge., Blockbench, VS Code) | post-launch |

---

## Top 3 Priority Issues (Apr 20, 1:46am — post-v16)

### 🥇 #1: File New Issue — Create Recipe Converter Coverage Improvement

**Current state**: #1119 converters shipped and working — Create recipes improved from 36% to 40%. But only ~126 of 750 custom recipes are now converting (~21% hit rate). 1,661 Create recipes remain unconverted (59.7% of Create total). With semantic chunking and the modular java_analyzer in place, the infrastructure is ready for a deeper pass.

**Investigation areas**:
- `create:compacting` recipes not in original breakdown — how many exist and what's coverage?
- Multi-output result handling (Create's milling/crushing often produce multiple outputs with probability weights — Bedrock has no direct equivalent)
- Tag-based ingredient resolution (`#forge:ingots/iron` → specific item lookup)
- Recipes that require machine-specific mechanics (e.g., RPM requirements in deploying) may need a fallback/approximation strategy

**Expected impact**: Each 100 additional Create recipes converted adds ~0.4pp to aggregate recipe coverage and ~0.1pp to B2B.

### 🥈 #2: [#1097](https://github.com/anchapin/portkit/issues/1097) — Consolidate 5 Backend Error-Handling Files

The last medium-priority open tech debt. Five separate error-handling modules creates inconsistent error propagation behavior — a stability risk during beta load. Consolidating into an `errors/` package with a unified exception hierarchy improves predictability, makes error telemetry more actionable, and is a natural complement to Celery's retry policies (#1122, already merged).

### 🥉 #3: [#994](https://github.com/anchapin/portkit/issues/994) — Upgrade Embedding Model ada-002 → text-embedding-3

The embedding model underlies the hybrid search at the core of Java→Bedrock concept mapping. `text-embedding-3-small` cuts cost by ~5× vs ada-002 while improving retrieval quality, and `text-embedding-3-large` improves accuracy further. Upgrading the embedding model is the highest-leverage ML quality improvement available without changing the model architecture — better embeddings means more accurate Java class→Bedrock behavior mappings, which benefits all asset types but especially entities and recipes.

---

## Audit Reports

- [v12 — Apr 18 8:48pm](docs/audit-reports/real-world-scan-v12-20260418.md) — B2B 66.4%, 8/8 PASS, recipe +509
- [v13 — Apr 19 12:51am](docs/audit-reports/real-world-scan-v13-20260419.md) — B2B 66.4% stable, M4 complete
- [v14 — Apr 19 1:33pm](docs/audit-reports/real-world-scan-v14-20260419.md) — B2B 66.4% (3rd cycle), ceiling confirmed
- [v15 — Apr 19 7:53pm](docs/audit-reports/real-world-scan-v15-20260419.md) — B2B 66.4% (4th cycle), semantic chunking ✅
- [**v16 — Apr 20 1:46am**](docs/audit-reports/real-world-scan-v16-20260420.md) — **B2B 67.0% 🆕**, Create recipe converters ✅ (+127), ceiling partially broken
