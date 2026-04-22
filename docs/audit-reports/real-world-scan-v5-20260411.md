---
type: markdown
---
# Conversion Audit v5 — Apr 11, 2026

**Pipeline:** `997c1b6a` — includes #1035 (model + recipe wired into pipeline), #1044 (LLM tools), #1041 (RAG), #1040 (StrategySelector), plus all prior fixes

## v1 → v5 Trend

| Metric | v1 (Apr 8) | v2 (Apr 9) | v3 (Apr 10a) | v4 (Apr 10b) | **v5 (Apr 11)** | Δ v4→v5 |
|--------|-----------|-----------|------------|------------|----------------|---------|
| Pass rate | 8/8 | 8/8 | 8/8 | 8/8 | **8/8** | — |
| Texture | ~0% | 54.8% | 54.7% | 54.7% | **54.7%** | 0 |
| Model | 0% | 0.2% | 0% | 0% | **82.3%** | **+82.3%** 🟢 |
| Recipe | 0% | 0% | 0% | 0% | **25.8%** | **+25.8%** 🟢 |
| Entity defs | ~1/mod | 1/mod | 15 total | 15 total | **15 total** | 0 |
| B2B readiness | ~5% | ~25% | ~28% | ~28% | **~45%** | **+17%** 🟢 |

## Per-Mod Results (v5)

| Mod | Textures | Models | Recipes | Entities | Files | Size |
|-----|----------|--------|---------|----------|-------|------|
| **Iron Chests** | 36/36 (100%) ✅ | 21/28 (75%) 🟢 | 20/44 (45%) 🟡 | 1 | 82 | 121 KB |
| **Waystones** | 23/25 (92%) ✅ | 49/50 (98%) ✅ | 30/34 (88%) ✅ | 1 | 109 | 68 KB |
| **Farmer's Delight** | 358/395 (91%) ✅ | 302/342 (88%) ✅ | 135/533 (25%) 🟡 | 1 | 805 | 432 KB |
| **Supplementaries** | 681/1103 (62%) 🟡 | 1623/1702 (95%) ✅ | 186/459 (41%) 🟡 | 1 | 2541 | 1.7 MB |
| **Create** | 633/1289 (49%) 🟡 | 1962/2684 (73%) 🟢 | 624/2782 (22%) 🟡 | 9 | 3274 | 2.1 MB |
| Xaero's Minimap | 12/12 (100%) ✅ | — | — | 1 | 17 | 46 KB |
| JourneyMap | 22/323 (7%) 🔴 | — | — | 1 | 74 | 37 KB |
| JEI | 0/46 (0%) 🔴 | — | — | 0 | 6 | 2 KB |
| **Totals** | **1765/3229 (54.7%)** | **3957/4806 (82.3%)** | **995/3852 (25.8%)** | **15** | **6908** | **4.5 MB** |

## B2B Readiness Assessment (~45%)

Weighted score estimate:

| Component | Coverage | Weight | Score |
|-----------|----------|--------|-------|
| Textures | 54.7% | 25% | 13.7 pts |
| Models | 82.3% | 30% | 24.7 pts |
| Recipes | 25.8% | 25% | 6.5 pts |
| Entities | ~15% (full behaviors) | 10% | 1.5 pts |
| Sound / Localization | 0% | 10% | 0 pts |
| **Total** | | | **~46 pts (~46%)** |

**Target: 60%** — gap is ~14 points, primarily from recipes (could add ~10 pts at 60% recipe coverage) and entities.

## Standout Performers

- **Waystones**: 92% tex / 98% models / 88% recipes — essentially converter-complete for a teleportation mod
- **Supplementaries**: 62% tex / 95% models / 41% recipes — models virtually complete
- **Farmer's Delight**: 91% tex / 88% models / only 25% recipes — recipe complexity is the blocker

## Gaps Remaining

### Recipe coverage (25.8% → target 60%+)
- Farmer's Delight: 135/533 — many custom recipe types (cutting board, cooking pot, skillet) not supported
- Create: 624/2,782 — mostly custom crafting types (sequenced assembly, mechanical crafting)
- Iron Chests: 20/44 — likely shapeless/NBT recipes failing

### Texture gaps (54.7%)
- JourneyMap: 22/323 (7%) — most textures are UI sprites at non-standard paths
- JEI: 0/46 (0%) — all textures in a custom atlas

### Entity completion (15 total defs, no behaviors/loot/spawn)
- #1003 entity behaviors still open — entity defs exist but have no spawn rules, loot tables, or AI

### Sound / Localization (0%)
- #1002 still open — 187 sounds and 292 lang files across 8 mods

## Open Issues Summary (17 total)

### Active Sprint (M2 — Week 3-4, due May 4)
- **#971**: E2E validation 20+ mods — expand test library
- **#1002**: Sound + localization (0/187 sounds, 0/292 lang)
- **#1003**: Full entity behaviors/spawn/loot (15 defs exist, no behaviors)

### Infrastructure (M3 — Week 5-6, due May 18)
- #970, #972, #973, #976, #977 — billing, feature flags, security, email, metering

### Marketing / Legal (M4 — Week 7, due May 25)
- #975, #978, #979, #980 — ToS, landing page, history dashboard, OAuth

### AI Enhancements (Unscheduled)
- #989, #994, #996, #997 — RL, embeddings, LoRA textures, code LLM

### New
- **#1043**: Rebrand portkit → PortKit (open, unscheduled)

### Open PRs (3)
- #1047: aria-expanded UI fix (open)
- #1046: Bolt perf improvement (open)
- #1045: Prompt-based RL feedback loop (open, #989)
