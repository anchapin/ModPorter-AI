"""
Enhanced Template Engine for ModPorter-AI
Supports dynamic template selection, inheritance, and extensible template categories.
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from enum import Enum
from abc import ABC, abstractmethod
import logging
from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger(__name__)


class TemplateCategory(Enum):
    """Supported template categories for Bedrock conversion."""
    BLOCKS = "blocks"
    ITEMS = "items"
    ENTITIES = "entities"
    RECIPES = "recipes"
    BIOMES = "biomes"
    LOOT_TABLES = "loot_tables"


class TemplateType(Enum):
    """Template types within categories."""
    # Block types
    BASIC_BLOCK = "basic_block"
    CONTAINER_BLOCK = "container_block"
    INTERACTIVE_BLOCK = "interactive_block"
    MULTI_BLOCK = "multi_block"
    MACHINE_BLOCK = "machine_block"
    
    # Item types
    BASIC_ITEM = "basic_item"
    TOOL = "tool"
    WEAPON = "weapon"
    ARMOR = "armor"
    CONSUMABLE = "consumable"
    DECORATIVE = "decorative"
    
    # Entity types
    PASSIVE_MOB = "passive_mob"
    HOSTILE_MOB = "hostile_mob"
    NPC = "npc"
    PROJECTILE = "projectile"
    
    # Recipe types
    CRAFTING_RECIPE = "crafting_recipe"
    SMELTING_RECIPE = "smelting_recipe"
    BREWING_RECIPE = "brewing_recipe"
    CUSTOM_RECIPE = "custom_recipe"


class TemplateSelector:
    """Smart template selection based on Java feature analysis."""
    
    def __init__(self):
        self.selection_rules = self._load_selection_rules()
    
    def select_template(self, feature_type: str, properties: Dict[str, Any]) -> TemplateType:
        """
        Select appropriate template based on Java feature analysis.
        
        Args:
            feature_type: Type of feature from Java analysis (block, item, entity, etc.)
            properties: Properties extracted from Java code
            
        Returns:
            TemplateType: The most appropriate template type
        """
        # Convert feature type to category
        category = self._map_feature_to_category(feature_type)
        
        # Apply selection logic based on properties
        if category == TemplateCategory.BLOCKS:
            return self._select_block_template(properties)
        elif category == TemplateCategory.ITEMS:
            return self._select_item_template(properties)
        elif category == TemplateCategory.ENTITIES:
            return self._select_entity_template(properties)
        elif category == TemplateCategory.RECIPES:
            return self._select_recipe_template(properties)
        else:
            # Default fallback
            return TemplateType.BASIC_BLOCK
    
    def _map_feature_to_category(self, feature_type: str) -> TemplateCategory:
        """Map Java feature type to template category."""
        feature_mapping = {
            'block': TemplateCategory.BLOCKS,
            'item': TemplateCategory.ITEMS,
            'entity': TemplateCategory.ENTITIES,
            'recipe': TemplateCategory.RECIPES,
            'biome': TemplateCategory.BIOMES,
            'loot_table': TemplateCategory.LOOT_TABLES,
        }
        return feature_mapping.get(feature_type.lower(), TemplateCategory.BLOCKS)
    
    def _select_block_template(self, properties: Dict[str, Any]) -> TemplateType:
        """Select block template based on properties."""
        # Check for container functionality
        if any(keyword in str(properties).lower() for keyword in ['inventory', 'container', 'chest', 'storage']):
            return TemplateType.CONTAINER_BLOCK
            
        # Check for interactive functionality
        if any(keyword in str(properties).lower() for keyword in ['interact', 'click', 'gui', 'interface']):
            return TemplateType.INTERACTIVE_BLOCK
            
        # Check for machine functionality
        if any(keyword in str(properties).lower() for keyword in ['machine', 'process', 'energy', 'power']):
            return TemplateType.MACHINE_BLOCK
            
        # Check for multi-block structures
        if any(keyword in str(properties).lower() for keyword in ['multiblock', 'structure', 'formation']):
            return TemplateType.MULTI_BLOCK
            
        return TemplateType.BASIC_BLOCK
    
    def _select_item_template(self, properties: Dict[str, Any]) -> TemplateType:
        """Select item template based on properties."""
        # Check for tool functionality
        if any(keyword in str(properties).lower() for keyword in ['tool', 'pickaxe', 'axe', 'shovel', 'hoe']):
            return TemplateType.TOOL
            
        # Check for weapon functionality
        if any(keyword in str(properties).lower() for keyword in ['weapon', 'sword', 'bow', 'damage', 'attack']):
            return TemplateType.WEAPON
            
        # Check for armor functionality
        if any(keyword in str(properties).lower() for keyword in ['armor', 'helmet', 'chestplate', 'leggings', 'boots']):
            return TemplateType.ARMOR
            
        # Check for consumable functionality
        if any(keyword in str(properties).lower() for keyword in ['food', 'consumable', 'potion', 'drink', 'eat']):
            return TemplateType.CONSUMABLE
            
        return TemplateType.BASIC_ITEM
    
    def _select_entity_template(self, properties: Dict[str, Any]) -> TemplateType:
        """Select entity template based on properties."""
        # Check for hostile behavior
        if any(keyword in str(properties).lower() for keyword in ['hostile', 'aggressive', 'attack', 'damage']):
            return TemplateType.HOSTILE_MOB
            
        # Check for NPC functionality
        if any(keyword in str(properties).lower() for keyword in ['npc', 'villager', 'trader', 'merchant']):
            return TemplateType.NPC
            
        # Check for projectile
        if any(keyword in str(properties).lower() for keyword in ['projectile', 'arrow', 'bullet', 'thrown']):
            return TemplateType.PROJECTILE
            
        return TemplateType.PASSIVE_MOB
    
    def _select_recipe_template(self, properties: Dict[str, Any]) -> TemplateType:
        """Select recipe template based on properties."""
        # Check for smelting recipes
        if any(keyword in str(properties).lower() for keyword in ['smelt', 'furnace', 'cook']):
            return TemplateType.SMELTING_RECIPE
            
        # Check for brewing recipes
        if any(keyword in str(properties).lower() for keyword in ['brew', 'potion', 'brewing']):
            return TemplateType.BREWING_RECIPE
            
        # Check for custom recipes
        if any(keyword in str(properties).lower() for keyword in ['custom', 'special', 'unique']):
            return TemplateType.CUSTOM_RECIPE
            
        return TemplateType.CRAFTING_RECIPE
    
    def _load_selection_rules(self) -> Dict[str, Any]:
        """Load template selection rules from configuration."""
        # For now, return empty dict - can be extended with external config
        return {}


class BaseTemplate(ABC):
    """Base class for all templates."""
    
    def __init__(self, template_path: Path, template_type: TemplateType):
        self.template_path = template_path
        self.template_type = template_type
        self.metadata = self._load_metadata()
        
    @abstractmethod
    def render(self, context: Dict[str, Any]) -> str:
        """Render template with given context."""
        pass
    
    @abstractmethod
    def validate_context(self, context: Dict[str, Any]) -> bool:
        """Validate that context contains required parameters."""
        pass
    
    def _load_metadata(self) -> Dict[str, Any]:
        """Load template metadata if available."""
        metadata_path = self.template_path.with_suffix('.meta.json')
        if metadata_path.exists():
            with open(metadata_path, 'r') as f:
                return json.load(f)
        return {}


class JinjaTemplate(BaseTemplate):
    """Jinja2-based template implementation."""
    
    def __init__(self, template_path: Path, template_type: TemplateType, jinja_env: Environment, templates_dir: Path = None):
        super().__init__(template_path, template_type)
        self.jinja_env = jinja_env
        
        # Calculate relative path from templates directory for Jinja2
        if templates_dir and template_path.is_relative_to(templates_dir):
            relative_path = template_path.relative_to(templates_dir)
            # Convert to forward slashes for Jinja2 compatibility
            template_name = str(relative_path).replace('\\', '/')
        else:
            template_name = template_path.name
            
        self.template = jinja_env.get_template(template_name)
        
    def render(self, context: Dict[str, Any]) -> str:
        """Render Jinja2 template with context."""
        if not self.validate_context(context):
            raise ValueError(f"Invalid context for template {self.template_path}")
            
        # Apply template-specific context transformations
        enhanced_context = self._enhance_context(context)
        
        return self.template.render(**enhanced_context)
    
    def validate_context(self, context: Dict[str, Any]) -> bool:
        """Validate context against template requirements."""
        required_params = self.metadata.get('required_parameters', [])
        return all(param in context for param in required_params)
    
    def _enhance_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Add template-specific enhancements to context."""
        enhanced = context.copy()
        
        # Add defaults from metadata
        defaults = self.metadata.get('defaults', {})
        for key, value in defaults.items():
            if key not in enhanced:
                enhanced[key] = value
                
        # Add template-specific utilities
        enhanced['template_type'] = self.template_type.value
        enhanced['template_category'] = self._get_category().value
        
        return enhanced
    
    def _get_category(self) -> TemplateCategory:
        """Get category for this template type."""
        category_mapping = {
            TemplateType.BASIC_BLOCK: TemplateCategory.BLOCKS,
            TemplateType.CONTAINER_BLOCK: TemplateCategory.BLOCKS,
            TemplateType.INTERACTIVE_BLOCK: TemplateCategory.BLOCKS,
            TemplateType.MULTI_BLOCK: TemplateCategory.BLOCKS,
            TemplateType.MACHINE_BLOCK: TemplateCategory.BLOCKS,
            TemplateType.BASIC_ITEM: TemplateCategory.ITEMS,
            TemplateType.TOOL: TemplateCategory.ITEMS,
            TemplateType.WEAPON: TemplateCategory.ITEMS,
            TemplateType.ARMOR: TemplateCategory.ITEMS,
            TemplateType.CONSUMABLE: TemplateCategory.ITEMS,
            TemplateType.DECORATIVE: TemplateCategory.ITEMS,
            TemplateType.PASSIVE_MOB: TemplateCategory.ENTITIES,
            TemplateType.HOSTILE_MOB: TemplateCategory.ENTITIES,
            TemplateType.NPC: TemplateCategory.ENTITIES,
            TemplateType.PROJECTILE: TemplateCategory.ENTITIES,
            TemplateType.CRAFTING_RECIPE: TemplateCategory.RECIPES,
            TemplateType.SMELTING_RECIPE: TemplateCategory.RECIPES,
            TemplateType.BREWING_RECIPE: TemplateCategory.RECIPES,
            TemplateType.CUSTOM_RECIPE: TemplateCategory.RECIPES,
        }
        return category_mapping.get(self.template_type, TemplateCategory.BLOCKS)


class TemplateEngine:
    """
    Enhanced template engine with dynamic selection, inheritance, and validation.
    Replaces the simple Jinja2 template loading in BedrockBuilderAgent.
    """
    
    def __init__(self, templates_dir: Optional[Path] = None):
        if templates_dir is None:
            templates_dir = Path(__file__).parent / 'bedrock'
        
        self.templates_dir = templates_dir
        # Set up Jinja2 to search in all subdirectories
        search_paths = [str(templates_dir)]
        for category in TemplateCategory:
            category_path = templates_dir / category.value
            if category_path.exists():
                search_paths.append(str(category_path))
        
        self.jinja_env = Environment(loader=FileSystemLoader(search_paths))
        self.selector = TemplateSelector()
        self.template_cache: Dict[TemplateType, BaseTemplate] = {}
        
        # Load all available templates
        self._discover_templates()
        
    def render_template(self, feature_type: str, properties: Dict[str, Any], 
                       context: Dict[str, Any], pack_type: str = "bp") -> str:
        """
        Main entry point for template rendering.
        
        Args:
            feature_type: Type of feature from Java analysis
            properties: Properties extracted from Java code
            context: Rendering context with parameters
            pack_type: "bp" for behavior pack, "rp" for resource pack
            
        Returns:
            str: Rendered template content
        """
        # Select appropriate template
        template_type = self.selector.select_template(feature_type, properties)
        
        # Get template instance (handle RP/BP distinction)
        if pack_type == "rp" and feature_type == "block":
            # Try to get resource pack specific template
            rp_template_name = f"{template_type.value}_rp"
            try:
                template = self._get_template_by_name(rp_template_name)
            except FileNotFoundError:
                # Fallback to behavior pack template
                template = self.get_template(template_type)
        else:
            template = self.get_template(template_type)
        
        # Render with context
        return template.render(context)
    
    def get_template(self, template_type: TemplateType) -> BaseTemplate:
        """Get template instance by type."""
        if template_type not in self.template_cache:
            template_path = self._find_template_path(template_type)
            if template_path is None:
                raise FileNotFoundError(f"Template not found for type: {template_type}")
            
            self.template_cache[template_type] = JinjaTemplate(
                template_path, template_type, self.jinja_env, self.templates_dir
            )
            
        return self.template_cache[template_type]
    
    def register_template(self, template_type: TemplateType, template_path: Path):
        """Register a new template type."""
        self.template_cache[template_type] = JinjaTemplate(
            template_path, template_type, self.jinja_env, self.templates_dir
        )
    
    def _get_template_by_name(self, template_name: str) -> BaseTemplate:
        """Get template by filename (for RP/BP variants)."""
        template_path = self._find_template_path_by_name(template_name)
        if template_path is None:
            raise FileNotFoundError(f"Template not found: {template_name}")
        
        # Create a temporary template type for this variant
        return JinjaTemplate(template_path, TemplateType.BASIC_BLOCK, self.jinja_env, self.templates_dir)
        
    def list_available_templates(self) -> List[TemplateType]:
        """List all available template types."""
        return list(self.template_cache.keys())
    
    def validate_template_output(self, output: str, template_type: TemplateType) -> bool:
        """Validate template output against Bedrock schemas."""
        try:
            # Parse as JSON
            data = json.loads(output)
            
            # Basic validation - check for required Bedrock structure
            if template_type.value.endswith('_block'):
                return 'minecraft:block' in data
            elif template_type.value.endswith('_item'):
                return 'minecraft:item' in data
            elif template_type.value.endswith('_entity') or template_type.value.endswith('_mob'):
                return 'minecraft:entity' in data
            elif template_type.value.endswith('_recipe'):
                return 'minecraft:recipe' in data or 'type' in data
                
            return True
            
        except json.JSONDecodeError:
            logger.error(f"Template output is not valid JSON: {template_type}")
            return False
    
    def _discover_templates(self):
        """Discover and load all available templates."""
        for category in TemplateCategory:
            category_dir = self.templates_dir / category.value
            if category_dir.exists():
                for template_file in category_dir.glob('*.json'):
                    # Skip .meta.json and variant files (basic_block_bp.json, basic_block_rp.json)
                    if template_file.name.endswith('.meta.json'):
                        continue
                    if '_bp.json' in template_file.name or '_rp.json' in template_file.name:
                        continue
                    template_type = self._map_filename_to_type(template_file.name)
                    if template_type:
                        self.template_cache[template_type] = JinjaTemplate(
                            template_file, template_type, self.jinja_env, self.templates_dir
                        )
    
    def _find_template_path(self, template_type: TemplateType) -> Optional[Path]:
        """Find template file path for given type."""
        # Map template type to category
        category = self._get_template_category(template_type)
        
        # Look for template file
        category_dir = self.templates_dir / category.value
        if category_dir.exists():
            template_file = category_dir / f"{template_type.value}.json"
            if template_file.exists():
                return template_file
                
        # Fallback: look in root templates directory
        template_file = self.templates_dir / f"{template_type.value}.json"
        if template_file.exists():
            return template_file
            
        return None
    
    def _find_template_path_by_name(self, template_name: str) -> Optional[Path]:
        """Find template file path by filename."""
        # Look in all category directories
        for category in TemplateCategory:
            category_dir = self.templates_dir / category.value
            if category_dir.exists():
                template_file = category_dir / f"{template_name}.json"
                if template_file.exists():
                    return template_file
                    
        # Fallback: look in root templates directory
        template_file = self.templates_dir / f"{template_name}.json"
        if template_file.exists():
            return template_file
            
        return None
    
    def _get_template_category(self, template_type: TemplateType) -> TemplateCategory:
        """Get category for template type."""
        if template_type.value.endswith('_block'):
            return TemplateCategory.BLOCKS
        elif template_type.value.endswith('_item') or template_type.value in ['tool', 'weapon', 'armor', 'consumable', 'decorative']:
            return TemplateCategory.ITEMS
        elif template_type.value.endswith('_mob') or template_type.value in ['npc', 'projectile']:
            return TemplateCategory.ENTITIES
        elif template_type.value.endswith('_recipe'):
            return TemplateCategory.RECIPES
        else:
            return TemplateCategory.BLOCKS
    
    def _map_filename_to_type(self, filename: str) -> Optional[TemplateType]:
        """Map template filename to TemplateType."""
        name = filename.replace('.json', '')
        try:
            return TemplateType(name)
        except ValueError:
            logger.warning(f"Unknown template file: {filename}")
            return None