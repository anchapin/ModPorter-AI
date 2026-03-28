"""
Pattern library for Java→Bedrock conversions.

Provides conversion patterns, pattern registries, and mapping logic.
"""

from .base import ConversionPattern, PatternLibrary
from .java_patterns import JavaPatternRegistry
from .bedrock_patterns import BedrockPatternRegistry
from .mappings import PatternMapping, PatternMappingRegistry
from .sound_patterns import (
    SoundPattern,
    SoundPatternLibrary,
    SoundCategory,
    SOUND_PATTERNS,
    get_sound_pattern,
    search_sound_patterns,
    get_patterns_by_category,
    get_sound_stats,
)
from .dimension_patterns import (
    WorldGenPattern,
    WorldGenPatternLibrary,
    WorldGenCategory,
    WORLDGEN_PATTERNS,
    get_worldgen_pattern,
    search_worldgen_patterns,
    get_patterns_by_category as get_dimension_patterns_by_category,
    get_patterns_by_dimension,
    get_worldgen_stats,
)
from .gui_patterns import (
    GUIPattern,
    GUIPatternLibrary,
    GUICategory,
    GUI_PATTERNS,
    get_gui_pattern,
    search_gui_patterns,
)
from .particle_patterns import (
    ParticlePattern,
    ParticlePatternLibrary,
    ParticleCategory,
    PARTICLE_PATTERNS,
    get_particle_pattern,
    search_particle_patterns,
)
from .advancement_patterns import (
    AdvancementPattern,
    AdvancementPatternLibrary,
    AdvancementCategory,
    ADVANCEMENT_PATTERNS,
    get_advancement_pattern,
    search_advancement_patterns,
)
from .potion_patterns import (
    PotionPattern,
    PotionPatternLibrary,
    PotionCategory,
    POTION_PATTERNS,
    get_potion_pattern,
    search_potion_patterns,
)
from .villager_patterns import (
    VillagerPattern,
    VillagerPatternLibrary,
    VillagerCategory,
    VILLAGER_PATTERNS,
    get_villager_pattern,
    search_villager_patterns,
)
from .rendering_patterns import (
    RenderingPattern,
    RenderingPatternLibrary,
    RenderingCategory,
    RENDERING_PATTERNS,
    get_rendering_pattern,
    search_rendering_patterns,
)
from .weapon_tool_patterns import (
    WeaponToolPattern,
    WeaponToolPatternLibrary,
    WeaponToolCategory,
    WEAPON_TOOL_PATTERNS,
    get_weapon_tool_pattern,
    search_weapon_tool_patterns,
)
from .command_patterns import (
    CommandPattern,
    CommandPatternLibrary,
    CommandCategory,
    COMMAND_PATTERNS,
    get_command_pattern,
    search_command_patterns,
)
from .entity_behavior_patterns import (
    BehaviorPattern,
    EntityBehaviorType,
    ENTITY_BEHAVIOR_PATTERNS,
    get_behavior_pattern,
    get_behaviors_by_type,
    get_entity_ai_templates,
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
    "AdvancementCategory",
    "ADVANCEMENT_PATTERNS",
    "get_advancement_pattern",
    "search_advancement_patterns",
    # Potion patterns
    "PotionPattern",
    "PotionPatternLibrary",
    "PotionCategory",
    "POTION_PATTERNS",
    "get_potion_pattern",
    "search_potion_patterns",
    # Villager patterns
    "VillagerPattern",
    "VillagerPatternLibrary",
    "VillagerCategory",
    "VILLAGER_PATTERNS",
    "get_villager_pattern",
    "search_villager_patterns",
    # Rendering patterns
    "RenderingPattern",
    "RenderingPatternLibrary",
    "RenderingCategory",
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
