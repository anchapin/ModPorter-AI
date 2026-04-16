# PortKit (ModPorter-AI) — Development Roadmap

**Last Updated:** 2026-04-16 (v7 audit)
**Status:** M2 Target Exceeded ✅ — Advancing to M3 (SaaS Infrastructure)
**Repo:** [anchapin/ModPorter-AI](https://github.com/anchapin/ModPorter-AI) | Rebrand to PortKit pending ([#1043](https://github.com/anchapin/ModPorter-AI/issues/1043))
**Target:** Public launch at modporter.ai by June 22, 2026

---

## Executive Summary

PortKit converts Minecraft Java mods to Bedrock add-ons. Positioned as a **B2B conversion accelerator** targeting Marketplace creators.

**Current pipeline maturity: ~63% weighted B2B coverage** (v7 audit, Apr 16 — canonical 8 mods).  
**M2 target (60%) exceeded.** Pipeline is now production-grade enough for beta creator testing.  
**Next milestone:** M3 SaaS infrastructure (Stripe, auth, security) → Beta launch (Jun 1).

---

## Conversion Audit History

| Cycle | Date | Mods | Textures | Models | Recipes | Sound | Lang | B2B est. | Key Changes |
|-------|------|------|----------|--------|---------|-------|------|-----------|-------------|
| v1 | Apr 8 | 8 | ~0% | 0% | 0% | 0% | 0% | ~5% | Baseline |
| v2 | Apr 9 | 8 | 54.8% | 0.2% | 0% | 0% | 0% | ~25% | Bulk texture extraction (#999) |
| v3 | Apr 10a | 8 | 54.7% | 0% | 0% | 0% | 0% | ~28% | Entity routing fix (#1027) |
| v4 | Apr 10b | 8 | 54.7% | 0% | 0% | 0% | 0% | ~28% | Agents built, not yet wired |
| v5 | Apr 11 | 8 | 54.7% | 82.3% | 25.8% | 0% | 0% | ~46% | Model+recipe converters wired (#1035) |
| v6 | Apr 15 | 30 | 68.7% | 68.3% | 40.2% | 0% | 0% | ~49% | NeoForge 1.21+ recipe fix (#1071), 30-mod expansion |
| **v7** | **Apr 16** | **8** | **54.7%** | **82.3%** | **25.8%** | **~100%** | **89.3%** | **~63%** 🎯 | **Sound+lang (#1075), Loot tables+spawn rules (#1074), Report enhancements (#1076)** |

**v7 B2B readiness breakdown:**
| Asset Type | Coverage | Weight | Contribution |
|------------|----------|--------|-------------|
| Texture | 54.7% | 25% | 13.7% |
| Model | 82.3% | 30% | 24.7% |
| Recipe | 25.8% | 20% | 5.2% |
| Sound | ~100% | 10% | 10.0% |
| Localization | 89.3% | 10% | 8.9% |
| Entity | ~15% | 5% | 0.8% |
| **Total** | | | **63.2%** ✅ |

**M2 target (60%) exceeded by 3.2 points. Ready to advance to M3.**

---

## 11-Week Launch Roadmap

### ✅ M1 — Weeks 1-2: Conversion Proof + Pipeline (Complete Apr 10 — 10 days early)

All M1 converters wired: textures 68.7%, models 82.3%, recipes 40.2% (30-mod avg).

### ✅ M2 — Weeks 3-4: Entity Behaviors + Sound/Lang + B2B UX (Target exceeded Apr 16 — ahead of May 4 deadline)

**B2B readiness went from ~46% → ~63% (+17 points)**

| Issue | Description | Status |
|-------|-------------|--------|
| [#971](https://github.com/anchapin/ModPorter-AI/issues/971) | E2E 20+ mods validation | ✅ Closed Apr 15 |
| [#1003](https://github.com/anchapin/ModPorter-AI/issues/1003) | Entity behaviors (spawn rules, loot tables) | ✅ Closed by #1074 |
| [#1002](https://github.com/anchapin/ModPorter-AI/issues/1002) | Sound + localization (0%→~100%) | ✅ Closed by #1075 |
| [#1067](https://github.com/anchapin/ModPorter-AI/issues/1067) | Conversion Report auto/manual handoff (B2B UX) | ✅ Closed by #1076 |
| [#1066](https://github.com/anchapin/ModPorter-AI/issues/1066) | Production secrets hardening | ✅ Closed by #1072 |
| [#1068](https://github.com/anchapin/ModPorter-AI/issues/1068) | Error handling & user-visible feedback | 🔄 Open — P1 |

**Remaining converter gap (path to 70%+):**
- Custom Forge recipe types: cutting board, cooking pot, sequenced assembly, mechanical crafting → currently 0% of custom recipe types; could push recipe from 25.8% → 50%+ → **+5-8% B2B** (no issue filed yet)
- Texture atlas mods: JEI 0%, JourneyMap 7%, Create 49% — specialized extractor needed → +3-5% B2B
- Entity loot tables: spawn rules working (7/8 mods), loot tables still 0 on real-world mods → +1-2% B2B

### 🔄 M3 — Weeks 5-6: Infrastructure (Due: May 18) — NOW UNBLOCKED

Pipeline has cleared 60% threshold. Time to build the business layer.

| Issue | Description | Priority |
|-------|-------------|----------|
| [#970](https://github.com/anchapin/ModPorter-AI/issues/970) | Stripe subscription billing | P0 — revenue gate |
| [#977](https://github.com/anchapin/ModPorter-AI/issues/977) | Usage limits + metering per tier | P1 |
| [#972](https://github.com/anchapin/ModPorter-AI/issues/972) | Feature flags for accounts and API keys | P1 |
| [#973](https://github.com/anchapin/ModPorter-AI/issues/973) | File upload security (sandboxing, validation) | P1 |
| [#976](https://github.com/anchapin/ModPorter-AI/issues/976) | Transactional email (verification, notifications) | P1 |
| [#980](https://github.com/anchapin/ModPorter-AI/issues/980) | OAuth login (Discord, GitHub, Google) | P2 |
| [#1068](https://github.com/anchapin/ModPorter-AI/issues/1068) | Error handling & user feedback | P1 — carry from M2 |

### ⏳ M4 — Week 7: Landing Page + Legal + Rebrand (Due: May 25)

| Issue | Description |
|-------|-------------|
| [#978](https://github.com/anchapin/ModPorter-AI/issues/978) | Marketing landing page — conversion accelerator positioning |
| [#975](https://github.com/anchapin/ModPorter-AI/issues/975) | Terms of Service and Privacy Policy |
| [#979](https://github.com/anchapin/ModPorter-AI/issues/979) | Conversion history dashboard |
| [#1043](https://github.com/anchapin/ModPorter-AI/issues/1043) | Rebrand to PortKit |

### ⏳ M5 — Week 8: Beta Launch (Due: Jun 1)

Target: 20–30 Marketplace creators. Demo mods: Waystones (98% models/88% recipes), Farmer's Delight (88% models/98% lang), Supplementaries (95% models/100% lang/101% sounds).

### ⏳ M6-M7 — Weeks 9-11: Beta Feedback + Public Launch (Due: Jun 22)

---

## Top 3 Priority Issues (Apr 16 — post-v7)

### 🥇 #1: Custom Forge Recipe Type Handlers — File New Issue
Recipe coverage is 25.8% because standard shaped/shapeless/smelting work, but custom Forge CraftingType patterns produce 0 output. These types appear in the most popular demo mods:
- Farmer's Delight: `cooking_pot`, `cutting_board` (533 recipes, only 135 converted = 25%)
- Create: `sequenced_assembly`, `mechanical_crafting`, `mixing`, `pressing`, `deploying` (2,782 recipes, only 22% converted)
- Fix: implement `IRecipeSerializer` pattern matchers + Bedrock custom recipe mappings
- **Expected impact: Recipe 25.8% → 50%+ → +5% B2B readiness**

### 🥈 #2: [#1068](https://github.com/anchapin/ModPorter-AI/issues/1068) — Error Handling & User Feedback
Last remaining M2 P1. Creators need actionable error messages for partial failures. When JourneyMap produces 7% texture coverage or Create produces 22% recipe coverage, the conversion report should explain why and suggest next steps. **Needed before any beta creator testing.**

### 🥉 #3: [#970](https://github.com/anchapin/ModPorter-AI/issues/970) — Stripe Subscription Billing
M2 target has been crossed — the pipeline is ready. Stripe is the gate to revenue and the first M3 item. Without it, PortKit is a free demo. With it, the B2B Creator ($7.99/mo) and Studio ($24.99/mo + API) tiers can launch. **Unblocked by M2 completion.**

---

## Open Issues Summary (18 total)

### Active Priority
- **Custom recipe types** — no issue yet, file one **← #1 PRIORITY** 
- [#1068](https://github.com/anchapin/ModPorter-AI/issues/1068) Error handling UX — P1 **← #2 PRIORITY**
- [#970](https://github.com/anchapin/ModPorter-AI/issues/970) Stripe billing — P0 revenue gate **← #3 PRIORITY**

### M3 Infrastructure
- #972 Feature flags | #973 Upload security | #976 Transactional email | #977 Usage limits | #980 OAuth

### M4 Marketing/Legal
- #975 ToS/Privacy | #978 Landing page | #979 History dashboard | #1043 Rebrand

### Post-Launch / AI
- #1048 IDE plugins | #994 Embedding upgrade | #996 Diffusion LoRA | #997 LLM fine-tune

### Open PRs: 0 ✅

---

## Audit Reports

- [v1 — Apr 8](docs/audit-reports/real-world-scan-20260408.md) through [v5 — Apr 11](docs/audit-reports/real-world-scan-v5-20260411.md)
- [v6 — Apr 15](docs/audit-reports/real-world-scan-v6-20260415.md) — 30 mods, NeoForge fix, B2B ~49%
- [**v7 — Apr 16**](docs/audit-reports/real-world-scan-v7-20260416.md) — Sound ~100%, Lang 89.3%, B2B **63.2%** 🎯 M2 target exceeded
