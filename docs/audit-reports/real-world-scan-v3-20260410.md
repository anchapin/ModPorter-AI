---
type: markdown
---
# Conversion Audit v3 — Apr 10, 2026

**Pipeline:** `775e339` — includes #999 (bulk textures), #982/#983 (entity converter), #1027 (entity detection fix)

## v1 → v2 → v3 Trend

| Metric | v1 (Apr 8) | v2 (Apr 9) | v3 (Apr 10) | Trend |
|--------|-----------|-----------|------------|-------|
| **Pass rate** | 8/8 | 8/8 | **8/8** | Stable ✅ |
| **Texture coverage** | ~0% | 54.8% | **54.7%** | Stable ✅ |
| **Model coverage** | 0% | 0.2% | **0%** | 🔴 No progress |
| **Recipe coverage** | 0% | 0% | **0%** | 🔴 No progress |
| **Entity defs** | 1/mod (manual) | 1/mod | **15 total** (Create: 9) | 🟡 Partial fix |
| **Avg output size** | ~36 KB | 295 KB | **302 KB** | Stable |

## Per-Mod Results

| Mod | Textures | Models | Entities | Recipes | Sounds | Overall |
|-----|----------|--------|----------|---------|--------|---------|
| **Iron Chests** | 36/36 **(100%)** ✅ | 0/28 | 1 | 0/44 | — | 🟡 |
| **Waystones** | 23/25 **(92%)** ✅ | 0/50 | 1 | 0/34 | — | 🟡 |
| **Farmer's Delight** | 358/395 **(91%)** ✅ | 0/342 | 1 | 0/533 | 0/19 | 🟡 |
| **Supplementaries** | 681/1,103 **(62%)** 🟡 | 0/1,702 | 1 | 0/459 | 0/129 | 🟡 |
| **Create** | 633/1,289 **(49%)** 🟡 | 0/2,684 | **9** 🟢 | 0/2,782 | 0/39 | 🟡 |
| **Xaero's Minimap** | 12/12 **(100%)** ✅ | — | 1 | — | — | ✅ |
| **JourneyMap** | 22/323 (7%) 🔴 | — | 1 | — | — | 🟡 |
| **JEI** | 0/46 (0%) 🔴 | — | 0 | — | — | 🔴 |

## Entity Fix Assessment (#1027)

PR #1027 partially resolved the entity detection regression. **Create** jumped from 1 → 9 entity definitions (the only mod where full AST found entity textures/models). Most other mods still show 1 entity because:
- The fix correctly routes through `analyze_jar_with_ast()` first
- But entity RP (resource pack) definitions only generate when entity textures are found in JAR
- Most mods have entities but no textures at standard entity texture paths (`/textures/entity/`)
- **Iron Chests**: chest tile entities — textures live at `/textures/block/`, not `/textures/entity/`
- **Create**: has actual entity textures (contraption entities, trains) — hence 9 defs

**Conclusion:** The entity regression is fixed at the routing level, but entity texture matching needs broadening to handle block entities and non-standard texture paths. This is a #1001 (BlockEntity classification) concern.

## Gap Status

| Converter | Coverage | Issue | Status |
|-----------|----------|-------|--------|
| **Textures** | 54.7% | #999 | ✅ Closed |
| **Entity detection** | Partial (15 defs) | #1023/#1027 | 🟡 Routing fixed, texture matching still narrow |
| **Models** | **0%** (4,806 missing) | #1000 | 🔴 **P0 — Week 3-4** |
| **Recipes** | **0%** (3,852 missing) | #998 | 🔴 **P0 — Week 3-4** |
| **BlockEntity classification** | Not started | #1001 | 🔴 **P0 — Week 3-4** |
| **Sounds** | 0% (187 missing) | #1002 | 🟡 P1 |
| **Localization** | 0% (292 files missing) | N/A | 🟡 P1 |

## B2B Readiness Score

| Dimension | Score | Notes |
|-----------|-------|-------|
| **Structural integrity** | 100% | 8/8 valid .mcaddon files, zero crashes |
| **Texture fidelity** | 55% | Excellent for simple mods (90-100%), weaker for complex (49-62%) |
| **Model fidelity** | 0% | Complete gap — blocks look flat without models |
| **Recipe fidelity** | 0% | Complete gap — mods unplayable without crafting |
| **Entity fidelity** | ~10% | Routing fixed, but most entities still missing RP definitions |
| **Weighted overall** | **~25-30%** | Needs models + recipes to reach 60% target |
