# PortKit — Development Roadmap

**Last Updated:** 2026-04-19 (v15 audit — 7:53pm ET)
**Status:** M1–M4 ✅ | M5 In Progress (beta launch) | 8/8 PASS ✅ | B2B 66.4%
**Repo:** [anchapin/ModPorter-AI](https://github.com/anchapin/ModPorter-AI) | Rebranded to PortKit ✅ (#1114)
**Target:** Public launch at modporter.ai by June 22, 2026

---

## Executive Summary

PortKit converts Minecraft Java mods to Bedrock add-ons. Positioned as a **B2B conversion accelerator** targeting Marketplace creators.

**B2B readiness: 66.4%** (v15, 8/8 PASS). M1–M4 all complete. B2B stable for 4 cycles (v12→v15). The pipeline now handles standard and non-standard JAR layouts, Java 17+ mods (tree-sitter), 1,152 item mappings (minecraft-data), per-segment confidence scoring, semantic chunking for large mods, and a modular java_analyzer package. The 66.4% ceiling is structural: Create's 750 custom recipe types (milling/crushing/deploying/splashing, no Bedrock equivalent) and JEI/JourneyMap as GUI-only mods. **#1119 (Create recipe type converters) is the next ceiling-breaker.**

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
| **v15** | **Apr 19 19:53** | **8/8 ✅** | **54.7%** | **82.3%** | **41.7%** | **~100%** | **89.3%** | **66.4% ✅** | **semantic chunking ✅, java_analyzer split ✅ (6 modules), Celery ✅, #1119 filed** |

\* v11 adjusted (Create excluded due to crash)

**v15 B2B breakdown:**
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

## Structural Ceiling Analysis (Audit-Verified, v12–v15 stable — 4 cycles)

### Texture — 54.7% ceiling
- **JEI (0%)**: All textures are GUI sprites packed in atlases — no Bedrock UI equivalent. 0% is correct/expected.
- **JourneyMap (7%)**: Minimap UI theme images + vanilla entity icons referenced by namespace. 7% is the true ceiling for this mod.
- **Create (49%)**: Many textures tied to custom block animations/mechanisms that don't have direct Bedrock mappings.
- **Non-standard JAR mods** (REI, Storage Drawers, etc.): Now supported via #1105 fallback scanner — expected to improve 30-mod aggregate.
- **Next lever**: Custom entity texture path expansion (FM-001 partial fix) and block state texture coverage.

### Recipe — 41.7% ceiling (NEXT CEILING-BREAKER: #1119)
- **Create custom types (750 recipes / 27%)**: `create:milling`, `crushing`, `deploying`, `splashing` — zero Bedrock equivalents. Hard ceiling until #1119 Create-specific converters are implemented.
- **Semantic chunking (#1120) now deployed**: Infrastructure ready to feed Create recipe chunks to type-specific converters. #1119 will leverage this directly.
- **Standard ceiling without Create customs**: ~47–50% — FD cooking_pot, cutting board, iron chests at ~48–94%.
- **minecraft-data item map** (#1117): 1,152 items — benefits 30-mod set with diverse non-vanilla items.

### Model — 82.3% ceiling
- Solid baseline. Drag from Create's custom parent model paths and Iron Chests item models.
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
**Next B2B ceiling break requires #1119 (Create recipe type converters).**

### ⏳ M6-M7 — Weeks 9-11: Beta Feedback + Public Launch (Jun 22)

---

## Open Issues (10 total — 0 open PRs)

### Conversion Quality / AI Engine
| Issue | Labels | Priority |
|-------|--------|----------|
| [#1119](https://github.com/anchapin/ModPorter-AI/issues/1119) **Create mod: converters for custom recipe types** (milling, crushing, deploying, splashing) | P1, enhancement, component:recipe-conversion | **🥇 #1 — breaks the 66.4% ceiling; semantic chunker (#1120) ready to feed it** |
| [#1089](https://github.com/anchapin/ModPorter-AI/issues/1089) Multi-candidate consistency check | phase:2, priority:medium | 🥈 #2 — halluci­nation guard for AI-generated Bedrock code; complements confidence scoring |
| [#994](https://github.com/anchapin/ModPorter-AI/issues/994) Upgrade embedding model ada-002 → text-embedding-3 | post-launch | — |
| [#996](https://github.com/anchapin/ModPorter-AI/issues/996) Diffusion LoRA for texture pairs | post-launch | — |
| [#997](https://github.com/anchapin/ModPorter-AI/issues/997) Fine-tune open-weights LLM | post-launch | — |

### Refactor / Tech Debt
| Issue | Labels | Priority |
|-------|--------|----------|
| [#1103](https://github.com/anchapin/ModPorter-AI/issues/1103) Split texture_converter.py (57K) + model_converter.py (32K) | refactor | 🥉 #3 — same pattern as #1099 (java_analyzer now done); improves dev velocity for texture/model improvements |
| [#1097](https://github.com/anchapin/ModPorter-AI/issues/1097) Consolidate 5 backend error-handling files | refactor | — |
| [#1101](https://github.com/anchapin/ModPorter-AI/issues/1101) Remove dead BM25 fallback | refactor | — |
| [#1102](https://github.com/anchapin/ModPorter-AI/issues/1102) Consolidate 4 backend report files | refactor | — |

### Post-Launch Enhancements
| Issue | Note |
|-------|------|
| [#1048](https://github.com/anchapin/ModPorter-AI/issues/1048) IDE/Plugin ecosystem (bridge., Blockbench, VS Code) | post-launch |

---

## Top 3 Priority Issues (Apr 19, 7:53pm — post-v15)

### 🥇 #1: [#1119](https://github.com/anchapin/ModPorter-AI/issues/1119) — Create Custom Recipe Type Converters (P1)

The only remaining lever to move B2B past 66.4% on the canonical 8-mod set. Create's 750 recipes (milling, crushing, deploying, splashing) are the single largest uncovered category. With semantic chunking (#1120) now deployed, the pipeline can isolate each Create recipe type as an individual chunk and pass it to a dedicated converter. Bedrock behavior pack approximations exist for all four types. Implementing converters for these would push Create's recipe coverage from 36% → potentially 60%+, and aggregate recipe coverage from 41.7% → ~50%+, lifting B2B to ~68%.

### 🥈 #2: [#1089](https://github.com/anchapin/ModPorter-AI/issues/1089) — Multi-Candidate Consistency Check (Phase 2)

With per-segment confidence scoring (#1118) already deployed, the next quality layer is a training-free consistency check: generate N candidate Bedrock outputs per Java segment, apply conformal prediction to identify the most reliable one, and flag inconsistent candidates rather than arbitrarily picking one. This reduces hallucination in AI-generated Bedrock entity behaviors and reduces manual review burden for beta users — directly improving the B2B creator experience.

### 🥉 #3: [#1103](https://github.com/anchapin/ModPorter-AI/issues/1103) — Split texture_converter.py (57K) + model_converter.py (32K)

Following the pattern of #1099 (java_analyzer, 131K → 6 modules, now complete), texture_converter.py at 57K and model_converter.py at 32K are the next largest single-file bottlenecks. Model coverage is the second highest-weight factor in B2B (30%). Splitting these into focused submodules (e.g., by block/item/entity/animation) enables targeted improvements to specific texture and model types without touching the entire converter on every change.

---

## Audit Reports

- [v12 — Apr 18 8:48pm](docs/audit-reports/real-world-scan-v12-20260418.md) — B2B 66.4%, 8/8 PASS, recipe +509
- [v13 — Apr 19 12:51am](docs/audit-reports/real-world-scan-v13-20260419.md) — B2B 66.4% stable, M4 complete, #1105 non-std JAR validated
- [v14 — Apr 19 1:33pm](docs/audit-reports/real-world-scan-v14-20260419.md) — B2B 66.4% (3rd cycle), tree-sitter, item map 1152, confidence scoring, ceiling confirmed
- [**v15 — Apr 19 7:53pm**](docs/audit-reports/real-world-scan-v15-20260419.md) — **B2B 66.4% (4th cycle)**, semantic chunking ✅, java_analyzer split ✅, Celery ✅, #1119 filed as P1 ceiling-breaker
