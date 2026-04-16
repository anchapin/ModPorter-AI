# PortKit (ModPorter-AI) — Development Roadmap

**Last Updated:** 2026-04-16
**Status:** Active Development — M2 Sprint (Entity Behaviors + Sound/Lang + B2B UX)
**Repo:** [anchapin/ModPorter-AI](https://github.com/anchapin/ModPorter-AI) | Rebrand to PortKit pending ([#1043](https://github.com/anchapin/ModPorter-AI/issues/1043))
**Target:** Public launch at modporter.ai by June 22, 2026

---

## Executive Summary

PortKit converts Minecraft Java mods to Bedrock add-ons. Positioned as a **B2B conversion accelerator** targeting Marketplace creators.

**Current pipeline maturity: ~49% weighted B2B coverage** (v6 audit, Apr 15, 30 mods).  
**Next milestone target: 60%** — blocked on entity behaviors, sound/lang, and B2B UX features.

---

## Conversion Audit History

| Cycle | Date | Mods | Textures | Models | Recipes | Entities | B2B est. | Key Changes |
|-------|------|------|----------|--------|---------|----------|-----------|-------------|
| v1 | Apr 8 | 8 | ~0% | 0% | 0% | ~1/mod | ~5% | Baseline |
| v2 | Apr 9 | 8 | 54.8% | 0.2% | 0% | 1/mod | ~25% | Bulk texture extraction (#999) |
| v3 | Apr 10a | 8 | 54.7% | 0% | 0% | 15 | ~28% | Entity routing fix (#1027) |
| v4 | Apr 10b | 8 | 54.7% | 0% | 0% | 15 | ~28% | Agents built, not yet wired |
| v5 | Apr 11 | 8 | 54.7% | 82.3% | 25.8% | 15 | ~46% | Model+recipe converters wired (#1035) |
| **v6** | **Apr 15** | **30** | **68.7%** | **68.3%** | **40.2%** | **19** | **~49%** | **NeoForge 1.21+ recipe fix (#1071), 30-mod expansion (#971 ✅)** |

**v6 notes:**
- 22/30 mods pass (73%); 8 fail (REI, Storage Drawers, Astral Sorcery, Silent Gear, Tinkers Construct, ProjectE, AbyssalCraft, Compact Machines) — likely non-standard JAR structures
- Canonical 8-mod numbers unchanged from v5 (NeoForge fix targets 1.21+ format; canonical mods are 1.20.x)
- Broader mod set reveals lower average models (68.3% vs 82.3%) — complex mods with custom model parents drag the average
- Recipe improvement (+14.4%) from NeoForge path fix meaningful on newer mods

---

## 11-Week Launch Roadmap

### ✅ M1 — Weeks 1-2: Conversion Proof + Pipeline (Complete Apr 10 — 10 days early)

- Texture extraction: 68.7% coverage (30-mod avg)
- Model converter wired: 82.3% (canonical) / 68.3% (30-mod avg)
- Recipe converter wired: 40.2% (30-mod avg)
- Entity converter, BlockEntity classification, RAG, StrategySelector, LLM tools
- Production security hardening, error handling, RL feedback loop

### 🔄 M2 — Weeks 3-4: Entity Behaviors + Sound/Lang + B2B UX (Due: May 4)

**Status: In Progress — ~49% B2B readiness, targeting 60%+**

| Issue | Description | Priority | Status |
|-------|-------------|----------|--------|
| [#1003](https://github.com/anchapin/ModPorter-AI/issues/1003) | Full entity behaviors (spawn rules, loot tables, AI, animations) | P1 | Open |
| [#1002](https://github.com/anchapin/ModPorter-AI/issues/1002) | Sound + localization extraction (0% on both) | P1 | Open |
| [#1067](https://github.com/anchapin/ModPorter-AI/issues/1067) | Conversion Report: auto-converted vs. manual review handoff (B2B UX) | P1 | Open 🆕 |
| [#1068](https://github.com/anchapin/ModPorter-AI/issues/1068) | Error handling & user-visible feedback for conversion failures | P1 | Open 🆕 |
| Custom recipe types | Forge CraftingType handlers for cutting board, sequenced assembly etc. | P1 | No issue yet |

**Also completed in M2 window:**
- [#971](https://github.com/anchapin/ModPorter-AI/issues/971) ✅ E2E validation 30 real mods (closed Apr 15 — 30-mod v6 audit, 22/30 pass)
- [#1066](https://github.com/anchapin/ModPorter-AI/issues/1066) ✅ Production secrets hardening for Fly.io (closed Apr 16 via #1072)
- NeoForge 1.21+ recipe extraction fix (#1071) — singular `/recipe/` path, advancement file filtering
- CI stabilization: Docker Python 3.11 (#1069), pnpm lockfile sync (#1069)
- Accessibility improvements: ARIA labels (#1073), focus-visible states (#1049)

**Remaining coverage gaps (path to 60%):**
- Entity behaviors (15 defs exist, no spawn/loot/AI) → +3-5% B2B
- Sound extraction (0% on 187+ sounds) → +2-3% B2B
- Localization (0% on 292+ lang files) → +2-3% B2B
- Custom Forge recipe types → +5-8% B2B recipe coverage
- **Total potential if all addressed: ~60-63%** ✅

### ⏳ M3 — Weeks 5-6: Infrastructure (Due: May 18)

| Issue | Description |
|-------|-------------|
| [#970](https://github.com/anchapin/ModPorter-AI/issues/970) | Stripe subscription billing (B2B hybrid pricing) |
| [#977](https://github.com/anchapin/ModPorter-AI/issues/977) | Usage limits and metering per tier |
| [#972](https://github.com/anchapin/ModPorter-AI/issues/972) | Feature flags for accounts and API keys |
| [#973](https://github.com/anchapin/ModPorter-AI/issues/973) | File upload security (sandboxing, validation) |
| [#976](https://github.com/anchapin/ModPorter-AI/issues/976) | Transactional email (verification, notifications) |
| [#980](https://github.com/anchapin/ModPorter-AI/issues/980) | OAuth login (Discord, GitHub, Google) |

### ⏳ M4 — Week 7: Landing Page + Legal + Rebrand (Due: May 25)

| Issue | Description |
|-------|-------------|
| [#978](https://github.com/anchapin/ModPorter-AI/issues/978) | Marketing landing page — conversion accelerator positioning |
| [#975](https://github.com/anchapin/ModPorter-AI/issues/975) | Terms of Service and Privacy Policy |
| [#979](https://github.com/anchapin/ModPorter-AI/issues/979) | Conversion history dashboard |
| [#1043](https://github.com/anchapin/ModPorter-AI/issues/1043) | Rebrand to PortKit |

### ⏳ M5 — Week 8: Beta Launch (Due: Jun 1)

Target: 20–30 Marketplace creators for beta testing.  
Demo candidates: Waystones (98% models / 88% recipes), Farmer's Delight (88% models), Supplementaries (95% models).

### ⏳ M6-M7 — Weeks 9-11: Beta Feedback + Public Launch (Due: Jun 22)

---

## Open Issues Summary (20 total)

### Active M2 Sprint
- [#1003](https://github.com/anchapin/ModPorter-AI/issues/1003) Entity behaviors — P1 **← #1 PRIORITY**
- [#1002](https://github.com/anchapin/ModPorter-AI/issues/1002) Sound + localization — P1 **← #2 PRIORITY**
- [#1067](https://github.com/anchapin/ModPorter-AI/issues/1067) Conversion report handoff (B2B UX) — P1 🆕 **← #3 PRIORITY**
- [#1068](https://github.com/anchapin/ModPorter-AI/issues/1068) Error handling UX — P1 🆕
- [#1060](https://github.com/anchapin/ModPorter-AI/issues/1060) CI pnpm lockfile (resolved by #1062/#1069 — needs close)
- [#1061](https://github.com/anchapin/ModPorter-AI/issues/1061) CI Docker Python 3.14 (resolved by #1063/#1069 — needs close)

### Infrastructure (M3)
- #970, #972, #973, #976, #977, #980

### Marketing / Legal (M4)
- #975, #978, #979, #1043

### Post-Launch / AI
- [#1048](https://github.com/anchapin/ModPorter-AI/issues/1048) IDE/Plugin Ecosystem
- #994, #996, #997 AI enhancements (unscheduled)

### Open PRs: 0 ✅

---

## Top 3 Priority Issues (Apr 16)

### 🥇 #1: [#1003](https://github.com/anchapin/ModPorter-AI/issues/1003) — Entity Behaviors
Entity definitions exist (15 across 30 mods) but have no spawn rules, loot tables, AI behaviors, or animations. Without this, converted mobs are static and non-functional — a hard blocker for any mod with custom entities. **Impact: +3-5% B2B readiness, unblocks full mob conversion.**

### 🥈 #2: [#1002](https://github.com/anchapin/ModPorter-AI/issues/1002) — Sound + Localization
Currently 0% transfer rate on both categories (187+ sounds, 292+ lang files across 30 mods). Sound is needed for mods like Farmer's Delight (19 sounds), Create (39 sounds), Supplementaries (129 sounds). Localization is required for all UI text. **Impact: +4-6% B2B readiness, completes the asset pipeline.**

### 🥉 #3: [#1067](https://github.com/anchapin/ModPorter-AI/issues/1067) — Conversion Report Handoff
B2B creators need to know exactly what was auto-converted vs. what requires manual work. This is the core UX differentiator — without it, creators can't efficiently use PortKit as a conversion accelerator. **Impact: B2B usability, critical for paid tier conversion.**

---

## Audit Reports

- [v1 — Apr 8](docs/audit-reports/real-world-scan-20260408.md)
- [v2 — Apr 9](docs/audit-reports/real-world-scan-v2-20260409.md)
- [v3 — Apr 10a](docs/audit-reports/real-world-scan-v3-20260410.md)
- [v4 — Apr 10b](docs/audit-reports/real-world-scan-v4-20260410.md)
- [v5 — Apr 11](docs/audit-reports/real-world-scan-v5-20260411.md) — Models 82.3%, Recipes 25.8%
- [**v6 — Apr 15**](docs/audit-reports/real-world-scan-v6-20260415.md) — 30 mods, NeoForge fix, B2B ~49% 🟢
