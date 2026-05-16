# Mod Loader Detection and Upgrade Guidance

This guide covers mod loader compatibility, detection methods, and migration paths for converting Java Edition mods to Bedrock Edition.

## Supported Mod Loaders

| Loader | Version Support | Notes |
|--------|----------------|-------|
| Forge | 1.19+ | Recommended for conversion |
| Fabric | 1.19+ | Lightweight, good compatibility |
| Fabric + Mixin | 1.16.5+ | Requires special handling |

### Forge 1.19+

Fully supported. Update to latest stable Forge version before conversion.

**To check your Forge version:**
1. Open Minecraft launcher
2. Select the modded profile
3. Click "Edit" → check version in profile editor

### Fabric 1.19+

Supported. Ensure Fabric API is updated to latest version.

**To check Fabric version:**
1. Locate `fabric-loader` in your mods folder
2. Check the version in the filename: `fabric-loader-X.X.X.jar`

### Fabric with Mixin

Partially supported. Mixin is used for bytecode injection and requires special handling.

**Detection**: Look for `mixin` references in mod JSON or `mixin.refmap.json` files.

---

## Problematic Patterns

These patterns cause conversion failures or silent corruption:

### 1. Mixin Usage

**Problem**: Mixin injects bytecode at runtime, which cannot be statically analyzed.

**Symptoms**:
- Conversion succeeds but mod crashes in-game
- Missing functionality that appeared to convert
- Silent corruption of class files

**Detection**:
```bash
# Check for Mixin configuration files
find . -name "*mixin*" -o -name "*Mixin*" | head -20

# Look for Mixin annotations in JAR
unzip -l yourmod.jar | grep -i mixin
```

**Files indicating Mixin usage**:
- `mixinrefs.json`
- `mixin.config`
- Classes annotated with `@Mixin`
- `net.fabricmc.mixin` package references

### 2. Access Wideners

**Problem**: Access wideners modify class access modifiers, causing binary incompatibilities.

**Detection**:
```bash
# Check for .accesswidener files
find . -name "*.accesswidener"

# In JAR contents
unzip -l yourmod.jar | grep -i accesswidener
```

**Note**: Access wideners often accompany Mixin usage.

### 3. Forge Internal API Usage

**Problem**: Internal APIs (`net.minecraftforge.internal`, `net.minecraftforge.fml.internal`) are not stable and change between versions.

**Detection**:
```java
// Patterns to search for in decompiled source
import net.minecraftforge.internal
import net.minecraftforge.fml.internal
import net.minecraftforge.api.internal

// Obfuscated names (if not deobfuscated)
net/minecraftforge/
```

**Impact**: Non-convertible. These APIs have no Bedrock equivalent.

### 4. ASM Bytecode Manipulation

**Problem**: Direct bytecode manipulation using ASM or similar libraries cannot be converted.

**Detection**:
```java
// Search for these imports
import org.objectweb.asm
import org.apache.commons.asm
import jdk.internal.vm.annotation  // JDK internal manipulation

// Look for ClassReader/ClassWriter usage
```

---

## Detection Guide

### Quick Detection (Automated)

Use this checklist to determine if your mod is convertible:

- [ ] No `mixin` references in mod JAR
- [ ] No `.accesswidener` files
- [ ] No `net.minecraftforge.internal` imports
- [ ] No direct `org.objectweb.asm` usage
- [ ] Mod targets Forge 1.19+ or Fabric 1.19+

If any box is unchecked, see [Migration Paths](#migration-paths) below.

### Manual Detection Steps

1. **Extract the JAR**:
```bash
unzip yourmod.jar -d extracted_mod
```

2. **Check for problematic files**:
```bash
# List all config and JSON files
find extracted_mod -name "*.json" -o -name "*.accesswidener" -o -name "*mixin*"
```

3. **Analyze class dependencies** (requires Java decompiler):
```bash
# Use Fernflower or Procyon to decompile
# Check imports for internal Forge/Fabric patterns
```

4. **Check mods.toml or fabric.mod.json**:
```bash
# Forge mods have mods.toml
cat extracted_mod/META-INF/mods.toml

# Fabric mods have fabric.mod.json
cat extracted_mod/fabric.mod.json
```

---

## Migration Paths

### Upgrading from Forge 1.16.5 to 1.19+

**Why upgrade**: Forge 1.16.5 uses deprecated internal APIs not available in 1.19+.

**Steps**:
1. Backup your current mod project
2. Update `build.gradle` to use new Forge version:
```groovy
minecraft {
    mappings channel: 'official', version: '1.19.4'
}

dependencies {
    minecraft 'net.minecraftforge:forge:1.19.4-45.1.0'
}
```
3. Update any deprecated API calls
4. Test extensively before conversion

**Timeline**: 4-8 hours for typical mods.

### Upgrading from Fabric 1.16.5 to 1.19+

**Steps**:
1. Update `fabric.mod.json`:
```json
{
  "depends": {
    "fabricloader": ">=0.14.0",
    "fabric-api": ">=0.76.0"
  }
}
```
2. Update Mixin configuration if used
3. Update mod initialization code for API changes

### Removing Mixin Dependencies

For Mixin-dependent mods, you have two options:

**Option A: Remove Mixin (if functionality can be achieved differently)**
1. Identify what Mixin was doing
2. Rewrite using standard Forge event system
3. Test equivalent functionality

**Option B: Accept Limited Conversion**
- Portkit will convert what it can
- Non-Mixin features may work
- Mixin-injected features will be missing
- Document expected limitations

### Handling Access Wideners

Access wideners typically serve one of two purposes:

1. **Accessing private members**: Rewrite to use public APIs or events
2. **Subclassing internal classes**: Find stable alternatives or refactor

---

## Community Workarounds

### Pattern 1: Multi-Version Support

Some mod authors maintain separate branches for different versions:

```bash
# Example: Branch structure
main           # Latest
1.19-port      # 1.19 version
1.18.2-port    # 1.18.2 version
```

**Strategy**: Convert from the most recent stable version with compatible code.

### Pattern 2: Dependency Splitting

Split mod into convertibile and non-convertible parts:

```
mod-core/           # Convertible base functionality
mod-integration/    # Forge-specific, not converted
```

**Result**: Core converts, integration features documented as manual work.

### Pattern 3: Equivalent Replacement

Find Bedrock-native alternatives for Java-specific features:

| Java Feature | Bedrock Equivalent |
|--------------|---------------------|
| Forge Events | Bedrock Event System |
| Mixin | Script API + Events |
| Internal API | Public API Wrapper |

### Pattern 4: Community Resources

- **Discord**: Ask in `#conversion-help` for mod-specific guidance
- **GitHub**: Check if similar mods have documented conversion paths
- **Wiki**: Some mods have community-maintained conversion guides

---

## Decision Matrix

Use this matrix to determine your path forward:

| Condition | Action |
|-----------|--------|
| Mod uses Mixin + Access Widener | Remove Mixin first, then convert |
| Mod uses Forge internal APIs | Refactor to public APIs, then convert |
| Mod uses ASM bytecode manipulation | Accept limitations or rewrite feature |
| Mod is Forge 1.16.5 | Upgrade to 1.19+ before converting |
| Mod is Fabric + Mixin 1.16.5 | Upgrade Fabric/Mixin, then convert |
| Mod meets all detection criteria | Ready for conversion |

---

## Pre-Conversion Checklist

Before uploading to Portkit:

- [ ] Updated to Forge 1.19+ or Fabric 1.19+
- [ ] No Mixin dependencies (or documented as limited)
- [ ] No Access Wideners (or converted to public API)
- [ ] No Forge internal API usage
- [ ] No direct bytecode manipulation
- [ ] Tested original mod works correctly
- [ ] Backed up original JAR

---

## Getting Help

If your mod has problematic patterns:

1. **Discord**: Post in `#mod-loader-help` with:
   - Mod name and version
   - Which problematic patterns apply
   - Screenshots of any errors

2. **GitHub**: Open an issue with:
   - Mod loader and version
   - Detection command output
   - Specific features that may not convert

3. **Community**: Search existing discussions for similar mods

---

## Version History

| Date | Version | Changes |
|------|---------|---------|
| 2024-06 | 1.0 | Initial release |
| 2024-07 | 1.1 | Added community workarounds section |

---

*Last updated: 2024-07*