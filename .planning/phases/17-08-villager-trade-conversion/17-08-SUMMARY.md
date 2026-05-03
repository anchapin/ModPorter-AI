---
phase: "17-08"
plan: "01"
subsystem: "ai-engine/converters"
tags: [villager, trade, conversion, bedrock, java]
dependency_graph:
  requires:
    - "17-07"
  provides:
    - "VillagerConverter"
    - "TradeOfferConverter"
    - "VillagerPatternLibrary"
  affects:
    - "ai-engine/converters"
    - "ai-engine/knowledge/patterns"
tech_stack:
  added:
    - "VillagerProfession enum (16 professions)"
    - "VillagerConverter class"
    - "TradeOfferConverter class"
    - "VillagerPatternLibrary class (20 patterns)"
    - "TradeDefinition dataclass"
    - "VillagerDefinition dataclass"
  patterns:
    - "Enum-based profession mapping"
    - "Dataclass-based trade definitions"
    - "Pattern library with category filtering"
key_files:
  created:
    - "ai-engine/converters/villager_converter.py"
    - "ai-engine/knowledge/patterns/villager_patterns.py"
    - "ai-engine/tests/test_villager_conversion.py"
decisions:
  - "Use enum for Bedrock professions for type safety"
  - "Implement separate TradeOfferConverter for trade-specific logic"
  - "Create 20 patterns across 6 categories (agriculture, combat, commerce, knowledge, crafting, service)"
  - "Support mod profession fallback to closest Bedrock equivalent"
metrics:
  duration: "task-level commits"
  completed_date: "2026-03-28"
  task_count: 4
  file_count: 3
  test_count: 29
---

# Phase 17-08 Plan 01 Summary: Villager/Trade Conversion

## One-Liner

Villager and trade conversion from Java mods to Bedrock, including profession mapping, career conversion, and custom trade offer support with 20+ pattern library.

## Overview

Implemented complete villager and trade conversion system for converting Java villager professions, careers, and merchant recipes to Bedrock format. The system includes converters for villager entities, profession components, trade tables, and a comprehensive pattern library for RAG-based conversions.

## Tasks Completed

### Task 1: Create VillagerConverter Module
**Commit:** Created `VillagerConverter` with:
- `VillagerProfession` enum with 16 professions (NONE, ARMORER, BUTCHER, CARTOGRAPHER, CLERIC, FARMER, FISHERMAN, FLETCHER, LEATHERWORKER, LIBRARIAN, MASON, SHEPHERD, TOOLSMITH, WEAPONSMITH, NITWIT, UNEMPLOYED)
- Profession mapping from Java to Bedrock
- Career conversion with profession context
- Trade table JSON generation

### Task 2: Create VillagerPatternLibrary
**Commit:** Created `VillagerPatternLibrary` with:
- 20 patterns across 6 categories
- Category filtering (agriculture, combat, commerce, knowledge, crafting, service)
- Search and lookup functionality
- Pattern aliases for mod compatibility

### Task 3: Implement TradeOffer Conversion
**Commit:** Implemented `TradeOfferConverter` with:
- Trade offer conversion (wants/gives)
- Trade level, max uses, experience, price adjustment conversion
- Merchant recipe JSON generation
- Custom trade support (suspicious stew, composter, wandering trader, piglin barter)

### Task 4: Create Unit Tests
**Commit:** Created 29 unit tests covering:
- 5 profession conversion tests
- 3 career conversion tests
- 5 trade conversion tests
- 4 trade offer conversion property tests
- 7 villager pattern tests
- 5 integration tests

## Verification Results

All verification steps passed:
- VillagerConverter initialized successfully (16 professions)
- VillagerPatternLibrary loaded with 20 patterns in 6 categories
- TradeOfferConverter converts basic trade offers correctly
- 29 unit tests passing

## Files Created

| File | Lines | Description |
|------|-------|-------------|
| `ai-engine/converters/villager_converter.py` | ~560 | Villager and trade converter classes |
| `ai-engine/knowledge/patterns/villager_patterns.py` | ~430 | Pattern library with 20 patterns |
| `ai-engine/tests/test_villager_conversion.py` | ~340 | 29 unit tests |

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None - all features fully implemented.

## Self-Check: PASSED

- [x] All imports work correctly
- [x] VillagerConverter with profession mapping (16 professions)
- [x] TradeOfferConverter for trade offers
- [x] VillagerPatternLibrary with 20+ patterns (actually 20)
- [x] 29 unit tests passing (exceeds 20 requirement)
- [x] Trade table generation works