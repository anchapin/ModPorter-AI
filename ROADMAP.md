# PortKit (ModPorter-AI) — Development Roadmap

**Last Updated:** 2026-04-18 (v9 audit)
**Status:** M2 Complete + M3 Infrastructure underway
**Repo:** [anchapin/ModPorter-AI](https://github.com/anchapin/ModPorter-AI) | Rebrand to PortKit pending ([#1043](https://github.com/anchapin/ModPorter-AI/issues/1043))
**Target:** Public launch at modporter.ai by June 22, 2026

---

## Executive Summary

PortKit converts Minecraft Java mods to Bedrock add-ons. Positioned as a **B2B conversion accelerator** targeting Marketplace creators.

**Current pipeline maturity: ~63.4% weighted B2B coverage** (v9 audit, Apr 18 — canonical 8 mods, HEAD `9c6bd27`).  
**M2 target (60%) exceeded.** Stripe billing, file upload security, and feature flags shipped. M3 infrastructure underway.  
**Known gap:** Cutting board recipes still broken — `block_item_generator.py` list result collision. Fix filed as [#1086](https://github.com/anchapin/ModPorter-AI/issues/1086).

---

## Conversion Audit History

| Cycle | Date | Mods | Textures | Models | Recipes | Sound | Lang | B2B est. | Key Changes |
|-------|------|------|----------|--------|---------|-------|------|-----------|-------------|
| v1 | Apr 8 | 8 | ~0% | 0% | 0% | 0% | 0% | ~5% | Baseline |
| v2 | Apr 9 | 8 | 54.8% | 0.2% | 0% | 0% | 0% | ~25% | Bulk texture extraction |
| v3 | Apr 10a | 8 | 54.7% | 0% | 0% | 0% | 0% | ~28% | Entity routing fix |
| v4 | Apr 10b | 8 | 54.7% | 0% | 0% | 0% | 0% | ~28% | Agents built, not yet wired |
| v5 | Apr 11 | 8 | 54.7% | 82.3% | 25.8% | 0% | 0% | ~46% | Model+recipe converters wired |
| v6 | Apr 15 | 30 | 68.7% | 68.3% | 40.2% | 0% | 0% | ~49% | NeoForge fix, 30-mod set |
| v7 | Apr 16 | 8 | 54.7% | 82.3% | 25.8% | ~100% | 89.3% | ~63% 🎯 | Sound+lang, loot tables, spawn rules |
| v8 | Apr 17 | 8 | 54.7% | 82.3% | 25.9% | ~100% | 89.3% | ~63% | Stripe, Error handling, Custom recipe types (#1079 — still buggy) |
| **v9** | **Apr 18** | **8** | **54.7%** | **82.3%** | **26.6%** | **~100%** | **89.3%** | **63.4%** | **Cooking recipe fix (+27), File security (#1084), Feature flags (#1085)** |

**v9 B2B breakdown:**
| Asset Type | Coverage | Weight | Contribution |
|------------|----------|--------|-------------|
| Texture | 54.7% | 25% | 13.7% |
| Model | 82.3% | 30% | 24.7% |
| Recipe | 26.6% | 20% | 5.3% |
| Sound | ~100% | 10% | 10.0% |
| Localization | 89.3% | 10% | 8.9% |
| Entity | ~15% | 5% | 0.8% |
| **Total** | | | **63.4%** |

---

## Recipe Coverage Ceiling Analysis

Recipe coverage is **capped by unconvertible custom machine recipes**, primarily in Create:

| Recipe type | Count (8 mods) | Status |
|-------------|----------------|--------|
| `create:milling` / `crushing` / `deploying` / `splashing` | ~600+ | ❌ No Bedrock equivalent |
| `farmersdelight:cutting` (list result) | 126 | ⚠️ Bug [#1086](https://github.com/anchapin/ModPorter-AI/issues/1086) |
| `farmersdelight:cooking` | 27 | ✅ Fixed in #1083 |
| Standard shaped/shapeless/smelting | ~2,900 | ✅ ~35% conversion rate |

**After #1086 fix:** Recipe ~30%, B2B ~64%. Further gains require Create machine converter (post-launch) or adjusting recipe weight in B2B score.

---

## 11-Week Launch Roadmap

### ✅ M1 — Weeks 1-2: Conversion Proof + Pipeline (Complete Apr 10)

### ✅ M2 — Weeks 3-4: Entity Behaviors + Sound/Lang + B2B UX (Complete Apr 16 — 3 weeks early)

| Issue | Status |
|-------|--------|
| #971 E2E validation (20+ mods) | ✅ |
| #1003 Entity behaviors (spawn rules, loot tables) | ✅ |
| #1002 Sound + localization | ✅ |
| #1067 Conversion Report handoff (B2B UX) | ✅ |
| #1066 Production secrets hardening | ✅ |
| #1068 Error handling & user-visible feedback | ✅ |
| #1078 Custom Forge recipe types | ✅ (partial — cooking fixed; cutting board [#1086] pending) |

### 🔄 M3 — Weeks 5-6: Infrastructure (Due: May 18)

| Issue | Status | Priority |
|-------|--------|----------|
| [#970](https://github.com/anchapin/ModPorter-AI/issues/970) Stripe subscription billing | ✅ Closed (#1081) | Done |
| [#973](https://github.com/anchapin/ModPorter-AI/issues/973) File upload security | ✅ Closed (#1084) | Done |
| [#972](https://github.com/anchapin/ModPorter-AI/issues/972) Feature flags | ✅ Closed (#1085) | Done |
| [#1086](https://github.com/anchapin/ModPorter-AI/issues/1086) Cutting board recipe fix | Open | **P1 — quick fix** |
| [#977](https://github.com/anchapin/ModPorter-AI/issues/977) Usage limits + metering | Open | **P1 — Stripe tiers need enforcement** |
| [#976](https://github.com/anchapin/ModPorter-AI/issues/976) Transactional email | Open | P2 |
| [#980](https://github.com/anchapin/ModPorter-AI/issues/980) OAuth login | Open | P2 |

### ⏳ M4 — Week 7: Landing Page + Legal + Rebrand (Due: May 25)

| Issue | Description |
|-------|-------------|
| [#978](https://github.com/anchapin/ModPorter-AI/issues/978) | Marketing landing page |
| [#975](https://github.com/anchapin/ModPorter-AI/issues/975) | Terms of Service and Privacy Policy |
| [#979](https://github.com/anchapin/ModPorter-AI/issues/979) | Conversion history dashboard |
| [#1043](https://github.com/anchapin/ModPorter-AI/issues/1043) | Rebrand to PortKit |

### ⏳ M5 — Week 8: Beta Launch (Due: Jun 1)
Target: 20–30 Marketplace creators. Demo mods: Waystones (98% model/88% recipe), Farmer's Delight (88% model/98% lang), Supplementaries (95% model/101% sounds).

### ⏳ M6-M7 — Weeks 9-11: Beta Feedback + Public Launch (Due: Jun 22)

---

## Top 3 Priority Issues (Apr 18 — post-v9)

### 🥇 #1: [#1086](https://github.com/anchapin/ModPorter-AI/issues/1086) — Cutting Board Recipe Fix (P1)

**One-line fix in `block_item_generator.py`.** When `result` is a list (e.g., FD cutting board), `result_item_id = "unknown"` causes all 126 recipes to collide on the same name. Fix: add `elif isinstance(result_item, list) and len(result_item) > 0: result_item_id = result_item[0].get("item", "unknown")`. Expected: +126 FD cutting recipes, recipe ~30%, B2B ~64%.

### 🥈 #2: [#977](https://github.com/anchapin/ModPorter-AI/issues/977) — Usage Limits + Metering (P1)

Stripe (#1081) and feature flags (#1085) are now live. Without usage metering, the tier limits (Free/Creator/Studio conversion quotas) can't be enforced. This is the last missing piece to make billing operational.

### 🥉 #3: [#976](https://github.com/anchapin/ModPorter-AI/issues/976) — Transactional Email (P2)

Email verification, password reset, and subscription confirmations are needed before any real users can sign up. Blocks beta invitations.

---

## Open Issues (12 total — 0 open PRs)

### Conversion pipeline bugs
- [#1086](https://github.com/anchapin/ModPorter-AI/issues/1086) Cutting board recipe fix **← #1 PRIORITY**

### M3 Infrastructure
- [#977](https://github.com/anchapin/ModPorter-AI/issues/977) Usage limits / metering **← #2 PRIORITY**
- [#976](https://github.com/anchapin/ModPorter-AI/issues/976) Transactional email **← #3 PRIORITY**
- [#980](https://github.com/anchapin/ModPorter-AI/issues/980) OAuth login

### M4 Marketing/Legal
- [#978](https://github.com/anchapin/ModPorter-AI/issues/978) Landing page | [#975](https://github.com/anchapin/ModPorter-AI/issues/975) ToS/Privacy | [#979](https://github.com/anchapin/ModPorter-AI/issues/979) History dashboard | [#1043](https://github.com/anchapin/ModPorter-AI/issues/1043) Rebrand

### Post-Launch / AI
- [#1048](https://github.com/anchapin/ModPorter-AI/issues/1048) IDE plugins | [#994](https://github.com/anchapin/ModPorter-AI/issues/994) Embedding upgrade | [#996](https://github.com/anchapin/ModPorter-AI/issues/996) Diffusion LoRA | [#997](https://github.com/anchapin/ModPorter-AI/issues/997) LLM fine-tune

---

## Audit Reports

- [v6 — Apr 15](docs/audit-reports/real-world-scan-v6-20260415.md) — 30 mods, B2B ~49%
- [v7 — Apr 16](docs/audit-reports/real-world-scan-v7-20260416.md) — Sound ~100%, Lang 89.3%, B2B 63.2% ✅
- [v8 — Apr 17](docs/audit-reports/real-world-scan-v8-20260417.md) — B2B 63.2% (flat), custom recipe types partially broken
- [**v9 — Apr 18**](docs/audit-reports/real-world-scan-v9-20260418.md) — B2B **63.4%**, cooking fix +27 recipes, cutting board bug found (#1086)
