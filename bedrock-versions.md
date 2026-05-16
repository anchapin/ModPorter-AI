# Bedrock Version Compatibility

This document covers Bedrock Edition version compatibility, cross-version support, and migration guidance for converted mods.

## Version Support Matrix

Portkit supports conversion targeting the following Bedrock Edition versions:

| Bedrock Version | Support Level | Default | Notes |
|-----------------|---------------|---------|-------|
| 1.19.x | Full | No | Stable release, wide player base |
| 1.20.x | Full | Yes | Current default target |
| 1.21.x | Full | No | Latest features, newest format |

### Setting Target Version

Specify the target Bedrock version during conversion:

```json
{
  "target_version": "1.20"
}
```

Or via API:

```bash
curl -X POST http://localhost:8080/api/v1/convert \
  -H "Content-Type: application/json" \
  -d '{"file": "mod.jar", "target_version": "1.20"}'
```

---

## Cross-Version Compatibility

### What Happens When Players Use Different Versions

When a converted mod targets a specific Bedrock version but players use a different version:

| Player Version vs Target | Compatibility | Behavior |
|------------------------|---------------|----------|
| Same version | Full | Works as expected |
| Newer version (e.g., target 1.20, player has 1.21) | Generally works | Forward compatibility usually holds; features may be missing if they rely on newer APIs |
| Older version (e.g., target 1.20, player has 1.19) | May fail | Backward compatibility is not guaranteed; newer component formats may not parse |

### Forward Compatibility

Converted mods targeting an older Bedrock version generally work on newer versions because:

1. **Component evolution**: Bedrock adds new components but rarely removes or breaks existing ones
2. **JSON format stability**: Schema changes are typically additive
3. **Script API compatibility**: Script API is designed with backward compatibility in mind

**Recommendation**: Target the oldest version your players use to maximize compatibility.

### Backward Compatibility

Mods targeting Bedrock 1.20+ may fail on 1.19 due to:

- New item/block components introduced in 1.20 (e.g., `minecraft:weapon` item component)
- Updated entity component syntax
- New recipe formats

If you need 1.19 compatibility, target 1.19 explicitly.

---

## Feature Gaps by Version

Some features are only available in newer Bedrock versions. Use this matrix to understand which features require which versions.

### Item Components

| Feature | 1.19 | 1.20 | 1.21 |
|---------|------|------|------|
| Basic item properties | Yes | Yes | Yes |
| Enchantments (standard) | Yes | Yes | Yes |
| Food items | Yes | Yes | Yes |
| `minecraft:weapon` component | No | Yes | Yes |
| `minecraft:repairable` component | No | Yes | Yes |
| Charged items | No | Partial | Yes |

### Block Features

| Feature | 1.19 | 1.20 | 1.21 |
|---------|------|------|------|
| Basic blocks | Yes | Yes | Yes |
| Block entities | Yes | Yes | Yes |
| Custom block models | Yes | Yes | Yes |
| Block component updates | No | Yes | Yes |
| `minecraft:geometry` component | No | Yes | Yes |

### Entity Features

| Feature | 1.19 | 1.20 | 1.21 |
|---------|------|------|------|
| Basic mobs | Yes | Yes | Yes |
| Projectiles | Yes | Yes | Yes |
| Custom AI (goals) | Partial | Yes | Yes |
| `minecraft:behavior.*` components | Yes | Yes | Yes |
| Dynamic asset loading | No | No | Yes |

### Recipe Features

| Feature | 1.19 | 1.20 | 1.21 |
|---------|------|------|------|
| Shaped recipes | Yes | Yes | Yes |
| Shapeless recipes | Yes | Yes | Yes |
| Smelting recipes | Yes | Yes | Yes |
| Stonecutter recipes | Yes | Yes | Yes |
| Smithing recipes | No | Yes | Yes |

### Script API

| Feature | 1.19 | 1.20 | 1.21 |
|---------|------|------|------|
| Basic scripting | Yes | Yes | Yes |
| `@minecraft/server` v1.x | Yes | Yes | Yes |
| `@minecraft/server-ui` | Yes | Yes | Yes |
| `World immutable methods` | No | Yes | Yes |
| `Dimension.getEntities()` filtering | No | Yes | Yes |

---

## Multi-Version Output

### Current Capability

Portkit generates a single target version per conversion. To create mods for multiple Bedrock versions, run conversions separately for each target version.

### Workflow for Multi-Version Support

1. **Identify your player base versions**
   - Survey or check server logs to understand which Bedrock versions your players use
   - Prioritize the versions with the most players

2. **Convert for each target version**

   ```bash
   # Convert for Bedrock 1.19
   curl -X POST http://localhost:8080/api/v1/convert \
     -d '{"file": "mod.jar", "target_version": "1.19"}' -o mod-1.19.mcaddon

   # Convert for Bedrock 1.20
   curl -X POST http://localhost:8080/api/v1/convert \
     -d '{"file": "mod.jar", "target_version": "1.20"}' -o mod-1.20.mcaddon

   # Convert for Bedrock 1.21
   curl -X POST http://localhost:8080/api/v1/convert \
     -d '{"file": "mod.jar", "target_version": "1.21"}' -o mod-1.21.mcaddon
   ```

3. **Distribute appropriate versions**
   - Host multiple download links per version
   - Clearly label which file is for which version
   - Consider using Modrinth/Planet Mods with version-specific downloads

4. **Document version requirements**
   - Clearly state the minimum Bedrock version in your mod description
   - Include a compatibility note in your mod's README

### Planned Improvements

Multi-version output in a single conversion is on the roadmap. Track progress in GitHub issue #1552.

---

## Migration Guide

### Moving from Older to Newer Bedrock Targeting

When you want to update your converted mod to target a newer Bedrock version:

### Step 1: Review Feature Gaps

Check the [Feature Gaps by Version](#feature-gaps-by-version) section above. If your mod uses features only available in newer versions, verify they work correctly.

### Step 2: Re-Run Conversion

```bash
curl -X POST http://localhost:8080/api/v1/convert \
  -d '{"file": "original-mod.jar", "target_version": "1.21"}' -o mod-updated.mcaddon
```

### Step 3: Validate Output

1. Extract and inspect the generated add-on
2. Check that new component formats are used correctly
3. Verify JSON syntax is valid
4. Test in-game on the target Bedrock version

### Step 4: Compare with Previous Output

Review the conversion report for any new warnings or notes about features that were handled differently.

### Step 5: Update Distribution

1. Replace the old add-on file with the new one
2. Update your mod description to reflect the new target version
3. Notify your player base of the update

---

## Recommendations by Use Case

### For Server Operators

| Scenario | Recommendation |
|----------|----------------|
| All players on same version | Target that version explicitly |
| Mixed version player base | Target the oldest common version or provide multiple downloads |
| Planning a server upgrade | Upgrade player base first, then re-convert for newer version |

### For Mod Developers

| Scenario | Recommendation |
|----------|----------------|
| New conversion | Target Bedrock 1.20 (default) unless you need 1.19 compatibility |
| Existing mod with issues on 1.21 | Re-convert targeting 1.21 after checking feature gaps |
| Maintaining multiple versions | Consider automated conversion pipeline using the API |

### For Compatibility-Critical Projects

If your project cannot tolerate any compatibility risk:

1. Target the oldest Bedrock version that has all the features you need
2. Test on all target versions before release
3. Maintain separate conversion outputs per version
4. Document minimum version requirements clearly

---

## Troubleshooting Version Issues

### Mod Works on 1.20 but Not 1.19

**Cause**: Your mod uses features introduced in Bedrock 1.20.

**Solution**:
1. Re-convert targeting 1.19 explicitly
2. Check the conversion report for features that couldn't be downgraded
3. Manually adjust any 1.20-only features

### Add-on Won't Install

**Cause**: Invalid manifest `header.version` or format_version incompatibility.

**Solution**:
1. Verify the `manifest.json` has valid version fields
2. Ensure `format_version` matches the target Bedrock version schema
3. Check that all referenced files exist in the package

### Features Missing In-Game

**Cause**: Some features may fail silently if Bedrock doesn't recognize them.

**Solution**:
1. Check the Bedrock Edition version matches your target
2. Verify the component names are correct for that version
3. Enable debug logging during conversion to see warnings

---

## Additional Resources

- [MINECRAFT_VERSION_TRACKING.md](./MINECRAFT_VERSION_TRACKING.md) - How Portkit tracks and updates for new Minecraft versions
- [conversion-guide.md](./conversion-guide.md) - General conversion process and options
- [Bedrock Creator Documentation](https://learn.microsoft.com/en-us/minecraft/creator/)
- [Minecraft Changelog](https://www.minecraft.net/en-us/article/minecraft-java-edition-1-21)

---

## Version History

| Date | Version | Changes |
|------|---------|---------|
| 2024-01 | 1.0 | Initial release |
| 2025-05 | 1.1 | Added 1.21 support, cross-version compatibility details |
