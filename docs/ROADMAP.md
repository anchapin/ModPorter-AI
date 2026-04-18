# PortKit (ModPorter-AI) — Development Roadmap

**Last Updated:** 2026-04-18 (v10 audit — 10am)
**Status:** M2 Complete + M3 nearly done (OAuth remaining) | M4 starting
**Repo:** [anchapin/ModPorter-AI](https://github.com/anchapin/ModPorter-AI) | Rebrand to PortKit pending ([#1043](https://github.com/anchapin/ModPorter-AI/issues/1043))
**Target:** Public launch at modporter.ai by June 22, 2026

---

## Executive Summary

PortKit converts Minecraft Java mods to Bedrock add-ons. Positioned as a **B2B conversion accelerator** targeting Marketplace creators.

**Current pipeline maturity: ~63.7% weighted B2B coverage** (v10 audit, Apr 18 — canonical 8 mods, HEAD `d3611dc`).  
**M2 target (60%) exceeded. M3 almost complete** (Stripe ✅, email ✅, feature flags ✅, usage metering ✅ — OAuth remaining).  
**Known gap:** Cutting board name collision still losing ~54 recipes. Fix filed as [#1093](https://github.com/anchapin/ModPorter-AI/issues/1093).  
**Recipe ceiling:** Create's 750 machine recipes (milling/crushing/deploying) are unconvertible — no Bedrock equivalent. Recipe coverage tops out at ~35% without a Create-specific converter.

---

## Conversion Audit History

| Cycle | Date | Mods | Textures | Models | Recipes | Sound | Lang | B2B est. | Key Changes |
|-------|------|------|----------|--------|---------|-------|------|-----------|-------------|
| v1 | Apr 8 | 8 | ~0% | 0% | 0% | 0% | 0% | ~5% | Baseline |
| v2 | Apr 9 | 8 | 54.8% | 0.2% | 0% | 0% | 0% | ~25% | Bulk texture extraction |
| v3 | Apr 10a | 8 | 54.7% | 0% | 0% | 0% | 0% | ~28% | Entity routing fix |
| v4 | Apr 10b | 8 | 54.7% | 0% | 0% | 0% | 0% | ~28% | Agents built, not wired |
| v5 | Apr 11 | 8 | 54.7% | 82.3% | 25.8% | 0% | 0% | ~46% | Model+recipe converters wired |
| v6 | Apr 15 | 30 | 68.7% | 68.3% | 40.2% | 0% | 0% | ~49% | NeoForge fix, 30-mod set |
| v7 | Apr 16 | 8 | 54.7% | 82.3% | 25.8% | ~100% | 89.3% | ~63% 🎯 | Sound+lang, loot tables, spawn rules |
| v8 | Apr 17 | 8 | 54.7% | 82.3% | 25.9% | ~100% | 89.3% | ~63% | Stripe, error handling, custom recipe types (cooking bug) |
| v9 | Apr 18 00:06 | 8 | 54.7% | 82.3% | 26.6% | ~100% | 89.3% | 63.4% | Cooking recipe fix +27, file security, feature flags |
| **v10** | **Apr 18 10:15** | **8** | **54.7%** | **82.3%** | **28.5%** | **~100%** | **89.3%** | **63.7%** | **Cutting board fix +72 (partial), usage metering, transactional email** |

**v10 B2B breakdown:**
| Asset Type | Coverage | Weight | Contribution |
|------------|----------|--------|-------------|
| Texture | 54.7% | 25% | 13.7% |
| Model | 82.3% | 30% | 24.7% |
| Recipe | 28.5% | 20% | 5.7% |
| Sound | ~100% | 10% | 10.0% |
| Localization | 89.3% | 10% | 8.9% |
| Entity | ~15% | 5% | 0.8% |
| **Total** | | | **63.7%** |

---

## Recipe Coverage Ceiling Analysis

| Recipe type | Count (8 mods) | Status |
|-------------|----------------|--------|
| `create:milling` / `crushing` / `deploying` / `splashing` | ~600+ | ❌ No Bedrock equivalent |
| `farmersdelight:cutting` (name collision) | ~54 | ⚠️ Bug [#1093](https://github.com/anchapin/ModPorter-AI/issues/1093) |
| `farmersdelight:cutting` (working) | 72 | ✅ Fixed in #1087 |
| `farmersdelight:cooking` | 27 | ✅ Fixed in #1083 |
| Standard shaped/shapeless/smelting | ~2,900 | ✅ ~35% conversion rate |

**After #1093 fix:** Recipe ~30%, B2B ~64%. Further gains require Create machine converter or entity improvements.

---

## 11-Week Launch Roadmap

### ✅ M1 — Weeks 1-2: Conversion Proof + Pipeline (Complete Apr 10)

### ✅ M2 — Weeks 3-4: Entity Behaviors + Sound/Lang + B2B UX (Complete Apr 16 — 3 weeks early)

### 🔄 M3 — Weeks 5-6: Infrastructure (Due: May 18)

| Issue | Status |
|-------|--------|
| [#970](https://github.com/anchapin/ModPorter-AI/issues/970) Stripe subscription billing | ✅ #1081 |
| [#973](https://github.com/anchapin/ModPorter-AI/issues/973) File upload security | ✅ #1084 |
| [#972](https://github.com/anchapin/ModPorter-AI/issues/972) Feature flags | ✅ #1085 |
| [#977](https://github.com/anchapin/ModPorter-AI/issues/977) Usage limits + metering | ✅ #1088 |
| [#976](https://github.com/anchapin/ModPorter-AI/issues/976) Transactional email | ✅ #1092 |
| [#980](https://github.com/anchapin/ModPorter-AI/issues/980) OAuth login (Discord/GitHub/Google) | **Open — last M3 item** |

### ⏳ M4 — Week 7: Landing Page + Legal + Rebrand (Due: May 25)

| Issue | Priority |
|-------|----------|
| [#978](https://github.com/anchapin/ModPorter-AI/issues/978) Marketing landing page | P1 |
| [#975](https://github.com/anchapin/ModPorter-AI/issues/975) Terms of Service and Privacy Policy | P1 |
| [#979](https://github.com/anchapin/ModPorter-AI/issues/979) Conversion history dashboard | P2 |
| [#1043](https://github.com/anchapin/ModPorter-AI/issues/1043) Rebrand to PortKit | P2 |

### ⏳ M5 — Week 8: Beta Launch (Due: Jun 1)
Target: 20–30 Marketplace creators. Demo mods: Waystones (98% model/88% recipe), Farmer's Delight (88% model/98% lang), Supplementaries (95% model/101% sounds).

### ⏳ M6-M7 — Weeks 9-11: Beta Feedback + Public Launch (Due: Jun 22)

---

## Top 3 Priority Issues (Apr 18, 10am — post-v10)

### 🥇 #1: [#1093](https://github.com/anchapin/ModPorter-AI/issues/1093) — Cutting Board Name Collision (P1)

Follow-up to #1087. Multiple cutting board inputs produce the same output item (e.g., `acacia_log` and `stripped_acacia_log` both produce `acacia_planks`) → recipe_name collision in `bedrock_recipes{}` → ~54 recipes lost. Fix: append primary input to recipe name when a key collision would occur. Recovers ~54 FD recipes, B2B ~64%.

### 🥈 #2: [#980](https://github.com/anchapin/ModPorter-AI/issues/980) — OAuth Login (P1)

Last remaining M3 blocker. Stripe billing, email verification, feature flags, and usage metering are all live. OAuth (Discord/GitHub/Google) completes the auth stack required for beta invitations.

### 🥉 #3: [#978](https://github.com/anchapin/ModPorter-AI/issues/978) — Marketing Landing Page (P2)

Highest-visibility M4 deliverable. Beta creators need a landing page at modporter.ai before invitations go out. Conversion accelerator positioning + demo mods showcase.

---

## Open Issues (12 total — 0 open PRs)

### Conversion pipeline
- [#1093](https://github.com/anchapin/ModPorter-AI/issues/1093) Cutting board name collision **← #1 PRIORITY**

### M3 Infrastructure
- [#980](https://github.com/anchapin/ModPorter-AI/issues/980) OAuth login **← #2 PRIORITY**

### M4 Marketing/Legal
- [#978](https://github.com/anchapin/ModPorter-AI/issues/978) Landing page **← #3 PRIORITY**
- [#975](https://github.com/anchapin/ModPorter-AI/issues/975) ToS/Privacy Policy
- [#979](https://github.com/anchapin/ModPorter-AI/issues/979) History dashboard
- [#1043](https://github.com/anchapin/ModPorter-AI/issues/1043) Rebrand to PortKit

### AI Research (Scout findings — Apr 18)
- [#1089](https://github.com/anchapin/ModPorter-AI/issues/1089) Multi-candidate consistency check
- [#1090](https://github.com/anchapin/ModPorter-AI/issues/1090) Semantic chunking for large mods
- [#1091](https://github.com/anchapin/ModPorter-AI/issues/1091) Per-segment confidence scoring

### Post-Launch / AI
- [#1048](https://github.com/anchapin/ModPorter-AI/issues/1048) IDE plugins
- [#994](https://github.com/anchapin/ModPorter-AI/issues/994) Embedding upgrade
- [#996](https://github.com/anchapin/ModPorter-AI/issues/996) Diffusion LoRA
- [#997](https://github.com/anchapin/ModPorter-AI/issues/997) LLM fine-tune

---

## Audit Reports

- [v7 — Apr 16](docs/audit-reports/real-world-scan-v7-20260416.md) — Sound ~100%, Lang 89.3%, B2B 63.2% ✅
- [v8 — Apr 17](docs/audit-reports/real-world-scan-v8-20260417.md) — B2B 63.2% (flat), cooking recipe bug found
- [v9 — Apr 18 midnight](docs/audit-reports/real-world-scan-v9-20260418.md) — B2B 63.4%, cooking fix +27, cutting board bug #1086 found
- [**v10 — Apr 18 10am**](docs/audit-reports/real-world-scan-v10-20260418.md) — B2B **63.7%**, cutting board +72 (partial), name collision #1093 found
