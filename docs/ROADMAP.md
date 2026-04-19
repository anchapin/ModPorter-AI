# PortKit — Development Roadmap

**Last Updated:** 2026-04-19 (v14 audit — 1:33pm ET)
**Status:** M1–M4 ✅ | M5 In Progress (beta launch) | 8/8 PASS ✅ | B2B 66.4%
**Repo:** [anchapin/ModPorter-AI](https://github.com/anchapin/ModPorter-AI) | Rebranded to PortKit ✅ (#1114)
**Target:** Public launch at modporter.ai by June 22, 2026

---

## Executive Summary

PortKit converts Minecraft Java mods to Bedrock add-ons. Positioned as a **B2B conversion accelerator** targeting Marketplace creators.

**B2B readiness: 66.4%** (v14, 8/8 PASS). M1–M4 all complete. B2B has been stable for 3 cycles (v12→v13→v14). The pipeline now handles standard and non-standard JAR layouts, Java 17+ mods (tree-sitter), 1,152 item mappings (minecraft-data), and per-segment confidence scoring. The 66.4% ceiling is structural: Create's 750 custom recipe types (milling/crushing/deploying/splashing with no Bedrock equivalent) and JEI/JourneyMap as GUI-only mods. Moving to M5 beta launch.

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
| **v14** | **Apr 19 13:33** | **8/8 ✅** | **54.7%** | **82.3%** | **41.7%** | **~100%** | **89.3%** | **66.4% ✅** | **tree-sitter ✅, minecraft-data 1152 items ✅, confidence scoring ✅** |

\* v11 adjusted (Create excluded due to crash)

**v14 B2B breakdown:**
| Asset Type | Coverage | Weight | Contribution |
|------------|----------|--------|-------------|
| Texture | 54.7% | 25% | 13.7% |
| Model | 82.3% | 30% | 24.7% |
| Recipe | 41.7% | 20% | 8.3% |
| Sound | ~100% | 10% | 10.0% |
| Localization | 89.3% | 10% | 8.9% |
| Entity | ~15% | 5% | 0.8% |
| **Total** | | | **66.4%** |

---

## Structural Ceiling Analysis (Audit-Verified, v12–v14 stable)

### Texture — 54.7% ceiling
- **JEI (0%)**: All textures are GUI sprites packed in atlases — no Bedrock UI equivalent. 0% is correct/expected.
- **JourneyMap (7%)**: Minimap UI theme images + vanilla entity icons referenced by namespace. 7% is the true ceiling for this mod.
- **Create (49%)**: Many textures tied to custom block animations/mechanisms that don't have direct Bedrock mappings.
- **Non-standard JAR mods** (REI, Storage Drawers, etc.): Now supported via #1105 fallback scanner — expected to improve 30-mod aggregate.
- **Next lever**: Custom entity texture path expansion (FM-001 partial fix) and block state texture coverage.

### Recipe — 41.7% ceiling
- **Create custom types (750 recipes / 27%)**: `create:milling`, `crushing`, `deploying`, `splashing` — zero Bedrock equivalents. Hard ceiling until Create-specific addon converters are added.
- **Standard ceiling without Create customs**: ~47–50% — FD cooking_pot, cutting board, and iron chests recipes at ~48–94%.
- **minecraft-data item map** (#1117): 50→1,152 items — confirms canonical mods mostly use vanilla IDs already, benefit falls to 30-mod set with more varied item IDs.
- **Next lever**: Create-specific recipe type converters OR add issue for large-mod semantic chunking (#1090) to improve Java analysis depth.

### Model — 82.3% ceiling
- Solid baseline. Drag from Create's custom parent model paths and Iron Chests' item models.
- No active blocker — incremental improvements expected as model converter matures.

---

## Milestone Status

### ✅ M1 — Weeks 1-2: Conversion Proof + Pipeline (Complete Apr 10)
### ✅ M2 — Weeks 3-4: Entity Behaviors + Sound/Lang + B2B UX (Complete Apr 16)
### ✅ M3 — Weeks 5-6: Infrastructure (Complete Apr 18)
All 6 infrastructure issues: Stripe (#970), file security (#973), feature flags (#972), usage limits (#977), transactional email (#976), OAuth login (#980).

### ✅ M4 — Week 7: Landing Page + Legal + Rebrand (Complete Apr 19)
Landing page (#978), ToS/Privacy (#975), history dashboard (#979), PortKit rebrand (#1043).

### 🔄 M5 — Week 8: Beta Launch
All prerequisites complete. Key M5 work: beta user onboarding, conversion quality tuning, confidence score UI.

### ⏳ M6-M7 — Weeks 9-11: Beta Feedback + Public Launch (Jun 22)

---

## Open Issues (12 total — 0 open PRs)

### Conversion Quality / AI Engine
| Issue | Labels | Priority |
|-------|--------|----------|
| [#1090](https://github.com/anchapin/ModPorter-AI/issues/1090) Semantic chunking for large Java mods | phase:1, priority:medium | **#1 — direct conversion quality lever for Create** |
| [#1089](https://github.com/anchapin/ModPorter-AI/issues/1089) Multi-candidate consistency check | phase:2, priority:medium | Quality guard for AI-generated Bedrock code |
| [#994](https://github.com/anchapin/ModPorter-AI/issues/994) Upgrade embedding model ada-002 → text-embedding-3 | post-launch | — |
| [#996](https://github.com/anchapin/ModPorter-AI/issues/996) Diffusion LoRA for texture pairs | post-launch | — |
| [#997](https://github.com/anchapin/ModPorter-AI/issues/997) Fine-tune open-weights LLM | post-launch | — |

### Refactor / Tech Debt
| Issue | Labels | Note |
|-------|--------|------|
| [#1099](https://github.com/anchapin/ModPorter-AI/issues/1099) Split java_analyzer.py (131K chars) | refactor | **#2 — highest development leverage** |
| [#1098](https://github.com/anchapin/ModPorter-AI/issues/1098) Consolidate task queues → Celery | refactor | **#3 — beta production stability** |
| [#1097](https://github.com/anchapin/ModPorter-AI/issues/1097) Consolidate 5 error-handling files | refactor | — |
| [#1101](https://github.com/anchapin/ModPorter-AI/issues/1101) Remove dead BM25 fallback | refactor | — |
| [#1102](https://github.com/anchapin/ModPorter-AI/issues/1102) Consolidate 4 backend report files | refactor | — |
| [#1103](https://github.com/anchapin/ModPorter-AI/issues/1103) Split texture_converter.py + model_converter.py | refactor | — |

### Post-Launch Enhancements
| Issue | Note |
|-------|------|
| [#1048](https://github.com/anchapin/ModPorter-AI/issues/1048) IDE/Plugin ecosystem (bridge., Blockbench, VS Code) | post-launch |

---

## Top 3 Priority Issues (Apr 19, 1:33pm — post-v14)

### 🥇 #1: [#1090](https://github.com/anchapin/ModPorter-AI/issues/1090) — Semantic Chunking for Large Mods (Phase 1)

Create has 2,782 recipes and 2,684 models — the largest mod in the canonical set and the one hitting a 36% recipe ceiling. Large Java analyzers and recipe files likely exceed LLM context windows during analysis, causing the AI to truncate or hallucinate mappings. Semantic chunking divides the analysis into coherent sub-tasks (one recipe type at a time, one model family at a time), each within context budget. This is the most direct lever for moving the B2B number beyond 66.4% — specifically targeting the Create recipe floor.

### 🥈 #2: [#1099](https://github.com/anchapin/ModPorter-AI/issues/1099) — Split java_analyzer.py (131K chars)

At 131K characters, `java_analyzer.py` is the largest file in the codebase and handles the critical Java → Bedrock analysis step. It's a bottleneck for every future improvement: adding tree-sitter queries, new entity types, custom recipe heuristics all require touching this file. Splitting it into a proper subpackage accelerates development velocity across all conversion improvements and is prerequisite work for #1090.

### 🥉 #3: [#1098](https://github.com/anchapin/ModPorter-AI/issues/1098) — Consolidate Task Queues → Celery

M5 beta users will be running concurrent conversions. The current dual task_queue.py setup is a reliability risk under load — tasks may drop, retry storms can occur, and there's no visibility into queue depth. Migrating to Celery provides production-grade async task execution, retry policies, monitoring, and horizontal scalability before beta traffic arrives.

---

## Suggested New Issue: Create Recipe Type Converters

The 41.7% recipe ceiling is structurally blocked by 750 Create custom recipe types (milling, crushing, deploying, splashing) with no existing conversion path. These have well-documented Bedrock approximations (custom crafting tables via behavior packs). Filing a dedicated issue would directly move B2B from 41.7% → ~50%+ for the canonical 8-mod set.

---

## Audit Reports

- [v12 — Apr 18 8:48pm](docs/audit-reports/real-world-scan-v12-20260418.md) — B2B 66.4%, 8/8 PASS, recipe +509
- [v13 — Apr 19 12:51am](docs/audit-reports/real-world-scan-v13-20260419.md) — B2B 66.4% stable, M4 complete, #1105 non-std JAR validated
- [**v14 — Apr 19 1:33pm**](docs/audit-reports/real-world-scan-v14-20260419.md) — **B2B 66.4% (3rd stable cycle)**, tree-sitter ✅, minecraft-data 1152 items ✅, confidence scoring ✅, ceiling analysis complete
