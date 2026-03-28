"""
Potion Converter for converting Java potion/effect systems to Bedrock format.

Converts Java MobEffect, MobEffectInstance, and PotionType to Bedrock's
minecraft:entity_effects component and potion items.
"""

import json
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class EffectType(Enum):
    """Bedrock effect types (status effects)."""

    SPEED = "speed"
    SLOWNESS = "slowness"
    HASTE = "haste"
    MINING_FATIGUE = "mining_fatigue"
    STRENGTH = "strength"
    JUMP_BOOST = "jump_boost"
    REGENERATION = "regeneration"
    DAMAGE_RESISTANCE = "damage_resistance"
    FIRE_RESISTANCE = "fire_resistance"
    WATER_BREATHING = "water_breathing"
    INVISIBILITY = "invisibility"
    BLINDNESS = "blindness"
    NIGHT_VISION = "night_vision"
    ABSORPTION = "absorption"
    SATURATION = "saturation"
    GLOWING = "glowing"
    LEVITATION = "levitation"
    LUCK = "luck"
    DOLPHINS_GRACE = "dolphins_grace"
    BAD_OMEN = "bad_omen"
    HERO_OF_THE_VILLAGE = "hero_of_the_village"
    CONDUIT_POWER = "conduit_power"
    SUNLIGHT = "sunlight"
    SLOW_FALLING = "slow_falling"


# Java to Bedrock effect mapping
JAVA_TO_BEDROCK_EFFECT = {
    "speed": "speed",
    "slowness": "slowness",
    "haste": "haste",
    "mining_fatigue": "mining_fatigue",
    "strength": "strength",
    "jump_boost": "jump_boost",
    "regeneration": "regeneration",
    "damage_resistance": "damage_resistance",
    "fire_resistance": "fire_resistance",
    "water_breathing": "water_breathing",
    "invisibility": "invisibility",
    "blindness": "blindness",
    "night_vision": "night_vision",
    "absorption": "absorption",
    "saturation": "saturation",
    "glowing": "glowing",
    "levitation": "levitation",
    "luck": "luck",
    "dolphins_grace": "dolphins_grace",
    "bad_omen": "bad_omen",
    "hero_of_the_village": "hero_of_the_village",
    "poison": "poison",
    "wither": "wither",
    "hunger": "hunger",
    "weakness": "weakness",
    "nausea": "nausea",
    "resistance": "damage_resistance",
    "conduit_power": "conduit_power",
    "slow_falling": "slow_falling",
}


# Potion type mapping
JAVA_POTION_TYPE_TO_BEDROCK = {
    "water": "potion",
    "awkward": "potion",
    "thick": "potion",
    "mundane": "potion",
    "swiftness": "potion",
    "swiftness_long": "potion",
    "slowness": "potion",
    "slowness_long": "potion",
    "strength": "potion",
    "strength_long": "potion",
    "healing": "potion",
    "healing_long": "potion",
    "harming": "potion",
    "harming_long": "potion",
    "regeneration": "potion",
    "regeneration_long": "potion",
    "fire_resistance": "potion",
    "fire_resistance_long": "potion",
    "poison": "potion",
    "poison_long": "potion",
    "night_vision": "potion",
    "night_vision_long": "potion",
    "invisibility": "potion",
    "invisibility_long": "potion",
    "leaping": "potion",
    "leaping_long": "potion",
    "water_breathing": "potion",
    "water_breathing_long": "potion",
    "luck": "potion",
    "slow_falling": "potion",
    "slow_falling_long": "potion",
    "splash": "splash_potion",
    "lingering": "lingering_potion",
}


@dataclass
class EffectDefinition:
    """Represents a converted effect definition."""

    effect_id: str
    duration: int  # in seconds
    amplifier: int  # 0-based (0 = level 1)
    ambient: bool = False
    particles: bool = True


@dataclass
class PotionItem:
    """Represents a Bedrock potion item."""

    name: str
    effects: List[EffectDefinition]
    potion_type: str = "potion"


class PotionConverter:
    """
    Converter for Java potions and effects to Bedrock format.

    Handles effect conversion, duration/amplifier mapping,
    and potion item generation for Bedrock.
    """

    def __init__(self):
        """Initialize the PotionConverter."""
        self.effect_map = JAVA_TO_BEDROCK_EFFECT.copy()
        self.potion_type_map = JAVA_POTION_TYPE_TO_BEDROCK.copy()

    def convert_effect(self, java_effect: Dict[str, Any]) -> EffectDefinition:
        """
        Convert a Java MobEffectInstance to Bedrock effect.

        Args:
            java_effect: Java effect dictionary containing effect type, duration, amplifier

        Returns:
            EffectDefinition object
        """
        effect_type = java_effect.get("id", "minecraft:speed")
        # Remove namespace if present
        if ":" in effect_type:
            effect_type = effect_type.split(":", 1)[1]

        # Map to Bedrock effect
        bedrock_effect = self.map_mob_effect(effect_type)

        # Convert duration from ticks to seconds
        duration_ticks = java_effect.get("duration", 180)  # Default 90 seconds
        duration_seconds = self.convert_duration(duration_ticks)

        # Convert amplifier
        amplifier = java_effect.get("amplifier", 0)
        converted_amplifier = self.convert_amplifier(amplifier)

        # Ambient particles
        ambient = java_effect.get("ambient", False)

        # Particles visibility
        particles = java_effect.get("show_particles", True)

        return EffectDefinition(
            effect_id=bedrock_effect,
            duration=duration_seconds,
            amplifier=converted_amplifier,
            ambient=ambient,
            particles=particles,
        )

    def map_mob_effect(self, java_effect: str) -> str:
        """
        Map Java MobEffect to Bedrock effect.

        Args:
            java_effect: Java effect name (e.g., "speed", "regeneration")

        Returns:
            Bedrock effect identifier
        """
        effect_lower = java_effect.lower()
        return self.effect_map.get(effect_lower, f"modporter:{java_effect}")

    def convert_duration(self, ticks: int) -> int:
        """
        Convert Java duration (in ticks) to Bedrock duration (in seconds).

        Args:
            ticks: Duration in ticks (20 ticks = 1 second)

        Returns:
            Duration in seconds
        """
        # Java uses 20 ticks per second
        return max(1, ticks // 20)

    def convert_amplifier(self, level: int) -> int:
        """
        Convert Java amplifier level to Bedrock amplifier.

        Args:
            level: Java amplifier (0 = Level I, 1 = Level II, etc.)

        Returns:
            Bedrock amplifier (0 = Level I, 1 = Level II, etc.)
        """
        return max(0, min(level, 255))  # Clamp to byte range

    def convert_potion(self, java_potion: Dict[str, Any]) -> PotionItem:
        """
        Convert a Java PotionType to Bedrock potion item.

        Args:
            java_potion: Java potion dictionary

        Returns:
            PotionItem object
        """
        potion_type = java_potion.get("type", "minecraft:potion")
        # Remove namespace
        if ":" in potion_type:
            potion_type = potion_type.split(":", 1)[1]

        # Convert potion type
        bedrock_potion_type = self.convert_potion_type(potion_type)

        # Convert effects
        effects = []
        if "effects" in java_potion:
            for effect in java_potion["effects"]:
                effects.append(self.convert_effect(effect))

        return PotionItem(
            name=bedrock_potion_type,
            effects=effects,
            potion_type=bedrock_potion_type,
        )

    def convert_potion_type(self, java_type: str) -> str:
        """
        Convert Java potion type to Bedrock item.

        Args:
            java_type: Java potion type

        Returns:
            Bedrock item identifier
        """
        type_lower = java_type.lower()
        return self.potion_type_map.get(type_lower, "potion")

    def create_potion_item(self, effects: List[EffectDefinition]) -> Dict[str, Any]:
        """
        Create a Bedrock potion item JSON.

        Args:
            effects: List of EffectDefinition objects

        Returns:
            Bedrock potion item JSON
        """
        potion_json = {
            "format_version": "1.17.0",
            "minecraft:item": {
                "description": {
                    "identifier": "minecraft:potion",
                },
                "components": {
                    "minecraft:potion": {
                        "effects": {},
                    }
                },
            },
        }

        # Add effects
        for effect in effects:
            potion_json["minecraft:item"]["components"]["minecraft:potion"]["effects"][
                effect.effect_id
            ] = {
                "duration": effect.duration,
                "amplifier": effect.amplifier,
                "ambient": effect.ambient,
            }

        return potion_json

    def create_entity_effect_component(self, effects: List[EffectDefinition]) -> Dict[str, Any]:
        """
        Create a Bedrock entity effects component.

        Args:
            effects: List of EffectDefinition objects

        Returns:
            Entity effects component JSON
        """
        component = {
            "format_version": "1.17.0",
            "minecraft:entity": {"components": {"minecraft:entity_effects": {"effects": {}}}},
        }

        # Add each effect
        for effect in effects:
            component["minecraft:entity"]["components"]["minecraft:entity_effects"]["effects"][
                effect.effect_id
            ] = {
                "duration": effect.duration,
                "amplifier": effect.amplifier,
                "ambient": effect.ambient,
                "visible": effect.particles,
            }

        return component


class CustomEffectConverter:
    """
    Converter for custom Java effects (mod effects) to Bedrock format.

    Handles custom effect conversion, particle effects, sound effects,
    and area effect clouds.
    """

    def __init__(self):
        """Initialize the CustomEffectConverter."""
        self.custom_effects: Dict[str, str] = {}

    def convert_custom_effect(self, java_custom: str) -> str:
        """
        Convert a custom Java effect to Bedrock format.

        Args:
            java_custom: Custom effect identifier

        Returns:
            Bedrock custom effect identifier
        """
        # Remove namespace if present
        effect_id = java_custom
        if ":" in java_custom:
            namespace, effect_id = java_custom.split(":", 1)

        # Store mapping
        self.custom_effects[java_custom] = f"modporter:custom_{effect_id}"
        return f"modporter:custom_{effect_id}"

    def convert_particle_effect(self, java_particle: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert a Java particle effect to Bedrock particle system.

        Args:
            java_particle: Java particle effect dictionary

        Returns:
            Bedrock particle effect definition
        """
        particle_type = java_particle.get("type", "minecraft:particle")
        if ":" in particle_type:
            particle_type = particle_type.split(":", 1)[1]

        return {
            "particle_type": f"minecraft:{particle_type}",
            "local_offset": java_particle.get("offset", [0, 0, 0]),
            "local_origin": java_particle.get("origin", [0, 0, 0]),
            "rate": java_particle.get("rate", 1),
        }

    def convert_sound_effect(self, java_sound: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert a Java sound effect to Bedrock sound event.

        Args:
            java_sound: Java sound effect dictionary

        Returns:
            Bedrock sound effect definition
        """
        sound_id = java_sound.get("sound", "minecraft:ambient")
        if ":" in sound_id:
            sound_id = sound_id.split(":", 1)[1]

        return {
            "sound": f"minecraft:{sound_id}",
            "volume": java_sound.get("volume", 1.0),
            "pitch": java_sound.get("pitch", 1.0),
        }

    def convert_damage_over_time(self, damage: float, interval_ticks: int = 20) -> Dict[str, Any]:
        """
        Convert damage over time effect to Bedrock component.

        Args:
            damage: Damage amount per tick
            interval_ticks: Tick interval between damage

        Returns:
            Damage over time component
        """
        return {
            "damage_per_hurt": damage,
            "time_until_hurt": interval_ticks / 20,  # Convert to seconds
        }

    def create_entity_effect_component(self, effects: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Create entity effects component with custom effects.

        Args:
            effects: List of custom effect dictionaries

        Returns:
            Entity effects component JSON
        """
        component = {
            "format_version": "1.17.0",
            "minecraft:entity": {"components": {"minecraft:entity_effects": {"effects": {}}}},
        }

        for effect in effects:
            effect_id = effect.get("id", "custom_effect")
            # Convert custom effect
            bedrock_effect = self.convert_custom_effect(effect_id)

            component["minecraft:entity"]["components"]["minecraft:entity_effects"]["effects"][
                bedrock_effect
            ] = {
                "duration": effect.get("duration", 30),
                "amplifier": effect.get("amplifier", 0),
                "ambient": effect.get("ambient", False),
            }

        return component

    def convert_area_effect_cloud(self, java_cloud: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert Java AreaEffectCloud to Bedrock format.

        Args:
            java_cloud: Java area effect cloud dictionary

        Returns:
            Bedrock area effect cloud definition
        """
        # Convert radius
        radius = self.convert_radius(java_cloud.get("radius", 3.0))

        # Get effects
        effects = []
        if "effects" in java_cloud:
            for effect_data in java_cloud["effects"]:
                effects.append(
                    {
                        "effect": self.convert_custom_effect(effect_data.get("id", "")),
                        "duration": self.convert_duration(effect_data.get("duration", 120)),
                        "amplifier": effect_data.get("amplifier", 0),
                    }
                )

        return {
            "format_version": "1.17.0",
            "minecraft:area_effect_cloud": {
                "radius": radius,
                "particle": java_cloud.get("particle", "minecraft:particle_generic"),
                "effects": effects,
                "duration": self.convert_duration(java_cloud.get("duration", 300)),
            },
        }

    def convert_radius(self, java_radius: float) -> float:
        """
        Convert Java radius to Bedrock radius.

        Args:
            java_radius: Java radius value

        Returns:
            Bedrock radius value
        """
        return max(0.5, java_radius)

    def convert_duration(self, ticks: int) -> int:
        """
        Convert Java duration (in ticks) to Bedrock duration (in seconds).

        Args:
            ticks: Duration in ticks

        Returns:
            Duration in seconds
        """
        return max(1, ticks // 20)


# Convenience functions
def convert_effect(java_effect: Dict[str, Any]) -> EffectDefinition:
    """Convert Java effect to Bedrock effect definition."""
    converter = PotionConverter()
    return converter.convert_effect(java_effect)


def convert_potion(java_potion: Dict[str, Any]) -> PotionItem:
    """Convert Java potion to Bedrock potion item."""
    converter = PotionConverter()
    return converter.convert_potion(java_potion)


def create_potion_item_json(effects: List[EffectDefinition]) -> Dict[str, Any]:
    """Create Bedrock potion item JSON."""
    converter = PotionConverter()
    return converter.create_potion_item(effects)


def convert_custom_effect(java_custom: str) -> str:
    """Convert custom Java effect to Bedrock."""
    converter = CustomEffectConverter()
    return converter.convert_custom_effect(java_custom)


def create_entity_effects_json(effects: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Create entity effects component JSON."""
    converter = CustomEffectConverter()
    return converter.create_entity_effect_component(effects)
