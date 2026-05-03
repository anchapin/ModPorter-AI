# Troubleshooting Guide

This guide helps you resolve common issues when using Portkit to convert Java mods to Bedrock add-ons.

## Table of Contents

- [Upload Issues](#upload-issues)
- [Conversion Failures](#conversion-failures)
- [Missing Features](#missing-features)
- [Installation Problems](#installation-problems)
- [Runtime Errors](#runtime-errors)
- [Performance Issues](#performance-issues)

---

## Upload Issues

### "File not supported" Error

**Problem**: Your mod file won't upload

**Possible Causes**:
1. File format not supported (must be .jar or .zip)
2. File corrupted during download
3. File size exceeds limit (100MB for free tier)
4. Mod uses non-standard loader (not Forge/Fabric)

**Solutions**:

```bash
# Verify file type
file your_mod.jar

# Check file size
ls -lh your_mod.jar

# Validate JAR structure
unzip -l your_mod.jar | grep ".class"
```

**Workaround**:
- Re-download the mod from original source
- Extract and re-package as ZIP
- For non-Forge/Fabric mods, contact support

### "Mod analysis timeout"

**Problem**: Analysis takes longer than 2 minutes

**Causes**:
- Very large mod (>10,000 Java files)
- Complex dependencies
- Server overload

**Solutions**:
1. Wait and retry (server may be busy)
2. Split mod into smaller parts
3. Upgrade to Pro for priority processing
4. Use API for batch processing

---

## Conversion Failures

### "Conversion failed: Java parsing error"

**Problem**: AI cannot parse Java code

**Common Causes**:
1. Obfuscated code (common in decompiled mods)
2. Non-standard Java syntax
3. Corrupted class files

**Solutions**:

```java
// BAD - Obfuscated code
class a {
    public void a(b c) { ... }
}

// GOOD - Deobfuscated code
class SwordItem {
    public void attack(Entity target) { ... }
}
```

**Fix**:
- Use deobfuscator (ForgeFlower, CFR)
- Re-compile from source if available
- Contact mod author for deobfuscated version

### "Conversion failed: Missing dependencies"

**Problem**: Mod requires libraries not found

**Example Error**:
```
Error: Could not find dependency: com.example.library:1.0.0
```

**Solutions**:
1. Check if dependencies are bundled in JAR
2. Upload dependencies separately
3. Use mod with dependencies included
4. Manually add missing libraries to .mcaddon

### "Out of memory during conversion"

**Problem**: Large mod causes memory errors

**Solutions**:
- Split mod into smaller modules
- Close other browser tabs
- Upgrade to Pro for higher memory limits
- Use API with increased timeout

---

## Missing Features

### "Items not appearing in game"

**Problem**: Conversion succeeds, but items don't show up

**Diagnosis**:

```bash
# Check if items are defined
unzip your.mcaddon -d temp
find temp -name "items/*.json"

# Verify identifiers
cat temp/behavior_packs/*/items/*.json | grep "identifier"
```

**Common Causes**:

1. **Experimental Features Disabled**
   - Solution: Enable in world settings
   - Settings → Experimental → "Holiday Creator Features"

2. **Wrong Identifier Format**
   ```json
   // BAD
   "identifier": "RubySword"

   // GOOD
   "identifier": "modpack:ruby_sword"
   ```

3. **Missing Creative Category**
   ```json
   // Add to item components
   "minecraft:creative_category": {
     "category": "equipment"
   }
   ```

### "Textures not loading"

**Problem**: Items appear as purple/black blocks

**Diagnosis**:

```bash
# Check texture files exist
find .mcaddon -name "*.png"

# Verify texture paths
cat behavior_packs/*/items/*.json | grep "texture"
```

**Solutions**:

1. **Resource pack not activated**
   - Settings → Global Resources → Activate resource pack

2. **Wrong texture path**
   ```json
   // BAD
   "textures/ruby_sword.png"

   // GOOD
   "textures/items/ruby_sword.png"
   ```

3. **Texture format issue**
   - Must be PNG format
   - Resolution: Power of 2 (16x16, 32x32, 64x64)
   - No transparency in main image (use separate alpha)

### "Custom behaviors not working"

**Problem**: Item/block doesn't behave as expected

**Example**: Sword doesn't deal custom damage

**Diagnosis**:

```javascript
// Check scripts are loaded
find .mcaddon -name "*.js"

// Look for console errors
// Minecraft Bedrock: Settings → Profile → Enable Content Logger
```

**Common Issues**:

1. **Script API not enabled**
   - Settings → Experimental → "Custom Biomes" (enables Script API)

2. **Syntax errors in JavaScript**
   ```javascript
   // BAD
   function onAttack() {
     damage = 10;
   }

   // GOOD
   function onAttack(event) {
     event.target.applyDamage(10);
   }
   ```

3. **Event handler not registered**
   ```javascript
   // Make sure to register
   world.events.beforeItemUseOn.subscribe(onUse);
   ```

---

## Installation Problems

### ".mcaddon file won't import"

**Problem**: Double-clicking file does nothing

**Platform-Specific Solutions**:

**Windows 10/11**:
```powershell
# Associate .mcaddon with Minecraft
assoc .mcaddon=MCAddonFile
ftype MCAddonFile="C:\Path\To\BedrockLauncher.exe" "%1"
```

**iOS**:
1. Save .mcaddon to Files app
2. Open in Minecraft → Settings → Storage
3. Import behavior pack

**Android**:
1. Download with Chrome
2. Open in Minecraft (should auto-open)
3. Or: Minecraft → Settings → Storage → Import

**Xbox/PS/Switch**:
1. Upload file to cloud storage (OneDrive, Google Drive)
2. Open in Minecraft browser
3. Download and import

### "Import failed: File too large"

**Problem**: File exceeds Marketplace size limit

**Limits**:
- Free: 100MB
- Pro: 500MB
- Enterprise: 2GB

**Solutions**:
1. Optimize textures (reduce resolution)
2. Compress sounds (use OGG format)
3. Remove unused assets
4. Split into multiple .mcaddon files

---

## Runtime Errors

### "Script runtime error: [string]"error

**Problem**: Add-on crashes when used

**Diagnosis**:

1. **Enable Content Logger**:
   - Minecraft Settings → Profile → "Enable Content Logger GUI"
   - Restart game
   - Check error messages

2. **Check Console**:
   ```
   Error: Script runtime error
   at scripts/main.js:15:5
   TypeError: Cannot read property 'damage' of undefined
   ```

**Common Fixes**:

```javascript
// BAD - Undefined check
function onAttack(event) {
  event.target.applyDamage(damage);
}

// GOOD - Null check
function onAttack(event) {
  if (event.target) {
    event.target.applyDamage(10);
  }
}
```

### "Pack format mismatch"

**Problem**: Warning about format versions

**Example**:
```
Warning: Pack format 1.16.0 may not be compatible
```

**Solution**:

Update format version in `manifest.json`:

```json
{
  "format_version": "1.16.100",
  "header": {
    "name": "My Addon",
    "version": [1, 0, 0],
    "uuid": "..."
  }
}
```

---

## Performance Issues

### "Lag when using custom item"

**Problem**: Game FPS drops with add-on

**Causes**:
1. Inefficient JavaScript loops
2. High-resolution textures
3. Too many event listeners

**Solutions**:

```javascript
// BAD - Runs every tick
world.events.tick.subscribe(() => {
  // Heavy computation
  for (let entity of world.getEntities()) {
    // Expensive operation
  }
});

// GOOD - Runs only when needed
world.events.beforeItemUse.subscribe((event) => {
  // Only runs when item used
  let entity = event.source;
  // Lightweight operation
});
```

**Texture Optimization**:
- Use 16x16 for simple items
- Use 32x32 for detailed items
- Avoid 128x128+ unless necessary

---

## Getting Help

### Automated Diagnostics

Use our diagnostic tool:

```bash
# Upload your .mcaddon for analysis
curl -X POST https://api.portkit.cloud/diagnose \
  -F "file=@addon.mcaddon" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

### Contact Support

**Include in your request**:
1. Mod name and version
2. Conversion report (attach PDF)
3. Error messages (screenshots)
4. Console logs from Content Logger

**Support Channels**:
- Email: support@portkit.cloud
- Discord: [discord.gg/modporter](https://discord.gg/modporter)
- GitHub Issues: [github.com/anchapin/portkit/issues](https://github.com/anchapin/portkit/issues)

### Community Help

- **Forum**: [community.portkit.cloud](https://community.portkit.cloud)
- **Wiki**: [docs.portkit.cloud](https://docs.portkit.cloud)
- **YouTube**: [youtube.com/@modporter](https://youtube.com/@modporter)

---

## Common Error Codes

| Error Code | Meaning | Solution |
|------------|---------|----------|
| `E001` | Invalid file format | Use .jar or .zip |
| `E002` | File too large | Compress or upgrade plan |
| `E003` | Java parse error | Deobfuscate code |
| `E004` | Missing dependency | Include libraries |
| `E005` | Timeout | Split mod or retry |
| `E006` | Out of memory | Close tabs, retry |
| `E007` | Script error | Check JavaScript syntax |
| `E008` | Texture error | Verify PNG format |
| `E009` | Model error | Validate JSON schema |
| `E010` | Pack format error | Update manifest |

---

## Prevention Tips

**Before Conversion**:
- Test mod works in Java Edition
- Clean up unused code
- Document custom behaviors
- Use standard APIs

**After Conversion**:
- Test on clean installation
- Verify all platforms work
- Profile performance
- Document manual steps

**Best Practices**:
- Keep mods simple when possible
- Avoid experimental Java features
- Use standard Minecraft APIs
- Test incrementally

---

Still stuck? Our AI-powered chatbot can help 24/7 at [portkit.cloud/support](https://portkit.cloud/support).
