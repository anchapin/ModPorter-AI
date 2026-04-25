"""
Dimension Converter for converting Java dimension, biome, and world generation to Bedrock format.

Converts Java dimension types, biomes, climate settings, and world presets
to Bedrock's dimension files, biome definitions, and world behavior.
"""

import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class DimensionType(Enum):
    """Bedrock dimension types."""

    OVERWORLD = "overworld"
    NETHER = "nether"
    THE_END = "the_end"
    CUSTOM = "custom"


class BiomeCategory(Enum):
    """Bedrock biome categories."""

    PLAINS = "plains"
    FOREST = "forest"
    DESERT = "desert"
    TAIGA = "taiga"
    JUNGLE = "jungle"
    SAVANNA = "savanna"
    ICY = "icy"
    MOUNTAIN = "mountain"
    SWAMP = "swamp"
    MUSHROOM = "mushroom"
    AQUATIC = "aquatic"
    NETHER = "nether"
    THE_END = "the_end"
    CUSTOM = "custom"


@dataclass
class DimensionProperties:
    """Properties for a dimension definition."""

    ambient_light: float = 0.0
    has_sky_light: bool = True
    has_ceiling: bool = False
    ultrawarm: bool = False
    natural: bool = True
    respawn_anchor: bool = False
    piglin_safe: bool = False
    bed_safe: bool = True
    spawn_invisible: bool = False
    spawn_animal: bool = True
    spawn_monster: bool = True


@dataclass
class BiomeDefinition:
    """Represents a biome definition."""

    identifier: str
    name: str
    category: BiomeCategory
    temperature: float = 0.5
    rainfall: float = 0.5
    grass_color: Optional[int] = None
    foliage_color: Optional[int] = None
    water_color: int = 0x3F76E4
    fog_color: int = 0xC0D8FF
    sky_color: int = 0x87CEEB


class DimensionConverter:
    """
    Converter for Java dimension and biome definitions to Bedrock format.

    Handles dimension type conversion, biome mapping, and world preset generation.
    """

    def __init__(self):
        # Base dimension file template
        self.dimension_template = {"format_version": "1.19.0"}

        # Java to Bedrock biome category mapping
        self.biome_category_map = {
            "plains": BiomeCategory.PLAINS,
            "forest": BiomeCategory.FOREST,
            "desert": BiomeCategory.DESERT,
            "taiga": BiomeCategory.TAIGA,
            "jungle": BiomeCategory.JUNGLE,
            "savanna": BiomeCategory.SAVANNA,
            "snowy": BiomeCategory.ICY,
            "icy": BiomeCategory.ICY,
            "mountain": BiomeCategory.MOUNTAIN,
            "swamp": BiomeCategory.SWAMP,
            "mushroom": BiomeCategory.MUSHROOM,
            "ocean": BiomeCategory.AQUATIC,
            "river": BiomeCategory.AQUATIC,
            "nether": BiomeCategory.NETHER,
            "the_end": BiomeCategory.THE_END,
        }

        # Java dimension type to Bedrock mapping
        self.dimension_type_map = {
            "overworld": DimensionType.OVERWORLD,
            "minecraft:overworld": DimensionType.OVERWORLD,
            "nether": DimensionType.NETHER,
            "minecraft:nether": DimensionType.NETHER,
            "the_end": DimensionType.THE_END,
            "minecraft:the_end": DimensionType.THE_END,
        }

        # Grass color mapping by temperature
        self.grass_color_map = {
            "cold": 0x8BBD6B,
            "medium": 0x91BD59,
            "warm": 0x7BC96F,
            "hot": 0x59C135,
        }

        # Default biome definitions
        self.default_biomes = self._create_default_biomes()

    def _create_default_biomes(self) -> Dict[str, BiomeDefinition]:
        """Create default biome definitions."""
        return {
            "plains": BiomeDefinition(
                identifier="plains",
                name="Plains",
                category=BiomeCategory.PLAINS,
                temperature=0.8,
                rainfall=0.4,
                grass_color=0x91BD59,
                foliage_color=0x77AB2F,
            ),
            "forest": BiomeDefinition(
                identifier="forest",
                name="Forest",
                category=BiomeCategory.FOREST,
                temperature=0.7,
                rainfall=0.8,
                grass_color=0x91BD59,
                foliage_color=0x59C135,
            ),
            "desert": BiomeDefinition(
                identifier="desert",
                name="Desert",
                category=BiomeCategory.DESERT,
                temperature=1.0,
                rainfall=0.0,
                grass_color=0xA0D485,
                foliage_color=0xA4D485,
            ),
            "taiga": BiomeDefinition(
                identifier="taiga",
                name="Taiga",
                category=BiomeCategory.TAIGA,
                temperature=0.25,
                rainfall=0.8,
                grass_color=0x6D9E5A,
                foliage_color=0x4A8C3F,
            ),
            "jungle": BiomeDefinition(
                identifier="jungle",
                name="Jungle",
                category=BiomeCategory.JUNGLE,
                temperature=0.95,
                rainfall=0.9,
                grass_color=0x91BD59,
                foliage_color=0x59C135,
            ),
            "savanna": BiomeDefinition(
                identifier="savanna",
                name="Savanna",
                category=BiomeCategory.SAVANNA,
                temperature=1.2,
                rainfall=0.0,
                grass_color=0xBFDA7F,
                foliage_color=0xA4D468,
            ),
            "snowy_plains": BiomeDefinition(
                identifier="snowy_plains",
                name="Snowy Plains",
                category=BiomeCategory.ICY,
                temperature=0.0,
                rainfall=0.5,
                grass_color=0xDEFBDE,
                foliage_color=0x8BCBDB,
            ),
            "mountains": BiomeDefinition(
                identifier="mountains",
                name="Mountains",
                category=BiomeCategory.MOUNTAIN,
                temperature=0.2,
                rainfall=0.3,
                grass_color=0x8BBD6B,
                foliage_color=0x6D9E5A,
            ),
        }

    def convert_dimension(self, java_dim: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert a Java dimension definition to Bedrock format.

        Args:
            java_dim: Java dimension dictionary

        Returns:
            Bedrock dimension definition
        """
        dim_type = java_dim.get("type", "minecraft:overworld")
        dimension = self.dimension_type_map.get(dim_type, DimensionType.CUSTOM)

        properties = DimensionProperties(
            ambient_light=java_dim.get("ambient_light", 0.0),
            has_sky_light=java_dim.get("has_sky_light", True),
            has_ceiling=java_dim.get("has_ceiling", False),
            ultrawarm=java_dim.get("ultrawarm", False),
            natural=java_dim.get("natural", True),
            respawn_anchor=java_dim.get("respawn_anchor", False),
            piglin_safe=java_dim.get("piglin_safe", dimension == DimensionType.NETHER),
            bed_safe=java_dim.get("bed_safe", dimension != DimensionType.NETHER),
        )

        return self._build_dimension_definition(dimension, properties)

    def convert_biome(self, java_biome: Dict[str, Any]) -> BiomeDefinition:
        """
        Convert a Java biome definition to Bedrock format.

        Args:
            java_biome: Java biome dictionary

        Returns:
            BiomeDefinition object
        """
        identifier = java_biome.get("id", java_biome.get("biome_id", "custom"))

        # Map category
        java_category = java_biome.get("category", "plains").lower()
        category = self.biome_category_map.get(java_category, BiomeCategory.CUSTOM)

        # Get climate settings
        temperature = java_biome.get("temperature", 0.5)
        rainfall = java_biome.get("downfall", java_biome.get("rainfall", 0.5))

        return BiomeDefinition(
            identifier=identifier,
            name=java_biome.get("name", identifier.title()),
            category=category,
            temperature=temperature,
            rainfall=rainfall,
            grass_color=self.convert_grass_color(temperature, rainfall),
            foliage_color=self.convert_foliage_color(temperature, rainfall),
            water_color=java_biome.get("water_color", 0x3F76E4),
            fog_color=java_biome.get("fog_color", 0xC0D8FF),
            sky_color=java_biome.get("sky_color", 0x87CEEB),
        )

    def convert_world_preset(self, java_preset: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert a Java world preset to Bedrock world_behavior.json.

        Args:
            java_preset: Java world preset dictionary

        Returns:
            Bedrock world behavior definition
        """
        preset_name = java_preset.get("name", "custom")

        # Determine dimension based on preset
        dimension = DimensionType.OVERWORLD
        if "nether" in preset_name.lower():
            dimension = DimensionType.NETHER
        elif "end" in preset_name.lower():
            dimension = DimensionType.THE_END

        return {
            "format_version": "1.19.0",
            "minecraft:world_generation_settings": {
                "dimension": dimension.value,
                "seed": java_preset.get("seed", 0),
                "generate_features": java_preset.get("generate_structures", True),
                "bonus_chest": java_preset.get("bonus_chest", False),
            },
            "minecraft:world_gen_seed": {
                "seed": java_preset.get("seed", 0),
                "generate_nether": dimension == DimensionType.NETHER or preset_name == "all",
                "generate_end": dimension == DimensionType.THE_END or preset_name == "all",
            },
        }

    def generate_dimension_file(
        self, dimension_type: DimensionType, properties: DimensionProperties
    ) -> Dict[str, Any]:
        """
        Generate a dimension.json file.

        Args:
            dimension_type: The dimension type
            properties: Dimension properties

        Returns:
            Bedrock dimension file content
        """
        return self._build_dimension_definition(dimension_type, properties)

    def create_overworld_dimension(self) -> Dict[str, Any]:
        """Create standard overworld dimension."""
        properties = DimensionProperties(
            ambient_light=0.0,
            has_sky_light=True,
            has_ceiling=False,
            ultrawarm=False,
            natural=True,
            respawn_anchor=False,
            piglin_safe=False,
            bed_safe=True,
            spawn_invisible=False,
            spawn_animal=True,
            spawn_monster=True,
        )
        return self._build_dimension_definition(DimensionType.OVERWORLD, properties)

    def create_nether_dimension(self) -> Dict[str, Any]:
        """Create nether dimension with bedrock ceiling."""
        properties = DimensionProperties(
            ambient_light=0.1,
            has_sky_light=False,
            has_ceiling=True,
            ultrawarm=True,
            natural=False,
            respawn_anchor=True,
            piglin_safe=True,
            bed_safe=False,
            spawn_invisible=True,
            spawn_animal=False,
            spawn_monster=True,
        )
        return self._build_dimension_definition(DimensionType.NETHER, properties)

    def create_end_dimension(self) -> Dict[str, Any]:
        """Create the end dimension with islands."""
        properties = DimensionProperties(
            ambient_light=0.0,
            has_sky_light=False,
            has_ceiling=False,
            ultrawarm=False,
            natural=False,
            respawn_anchor=False,
            piglin_safe=True,
            bed_safe=False,
            spawn_invisible=False,
            spawn_animal=False,
            spawn_monster=False,
        )
        return self._build_dimension_definition(DimensionType.THE_END, properties)

    def create_custom_dimension(self, props: Dict[str, Any]) -> Dict[str, Any]:
        """Create custom dimension from properties."""
        properties = DimensionProperties(
            ambient_light=props.get("ambient_light", 0.0),
            has_sky_light=props.get("has_sky_light", True),
            has_ceiling=props.get("has_ceiling", False),
            ultrawarm=props.get("ultrawarm", False),
            natural=props.get("natural", True),
            respawn_anchor=props.get("respawn_anchor", False),
            piglin_safe=props.get("piglin_safe", False),
            bed_safe=props.get("bed_safe", True),
            spawn_invisible=props.get("spawn_invisible", False),
            spawn_animal=props.get("spawn_animal", True),
            spawn_monster=props.get("spawn_monster", True),
        )
        return self._build_dimension_definition(DimensionType.CUSTOM, properties)

    def _build_dimension_definition(
        self, dimension_type: DimensionType, properties: DimensionProperties
    ) -> Dict[str, Any]:
        """Build the full dimension definition."""
        return {
            "format_version": "1.19.0",
            "minecraft:dimension": {
                "description": {
                    "identifier": f"minecraft:{dimension_type.value}",
                    "prefix": "minecraft:",
                },
                "components": {
                    "minecraft:ambient": properties.ambient_light,
                    "minecraft:has_sky_light": properties.has_sky_light,
                    "minecraft:has_ceiling": properties.has_ceiling,
                    "minecraft:ultrawarm": properties.ultrawarm,
                    "minecraft:natural": properties.natural,
                    "minecraft:respawn_anchor": properties.respawn_anchor,
                    "minecraft:piglin_safe": properties.piglin_safe,
                    "minecraft:bed_works": properties.bed_safe,
                    "minecraft:spawn_invisible": properties.spawn_invisible,
                    "minecraft:spawn_animal": properties.spawn_animal,
                    "minecraft:spawn_monster": properties.spawn_monster,
                },
            },
        }

    def convert_climate_settings(self, java_climate: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert Java climate settings to biome parameters.

        Args:
            java_climate: Java climate settings

        Returns:
            Biome parameters dictionary
        """
        temperature = java_climate.get("temperature", 0.5)
        rainfall = java_climate.get("rainfall", java_climate.get("downfall", 0.5))

        return {
            "temperature": temperature,
            "rainfall": rainfall,
            "grass_color": self.convert_grass_color(temperature, rainfall),
            "foliage_color": self.convert_foliage_color(temperature, rainfall),
        }

    def convert_grass_color(self, temperature: float, rainfall: float) -> int:
        """
        Convert climate to grass color.

        Args:
            temperature: Temperature value (0-1)
            rainfall: Rainfall value (0-1)

        Returns:
            RGB color integer
        """
        # Temperature ranges
        if temperature < 0.2:
            return self.grass_color_map["cold"]
        elif temperature < 0.7:
            return self.grass_color_map["medium"]
        elif temperature < 0.9:
            return self.grass_color_map["warm"]
        else:
            return self.grass_color_map["hot"]

    def convert_foliage_color(self, temperature: float, rainfall: float) -> int:
        """Convert climate to foliage color."""
        # Foliage is generally slightly darker than grass
        grass = self.convert_grass_color(temperature, rainfall)
        # Darken by ~15%
        r = (grass >> 16) & 0xFF
        g = (grass >> 8) & 0xFF
        b = grass & 0xFF
        r = int(r * 0.85)
        g = int(g * 0.85)
        b = int(b * 0.85)
        return (r << 16) | (g << 8) | b

    def map_biome_category(self, java_category: str) -> BiomeCategory:
        """
        Map Java biome category to Bedrock category.

        Args:
            java_category: Java biome category string

        Returns:
            BiomeCategory enum value
        """
        return self.biome_category_map.get(java_category.lower(), BiomeCategory.CUSTOM)


class StructureConverter:
    """
    Converter for Java structures, ruins, and mineshafts to Bedrock format.

    Handles structure definitions, feature conversion, and world generation templates.
    """

    def __init__(self):
        # Structure type mappings
        self.structure_mappings = {
            "village": "village",
            "desert_village": "village_desert",
            "taiga_village": "village_taiga",
            "plains_village": "village_plains",
            "savanna_village": "village_savanna",
            "snowy_village": "village_snowy",
            "pillager_outpost": "pillager_outpost",
            "desert_pyramid": "desert_pyramid",
            "jungle_temple": "jungle_temple",
            "witch_hut": "witch_hut",
            "ocean_monument": "monument",
            "woodland_mansion": "mansion",
            "stronghold": "stronghold",
            "mineshaft": "mineshaft",
            "mineshaft_mesa": "mineshaft_mesa",
            "ocean_ruin": "ocean_ruin",
            "ruined_portal": "ruined_portal",
            "fortress": "fortress",
            "ruined_portal_nether": "ruined_portal_nether",
            "shipwreck": "shipwreck",
            "shipwreck_beached": "shipwreck_beached",
            "buried_treasure": "buried_treasure",
            "bastion_remnant": "bastion_remnant",
            "nether_fortress": "fortress",
            "end_city": "end_city",
        }

        # Feature type mappings
        self.feature_mappings = {
            "tree": "tree",
            "big_tree": "tree",
            "dark_oak_tree": "tree",
            "acacia_tree": "tree",
            "jungle_tree": "tree",
            "oak_tree": "tree",
            "spruce_tree": "tree",
            "birch_tree": "tree",
            "flower": "flower",
            "tall_flower": "tall_flower",
            "grass": "grass",
            "tall_grass": "tall_grass",
            "fern": "fern",
            "large_fern": "large_fern",
            "sugar_cane": "sugar_cane",
            "cactus": "cactus",
            "vine": "vine",
            "water_lake": "water_lake",
            "lava_lake": "lava_lake",
            "ore_coal": "ore",
            "ore_iron": "ore",
            "ore_gold": "ore",
            "ore_diamond": "ore",
            "ore_emerald": "ore",
            "ore_copper": "ore",
            "ore_lapis": "ore",
            "ore_redstone": "ore",
            "gravel": "gravel",
            "dirt": "dirt",
            "sand": "sand",
            "clay": "clay",
            "cave_carver": "cave",
            "cave_legacy": "cave",
            "ravine": "ravine",
        }

    def convert_structure(self, java_structure: str) -> Dict[str, Any]:
        """
        Convert a Java structure type to Bedrock structure definition.

        Args:
            java_structure: Java structure type string

        Returns:
            Bedrock structure definition
        """
        structure_type = java_structure.lower()
        bedrock_id = self.structure_mappings.get(structure_type, f"custom_{structure_type}")

        return {
            "format_version": "1.19.0",
            "minecraft:structure": {
                "description": {
                    "identifier": f"minecraft:{bedrock_id}",
                },
                "structure": {" anatomic: structure_id": bedrock_id},
                "pool": "minecraft:pool",
            },
        }

    def convert_ruins(self, java_ruins: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert Java ruins to Bedrock ruin templates.

        Args:
            java_ruins: Java ruins dictionary

        Returns:
            Bedrock ruin template definition
        """
        ruins_type = java_ruins.get("type", "ruined_portal").lower()

        return {
            "format_version": "1.19.0",
            "minecraft:structure_template": {
                "description": {
                    "identifier": f"minecraft:{ruins_type}",
                },
                "structure": {" anatomic: template": ruins_type},
                "projection": "rigid",
            },
        }

    def convert_mineshaft(self, java_mineshaft: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert Java mineshaft to Bedrock mineshaft generation.

        Args:
            java_mineshaft: Java mineshaft dictionary

        Returns:
            Bedrock mineshaft definition
        """
        mineshaft_type = java_mineshaft.get("type", "normal").lower()

        return {
            "format_version": "1.19.0",
            "minecraft:structure": {
                "description": {
                    "identifier": f"minecraft:mineshaft_{mineshaft_type}",
                },
                "structure": {" anatomic: structure_id": f"mineshaft_{mineshaft_type}"},
                "pool": "minecraft:mineshaft",
                "type": mineshaft_type,
            },
        }

    def convert_world_feature(self, java_feature: str) -> Dict[str, Any]:
        """
        Convert a Java world feature to Bedrock feature.

        Args:
            java_feature: Java feature type string

        Returns:
            Bedrock feature definition
        """
        feature_type = java_feature.lower()
        bedrock_id = self.feature_mappings.get(feature_type, f"custom_{feature_type}")

        return {
            "format_version": "1.19.0",
            "minecraft:feature": {
                "description": {
                    "identifier": f"minecraft:{bedrock_id}",
                },
                "type": bedrock_id,
            },
        }

    def convert_tree_feature(self, java_tree: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert a Java tree feature to Bedrock tree definition.

        Args:
            java_tree: Java tree definition dictionary

        Returns:
            Bedrock tree feature definition
        """
        tree_type = java_tree.get("type", "oak").lower()

        return {
            "format_version": "1.19.0",
            "minecraft:tree": {
                "description": {
                    "identifier": f"minecraft:tree_{tree_type}",
                },
                "trunk_provider": {
                    "Name": f"minecraft:{tree_type}_log",
                },
                "leaves_provider": {
                    "Name": f"minecraft:{tree_type}_leaves",
                },
                "height": java_tree.get("height", 5),
                "foliage_height": java_tree.get("foliage_height", 2),
                "trunk_width": java_tree.get("trunk_width", 1),
            },
        }

    def convert_ore_vein(self, java_ore: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert a Java ore vein to Bedrock ore generation.

        Args:
            java_ore: Java ore definition dictionary

        Returns:
            Bedrock ore feature definition
        """
        ore_type = java_ore.get("type", "coal").lower()

        return {
            "format_version": "1.19.0",
            "minecraft:ore": {
                "description": {
                    "identifier": f"minecraft:ore_{ore_type}",
                },
                "ore_provider": {
                    "Name": f"minecraft:{ore_type}_ore",
                },
                "count": java_ore.get("count", 16),
                "skew": java_ore.get("skew", 0),
                "spread": java_ore.get("spread", 16),
                "replace_rules": [
                    {
                        "replace": "minecraft:stone",
                        "with": [f"minecraft:{ore_type}_ore"],
                    }
                ],
            },
        }

    def convert_world_preset(self, java_preset: str) -> Dict[str, Any]:
        """
        Convert a world preset to Bedrock world_behavior.json.

        Args:
            java_preset: Java world preset string

        Returns:
            Bedrock world behavior settings
        """
        preset = java_preset.lower()

        # Determine which dimensions to generate
        generate_nether = "nether" in preset or "normal" in preset
        generate_end = "end" in preset or "normal" in preset

        return {
            "format_version": "1.19.0",
            "minecraft:world_generation_rules": {
                "nether": generate_nether,
                "the_end": generate_end,
            },
        }

    def generate_biome_layout(self, biomes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate biome layout configuration.

        Args:
            biomes: List of biome definitions

        Returns:
            Biome layout dictionary
        """
        return {
            "format_version": "1.19.0",
            "minecraft:biome": {
                "description": {
                    "identifier": "biome_layout",
                },
                "biomes": [
                    {
                        "name": biome.get("name", "custom"),
                        "id": biome.get("id", 0),
                    }
                    for biome in biomes
                ],
            },
        }

    def get_structure_id(self, java_structure: str) -> str:
        """Get Bedrock structure ID for Java structure."""
        return self.structure_mappings.get(
            java_structure.lower(), f"custom_{java_structure.lower()}"
        )

    def get_feature_id(self, java_feature: str) -> str:
        """Get Bedrock feature ID for Java feature."""
        return self.feature_mappings.get(java_feature.lower(), f"custom_{java_feature.lower()}")
