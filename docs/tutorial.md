# Step-by-Step Conversion Tutorial

This detailed tutorial walks you through converting a Java mod to Bedrock using ModPorter AI. We'll use a simple "Custom Sword" mod as an example.

## Example Mod: Ruby Sword

For this tutorial, we'll convert a simple Java mod that adds:
- A new sword item (Ruby Sword)
- Custom texture
- Attack damage and durability

## Step 1: Prepare Your Java Mod

### What You Need

Your mod should include:
- **Java source files** (.java) - the mod logic
- **Resource files** - textures, models, sounds
- **mod metadata** - mcmod.info, fabric.json, or forge.mods.toml

### Example Structure

```
rubysword.jar
├── assets/
│   └── rubysword/
│       ├── textures/
│       │   └── items/ruby_sword.png
│       └── models/
│           └── item/ruby_sword.json
├── com/example/rubysword/
│   ├── RubySword.java
│   ├── RubySwordItem.java
│   └── RubySwordMod.java
└── META-INF/
    └── mods.toml
```

## Step 2: Upload to ModPorter AI

1. **Navigate to [portkit.cloud](https://portkit.cloud)**
2. **Click "Upload Mod"** or drag-and-drop your .jar file
3. **Wait for analysis** (30-60 seconds)

### What the Analysis Shows

```
Mod Analysis Complete
├── Detected Features
│   ├── Items: 1 (Ruby Sword)
│   ├── Blocks: 0
│   ├── Entities: 0
│   └── Recipes: 0
├── Complexity: Simple
├── Estimated Time: 5 minutes
└── Conversion Confidence: 95%
```

## Step 3: Review Conversion Plan

Before starting, review the AI's plan:

### Detected Components

| Component | Java Class | Bedrock Equivalent | Confidence |
|-----------|-----------|-------------------|------------|
| Ruby Sword Item | RubySwordItem | items/ruby_sword | 95% |
| Texture | ruby_sword.png | textures/items/ruby_sword.png | 100% |
| Model | ruby_sword.json | models/item/ruby_sword.json | 90% |

### Potential Issues

- **High confidence**: No issues expected
- **Medium confidence**: May need manual texture adjustment
- **Low confidence**: Custom attack logic may need tweaking

## Step 4: Start Conversion

Click "Start Conversion" and monitor progress:

### Phase 1: Java Analysis (1 minute)

```
✓ Parsing Java code
✓ Building AST (Abstract Syntax Tree)
✓ Analyzing dependencies
✓ Extracting item properties
```

### Phase 2: Bedrock Generation (2 minutes)

```
✓ Creating behavior pack items/
✓ Generating JavaScript item logic
✓ Converting texture format
✓ Creating resource pack structure
```

### Phase 3: Asset Conversion (1 minute)

```
✓ Processing textures (PNG optimization)
✓ Converting JSON models
✓ Validating file formats
```

### Phase 4: Validation (1 minute)

```
✓ Syntax checking (JavaScript)
✓ Schema validation (JSON)
✓ Asset integrity check
✓ Packaging into .mcaddon
```

## Step 5: Review Conversion Report

Once complete, you'll see a detailed report:

### Success Summary

```
Conversion Complete!
Overall Success Rate: 95%
Components Converted: 3/3
Manual Steps Required: 0
```

### Component Inventory

| File | Type | Status | Notes |
|------|------|--------|-------|
| `behavior_packs/rubysword/items/ruby_sword.json` | Item Definition | ✓ Success | - |
| `behavior_packs/rubysword/scripts/main.js` | JavaScript Logic | ✓ Success | Attack damage converted |
| `resource_packs/rubysword/textures/items/ruby_sword.png` | Texture | ✓ Success | Optimized for Bedrock |

### Assumptions Made

The AI explains its decisions:

1. **Attack Damage**: Converted from Java `10` to Bedrock attack damage `10`
2. **Durability**: Mapped to `max_durability` component
3. **Creative Tab**: Assigned to "equipment" category

### Manual Steps (if any)

For simple mods like this, you'll see:
```
No manual steps required! Your add-on is ready to use.
```

For complex mods, you might see:
```
⚠ Manual Steps Required:
1. Custom rendering logic needs JavaScript implementation
2. GUI elements need Bedrock forms (not Java GUI)
3. Network packets need Bedrock scripting API
```

## Step 6: Download and Test

### Download the .mcaddon File

Click "Download Add-on" to save `rubysword.mcaddon` (usually 50-200KB).

### Install in Bedrock Edition

**Windows 10/11:**
1. Double-click the .mcaddon file
2. Minecraft Bedrock opens automatically
3. Click "Import" to install

**Mobile (iOS/Android):**
1. Share the file to Minecraft
2. Open Minecraft → Settings → Storage → Behavior Packs
3. Activate "Ruby Sword"

**Console:**
1. Upload to a file sharing service
2. Download in Minecraft Marketplace → My Packs

### Test the Conversion

**Create a Test World:**

1. Enable cheats and Experimental Features:
   - Create new world
   - Cheats: ON
   - Experimental: "Holiday Creator Features" ON
   - "GameTest Framework" ON (if testing)

2. Obtain the item:
   ```
   /give @p rubysword:ruby_sword
   ```

3. Test functionality:
   - Does the sword appear in your hand?
   - Does it deal correct damage?
   - Does durability decrease?
   - Does the texture look right?

### Common Issues and Fixes

**Item doesn't appear:**
```
Solution: Check that Experimental Features are enabled
```

**Texture is missing:**
```
Solution: Verify resource pack is activated in world settings
```

**Wrong damage values:**
```
Solution: Edit behavior_packs/rubysword/items/ruby_sword.json
Adjust the "minecraft:attack_damage" component
```

## Step 7: Iterate and Improve

If something isn't perfect:

### Option A: Edit the Generated Files

1. Extract the .mcaddon (it's a ZIP file)
2. Edit the JSON/JavaScript files
3. Re-package as .mcaddon

**Example - Adjusting Attack Damage:**

File: `behavior_packs/rubysword/items/ruby_sword.json`
```json
{
  "format_version": "1.16.0",
  "minecraft:item": {
    "description": {
      "identifier": "rubysword:ruby_sword"
    },
    "components": {
      "minecraft:attack_damage": 12,  // Changed from 10
      "minecraft:max_durability": 1500,
      "minecraft:durability": {
        "max_durability": 1500
      }
    }
  }
}
```

### Option B: Re-convert with Adjustments

If the AI made wrong assumptions:
1. Edit the original Java mod
2. Re-upload to ModPorter AI
3. The AI will learn from the previous conversion

### Option C: Use the Visual Editor

Pro users can edit the conversion in our web-based editor:
1. Click "Open in Editor"
2. Make changes visually
3. Export updated .mcaddon

## Step 8: Share and Publish

Once satisfied with your conversion:

### Test Thoroughly

- Test in multiple Bedrock platforms (mobile, PC, console)
- Verify all features work as expected
- Check performance (no lag, crashes)

### Package for Distribution

1. Create a .mcaddon file (already done)
2. Add a README with installation instructions
3. Include screenshots or video demo
4. Test on a clean installation

### Publish Options

**Option 1: Free Distribution**
- Upload to Modrinth
- Share on Discord/Reddit
- Host on your website

**Option 2: Minecraft Marketplace**
- Requires Mojang approval
- Must meet quality standards
- Can monetize your add-on

**Option 3: Share with Community**
- Join our Discord
- Share conversion patterns
- Help improve the AI

## Advanced Tips

### Converting Complex Mods

For mods with custom entities, dimensions, or GUI:

1. **Break it down**: Convert one feature at a time
2. **Use batch mode**: Convert multiple related files together
3. **Leverage RAG**: Search for similar conversions in our database
4. **Manual polish**: Plan time for manual adjustments

### Optimizing Conversion Quality

**Before conversion:**
- Clean up Java code (remove unused imports)
- Standardize naming conventions
- Document custom behaviors

**During conversion:**
- Review the AI's assumptions
- Check confidence scores
- Read the manual steps carefully

**After conversion:**
- Test thoroughly on all platforms
- Profile performance
- Gather user feedback

## Next Steps

Congratulations! You've successfully converted your first mod. Now:

- **Try a complex mod**: Entities, dimensions, GUI
- **Explore the API**: Automate conversions programmatically
- **Join the community**: Share your experience
- **Upgrade to Pro**: Unlock unlimited conversions

## Additional Resources

- [Video Tutorial](https://youtube.com/modporter) (5 minutes)
- [FAQ](faq.md) - Common questions
- [API Documentation](api.md) - For developers
- [Community Discord](https://discord.gg/modporter)

Need help? Contact us at support@portkit.cloud
