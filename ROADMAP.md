# ModPorter AI — Development Roadmap

**Last Updated:** 2026-04-11
**Status:** Active Development — Week 3-4 Sprint (Recipe Coverage + Entity Behaviors)
**Target:** Public launch of modporter.ai by June 22, 2026

---

## Executive Summary

ModPorter converts Minecraft Java mods to Bedrock add-ons. Positioned as a **B2B conversion accelerator** targeting Marketplace creators — handles the majority of conversion work so creators finish in hours, not days.

**Current pipeline maturity: ~46% weighted B2B coverage** (up from ~5% on Apr 8).

---

## Conversion Audit Status (Apr 11, 2026 — v5)

8 real-world Java mods tested across 5 audit cycles:

| Metric | v1 (Apr 8) | v2 (Apr 9) | v3 (Apr 10a) | v4 (Apr 10b) | **v5 (Apr 11)** |
|--------|-----------|-----------|------------|------------|----------------|
| Pass rate (valid .mcaddon) | 8/8 | 8/8 | 8/8 | 8/8 | **8/8** ✅ |
| Texture coverage | ~0% | 54.8% | 54.7% | 54.7% | **54.7%** |
| Model coverage | 0% | 0.2% | 0% | 0% | **82.3%** 🟢 |
| Recipe coverage | 0% | 0% | 0% | 0% | **25.8%** 🟢 |
| Entity definitions | 1/mod | 1/mod | 15 total | 15 total | **15 total** |
| B2B readiness (weighted) | ~5% | ~25% | ~28% | ~28% | **~46%** 🟢 |

### Per-Mod Highlights (v5)
- **Waystones**: 92% tex / 98% models / 88% recipes — near-complete ✅
- **Farmer's Delight**: 91% tex / 88% models / 25% recipes (custom recipe types gap)
- **Supplementaries**: 62% tex / 95% models / 41% recipes
- **Create**: 49% tex / 73% models / 22% recipes (complex automation mod)

### Test Mods (from Modrinth)
1. Iron Chests, 2. Waystones, 3. Farmer's Delight, 4. Supplementaries, 5. Create
6. Xaero's Minimap, 7. JourneyMap, 8. Just Enough Items (JEI)

---

## 11-Week Launch Roadmap

### ✅ Week 1-2: Conversion Proof + Pipeline Validation (Completed Apr 10 — 10 days early)

All 13 M1 issues closed. Key deliveries:
- Bulk texture extraction (#999): 54.7% texture coverage
- Entity converter wired (#982/#983): entity detection operational
- Model converter built + wired (#1031, #1035): 82.3% model coverage
- Recipe converter built + wired (#998, #1032, #1035): 25.8% recipe coverage
- BlockEntity classification (#1001), entity detection (#1027), error handling (#974)
- RAG pipeline (#1041), StrategySelector (#1040), LLM tools (#1044)
- Production security hardening (#969, #1019, #1020)

### 🔄 Week 3-4: Recipe Coverage + Entity Behaviors (Due: May 4)

**Status: In Progress — ~46% B2B readiness, targeting 60%+**

| Issue | Description | Priority | Current |
|-------|-------------|----------|---------|
| #971 | E2E validation with 20+ real mods | **P0** | 8/20 mods |
| #1002 | Sound + localization extraction | P1 | 0/187 sounds, 0/292 lang |
| #1003 | Full entity behaviors (spawn, loot, AI) | P1 | 15 defs, 0 behaviors |
| Recipe gap | Custom recipe types (Forge CraftingType, etc.) | **P0** | 25.8% → target 60% |

**Recipe gap detail:** Farmer's Delight 25% (cutting board, cooking pot), Create 22% (sequenced assembly, mechanical crafting), Iron Chests 45% — standard shaped/shapeless work; custom Forge recipe types need a handler.

**Expected impact:** Recipe 25.8% → 55%+ would bring B2B readiness to ~57-60%.

### ⏳ Week 5-6: Infrastructure — Billing, Security, Metering (Due: May 18)

| Issue | Description |
|-------|-------------|
| #970 | Stripe subscription billing (B2B hybrid pricing) |
| #977 | Usage limits and metering per tier |
| #972 | Feature flags for accounts and API keys |
| #973 | File upload security (sandboxing, validation) |
| #976 | Transactional email (verification, notifications) |
| #980 | OAuth login (Discord, GitHub, Google) |

### ⏳ Week 7: Landing Page + Legal + Marketplace Positioning (Due: May 25)

| Issue | Description |
|-------|-------------|
| #978 | Marketing landing page — conversion accelerator positioning |
| #975 | Terms of Service and Privacy Policy |
| #979 | Conversion history dashboard |
| #1043 | Rebrand: PortKit (open, needs scheduling) |

### ⏳ Week 8: Beta Launch — Marketplace Creator Outreach (Due: Jun 1)

- Target: 20-30 Marketplace creators for beta testing
- Channels: r/feedthebeast, Fabric/Forge Discord, direct outreach
- Demo candidates: Waystones (88% recipe coverage), Farmer's Delight (blocks + items solid)

### ⏳ Week 9-11: Beta Feedback + Public Launch (Due: Jun 22)

- Iterate on beta feedback
- Fix top conversion gaps from creator testing
- Public launch at modporter.ai

---

## Open GitHub Issues (Active — 17 total)

### P0 — Critical Path
- [#971](https://github.com/anchapin/ModPorter-AI/issues/971) E2E validation 20+ mods (8/20 done)
- Recipe custom types — no issue yet, needs filing

### P1 — Important  
- [#1003](https://github.com/anchapin/ModPorter-AI/issues/1003) Full entity behaviors/spawn/loot
- [#1002](https://github.com/anchapin/ModPorter-AI/issues/1002) Sound + localization

### Open PRs (3)
- [#1045](https://github.com/anchapin/ModPorter-AI/pull/1045) Prompt-based RL (open)
- [#1046](https://github.com/anchapin/ModPorter-AI/pull/1046) Bolt perf improvement (open)
- [#1047](https://github.com/anchapin/ModPorter-AI/pull/1047) aria-expanded UI fix (open)

### AI Engine Enhancement (Unscheduled)
- [#989](https://github.com/anchapin/ModPorter-AI/issues/989) RL with conversion examples
- [#994](https://github.com/anchapin/ModPorter-AI/issues/994) Upgrade embedding model
- [#996](https://github.com/anchapin/ModPorter-AI/issues/996) Diffusion LoRA for textures
- [#997](https://github.com/anchapin/ModPorter-AI/issues/997) Fine-tune code LLM

---

## Coverage Gaps (What Remains)

| Gap | Mods Affected | Impact |
|-----|--------------|--------|
| Custom recipe types (Forge CraftingType) | Farmer's Delight, Create | +15-20% recipe |
| Texture atlas mods (JEI, JourneyMap) | 2/8 mods | +~5% aggregate |
| Entity behaviors (spawn, loot, AI) | All mods with entities | B2B quality gap |
| Sound extraction | 5/8 mods (187 sounds) | Minor |
| Localization (lang files) | All mods (292 files) | Moderate |

---

## Audit Reports

- [v1 — Apr 8, 2026](docs/audit-reports/real-world-scan-20260408.md) — Baseline: ~5% weighted
- [v2 — Apr 9, 2026](docs/audit-reports/real-world-scan-v2-20260409.md) — Texture fix: 54.8%
- [v3 — Apr 10a, 2026](docs/audit-reports/real-world-scan-v3-20260410.md) — Entity: 15 defs
- [v4 — Apr 10b, 2026](docs/audit-reports/real-world-scan-v4-20260410.md) — Agents built, not wired
- [**v5 — Apr 11, 2026**](docs/audit-reports/real-world-scan-v5-20260411.md) — Models 82.3%, Recipes 25.8% 🟢

---

*Rebrand to PortKit pending (#1043).*
