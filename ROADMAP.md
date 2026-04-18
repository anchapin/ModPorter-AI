# PortKit (ModPorter-AI) — Development Roadmap

**Last Updated:** 2026-04-18 (v11 audit — 7pm ET)
**Status:** M3 Complete ✅ | M4 In Progress | P0 regression in pipeline (#1107)
**Repo:** [anchapin/ModPorter-AI](https://github.com/anchapin/ModPorter-AI) | Rebrand to PortKit pending ([#1043](https://github.com/anchapin/ModPorter-AI/issues/1043))
**Target:** Public launch at modporter.ai by June 22, 2026

---

## Executive Summary

PortKit converts Minecraft Java mods to Bedrock add-ons. Positioned as a **B2B conversion accelerator** targeting Marketplace creators.

**M3 is complete** (all 6 infrastructure issues resolved). M4 landing page shipped. **Active P0 regression** in pipeline: Create crashes due to unsanitized Forge tag slashes in collision guard (#1107).

**True B2B readiness: ~64.4%** (excluding the Create regression introduced by #1094; the collision fix itself delivered +138 recipes, recipe coverage now 32.1%).

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
| v10 | Apr 18 10:15 | 8 | 54.7% | 82.3% | 28.5% | ~100% | 89.3% | 63.7% | Cutting board list-result fix +72 (name collision bug found) |
| **v11** | **Apr 18 19:16** | **8 (7✅ 1❌)** | **54.7%\*** | **82.3%\*** | **32.1%\*** | **~100%\*** | **89.3%\*** | **~64.4%\*** | **Collision fix +138 recipes ✅; Create crash P0 regression ⚠️** |

\* Adjusted figures exclude Create crash (P0 regression #1107). Raw v11: B2B 39.8% (7/8 pass).

**v11 B2B breakdown (adjusted):**
| Asset Type | Coverage | Weight | Contribution |
|------------|----------|--------|-------------|
| Texture | 54.7% | 25% | 13.7% |
| Model | 82.3% | 30% | 24.7% |
| Recipe | 32.1% | 20% | 6.4% |
| Sound | ~100% | 10% | 10.0% |
| Localization | 89.3% | 10% | 8.9% |
| Entity | ~15% | 5% | 0.8% |
| **Total** | | | **~64.4%** |

---

## Recipe Coverage Ceiling Analysis

| Recipe type | Count (8 mods) | Status |
|-------------|----------------|--------|
| `create:milling` / `crushing` / `deploying` / `splashing` | ~600+ | ❌ No Bedrock equivalent |
| `farmersdelight:cutting` | 126 | ✅ All converting (after #1087 + #1094) |
| `farmersdelight:cooking` | 27 | ✅ Fixed in #1083 |
| Forge tag collisions (Create crash) | ~198 recipes trigger crash | 🔴 **P0 regression #1107** |
| Standard shaped/shapeless/smelting | ~2,900 | ✅ ~35% conversion rate |

**After #1107 fix:** Recipe ~32.1% confirmed, B2B ~64.4%. Further gains require texture atlas fix (#1104) or entity improvements.

---

## 11-Week Launch Roadmap

### ✅ M1 — Weeks 1-2: Conversion Proof + Pipeline (Complete Apr 10)

### ✅ M2 — Weeks 3-4: Entity Behaviors + Sound/Lang + B2B UX (Complete Apr 16 — 3 weeks early)

### ✅ M3 — Weeks 5-6: Infrastructure (Complete Apr 18)

| Issue | Status |
|-------|--------|
| [#970](https://github.com/anchapin/ModPorter-AI/issues/970) Stripe subscription billing | ✅ #1081 |
| [#973](https://github.com/anchapin/ModPorter-AI/issues/973) File upload security | ✅ #1084 |
| [#972](https://github.com/anchapin/ModPorter-AI/issues/972) Feature flags | ✅ #1085 |
| [#977](https://github.com/anchapin/ModPorter-AI/issues/977) Usage limits + metering | ✅ #1088 |
| [#976](https://github.com/anchapin/ModPorter-AI/issues/976) Transactional email | ✅ #1092 |
| [#980](https://github.com/anchapin/ModPorter-AI/issues/980) OAuth login (Discord/GitHub/Google) | ✅ #1095 |

### 🔄 M4 — Week 7: Landing Page + Legal + Rebrand (Due: May 25)

| Issue | Status |
|-------|--------|
| [#978](https://github.com/anchapin/ModPorter-AI/issues/978) Marketing landing page | ✅ #1106 |
| [#975](https://github.com/anchapin/ModPorter-AI/issues/975) Terms of Service and Privacy Policy | **Open** |
| [#979](https://github.com/anchapin/ModPorter-AI/issues/979) Conversion history dashboard | Open |
| [#1043](https://github.com/anchapin/ModPorter-AI/issues/1043) Rebrand to PortKit | Open |

### ⏳ M5 — Week 8: Beta Launch (Due: Jun 1)
Requires: ToS/Privacy Policy (#975), OAuth (#1095 ✅), billing (#1081 ✅), email verification (#1092 ✅).

### ⏳ M6-M7 — Weeks 9-11: Beta Feedback + Public Launch (Due: Jun 22)

---

## Top 3 Priority Issues (Apr 18, 7pm — post-v11)

### 🥇 #1: [#1107](https://github.com/anchapin/ModPorter-AI/issues/1107) — Create Crash P0 (must-fix)

Regression from #1094. Forge Ore Dictionary tag IDs contain `/` (e.g., `forge:dyes/black`). The collision guard appends these unsanitized as recipe file path suffixes → `FileNotFoundError` → Create crashes entirely (0 output). Fix: `slug = item_id.split(":")[-1].replace("/", "_")`. One line. Without this fix, Create remains broken and B2B shows 39.8% (raw) instead of ~64.4%.

### 🥈 #2: [#1104](https://github.com/anchapin/ModPorter-AI/issues/1104) — Texture Atlas Unpacking (P1)

JEI at 0% (46 textures missed) and JourneyMap at 7% (22/323). Both use sprite atlas texture packing common in UI mods. Without atlas unpacking, the ~7% of textures from these mods stay at 0. Impact: texture coverage ~57–60% after fix.

### 🥉 #3: [#975](https://github.com/anchapin/ModPorter-AI/issues/975) — Terms of Service + Privacy Policy (P1)

Legal requirement before any real users can sign up via the now-live landing page and OAuth. Needed before M5 beta launch. Blocks sending beta invitations.

---

## Open Issues (21 total — 0 open PRs)

### P0 Pipeline regression
- [#1107](https://github.com/anchapin/ModPorter-AI/issues/1107) Create crash (Forge tag slash) **← #1 PRIORITY**

### P1 Pipeline bugs
- [#1104](https://github.com/anchapin/ModPorter-AI/issues/1104) Texture atlas (JEI 0%, JourneyMap 7%) **← #2 PRIORITY**
- [#1105](https://github.com/anchapin/ModPorter-AI/issues/1105) Non-standard JAR layouts (8 mods zero output)

### M4 Marketing/Legal
- [#975](https://github.com/anchapin/ModPorter-AI/issues/975) ToS/Privacy Policy **← #3 PRIORITY**
- [#979](https://github.com/anchapin/ModPorter-AI/issues/979) History dashboard
- [#1043](https://github.com/anchapin/ModPorter-AI/issues/1043) Rebrand to PortKit

### Refactor/Code Quality (filed Apr 18 by Dev)
- [#1096](https://github.com/anchapin/ModPorter-AI/issues/1096) Replace javalang with tree-sitter (Java 17+)
- [#1097](https://github.com/anchapin/ModPorter-AI/issues/1097) Consolidate backend error-handling files
- [#1098](https://github.com/anchapin/ModPorter-AI/issues/1098) Consolidate task queues → Celery
- [#1099](https://github.com/anchapin/ModPorter-AI/issues/1099) Split java_analyzer.py (131K chars)
- [#1100](https://github.com/anchapin/ModPorter-AI/issues/1100) Replace hardcoded JAVA_TO_BEDROCK_ITEM_MAP
- [#1101](https://github.com/anchapin/ModPorter-AI/issues/1101) Remove dead BM25 fallback
- [#1102](https://github.com/anchapin/ModPorter-AI/issues/1102) Consolidate backend report files
- [#1103](https://github.com/anchapin/ModPorter-AI/issues/1103) Split texture_converter.py and model_converter.py

### AI Research (Scout — Apr 18)
- [#1089](https://github.com/anchapin/ModPorter-AI/issues/1089) Multi-candidate consistency check
- [#1090](https://github.com/anchapin/ModPorter-AI/issues/1090) Semantic chunking for large mods
- [#1091](https://github.com/anchapin/ModPorter-AI/issues/1091) Per-segment confidence scoring

### Post-Launch / AI
- [#1048](https://github.com/anchapin/ModPorter-AI/issues/1048) IDE plugins | [#994](https://github.com/anchapin/ModPorter-AI/issues/994) Embedding upgrade | [#996](https://github.com/anchapin/ModPorter-AI/issues/996) Diffusion LoRA | [#997](https://github.com/anchapin/ModPorter-AI/issues/997) LLM fine-tune

---

## Audit Reports

- [v9 — Apr 18 midnight](docs/audit-reports/real-world-scan-v9-20260418.md) — B2B 63.4%, cooking fix +27, cutting board bug #1086
- [v10 — Apr 18 10am](docs/audit-reports/real-world-scan-v10-20260418.md) — B2B 63.7%, cutting board +72 (partial), name collision #1093
- [**v11 — Apr 18 7pm**](docs/audit-reports/real-world-scan-v11-20260418.md) — B2B **~64.4%** (adjusted), collision fix +138 recipes, Create crash regression #1107
