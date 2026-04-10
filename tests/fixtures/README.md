# Test Fixtures for ModPorter AI

This directory contains comprehensive test fixtures used for automated testing of the ModPorter AI conversion pipeline, covering entities, GUIs, complex logic, and more.

**✅ Issue #213 Implementation**: Curated Test Sample Repository with diverse mod types for comprehensive conversion validation.

## 🏗️ Test Repository Structure

```
tests/fixtures/
├── README.md                           # This documentation
├── enhanced_test_generator.py          # Comprehensive test mod generator
├── test_mod_validator.py              # Validation framework
├── test_validation_report.md          # Latest validation results
├── simple_copper_block.py             # Legacy simple mod generator
├── test_jar_generator.py              # Legacy test utilities
└── test_mods/                         # Organized test mod collection
    ├── existing/                      # Original test mods
    │   ├── simple_copper_block.jar    # Basic block test mod
    │   └── simple_test_mod.jar        # Simple test fixture
    ├── entities/                      # Entity test mods (NEW!)
    │   ├── passive_entity_mod.jar     # Passive mob with basic AI
    │   ├── hostile_entity_mod.jar     # Hostile mob with combat AI
    │   └── custom_ai_entity_mod.jar   # Entity with custom behavior
    ├── gui_mods/                      # GUI interface test mods (NEW!)
    │   ├── inventory_gui_mod.jar      # Custom inventory interfaces
    │   ├── config_gui_mod.jar         # Configuration screens
    │   └── hud_gui_mod.jar           # HUD overlays and displays
    ├── complex_logic/                 # Complex logic test mods (NEW!)
    │   ├── machinery_logic_mod.jar    # Tick-based machines
    │   ├── multiblock_logic_mod.jar   # Multi-block structures
    │   └── automation_logic_mod.jar   # Item transport networks
    └── expected_outputs/              # Conversion expectations (NEW!)
        ├── entity_conversion_expectations.json
        ├── gui_conversion_expectations.json
        └── complex_logic_conversion_expectations.json
```

## 📋 License Compliance

All test mods must comply with ModPorter AI's license requirements. See [`docs/legal/conversion-audit.md`](../../docs/legal/conversion-audit.md) for the approved test mod shortlist and license compliance guidelines.

**Key Points:**
- Only mods with permissive licenses (MIT, BSD, Apache 2.0, GPL 3.0+, CC0) are approved
- Mods with CC BY-NC-ND or similar non-derivative licenses are prohibited
- License verification is required before adding new test mods

## 🎯 Test Mod Categories

### 📦 Existing Mods (Baseline)
**Purpose**: Proven working test cases for basic conversion validation

#### `simple_copper_block.jar` ✅
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
      "minecraft:destroy_time": 3.0,
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

### 🧬 Entity Test Mods (NEW!)
**Purpose**: Test entity AI behavior conversion and complex mob mechanics

#### `passive_entity_mod.jar` 🐑
- **Features**: Passive mob with basic AI goals (wander, look at player)
- **Tests**: Entity spawning, basic AI conversion, model/texture handling
- **Conversion Challenges**: AI goal mapping to Bedrock behavior components
- **Expected Output**: Bedrock entity with creature spawn category and basic behaviors

#### `hostile_entity_mod.jar` ⚔️
- **Features**: Hostile mob with combat AI (attack players, revenge targeting)
- **Tests**: Combat mechanics, player targeting, aggressive behavior
- **Conversion Challenges**: Attack patterns, damage calculation, targeting logic
- **Expected Output**: Bedrock monster entity with combat behaviors

#### `custom_ai_entity_mod.jar` 🤖
- **Features**: Entity with custom AI goal class (timer-based jumping)
- **Tests**: Complex AI logic, custom behavior patterns, state management
- **Conversion Challenges**: Custom AI goal classes to Bedrock components
- **Expected Output**: Bedrock entity with timer-based custom behavior

### 🖥️ GUI Interface Test Mods (NEW!)
**Purpose**: Test GUI conversion limitations and smart assumption generation

#### `inventory_gui_mod.jar` 📦
- **Features**: Custom inventory screen with block entity storage
- **Tests**: Custom GUI layouts, inventory slot handling, screen interactions
- **Conversion Challenges**: GUI widgets not supported in Bedrock
- **Expected Smart Assumptions**: Convert to block-based container system

#### `config_gui_mod.jar` ⚙️
- **Features**: Configuration screen with text fields and buttons
- **Tests**: Client-side configuration, input widgets, settings persistence
- **Conversion Challenges**: No configuration screen equivalent in Bedrock
- **Expected Smart Assumptions**: Convert to command-based configuration

#### `hud_gui_mod.jar` 📊
- **Features**: HUD overlay displaying player health information
- **Tests**: Custom HUD rendering, overlay positioning, real-time updates
- **Conversion Challenges**: Custom HUD overlays not supported in Bedrock
- **Expected Smart Assumptions**: Convert to actionbar/title text displays

### 🔧 Complex Logic Test Mods (NEW!)
**Purpose**: Test complex system conversion and limitation handling

#### `machinery_logic_mod.jar` ⚡
- **Features**: Tick-based machine with power states and processing logic
- **Tests**: Block entity state management, tick-based processing, power systems
- **Conversion Challenges**: Complex state machines, continuous processing
- **Expected Smart Assumptions**: Convert to event-driven state changes

#### `multiblock_logic_mod.jar` 🏗️
- **Features**: Multi-block structure controller with spatial validation
- **Tests**: Structure formation detection, coordinated block behavior
- **Conversion Challenges**: No native multiblock support in Bedrock
- **Expected Smart Assumptions**: Individual block validation system

#### `automation_logic_mod.jar` 🚛
- **Features**: Item transport network with automatic routing
- **Tests**: Inter-block communication, item movement, network topology
- **Conversion Challenges**: No automatic item transport in Bedrock
- **Expected Smart Assumptions**: Manual item management system

## 🔍 Validation Framework

### Test Mod Validation (`test_mod_validator.py`)
Comprehensive validation system that checks:
- ✅ JAR file structure integrity
- ✅ Fabric metadata completeness
- ✅ Required assets and classes
- ✅ Type-specific feature validation
- ✅ Conversion challenge prediction

**Latest Validation Results**: 83.3% success rate (10/12 valid mods)

### Expected Output Definitions
JSON files defining expected conversion outcomes:
- `entity_conversion_expectations.json` - Expected Bedrock entity components
- `gui_conversion_expectations.json` - GUI limitation handling strategies  
- `complex_logic_conversion_expectations.json` - Logic system approximations

## 🚀 Usage Instructions

### Generate All Test Mods
```bash
cd tests/fixtures/
python enhanced_test_generator.py
```

### Validate Test Mods
```bash
cd tests/fixtures/
python test_mod_validator.py
```

### Regenerate Specific Categories
```python
from enhanced_test_generator import EnhancedTestModGenerator

generator = EnhancedTestModGenerator("tests/fixtures/test_mods")

# Generate specific types
generator.create_entity_mod("passive")
generator.create_gui_mod("inventory") 
generator.create_complex_logic_mod("machinery")
```

## 📊 Test Coverage Matrix

| Mod Category | Java Feature | Bedrock Support | Conversion Strategy | Smart Assumptions |
|--------------|---------------|-----------------|-------------------|-------------------|
| **Entities** | Custom AI | Partial | Behavior mapping | ✅ Component conversion |
| **GUI** | Custom screens | None | Alternative UI | ✅ Block/command alternatives |
| **Logic** | Complex state | Limited | Event-driven | ✅ Simplified interactions |
| **Baseline** | Basic blocks | Full | Direct mapping | ✅ Property preservation |

## 🎯 Integration with ModPorter AI Pipeline

### JavaAnalyzerAgent Testing
- Entity mods test AI behavior recognition
- GUI mods test interface pattern detection  
- Logic mods test complex system analysis
- All mods validate registry name extraction

### Conversion Pipeline Testing
- Validates template system expansion needs
- Tests smart assumption generation quality
- Measures conversion accuracy across complexity levels
- Provides regression testing foundation

### Performance Benchmarking
- 9 diverse test mods enable performance measurement
- Progressive complexity allows bottleneck identification
- Validation framework tracks conversion success rates
- Expected outputs enable accuracy measurement

## 🔄 Maintenance and Updates

### Adding New Test Categories
1. Extend `EnhancedTestModGenerator` with new category methods
2. Add validation rules in `TestModValidator`  
3. Create expected output definitions
4. Update this README documentation

### Updating Existing Mods
1. Modify generator methods for specific categories
2. Regenerate affected test mods
3. Re-run validation to ensure integrity
4. Update expected outputs if needed

## 🌍 World Gen / Biome Reference Mods

External mods used for testing world generation and biome conversion capabilities:

| Mod Name | License | Coverage | Notes |
|----------|---------|----------|-------|
| Terralith | MIT | World gen, biomes, terrain | Primary reference for world gen testing |
| The Aether | GPL 3.0 | Dimensions, world gen | Alternative dimension mod |
| Blue Skies | MIT | Multi-biome, dimension | Alternative biome mod |

**Note:** Biomes O' Plenty was removed due to CC BY-NC-ND license (see [`docs/legal/conversion-audit.md`](../../docs/legal/conversion-audit.md))

## Legacy Files

### `SimpleStoneBlock.java`
Source code for a basic stone block, used as reference for understanding Java mod structure.

### `create_test_texture.py`
Utility script for generating test texture files.

### `test_jar_generator.py`
Legacy test JAR creation utilities (superseded by `enhanced_test_generator.py`).