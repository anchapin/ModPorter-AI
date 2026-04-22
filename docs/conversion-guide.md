# Conversion Guide

This guide covers the conversion process, supported features, and best practices for converting Minecraft Java Edition mods to Bedrock Edition add-ons.

## Understanding the Conversion Process

Portkit uses a multi-agent AI system to analyze Java mod code and translate it to Bedrock-compatible formats. The conversion process involves:

1. **Analysis**: Extracting mod structure, dependencies, and components
2. **Translation**: Converting Java code to Bedrock Script API
3. **Asset Conversion**: Processing textures, models, and sounds
4. **Validation**: Checking for errors and compatibility issues
5. **Packaging**: Creating a distributable .mcaddon file

---

## Supported Features

### Blocks

| Feature | Support Level | Notes |
|---------|---------------|-------|
| Basic blocks | Full | Properties, states, loot tables |
| Block entities | Full | Inventory, tile entities |
| Custom textures | Full | PNG support, animation frames |
| Block models (JSON) | Full | Standard Bedrock JSON format |
| Tile entities | Full | Data-driven storage |

### Items

| Feature | Support Level | Notes |
|---------|---------------|-------|
| Basic items | Full | Name, lore, texture |
| Custom textures | Full | PNG support |
| Item components | Full | Bedrock 1.20+ components |
| Enchantments | Partial | Standard enchantments only |
| Food items | Full | Hunger restoration |

### Entities

| Feature | Support Level | Notes |
|---------|---------------|-------|
| Mobs/NPCs | Full | Basic behavior, AI |
| Projectiles | Full | Arrow, fireball, etc. |
| Entity models | Full | JSON models |
| Entity textures | Full | PNG support |
| Custom AI behaviors | Partial | Requires manual adjustment |

### Recipes

| Feature | Support Level | Notes |
|---------|---------------|-------|
| Crafting recipes | Full | Shaped, shapeless |
| Smelting recipes | Full | Furnace, blast furnace |
| Stonecutter recipes | Full | Single item output |
| Brewing recipes | Full | Standard potions |

### Dimensions

| Feature | Support Level | Notes |
|---------|---------------|-------|
| Custom dimensions | Partial | Basic portal setup |
| Biome mapping | Partial | Requires manual tuning |
| Dimension packages | Full | JSON configuration |

### Advanced Features

| Feature | Support Level | Notes |
|---------|---------------|-------|
| Particles | Full | Basic particle effects |
| Sounds | Full | Audio file conversion |
| Loot tables | Full | JSON format |
| Functions/Commands | Full | mcfunction conversion |
| Scoreboard | Partial | Basic objectives |

---

## Conversion Options

### Conversion Modes

Choose the appropriate mode based on your mod's complexity:

#### Simple Mode
- Single block/item conversions
- No complex dependencies
- Basic functionality only
- Best for: Learning, testing, simple mods

```json
{
  "conversion_mode": "simple"
}
```

#### Standard Mode (Default)
- Multiple blocks/items
- Basic entities
- Recipe conversions
- Sound and texture handling
- Best for: Most mod conversions

```json
{
  "conversion_mode": "standard"
}
```

#### Complex Mode
- Full entity support
- Custom AI behaviors
- Advanced scripting
- Dimension/biome conversions
- Best for: Complete mod conversions

```json
{
  "conversion_mode": "complex"
}
```

### Target Versions

Specify the target Bedrock version:

| Version | Support | Notes |
|---------|---------|-------|
| 1.19 | Full | Latest stable |
| 1.20 | Full | Current default |
| 1.21 | Full | Latest features |

```json
{
  "target_version": "1.20"
}
```

### Output Formats

| Format | Extension | Use Case |
|--------|-----------|----------|
| MCAddon | .mcaddon | Distribution, installation |
| ZIP | .zip | Manual extraction |

```json
{
  "output_format": "mcaddon"
}
```

---

## Best Practices

### Before Conversion

#### 1. Clean Your Mod

- Remove unnecessary dependencies
- Simplify complex code where possible
- Update to latest Forge/Fabric version

#### 2. Test the Original

- Ensure the Java mod works correctly
- Document expected behaviors
- Take screenshots for comparison

#### 3. Check Dependencies

- List all required mods
- Identify hard dependencies
- Note optional features

#### 4. Backup Original Files

- Keep original JAR files
- Document any modifications
- Save textures/models separately

### During Conversion

#### 1. Review Analysis Results

- Check detected components
- Verify complexity assessment
- Note potential issues

#### 2. Monitor Progress

- Watch for error messages
- Note failed components
- Check conversion logs

#### 3. Address Warnings

- Review AI assumptions
- Validate translations
- Correct obvious errors

### After Conversion

#### 1. Verify Output

- Check all files generated
- Validate JSON syntax
- Test textures/models

#### 2. Test In-Game

- Install in Bedrock Edition
- Test basic functionality
- Compare to original

#### 3. Document Issues

- Note what didn't convert
- Record manual steps needed
- Track workarounds found

---

## Validation Checklist

Use this checklist to verify your conversion:

### File Structure
- [ ] `.mcaddon` file created
- [ ] `manifest.json` present
- [ ] All textures in `textures/` folder
- [ ] All models in `models/` folder
- [ ] All behaviors in `behavior_packs/`
- [ ] All resources in `resource_packs/`

### Blocks
- [ ] Block places correctly
- [ ] Block breaks correctly
- [ ] Texture displays
- [ ] Metadata/properties work
- [ ] Block events fire

### Items
- [ ] Item appears in inventory
- [ ] Item can be held
- [ ] Item can be used
- [ ] Texture displays
- [ ] Custom NBT preserved

### Entities
- [ ] Entity spawns
- [ ] Entity has correct model
- [ ] Basic AI works
- [ ] Texture displays
- [ ] Entity can be interacted with

### Recipes
- [ ] Recipe shows in crafting
- [ ] Recipe produces output
- [ ] Recipe ingredients correct
- [ ] Recipe shaped correctly

### Sounds
- [ ] Sounds load
- [ ] Sounds play when triggered

---

## Troubleshooting Common Issues

### Blocks Not Appearing

**Cause**: Missing block definition

**Solution**:
1. Check `blocks.json` in behavior pack
2. Verify block ID format (e.g., `modname:blockname`)
3. Ensure block is registered in manifest

### Textures Not Loading

**Cause**: Incorrect texture path

**Solution**:
1. Verify texture file exists in `textures/blocks/` or `textures/items/`
2. Check case sensitivity (Bedrock is case-sensitive)
3. Ensure PNG format with .png extension

### Recipes Not Working

**Cause**: Incorrect recipe format

**Solution**:
1. Verify JSON syntax
2. Check item IDs match
3. Ensure crafting table present (if required)

### Entities Not Spawning

**Cause**: Missing spawn rule or entity definition

**Solution**:
1. Check `entity.json` exists
2. Verify spawn rules in `spawn_rules.json`
3. Ensure entity is enabled in manifest

### Addon Won't Install

**Cause**: Invalid package structure

**Solution**:
1. Verify file is `.mcaddon` not `.zip`
2. Check manifest.json is valid
3. Ensure all required folders present
4. Validate JSON files with linter

### Performance Issues

**Cause**: Too many entities or complex models

**Solution**:
1. Reduce entity count
2. Simplify models
3. Optimize textures (smaller sizes)
4. Remove unused features

---

## Manual Adjustments Required

Even with 60-80% automation, some features need manual work:

### Custom GUI Elements
Java GUIs don't map directly to Bedrock. Recreate using:
- Forms (UI screens)
- Custom inventory screens

### Network Code
Bedrock uses different networking:
- Rewrite packet handlers
- Adjust synchronization logic

### Complex AI
Advanced behaviors require manual scripting:
- State machines
- Custom goals
- Behavior trees

### Custom Rendering
Java rendering differs from Bedrock:
- Rewrite render controllers
- Adjust model formats
- Recreate shader effects

### Third-Party Libraries
External dependencies may not convert:
- Identify library usage
- Find Bedrock equivalents
- Manually implement missing features

---

## Advanced Options

### Batch Conversion

Convert multiple mods at once using the batch endpoint:

```bash
curl -X POST http://localhost:8080/api/v1/batch \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "files": [
      {"file_path": "/path/to/mod1.jar"},
      {"file_path": "/path/to/mod2.jar"}
    ],
    "options": {"conversion_mode": "standard"}
  }'
```

### Custom Behavior Templates

Define custom conversion templates for specific patterns:

```json
{
  "templates": [
    {
      "pattern": "CustomBlock",
      "conversion": "custom_block_template.json",
      "description": "Template for custom block types"
    }
  ]
}
```

### Webhook Notifications

Receive real-time updates on conversion progress:

```json
{
  "webhook_url": "https://your-server.com/webhook",
  "webhook_events": ["started", "progress", "completed", "failed"]
}
```

---

## Performance Tips

1. **Limit file size**: Keep mods under 50MB for faster processing
2. **Simplify code**: Remove unused features before conversion
3. **Organize assets**: Use clear folder structure for textures/models
4. **Test incrementally**: Convert simple mods first, then progress

---

## Getting Help

- **Documentation**: [docs.portkit.cloud](https://docs.portkit.cloud)
- **Discord**: [discord.gg/modporter](https://discord.gg/modporter)
- **GitHub Issues**: [github.com/portkit/issues](https://github.com/portkit/issues)
- **FAQ**: [faq.md](faq.md)

---

## Version History

| Date | Version | Changes |
|------|---------|---------|
| 2024-01 | 1.0 | Initial release |
| 2024-02 | 1.1 | Added batch conversion |
| 2024-03 | 1.2 | Added complex mode |
| 2024-04 | 1.3 | Added webhooks |

---

Happy converting!