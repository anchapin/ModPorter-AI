# PortKit — Development Roadmap

**Last Updated:** 2026-04-19 (v13 audit — 12:51am ET)
**Status:** M3 ✅ | M4 ✅ | M5 In Progress (beta launch) | 8/8 PASS ✅
**Repo:** [anchapin/ModPorter-AI](https://github.com/anchapin/ModPorter-AI) | Rebranded to PortKit ✅ (#1114)
**Target:** Public launch at modporter.ai by June 22, 2026

---

## Executive Summary

PortKit converts Minecraft Java mods to Bedrock add-ons. Positioned as a **B2B conversion accelerator** targeting Marketplace creators.

**B2B readiness: 66.4%** (v13, 8/8 PASS, no regressions). M3 and M4 both complete. All major infrastructure, landing page, legal, dashboard, and rebrand shipped. Pipeline now handles both standard and non-standard JAR layouts. Heading into M5 beta launch.

---

## Conversion Audit History

| Cycle | Date | Mods | Textures | Models | Recipes | Sound | Lang | B2B est. | Key Changes |
|-------|------|------|----------|--------|---------|-------|------|-----------|-------------|
| v1 | Apr 8 | 8 | ~0% | 0% | 0% | 0% | 0% | ~5% | Baseline |
| v2 | Apr 9 | 8 | 54.8% | 0.2% | 0% | 0% | 0% | ~25% | Bulk texture extraction |
| v3–v4 | Apr 10 | 8 | 54.7% | 0% | 0% | 0% | 0% | ~28% | Entity routing fix |
| v5 | Apr 11 | 8 | 54.7% | 82.3% | 25.8% | 0% | 0% | ~46% | Model+recipe converters wired |
| v6 | Apr 15 | 30 | 68.7% | 68.3% | 40.2% | 0% | 0% | ~49% | NeoForge fix, 30-mod set |
| v7 | Apr 16 | 8 | 54.7% | 82.3% | 25.8% | ~100% | 89.3% | ~63% 🎯 | Sound+lang, loot tables, spawn rules |
| v8 | Apr 17 | 8 | 54.7% | 82.3% | 25.9% | ~100% | 89.3% | ~63% | Stripe, error handling |
| v9 | Apr 18 00:06 | 8 | 54.7% | 82.3% | 26.6% | ~100% | 89.3% | 63.4% | Cooking recipe fix +27 |
| v10 | Apr 18 10:15 | 8 | 54.7% | 82.3% | 28.5% | ~100% | 89.3% | 63.7% | Cutting board fix +72 |
| v11 | Apr 18 19:16 | 7/8 ⚠️ | 54.7%* | 82.3%* | 32.1%* | ~100%* | 89.3%* | ~64.4%* | Collision fix +138; Create crash P0 |
| v12 | Apr 18 20:48 | 8/8 ✅ | 54.7% | 82.3% | 41.7% | ~100% | 89.3% | 66.4% 🎯 | Create restored; recipe +509 total |
| **v13** | **Apr 19 00:51** | **8/8 ✅** | **54.7%** | **82.3%** | **41.7%** | **~100%** | **89.3%** | **66.4% ✅** | **Non-std JAR fix ✅, rebrand ✅, M4 complete ✅** |

\* v11 adjusted (Create excluded due to crash)

**v13 B2B breakdown:**
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

## Structural Ceiling Notes (Audit-Verified)

### Texture (54.7% ceiling for canonical 8)
- **JEI (0%)**: All textures are GUI UI elements — no Bedrock equivalent. 0% is correct.
- **JourneyMap (7%)**: Minimap UI theme images + vanilla `minecraft`-namespace entity icons. 7% is the true ceiling.
- **Non-standard JAR mods** (REI, Storage Drawers, etc.): Now supported via #1105 fallback scanner. Expected to bring 30-mod texture coverage up from 68.7%.

### Recipe (41.7% ceiling for canonical 8)
- **Create custom recipe types** (~602 recipes): `create:milling`, `crushing`, `deploying`, `splashing` — no direct Bedrock equivalent. Hard ceiling until Create-specific mappings are added.
- **Standard recipe ceiling**: ~45–47% when Create custom types are excluded.

---

## 11-Week Launch Roadmap

### ✅ M1 — Weeks 1-2: Conversion Proof + Pipeline (Complete Apr 10)

### ✅ M2 — Weeks 3-4: Entity Behaviors + Sound/Lang + B2B UX (Complete Apr 16)

### ✅ M3 — Weeks 5-6: Infrastructure (Complete Apr 18)

All 6 infrastructure issues resolved: Stripe (#970), file security (#973), feature flags (#972), usage limits (#977), transactional email (#976), OAuth login (#980).

### ✅ M4 — Week 7: Landing Page + Legal + Rebrand (Complete Apr 19)

| Issue | Status |
|-------|--------|
| [#978](https://github.com/anchapin/ModPorter-AI/issues/978) Marketing landing page | ✅ #1106 |
| [#975](https://github.com/anchapin/ModPorter-AI/issues/975) Terms of Service and Privacy Policy | ✅ #1112 |
| [#979](https://github.com/anchapin/ModPorter-AI/issues/979) Conversion history dashboard | ✅ #1115 |
| [#1043](https://github.com/anchapin/ModPorter-AI/issues/1043) Rebrand to PortKit | ✅ #1114 |

### 🔄 M5 — Week 8: Beta Launch (Due: Jun 1)

All M4 prerequisites complete. Ready for beta invitations. Key M5 work:
- [ ] Beta user onboarding flow
- [ ] Conversion quality improvements (#1096, #1100)
- [ ] Confidence scoring for B2B users (#1091)

### ⏳ M6-M7 — Weeks 9-11: Beta Feedback + Public Launch (Due: Jun 22)

---

## Open Issues (15 total — 0 open PRs)

### Conversion Quality / AI Engine
- [#1096](https://github.com/anchapin/ModPorter-AI/issues/1096) Replace javalang with tree-sitter for Java 17+ support **← #1 PRIORITY**
- [#1100](https://github.com/anchapin/ModPorter-AI/issues/1100) Replace hardcoded JAVA_TO_BEDROCK_ITEM_MAP with minecraft-data JSON **← #2 PRIORITY**
- [#1091](https://github.com/anchapin/ModPorter-AI/issues/1091) Per-segment confidence scoring (priority:high, phase:2) **← #3 PRIORITY**
- [#1090](https://github.com/anchapin/ModPorter-AI/issues/1090) Semantic chunking for large mods (priority:medium, phase:1)
- [#1089](https://github.com/anchapin/ModPorter-AI/issues/1089) Multi-candidate consistency check (priority:medium, phase:2)

### Refactor / Code Quality
- [#1097](https://github.com/anchapin/ModPorter-AI/issues/1097) Consolidate backend error-handling files
- [#1098](https://github.com/anchapin/ModPorter-AI/issues/1098) Consolidate task queues → Celery
- [#1099](https://github.com/anchapin/ModPorter-AI/issues/1099) Split java_analyzer.py (131K chars)
- [#1100](https://github.com/anchapin/ModPorter-AI/issues/1100) Replace hardcoded item map (also conversion quality)
- [#1101](https://github.com/anchapin/ModPorter-AI/issues/1101) Remove dead BM25 fallback
- [#1102](https://github.com/anchapin/ModPorter-AI/issues/1102) Consolidate backend report files
- [#1103](https://github.com/anchapin/ModPorter-AI/issues/1103) Split texture_converter.py and model_converter.py

### Post-Launch Enhancements
- [#994](https://github.com/anchapin/ModPorter-AI/issues/994) Embedding upgrade (ada-002 → text-embedding-3)
- [#996](https://github.com/anchapin/ModPorter-AI/issues/996) Diffusion LoRA for texture pairs
- [#997](https://github.com/anchapin/ModPorter-AI/issues/997) Fine-tune open-weights LLM
- [#1048](https://github.com/anchapin/ModPorter-AI/issues/1048) IDE/Plugin ecosystem integration

---

## Top 3 Priority Issues (Apr 19, 12:51am — post-v13)

### 🥇 #1: [#1096](https://github.com/anchapin/ModPorter-AI/issues/1096) — Replace javalang with tree-sitter (Conversion Quality)

`javalang` cannot parse Java 17+ features: records, sealed classes, text blocks, pattern matching. Modern mods (1.20+) increasingly use these. tree-sitter supports the full Java grammar and is production-proven. Failure to parse modern Java means the analyzer falls back to heuristics, reducing recipe and entity accuracy for new mods. Direct B2B impact as the mod ecosystem moves to Java 17+.

### 🥈 #2: [#1100](https://github.com/anchapin/ModPorter-AI/issues/1100) — Replace Hardcoded Item Map with minecraft-data JSON

`JAVA_TO_BEDROCK_ITEM_MAP` is hand-curated (~50–100 entries). The `minecraft-data` package has 1,000+ auto-generated item mappings kept current with each MC release. Replacing it would substantially improve recipe conversion fidelity (more source items resolve to valid Bedrock equivalents) and reduce manual review flags. Has `conversion-quality` label.

### 🥉 #3: [#1091](https://github.com/anchapin/ModPorter-AI/issues/1091) — Per-Segment Confidence Scoring (priority:high, phase:2)

For the B2B positioning ("accelerator, not 100% automation"), confidence scores per converted segment let creators know exactly which parts of their pack need manual review. This directly reduces creator review time and is a key differentiator vs manual conversion. `priority:high` label confirms scope intent.

---

## Audit Reports

- [v10 — Apr 18 10am](docs/audit-reports/real-world-scan-v10-20260418.md) — B2B 63.7%, cutting board +72
- [v11 — Apr 18 7pm](docs/audit-reports/real-world-scan-v11-20260418.md) — B2B ~64.4% adj, Create crash regression
- [v12 — Apr 18 8:48pm](docs/audit-reports/real-world-scan-v12-20260418.md) — B2B 66.4%, 8/8 PASS, recipe +509
- [**v13 — Apr 19 12:51am**](docs/audit-reports/real-world-scan-v13-20260419.md) — **B2B 66.4% stable**, M4 complete, #1105 non-std JAR fix validated
