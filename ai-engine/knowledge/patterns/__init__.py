"""
Pattern library for Java→Bedrock conversions.

Provides conversion patterns, pattern registries, and mapping logic.
"""

from .advancement_patterns import (
    ADVANCEMENT_PATTERNS,
    AdvancementPattern,
    AdvancementPatternCategory,
    AdvancementPatternLibrary,
    get_advancement_pattern,
    search_advancement_patterns,
)
from .base import ConversionPattern, PatternLibrary
from .bedrock_patterns import BedrockPatternRegistry
from .command_patterns import (
    COMMAND_PATTERNS,
    CommandCategory,
    CommandPattern,
    CommandPatternLibrary,
    get_command_pattern,
    search_command_patterns,
)
from .dimension_patterns import (
    WORLDGEN_PATTERNS,
    WorldGenCategory,
    WorldGenPattern,
    WorldGenPatternLibrary,
    get_patterns_by_dimension,
    get_worldgen_pattern,
    get_worldgen_stats,
    search_worldgen_patterns,
)
from .dimension_patterns import (
    get_patterns_by_category as get_dimension_patterns_by_category,
)
from .entity_behavior_patterns import (
    ENTITY_BEHAVIOR_PATTERNS,
    BehaviorPattern,
    EntityBehaviorType,
    get_behavior_pattern,
    get_behaviors_by_type,
    get_entity_ai_templates,
)
from .gui_patterns import (
    GUI_PATTERNS,
    GUICategory,
    GUIPattern,
    GUIPatternLibrary,
    get_gui_pattern,
    search_gui_patterns,
)
from .java_patterns import JavaPatternRegistry
from .mappings import PatternMapping, PatternMappingRegistry
from .particle_patterns import (
    PARTICLE_PATTERNS,
    ParticleCategory,
    ParticlePattern,
    ParticlePatternLibrary,
    get_particle_pattern,
    search_particle_patterns,
)
from .potion_patterns import (
    POTION_PATTERNS,
    PotionPattern,
    PotionPatternCategory,
    PotionPatternLibrary,
    get_potion_pattern,
    search_potion_patterns,
)
from .rendering_patterns import (
    RENDERING_PATTERNS,
    RenderingPattern,
    RenderingPatternCategory,
    RenderingPatternLibrary,
    get_rendering_pattern,
    search_rendering_patterns,
)
from .sound_patterns import (
    SOUND_PATTERNS,
    SoundCategory,
    SoundPattern,
    SoundPatternLibrary,
    get_patterns_by_category,
    get_sound_pattern,
    get_sound_stats,
    search_sound_patterns,
)
from .villager_patterns import (
    VILLAGER_PATTERNS,
    VillagerPattern,
    VillagerPatternCategory,
    VillagerPatternLibrary,
    get_villager_pattern,
    search_villager_patterns,
)
from .weapon_tool_patterns import (
    WEAPON_TOOL_PATTERNS,
    WeaponToolCategory,
    WeaponToolPattern,
    WeaponToolPatternLibrary,
    get_weapon_tool_pattern,
    search_weapon_tool_patterns,
)

__all__ = [
    "ConversionPattern",
    "PatternLibrary",
    "JavaPatternRegistry",
    "BedrockPatternRegistry",
    "PatternMapping",
    "PatternMappingRegistry",
    # Sound patterns
    "SoundPattern",
    "SoundPatternLibrary",
    "SoundCategory",
    "SOUND_PATTERNS",
    "get_sound_pattern",
    "search_sound_patterns",
    "get_patterns_by_category",
    "get_sound_stats",
    # Dimension patterns
    "WorldGenPattern",
    "WorldGenPatternLibrary",
    "WorldGenCategory",
    "WORLDGEN_PATTERNS",
    "get_worldgen_pattern",
    "search_worldgen_patterns",
    "get_dimension_patterns_by_category",
    "get_patterns_by_dimension",
    "get_worldgen_stats",
    # GUI patterns
    "GUIPattern",
    "GUIPatternLibrary",
    "GUICategory",
    "GUI_PATTERNS",
    "get_gui_pattern",
    "search_gui_patterns",
    # Particle patterns
    "ParticlePattern",
    "ParticlePatternLibrary",
    "ParticleCategory",
    "PARTICLE_PATTERNS",
    "get_particle_pattern",
    "search_particle_patterns",
    # Advancement patterns
    "AdvancementPattern",
    "AdvancementPatternLibrary",
    "AdvancementPatternCategory",
    "ADVANCEMENT_PATTERNS",
    "get_advancement_pattern",
    "search_advancement_patterns",
    # Potion patterns
    "PotionPattern",
    "PotionPatternLibrary",
    "PotionPatternCategory",
    "POTION_PATTERNS",
    "get_potion_pattern",
    "search_potion_patterns",
    # Villager patterns
    "VillagerPattern",
    "VillagerPatternLibrary",
    "VillagerPatternCategory",
    "VILLAGER_PATTERNS",
    "get_villager_pattern",
    "search_villager_patterns",
    # Rendering patterns
    "RenderingPattern",
    "RenderingPatternLibrary",
    "RenderingPatternCategory",
    "RENDERING_PATTERNS",
    "get_rendering_pattern",
    "search_rendering_patterns",
    # Weapon/Tool patterns
    "WeaponToolPattern",
    "WeaponToolPatternLibrary",
    "WeaponToolCategory",
    "WEAPON_TOOL_PATTERNS",
    "get_weapon_tool_pattern",
    "search_weapon_tool_patterns",
    # Command patterns
    "CommandPattern",
    "CommandPatternLibrary",
    "CommandCategory",
    "COMMAND_PATTERNS",
    "get_command_pattern",
    "search_command_patterns",
    # Entity behavior patterns
    "BehaviorPattern",
    "EntityBehaviorType",
    "ENTITY_BEHAVIOR_PATTERNS",
    "get_behavior_pattern",
    "get_behaviors_by_type",
    "get_entity_ai_templates",
]
