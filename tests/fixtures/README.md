# Test Fixtures for ModPorter AI

This directory contains test fixtures used for automated testing of the ModPorter AI conversion pipeline.

## Simple Copper Block JAR (`simple_copper_block.jar`)

A minimal Fabric mod containing a single polished copper block, designed for testing the Java-to-Bedrock conversion pipeline.

### JAR Structure

```
simple_copper_block.jar
├── fabric.mod.json                                           # Fabric mod metadata
├── assets/simple_copper/textures/block/polished_copper.png   # Block texture
├── com/example/simple_copper/PolishedCopperBlock.class       # Compiled Java class
└── META-INF/MANIFEST.MF                                      # JAR manifest
```

### Mod Metadata (`fabric.mod.json`)

```json
{
  "schemaVersion": 1,
  "id": "simple_copper",
  "version": "1.0.0",
  "name": "Simple Copper Block",
  "description": "A simple mod that adds a polished copper block",
  "authors": ["ModPorter AI"],
  "license": "MIT"
}
```

### Expected Conversion Output

When processed through the ModPorter AI pipeline, this JAR should produce:

#### 1. JavaAnalyzerAgent Analysis Result
```json
{
  "success": true,
  "registry_name": "simple_copper:polished_copper",
  "texture_path": "assets/simple_copper/textures/block/polished_copper.png",
  "errors": []
}
```

#### 2. Bedrock Block Definition
```json
{
  "format_version": "1.16.100",
  "minecraft:block": {
    "description": {
      "identifier": "simple_copper:polished_copper"
    },
    "components": {
      "minecraft:destroy_time": 1.5,
      "minecraft:explosion_resistance": 6.0,
      "minecraft:material_instances": {
        "*": {
          "texture": "polished_copper"
        }
      }
    }
  }
}
```

#### 3. Resource Pack Structure
```
behavior_pack/
├── manifest.json
├── pack_icon.png
└── blocks/
    └── polished_copper.json

resource_pack/
├── manifest.json
├── pack_icon.png
├── textures/
│   └── blocks/
│       └── polished_copper.png
└── terrain_texture.json
```

#### 4. Final .mcaddon File
The conversion pipeline should produce a `ModPorter_simple_copper.mcaddon` file that can be imported into Minecraft Bedrock Edition.

### Usage in Tests

This fixture is used by:

- **JavaAnalyzerAgent tests** (`tests/agents/test_java_analyzer.py`) - Tests registry name and texture path extraction
- **Integration tests** (`tests/test_integration.py`) - End-to-end conversion testing
- **Packager tests** (`tests/test_packager.py`) - .mcaddon file generation testing

### Test Validation Points

When using this fixture in tests, validate:

1. ✅ **Registry name extraction**: Should identify `simple_copper:polished_copper`
2. ✅ **Texture path extraction**: Should find `assets/simple_copper/textures/block/polished_copper.png`
3. ✅ **Mod ID extraction**: Should extract `simple_copper` from `fabric.mod.json`
4. ✅ **Successful analysis**: Analysis should complete without errors
5. ✅ **Bedrock conversion**: Should generate valid Bedrock block definition
6. ✅ **Package creation**: Should create importable .mcaddon file

### Regenerating the Fixture

If the fixture needs to be recreated, run:

```bash
cd tests/fixtures/
python simple_copper_block.py
```

This will regenerate the `simple_copper_block.jar` file with the current structure.

## Other Test Files

### `SimpleStoneBlock.java`
Source code for a basic stone block, used as reference for understanding Java mod structure.

### `create_test_texture.py`
Utility script for generating test texture files.

### `expected_output/`
Contains reference files showing the expected conversion output format.