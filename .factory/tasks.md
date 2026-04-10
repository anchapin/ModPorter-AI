# Current Tasks

## In Progress
- 🔄 Issue #1034: Wire model + recipe converters into main convert_mod() pipeline
  - ✅ Add BlockItemGenerator import
  - ✅ Add model extraction via _extract_and_convert_models() 
  - ✅ Add recipe extraction via _extract_recipes_from_jar()
  - ✅ Add _convert_java_model_to_bedrock() conversion function
  - ⏳ Test end-to-end with real mod JAR

## Pending
- 🔄 Issue #971: E2E validation with 20+ real Java mods
  - ✅ Audit v1 (Apr 8): 8 real mods tested, all produce valid .mcaddon, 1-19% content coverage
  - ✅ Audit v2 (Apr 9): Bulk texture extraction (#999) → 54.8% texture coverage
  - ✅ Audit v3 (Apr 10): Entity detection fix (#1027) → 15 entity defs, textures stable at 54.7%
  - ⏳ Expand test library from 8 → 20+ mods

## Week 3-4 Sprint (Due: May 4) — NOT STARTED
- 🔴 Issue #1000: Model conversion — Java block/entity models → Bedrock geometry (0/4,806 models)
- 🔴 Issue #998: Recipe conversion — Java data pack recipes → Bedrock format (0/3,852 recipes)
- 🔴 Issue #1001: BlockEntity classification — tile entities misclassified as mobs
- 🔴 Issue #1004: Conversion report — per-mod breakdown (depends on #1000, #998)
- 🟡 Issue #1003: Full entity behaviors, spawn rules, loot tables, animation
- 🟡 Issue #1002: Sound and localization extraction (0/187 sounds, 0/292 lang files)

## Recently Completed
- ✅ Issue #1027: Entity detection regression fix (use AST-first path in convert_mod)
- ✅ Issue #1026: Flaky perf test fix (CI-deterministic thresholds)
- ✅ Issue #1025: AI engine test configuration
- ✅ Issue #1020: Security — fix token logging
- ✅ Issue #1019: Production secrets management
- ✅ Issue #999: Bulk texture extraction (54.7% coverage)
- ✅ Issue #982/#983: Entity converter wired into CLI pipeline
- ✅ Issue #981: Entity converter failure RCA + GitHub issue
- ✅ Issue #969: Production secrets management and security hardening

## Conversion Audit Summary (Apr 10, 2026)
- Pipeline: `775e339` (latest main)
- 8 real-world mods: Iron Chests, Waystones, Farmer's Delight, Supplementaries, Create, Xaero's Minimap, JourneyMap, JEI
- Pass rate: 8/8 (100%) — zero crashes
- Texture coverage: 54.7% (1,765/3,229)
- Model coverage: 0% (0/4,806)
- Recipe coverage: 0% (0/3,852)
- Entity defs: 15 total (Create: 9)
- B2B readiness: ~25-30% weighted
