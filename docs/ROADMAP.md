# PortKit (ModPorter-AI) — Development Roadmap

**Last Updated:** 2026-04-18 (v12 audit — 8:48pm ET)
**Status:** M3 Complete ✅ | M4 In Progress (landing page + ToS done) | 8/8 PASS ✅
**Repo:** [anchapin/ModPorter-AI](https://github.com/anchapin/ModPorter-AI) | Rebrand to PortKit pending ([#1043](https://github.com/anchapin/ModPorter-AI/issues/1043))
**Target:** Public launch at modporter.ai by June 22, 2026

---

## Executive Summary

PortKit converts Minecraft Java mods to Bedrock add-ons. Positioned as a **B2B conversion accelerator** targeting Marketplace creators.

**B2B readiness: 66.4%** (v12, 8/8 PASS, no crashes). M3 complete (all 6 infrastructure issues). M4 landing page and ToS/Privacy shipped. Recipe coverage at all-time high of 41.7% after collision guard fix fully effective across Create (+371), FD (+74), Supplementaries (+61).

---

## Conversion Audit History

| Cycle | Date | Mods | Textures | Models | Recipes | Sound | Lang | B2B est. | Key Changes |
|-------|------|------|----------|--------|---------|-------|------|-----------|-------------|
| v1 | Apr 8 | 8 | ~0% | 0% | 0% | 0% | 0% | ~5% | Baseline |
| v2 | Apr 9 | 8 | 54.8% | 0.2% | 0% | 0% | 0% | ~25% | Bulk texture extraction |
| v3–v4 | Apr 10 | 8 | 54.7% | 0% | 0% | 0% | 0% | ~28% | Entity routing fix; agents built |
| v5 | Apr 11 | 8 | 54.7% | 82.3% | 25.8% | 0% | 0% | ~46% | Model+recipe converters wired |
| v6 | Apr 15 | 30 | 68.7% | 68.3% | 40.2% | 0% | 0% | ~49% | NeoForge fix, 30-mod set |
| v7 | Apr 16 | 8 | 54.7% | 82.3% | 25.8% | ~100% | 89.3% | ~63% 🎯 | Sound+lang, loot tables, spawn rules |
| v8 | Apr 17 | 8 | 54.7% | 82.3% | 25.9% | ~100% | 89.3% | ~63% | Stripe, error handling (cooking recipe bug found) |
| v9 | Apr 18 00:06 | 8 | 54.7% | 82.3% | 26.6% | ~100% | 89.3% | 63.4% | Cooking recipe fix +27 (cutting board bug found) |
| v10 | Apr 18 10:15 | 8 | 54.7% | 82.3% | 28.5% | ~100% | 89.3% | 63.7% | Cutting board fix +72 (name collision bug found) |
| v11 | Apr 18 19:16 | 7/8 ⚠️ | 54.7%* | 82.3%* | 32.1%* | ~100%* | 89.3%* | ~64.4%* | Collision fix +138 recipes; Create crash P0 regression |
| **v12** | **Apr 18 20:48** | **8/8 ✅** | **54.7%** | **82.3%** | **41.7%** | **~100%** | **89.3%** | **66.4% 🎯** | **Create restored; collision guard fully effective** |

\* v11 adjusted (Create excluded due to crash)

**v12 B2B breakdown:**
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

## Texture Ceiling Analysis (v12 Finding)

JEI (0%) and JourneyMap (7%) are **structural ceilings**, not tooling gaps:

- **JEI**: All 46 textures are GUI UI elements (buttons, backgrounds, arrows). Bedrock uses a completely different JSON-based UI system — 0% is the correct result.
- **JourneyMap**: 323 PNGs = 239 minimap UI theme images + 218 vanilla entity icons (`minecraft` namespace, correctly excluded) + 105 Quark compat icons. No item/block textures with Bedrock equivalents. 7% is the true ceiling.

The atlas unpacking PR (#1111) is deployed and will benefit **content mods** using sprite-sheet atlases. It does not affect UI mods.

**54.7% is approximately the real texture ceiling for this canonical 8-mod set.**

---

## Recipe Coverage Ceiling Analysis

| Recipe type | Count (8 mods) | Status |
|-------------|----------------|--------|
| `create:milling` / `crushing` / `deploying` / `splashing` | ~602 | ❌ No Bedrock equivalent — hard ceiling |
| `farmersdelight:cutting` | 126 | ✅ All converting |
| `farmersdelight:cooking` | 27 | ✅ Fixed in #1083 |
| Forge tag collisions | Fixed by #1094 + #1108 | ✅ All recovered |
| Standard shaped/shapeless/smelting | ~3,024 | ~30% conversion rate |

**41.7% recipe ceiling likely near ~45–47%** until Create-specific recipe types get Bedrock mappings.

---

## 11-Week Launch Roadmap

### ✅ M1 — Weeks 1-2: Conversion Proof + Pipeline (Complete Apr 10)

### ✅ M2 — Weeks 3-4: Entity Behaviors + Sound/Lang + B2B UX (Complete Apr 16)

### ✅ M3 — Weeks 5-6: Infrastructure (Complete Apr 18)

| Issue | PR | Status |
|-------|----|--------|
| [#970](https://github.com/anchapin/ModPorter-AI/issues/970) Stripe subscription billing | #1081 | ✅ |
| [#973](https://github.com/anchapin/ModPorter-AI/issues/973) File upload security | #1084 | ✅ |
| [#972](https://github.com/anchapin/ModPorter-AI/issues/972) Feature flags | #1085 | ✅ |
| [#977](https://github.com/anchapin/ModPorter-AI/issues/977) Usage limits + metering | #1088 | ✅ |
| [#976](https://github.com/anchapin/ModPorter-AI/issues/976) Transactional email | #1092 | ✅ |
| [#980](https://github.com/anchapin/ModPorter-AI/issues/980) OAuth login | #1095 | ✅ |

### 🔄 M4 — Week 7: Landing Page + Legal + Rebrand (Due: May 25)

| Issue | PR | Status |
|-------|----|--------|
| [#978](https://github.com/anchapin/ModPorter-AI/issues/978) Marketing landing page | #1106 | ✅ |
| [#975](https://github.com/anchapin/ModPorter-AI/issues/975) Terms of Service and Privacy Policy | #1112 | ✅ |
| [#979](https://github.com/anchapin/ModPorter-AI/issues/979) Conversion history dashboard | — | **Open** |
| [#1043](https://github.com/anchapin/ModPorter-AI/issues/1043) Rebrand to PortKit | — | **Open** |

### ⏳ M5 — Week 8: Beta Launch (Due: Jun 1)
Requires: #979 history dashboard, #1043 rebrand, plus all M3 infra (complete ✅).

### ⏳ M6-M7 — Weeks 9-11: Beta Feedback + Public Launch (Due: Jun 22)

---

## Top 3 Priority Issues (Apr 18, 8:48pm — post-v12)

### 🥇 #1: [#1105](https://github.com/anchapin/ModPorter-AI/issues/1105) — Non-Standard JAR Layouts (P1, Pipeline)

8 mods in the 30-mod test produce **zero output** due to non-standard JAR structures (REI, Storage Drawers, Astral Sorcery, Silent Gear, Tinkers Construct, ProjectE, AbyssalCraft, Compact Machines). These are popular mods — fixing this would meaningfully expand the effective mod coverage percentage. Direct B2B pipeline impact.

### 🥈 #2: [#1043](https://github.com/anchapin/ModPorter-AI/issues/1043) — Rebrand to PortKit (M4)

The landing page and OAuth are live at modporter.ai — but the product is still called "ModPorter-AI" everywhere in the codebase, README, and GitHub repo. Needs to be PortKit before beta invitations go out. Alex confirmed PortKit is the name. Dependency for M5 beta launch.

### 🥉 #3: [#979](https://github.com/anchapin/ModPorter-AI/issues/979) — Conversion History Dashboard (M4)

Per-user conversion stats dashboard for beta. Creators need to see their past conversions, success rates, and download history. Required for M5 beta launch alongside rebrand.

---

## Open Issues (20 total — 2 open PRs: #1109 security, #1110 perf)

### P1 Pipeline
- [#1105](https://github.com/anchapin/ModPorter-AI/issues/1105) Non-standard JAR layouts (8 mods zero output) **← #1 PRIORITY**

### M4 Marketing/Legal/Product
- [#1043](https://github.com/anchapin/ModPorter-AI/issues/1043) Rebrand to PortKit **← #2 PRIORITY**
- [#979](https://github.com/anchapin/ModPorter-AI/issues/979) History dashboard **← #3 PRIORITY**

### Automated PRs (Open)
- [#1109](https://github.com/anchapin/ModPorter-AI/pull/1109) Security: prevent info leakage in upload error response
- [#1110](https://github.com/anchapin/ModPorter-AI/pull/1110) Perf: optimize BedrockDocsPanel search filtering

### Refactor/Code Quality
- [#1096](https://github.com/anchapin/ModPorter-AI/issues/1096) Replace javalang with tree-sitter
- [#1097](https://github.com/anchapin/ModPorter-AI/issues/1097) Consolidate backend error-handling files
- [#1098](https://github.com/anchapin/ModPorter-AI/issues/1098) Consolidate task queues → Celery
- [#1099](https://github.com/anchapin/ModPorter-AI/issues/1099) Split java_analyzer.py (131K chars)
- [#1100](https://github.com/anchapin/ModPorter-AI/issues/1100) Replace hardcoded JAVA_TO_BEDROCK_ITEM_MAP
- [#1101](https://github.com/anchapin/ModPorter-AI/issues/1101) Remove dead BM25 fallback
- [#1102](https://github.com/anchapin/ModPorter-AI/issues/1102) Consolidate backend report files
- [#1103](https://github.com/anchapin/ModPorter-AI/issues/1103) Split texture_converter.py and model_converter.py

### AI Research
- [#1089](https://github.com/anchapin/ModPorter-AI/issues/1089) Multi-candidate consistency check
- [#1090](https://github.com/anchapin/ModPorter-AI/issues/1090) Semantic chunking for large mods
- [#1091](https://github.com/anchapin/ModPorter-AI/issues/1091) Per-segment confidence scoring

### Post-Launch
- [#994](https://github.com/anchapin/ModPorter-AI/issues/994) Embedding upgrade | [#996](https://github.com/anchapin/ModPorter-AI/issues/996) Diffusion LoRA | [#997](https://github.com/anchapin/ModPorter-AI/issues/997) LLM fine-tune | [#1048](https://github.com/anchapin/ModPorter-AI/issues/1048) IDE plugins

---

## Audit Reports

- [v9 — Apr 18 midnight](docs/audit-reports/real-world-scan-v9-20260418.md) — B2B 63.4%, cooking fix +27
- [v10 — Apr 18 10am](docs/audit-reports/real-world-scan-v10-20260418.md) — B2B 63.7%, cutting board +72
- [v11 — Apr 18 7pm](docs/audit-reports/real-world-scan-v11-20260418.md) — B2B ~64.4% adj, Create crash regression
- [**v12 — Apr 18 8:48pm**](docs/audit-reports/real-world-scan-v12-20260418.md) — **B2B 66.4%** 🎯, 8/8 PASS, recipe +509 from v10
