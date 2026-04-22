# Conversion Audit - Test Mod Shortlist

## Purpose

This document tracks mods used for conversion testing and their license compliance. Only mods with permissive licenses that allow derivative works are approved for use in ModPorter AI's conversion testing.

## License Requirements

**Required License Characteristics:**
- Must allow creation of derivative works
- Must be compatible with commercial use
- Cannot restrict modifications or conversions

**Approved Licenses:** MIT, BSD, Apache 2.0, GPL 3.0+, CC0, Unlicense

**Prohibited Licenses:** CC BY-NC-ND, CC BY-NC, proprietary/eula

## Approved Test Mods

| Mod Name | Category | License | Conversion Focus |
|----------|----------|---------|-----------------|
| Simple Copper Block | Block | MIT | Basic block conversion |
| The Aether | Dimension/World Gen | GPL 3.0 | World generation, dimensions |
| Terralith | World Gen Datapack | MIT | Biome and terrain conversion |
| Blue Skies | Dimension/Biome | MIT | Multi-dimensional biome conversion |
| Oh The Biomes You'll Go | Biome | MIT | Biome generation and mapping |

## Removed Mods

### Biomes O' Plenty (REMOVED)
- **Reason:** CC BY-NC-ND 4.0 license violation
- **Issue:** [#1021](https://github.com/anchapin/portkit/issues/1021)
- **Removal Date:** 2026-04-09
- **Impact:** Cannot legally produce derivative works from this mod
- **Replacement:** Terralith (MIT licensed)

## Replacement Justification

### Terralith (Selected)
- **License:** MIT License (permissive, allows derivatives)
- **Coverage:** World generation, biome/terrain conversion
- **Type:** Datapack format (demonstrates datapack conversion)
- **Repository:** https://github.com/Terralith-Vanilla/terralith

### Alternative Candidates (Not Selected)
- **The Aether** - GPL 3.0 (strong copyleft, may complicate commercial use)
- **Blue Skies** - MIT (valid alternative, different biome set)
- **Oh The Biomes You'll Go** - MIT (valid alternative)

## QA Test Library Registry

Test mods must be registered in `tests/fixtures/README.md` with:
- License verification
- Conversion capability coverage
- Maintenance status

### Registry Categories
1. **Baseline Mods** - Basic features for fundamental conversion testing
2. **Feature Mods** - Test specific conversion capabilities (entities, GUIs, dimensions)
3. **Complex Logic Mods** - Test advanced conversion scenarios

## Compliance Verification

Before adding a mod to the test shortlist:
1. Verify license allows derivative works
2. Confirm license is on approved list
3. Document conversion coverage in registry
4. Add to this document with license info

## Related Issues

- [#1021](https://github.com/anchapin/portkit/issues/1021) - Biomes O' Plenty license violation
