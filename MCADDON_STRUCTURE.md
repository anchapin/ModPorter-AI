# Bedrock .mcaddon Package Structure Documentation

## Overview

A `.mcaddon` file is a ZIP archive containing one or more Minecraft Bedrock Edition add-on packages. This document specifies the correct internal structure for importing into Bedrock Edition.

## Critical Structure Requirements

### Top-Level Directories

**CORRECT (Plural):**
```
behavior_packs/
resource_packs/
```

**INCORRECT (Singular) - Will fail to import:**
```
behavior_pack/  ❌
resource_pack/  ❌
```

This is the most common error. Bedrock Edition requires the plural form.

## Complete Package Structure

```
my_addon.mcaddon
├── behavior_packs/                    # BEHAVIOR PACKS (plural)
│   └── my_mod_bp/                     # Individual behavior pack folder
│       ├── manifest.json              # REQUIRED: Pack metadata
│       ├── blocks/                    # Optional: Block definitions
│       │   ├── copper_block.json
│       │   └── tin_block.json
│       ├── items/                     # Optional: Item definitions
│       │   └── copper_item.json
│       ├── entities/                  # Optional: Entity definitions
│       │   └── custom_mob.json
│       ├── recipes/                   # Optional: Crafting recipes
│       │   └── copper_ingot.json
│       ├── loot_tables/               # Optional: Loot tables
│       ├── functions/                 # Optional: Command functions
│       ├── scripts/                   # Optional: JavaScript API scripts
│       │   └── main.js
│       ├── spawn_rules/               # Optional: Mob spawn rules
│       └── texts/                     # Optional: Language/localization
│           └── en_US.lang
│
└── resource_packs/                    # RESOURCE PACKS (plural)
    └── my_mod_rp/                     # Individual resource pack folder
        ├── manifest.json              # REQUIRED: Pack metadata
        ├── textures/                  # Optional: Texture files
        │   ├── blocks/
        │   │   ├── copper_block.png
        │   │   └── tin_block.png
        │   └── items/
        │       └── copper_ingot.png
        ├── models/                    # Optional: 3D entity models
        │   └── block/
        │       └── copper_block.geo.json
        ├── sounds/                    # Optional: Sound effects
        │   └── mob/
        │       └── custom_mob.fsb
        ├── animations/                # Optional: Animation controllers
        ├── particles/                 # Optional: Particle effects
        └── ui/                        # Optional: UI elements
```

## manifest.json Format

### Behavior Pack manifest.json

```json
{
  "format_version": 2,
  "header": {
    "name": "My Mod Behavior Pack",
    "description": "Adds copper and tin blocks to the game",
    "uuid": "12345678-1234-1234-1234-123456789abc",
    "version": [1, 0, 0],
    "min_engine_version": [1, 19, 0]
  },
  "modules": [
    {
      "type": "data",
      "uuid": "87654321-4321-4321-4321-cba987654321",
      "version": [1, 0, 0]
    }
  ]
}
```

### Resource Pack manifest.json

```json
{
  "format_version": 2,
  "header": {
    "name": "My Mod Resource Pack",
    "description": "Textures and models for copper and tin blocks",
    "uuid": "abcdef01-2345-6789-abcd-ef0123456789",
    "version": [1, 0, 0],
    "min_engine_version": [1, 19, 0]
  },
  "modules": [
    {
      "type": "resources",
      "uuid": "fedcba98-7654-3210-fedc-ba9876543210",
      "version": [1, 0, 0]
    }
  ]
}
```

### Manifest with Dependencies

If your resource pack depends on the behavior pack:

```json
{
  "format_version": 2,
  "header": {
    "name": "My Mod Resource Pack",
    "description": "Textures for copper mod",
    "uuid": "abcdef01-2345-6789-abcd-ef0123456789",
    "version": [1, 0, 0],
    "min_engine_version": [1, 19, 0]
  },
  "modules": [
    {
      "type": "resources",
      "uuid": "fedcba98-7654-3210-fedc-ba9876543210",
      "version": [1, 0, 0]
    }
  ],
  "dependencies": [
    {
      "uuid": "12345678-1234-1234-1234-123456789abc",
      "version": [1, 0, 0]
    }
  ]
}
```

## Block Definition Example

`behavior_packs/my_mod_bp/blocks/copper_block.json`:

```json
{
  "format_version": "1.20.0",
  "minecraft:block": {
    "description": {
      "identifier": "mymod:copper_block",
      "register_to_creative_menu": true,
      "category": "construction"
    },
    "components": {
      "minecraft:display_name": {
        "value": "Copper Block"
      },
      "minecraft:destroy_time": 2.0,
      "minecraft:explosion_resistance": 3.0,
      "minecraft:friction": 0.6,
      "minecraft:map_color": "#E8A040",
      "minecraft:creative_category": {
        "category": "construction",
        "group": "itemGroup.name.stone"
      },
      "minecraft:geometry": "geometry.copper_block",
      "minecraft:material": "metal",
      "minecraft:light_emission": 0,
      "minecraft:light_dampening": 15
    }
  }
}
```

## Item Definition Example

`behavior_packs/my_mod_bp/items/copper_ingot.json`:

```json
{
  "format_version": "1.20.0",
  "minecraft:item": {
    "description": {
      "identifier": "mymod:copper_ingot",
      "category": "items"
    },
    "components": {
      "minecraft:display_name": {
        "value": "Copper Ingot"
      },
      "minecraft:max_stack_size": 64,
      "minecraft:icon": {
        "texture": "copper_ingot"
      },
      "minecraft:creative_category": {
        "parent": "itemGroup.name.items"
      }
    }
  }
}
```

## Validation Checklist

Before distributing your `.mcaddon`, ensure:

- [ ] Uses `behavior_packs/` and `resource_packs/` (plural)
- [ ] Each pack has a valid `manifest.json`
- [ ] All UUIDs are valid and unique
- [ ] All JSON files are valid
- [ ] Block definitions follow Bedrock schema
- [ ] Item definitions follow Bedrock schema
- [ ] Textures are in `textures/` subdirectory
- [ ] No temporary files (.DS_Store, Thumbs.db, etc.)
- [ ] File size under 500MB
- [ ] Tested in actual Bedrock Edition

## Common Errors

### Error: "Failed to import pack"

**Cause:** Using singular directory names (`behavior_pack/`, `resource_pack/`)

**Fix:** Rename to plural (`behavior_packs/`, `resource_packs/`)

### Error: "Invalid manifest"

**Cause:** Missing required fields or invalid UUID format

**Fix:** Ensure manifest has all required fields and valid UUIDv4 format

### Error: "Duplicate UUID"

**Cause:** Same UUID used in multiple places

**Fix:** Generate unique UUIDs for each pack and module

## Testing Your Package

1. **Manual Testing:**
   - Copy `.mcaddon` to Bedrock Preview
   - Attempt to import
   - Check for error messages

2. **Automated Testing:**
   ```python
   from agents.packaging_validator import PackagingValidator

   validator = PackagingValidator()
   result = validator.validate_mcaddon(Path("my_addon.mcaddon"))

   print(validator.generate_report(result))
   ```

3. **Schema Validation:**
   - All JSON files validated against schemas
   - See `/ai-engine/schemas/` for schema definitions

## File Size Guidelines

- **Textures:** Use PNG, optimize file size
- **Models:** Use efficient geometry
- **Sounds:** Compress audio files
- **Total Package:** Under 500MB recommended

## Compatibility

### Minimum Engine Versions

- **1.19.0:** Most features supported
- **1.20.0:** Latest features and components

### Platform Support

- **Bedrock Edition:** Full support
- **Education Edition:** Limited (no JavaScript)
- **Preview:** All experimental features

## Additional Resources

- [Bedrock Documentation](https://learn.microsoft.com/en-us/minecraft/creator/)
- [JSON Schemas](/ai-engine/schemas/)
- [Validation Tool](/ai-engine/agents/packaging_validator.py)
