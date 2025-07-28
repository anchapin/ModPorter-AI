# Enhanced Template System Documentation

## Overview

The ModPorter-AI enhanced template system provides dynamic template selection, inheritance, and extensible template categories for converting Java mods to Bedrock add-ons. This system replaces the simple hard-coded block template with a comprehensive solution supporting items, entities, recipes, and more.

## Architecture

### Core Components

1. **TemplateEngine** - Main orchestrator that selects and renders templates
2. **TemplateSelector** - Smart selection logic based on Java feature analysis
3. **BaseTemplate/JinjaTemplate** - Template implementations with validation
4. **TemplateType/TemplateCategory** - Type system for organizing templates

### Template Categories

- **blocks/** - Block definitions (basic, container, interactive, machine, multi-block)
- **items/** - Item definitions (basic, tools, weapons, armor, consumables)
- **entities/** - Entity definitions (passive/hostile mobs, NPCs, projectiles)  
- **recipes/** - Recipe definitions (crafting, smelting, brewing, custom)
- **biomes/** - Biome definitions (for future expansion)
- **loot_tables/** - Loot table definitions (for future expansion)

## Directory Structure

```
ai-engine/templates/bedrock/
├── template_engine.py          # Core template engine
├── blocks/
│   ├── basic_block.json        # Basic block template
│   ├── basic_block.meta.json   # Template metadata
│   ├── basic_block_rp.json     # Resource pack variant
│   ├── container_block.json    # Container/inventory blocks
│   └── interactive_block.json  # Interactive/redstone blocks
├── items/
│   ├── basic_item.json         # Basic item template
│   ├── tool.json              # Tool template with durability
│   ├── tool.meta.json         # Tool metadata
│   └── consumable.json        # Food/potion templates
├── entities/
│   ├── passive_mob.json       # Peaceful creatures
│   └── hostile_mob.json       # Aggressive creatures
├── recipes/
│   ├── crafting_recipe.json   # Crafting table recipes
│   └── smelting_recipe.json   # Furnace recipes
└── README.md                  # This documentation
```

## Using the Template System

### Basic Usage

```python
from templates.template_engine import TemplateEngine

# Initialize engine
engine = TemplateEngine()

# Render a template
context = {
    "namespace": "mymod",
    "block_name": "custom_block",
    "texture_name": "custom_block"
}

# Engine automatically selects appropriate template based on properties
result = engine.render_template(
    feature_type="block",
    properties={},  # Analysis from Java code
    context=context
)
```

### Smart Template Selection

The system automatically selects templates based on Java code analysis:

```python
# Container block automatically selected
properties = {"inventory": True, "container": "chest"}
template_type = engine.selector.select_template("block", properties)
# Returns: TemplateType.CONTAINER_BLOCK

# Tool automatically selected  
properties = {"tool": True, "pickaxe": True}
template_type = engine.selector.select_template("item", properties)
# Returns: TemplateType.TOOL
```

### Resource Pack vs Behavior Pack

```python
# Behavior pack (default)
bp_result = engine.render_template("block", {}, context)

# Resource pack
rp_result = engine.render_template("block", {}, context, pack_type="rp")
```

## Adding New Templates

### Step 1: Define Template Type

Add new template types to the `TemplateType` enum in `template_engine.py`:

```python
class TemplateType(Enum):
    # Add your new type
    MAGIC_BLOCK = "magic_block"
    SPELL_ITEM = "spell_item"
```

### Step 2: Create Template File

Create the Jinja2 template file in the appropriate category directory:

Create `templates/bedrock/blocks/magic_block.json`:

```json
{
  "format_version": "1.20.10",
  "minecraft:block": {
    "description": {
      "identifier": "{{ namespace }}:{{ block_name }}",
      "menu_category": {
        "category": "{{ menu_category | default('equipment') }}"
      }
    },
    "components": {
      "minecraft:destroy_time": {{ destroy_time | default(2.0) }},
      "minecraft:light_emission": {{ light_level | default(10) }},
      "minecraft:unit_cube": {},
      "minecraft:material_instances": {
        "*": {
          "texture": "{{ texture_name }}",
          "render_method": "{{ render_method | default('blend') }}"
        }
      }{% if magical_effects %},
      "minecraft:custom_components": [
        "{{ namespace }}:magic_handler"
      ]{% endif %}
    }
  }
}
```

### Step 3: Create Metadata File (Optional)

Define template requirements and validation:

Create the metadata file `templates/bedrock/blocks/magic_block.meta.json`:

```json
{
  "template_type": "magic_block",
  "category": "blocks",
  "description": "Magical block with light emission and special effects",
  "required_parameters": [
    "namespace",
    "block_name", 
    "texture_name"
  ],
  "optional_parameters": [
    "menu_category",
    "destroy_time",
    "light_level",
    "render_method",
    "magical_effects"
  ],
  "defaults": {
    "menu_category": "equipment",
    "destroy_time": 2.0,
    "light_level": 10,
    "render_method": "blend"
  },
  "validation_rules": [
    "light_level must be integer 0-15",
    "destroy_time must be positive number"
  ]
}
```

### Step 4: Update Selection Logic

Add selection logic to `TemplateSelector._select_block_template()`:

```python
def _select_block_template(self, properties: Dict[str, Any]) -> TemplateType:
    # Check for magical functionality
    if any(keyword in str(properties).lower() for keyword in ['magic', 'spell', 'enchanted']):
        return TemplateType.MAGIC_BLOCK
    
    # ... existing logic
    return TemplateType.BASIC_BLOCK
```

### Step 5: Update Category Mapping

Add category mapping in `_get_template_category()`:

```python
def _get_template_category(self, template_type: TemplateType) -> TemplateCategory:
    category_mapping = {
        # ... existing mappings
        TemplateType.MAGIC_BLOCK: TemplateCategory.BLOCKS,
    }
    return category_mapping.get(template_type, TemplateCategory.BLOCKS)
```

## Template Variables and Features

### Common Variables

All templates support these base variables:

- `namespace` - Mod namespace (e.g., "mymod")
- `item_name`/`block_name`/`entity_name` - Feature identifier
- `texture_name` - Texture file reference
- `display_name` - Human-readable name

### Block-Specific Variables

- `menu_category` - Creative menu category
- `destroy_time` - Breaking time
- `explosion_resistance` - Blast resistance
- `map_color` - Map display color
- `light_emission` - Light level (0-15)
- `flammable` - Fire properties
- `redstone_*` - Redstone behavior

### Item-Specific Variables

- `max_stack_size` - Stack size limit
- `max_durability` - Tool durability
- `enchantment_*` - Enchanting properties
- `attack_damage` - Weapon damage
- `mining_speeds` - Tool efficiency

### Entity-Specific Variables

- `max_health` - Entity health
- `movement_speed` - Movement rate
- `attack_damage` - Damage dealt
- `detection_range` - AI detection distance
- `collision_*` - Hitbox dimensions

## Validation and Testing

### Template Validation

Templates are automatically validated:

```python
# Context validation against metadata
is_valid = template.validate_context(context)

# Output validation against Bedrock schemas
is_valid = engine.validate_template_output(result, template_type)
```

### Running Tests

```bash
# Run template engine tests
cd ai-engine
python -m pytest tests/test_template_engine.py -v

# Test specific template
python -c "
from templates.template_engine import TemplateEngine
engine = TemplateEngine()
result = engine.render_template('block', {'magic': True}, context)
print(result)
"
```

## Best Practices

### Template Design

1. **Use meaningful defaults** - Provide sensible fallbacks for optional parameters
2. **Include conditional sections** - Use Jinja2 `{% if %}` for optional features
3. **Validate input** - Define required parameters in metadata
4. **Follow Bedrock schemas** - Ensure output matches Bedrock format requirements

### Selection Logic

1. **Keywords over structure** - Check for descriptive keywords in properties
2. **Specific before general** - More specific templates should be checked first  
3. **Graceful fallbacks** - Always have a default template for each category
4. **Test thoroughly** - Verify selection logic with various property combinations

### Performance

1. **Cache templates** - Templates are automatically cached after first load
2. **Minimize file I/O** - Templates loaded once at initialization
3. **Validate early** - Check context before expensive rendering
4. **Use relative paths** - Keep templates in organized subdirectories

## Integration with BedrockBuilderAgent

The enhanced template system integrates seamlessly with the existing BedrockBuilderAgent:

```python
# In BedrockBuilderAgent.__init__()
self.template_engine = TemplateEngine(templates_dir)

# Usage in conversion methods
block_content = self.template_engine.render_template(
    feature_type="block",
    properties=java_analysis_result,  # From Java AST parsing
    context=template_context
)
```

## Future Enhancements

### Planned Features

1. **Template Inheritance** - Base templates with derived variations
2. **Multi-file Templates** - Templates that generate multiple files
3. **Dynamic Properties** - Runtime property calculation
4. **Schema Validation** - Full Bedrock schema compliance checking
5. **Visual Template Editor** - GUI for template creation

### Extension Points

1. **Custom Selectors** - Pluggable selection logic
2. **Template Processors** - Post-processing template output
3. **External Templates** - Loading templates from external sources
4. **Template Composition** - Combining multiple templates

## Troubleshooting

### Common Issues

**Template Not Found**
```
FileNotFoundError: Template not found for type: my_template
```
- Ensure template file exists in correct category directory
- Check template type is defined in TemplateType enum
- Verify filename matches template type value

**Invalid Template Output**
```
ValidationError: Template output invalid
```
- Check template produces valid JSON
- Verify Bedrock schema compliance
- Test template with minimal context

**Context Validation Failed**
```
ValueError: Invalid context for template
```
- Check required parameters are provided
- Verify parameter types match expectations
- Review template metadata requirements

### Debug Mode

Enable debug logging to troubleshoot template issues:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

engine = TemplateEngine()
# Detailed logging will show template selection and rendering
```

## Contributing

When contributing new templates:

1. Follow existing naming conventions
2. Include comprehensive metadata
3. Add appropriate selection logic
4. Write tests for new functionality
5. Update this documentation

For questions or issues, refer to the ModPorter-AI project documentation or create an issue on GitHub.