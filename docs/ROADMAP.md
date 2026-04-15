# PortKit (ModPorter-AI) — Development Roadmap

**Last Updated:** 2026-04-14
**Status:** Active Development — Week 3-4 Sprint (Recipe Custom Types + Entity Behaviors)
**Repo:** [anchapin/ModPorter-AI](https://github.com/anchapin/ModPorter-AI) | Rebrand to PortKit pending ([#1043](https://github.com/anchapin/ModPorter-AI/issues/1043))
**Target:** Public launch at modporter.ai by June 22, 2026

---

## Executive Summary

PortKit converts Minecraft Java mods to Bedrock add-ons. Positioned as a **B2B conversion accelerator** targeting Marketplace creators — handles the majority of conversion work so creators finish in hours, not days.

**Current pipeline maturity: ~46% weighted B2B coverage** (v5 audit, Apr 11).  
**Next milestone target: 60%** — blocked primarily on custom recipe type handlers and entity behaviors.

---

## Conversion Audit History

8 real-world Java mods tested across 5 audit cycles (Modrinth: Iron Chests, Waystones, Farmer's Delight, Supplementaries, Create, Xaero's Minimap, JourneyMap, JEI):

| Metric | v1 (Apr 8) | v2 (Apr 9) | v3 (Apr 10a) | v4 (Apr 10b) | **v5 (Apr 11)** |
|--------|-----------|-----------|------------|------------|----------------|
| Pass rate | 8/8 | 8/8 | 8/8 | 8/8 | **8/8** ✅ |
| Texture | ~0% | 54.8% | 54.7% | 54.7% | **54.7%** |
| Model | 0% | 0.2% | 0% | 0% | **82.3%** 🟢 |
| Recipe | 0% | 0% | 0% | 0% | **25.8%** 🟢 |
| Entities | 1/mod | 1/mod | 15 total | 15 total | **15 total** |
| B2B readiness (weighted) | ~5% | ~25% | ~28% | ~28% | **~46%** |

**Note:** No conversion pipeline changes since v5 (Apr 11–14 commits were CI fixes, dep bumps, UI/accessibility, RL feedback loop). Next audit (v6) will run once #1002 or #1003 lands.

### Per-Mod v5 Highlights
| Mod | Textures | Models | Recipes | Notes |
|-----|----------|--------|---------|-------|
| Waystones | 92% | 98% ✅ | 88% ✅ | Near-complete |
| Supplementaries | 62% | 95% ✅ | 41% | Models excellent |
| Farmer's Delight | 91% | 88% ✅ | 25% | Custom recipe types gap |
| Create | 49% | 73% | 22% | Complex mod, expected |
| JEI / JourneyMap | 0–7% | — | — | Atlas/UI sprite mods |

---

## 11-Week Launch Roadmap

### ✅ M1 — Week 1-2: Conversion Proof + Pipeline Validation (Completed Apr 10 — 10 days early)

All 13 M1 issues closed. Delivered:
- Texture extraction: 54.7% coverage
- Model converter wired: 82.3% coverage  
- Recipe converter wired: 25.8% coverage
- Entity converter operational, BlockEntity classification
- RAG pipeline, StrategySelector, LLM-powered tools
- Production security hardening, error handling, conversion reports

### 🔄 M2 — Week 3-4: Recipe Coverage + Entity Behaviors (Due: May 4)

**Status: In Progress — ~46% B2B readiness, targeting 60%+**

| Issue | Description | Priority | Status |
|-------|-------------|----------|--------|
| [#971](https://github.com/anchapin/ModPorter-AI/issues/971) | E2E validation 20+ real Java mods | **P0** | 8/20 done |
| [#1003](https://github.com/anchapin/ModPorter-AI/issues/1003) | Full entity behaviors (spawn, loot, AI) | P1 | Open |
| [#1002](https://github.com/anchapin/ModPorter-AI/issues/1002) | Sound + localization extraction | P1 | Open |
| Custom recipe types | Forge CraftingType handlers (cutting board, sequenced assembly) | **P0** | No issue filed yet |

**Also completed in this sprint window:**
- [#989](https://github.com/anchapin/ModPorter-AI/issues/989) ✅ Prompt-Based RL Feedback Loop (merged Apr 14 via #1045) — improves translation quality over time
- CI stabilization: pnpm lockfile (#1060/#1062), Docker Python (#1061/#1063), dep bumps (#1051–#1057, #1065)

**Recipe gap detail:** Standard shaped/shapeless/smelting work well (Waystones 88%). Custom Forge types return 0: cutting board and cooking pot (Farmer's Delight), sequenced/mechanical assembly (Create). A custom recipe type handler in `RecipeConverterAgent` could push recipe coverage to ~55%, lifting overall B2B readiness to ~57-60%.

**Open CI issues (likely resolved, needs verification):**
- [#1060](https://github.com/anchapin/ModPorter-AI/issues/1060): pnpm lockfile mismatch → fixed by #1062
- [#1061](https://github.com/anchapin/ModPorter-AI/issues/1061): Docker Python 3.14-slim CI failure → addressed by #1063

### ⏳ M3 — Week 5-6: Infrastructure (Due: May 18)

| Issue | Description |
|-------|-------------|
| [#970](https://github.com/anchapin/ModPorter-AI/issues/970) | Stripe subscription billing (B2B hybrid pricing) |
| [#977](https://github.com/anchapin/ModPorter-AI/issues/977) | Usage limits and metering per tier |
| [#972](https://github.com/anchapin/ModPorter-AI/issues/972) | Feature flags for accounts and API keys |
| [#973](https://github.com/anchapin/ModPorter-AI/issues/973) | File upload security (sandboxing, validation) |
| [#976](https://github.com/anchapin/ModPorter-AI/issues/976) | Transactional email (verification, notifications) |
| [#980](https://github.com/anchapin/ModPorter-AI/issues/980) | OAuth login (Discord, GitHub, Google) |

### ⏳ M4 — Week 7: Landing Page + Legal + Marketplace Positioning (Due: May 25)

| Issue | Description |
|-------|-------------|
| [#978](https://github.com/anchapin/ModPorter-AI/issues/978) | Marketing landing page — conversion accelerator positioning |
| [#975](https://github.com/anchapin/ModPorter-AI/issues/975) | Terms of Service and Privacy Policy |
| [#979](https://github.com/anchapin/ModPorter-AI/issues/979) | Conversion history dashboard |
| [#1043](https://github.com/anchapin/ModPorter-AI/issues/1043) | Rebrand to PortKit (schedule into this milestone) |

### ⏳ M5 — Week 8: Beta Launch (Due: Jun 1)

- Target: 20–30 Marketplace creators for beta testing
- Demo candidates: Waystones (98% models / 88% recipes), Farmer's Delight (88% models)
- Channels: r/feedthebeast, Fabric/Forge Discord, direct outreach

### ⏳ M6–M7 — Weeks 9-11: Beta Feedback + Public Launch (Due: Jun 22)

---

## Open Issues Summary (19 total)

### Active M2 Sprint
- [#971](https://github.com/anchapin/ModPorter-AI/issues/971) E2E 20+ mods (P0)
- [#1002](https://github.com/anchapin/ModPorter-AI/issues/1002) Sound + localization (P1)
- [#1003](https://github.com/anchapin/ModPorter-AI/issues/1003) Entity behaviors (P1)
- [#1060](https://github.com/anchapin/ModPorter-AI/issues/1060) / [#1061](https://github.com/anchapin/ModPorter-AI/issues/1061) CI failures (likely resolved)

### Infrastructure (M3)
- #970, #972, #973, #976, #977, #980

### Marketing / Legal (M4)
- #975, #978, #979, #1043 (PortKit rebrand)

### Post-Launch
- [#1048](https://github.com/anchapin/ModPorter-AI/issues/1048) IDE/Plugin Ecosystem Integration (Blockbench, VS Code, Bridge)

### AI Enhancements (Unscheduled)
- [#994](https://github.com/anchapin/ModPorter-AI/issues/994) Upgrade embedding model
- [#996](https://github.com/anchapin/ModPorter-AI/issues/996) Diffusion LoRA for textures
- [#997](https://github.com/anchapin/ModPorter-AI/issues/997) Fine-tune code LLM

### Open PRs: 0 ✅

---

## Coverage Gaps (What Remains for 60% Target)

| Gap | Impact | Issue |
|-----|--------|-------|
| Custom Forge recipe types (cutting board, cooking pot, sequenced assembly) | +~15-20% recipe coverage → +5-8% B2B | No issue yet |
| Entity behaviors / spawn / loot / AI | B2B quality gap | [#1003](https://github.com/anchapin/ModPorter-AI/issues/1003) |
| Sound extraction | Minor (+1-2%) | [#1002](https://github.com/anchapin/ModPorter-AI/issues/1002) |
| Localization (lang files) | Moderate (+2-3%) | [#1002](https://github.com/anchapin/ModPorter-AI/issues/1002) |
| Texture atlas mods (JEI, JourneyMap) | +~5% aggregate | No issue filed |

---

## Audit Reports

- [v1 — Apr 8](docs/audit-reports/real-world-scan-20260408.md) — Baseline: ~5% weighted
- [v2 — Apr 9](docs/audit-reports/real-world-scan-v2-20260409.md) — Textures: 54.8%
- [v3 — Apr 10a](docs/audit-reports/real-world-scan-v3-20260410.md) — Entities: 15 defs
- [v4 — Apr 10b](docs/audit-reports/real-world-scan-v4-20260410.md) — Agents built, not yet wired
- [**v5 — Apr 11**](docs/audit-reports/real-world-scan-v5-20260411.md) — Models 82.3%, Recipes 25.8% 🟢
- v6 — pending (trigger: #1002 or #1003 merge)
