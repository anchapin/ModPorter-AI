"""
Particle Converter for converting Java particle systems to Bedrock format.

Converts Java particle types, particle emitters, and particle effects
to Bedrock's particle definitions and entity/block attachments.
"""

import json
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ParticleType(Enum):
    """Bedrock particle types."""

    BASIC = "basic"
    DUST = "minecraft:particle_basic"
    BLOCK = "minecraft:block"
    ITEM = "minecraft:item"
    VILLAGER = "minecraft:villager"
    DRIPPING = "minecraft:dripping"
    FALLING = "minecraft:falling"
    LANDING = "minecraft:landing"
    AMBIENT = "minecraft:ambient_particles"
    EXPLOSION = "minecraft:explosion"
    FLAME = "minecraft:flame"
    SMOKE = "minecraft:smoke"
    REDSTONE = "minecraft:redstone"
    SLIME = "minecraft:slime"
    HEART = "minecraft:heart"
    CRIT = "minecraft:crit"
    SPELL = "minecraft:spell"
    DRAGON_DEATH = "minecraft:dragon_death"
    END_ROD = "minecraft:end_rod"


class JavaParticleCategory(Enum):
    """Java particle categories."""

    AMBIENT = "ambient"
    COMBAT = "combat"
    ENVIRONMENT = "environment"
    MAGIC = "magic"
    WEATHER = "weather"
    BLOCK = "block"
    ITEM = "item"


@dataclass
class ParticleDefinition:
    """Represents a particle definition."""

    particle_id: str
    particle_type: ParticleType
    color: Optional[str] = None
    size: float = 1.0
    lifetime: int = 20
    velocity: Optional[Dict[str, float]] = None
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EmitterBurst:
    """Represents a particle emitter burst."""

    particles: int
    duration: float = 0.0
    count: int = 1


@dataclass
class EmitterInterval:
    """Represents a particle emission interval."""

    min_particles: int = 1
    max_particles: int = 1
    interval: float = 1.0


@dataclass
class EmitterDefinition:
    """Represents a particle emitter definition."""

    emitter_id: str
    particle_id: str
    rate: float = 1.0
    lifetime: Optional[int] = None
    burst: Optional[EmitterBurst] = None
    interval: Optional[EmitterInterval] = None
    shape: str = "point"
    extent: Optional[Dict[str, float]] = None


class ParticleConverter:
    """
    Converter for Java particle types to Bedrock format.

    Handles particle type mapping, color conversion, velocity conversion,
    and particle file generation for Bedrock.
    """

    def __init__(self):
        # Java to Bedrock particle type mapping
        self.particle_type_map = {
            # Ambient particles
            "ParticleFlame": ParticleType.FLAME,
            "ParticleSmoke": ParticleType.SMOKE,
            "ParticlePortal": ParticleType.REDSTONE,
            "ParticleEnchant": ParticleType.SPELL,
            "ParticleWarning": ParticleType.CRIT,
            # Combat particles
            "ParticleHit": ParticleType.CRIT,
            "ParticleAttack": ParticleType.EXPLOSION,
            "ParticleDamage": ParticleType.CRIT,
            "ParticleMagic": ParticleType.SPELL,
            "ParticleExplosion": ParticleType.EXPLOSION,
            # Environment particles
            "ParticleRain": ParticleType.FALLING,
            "ParticleSnow": ParticleType.AMBIENT,
            "ParticleWater": ParticleType.DRIPPING,
            "ParticleLava": ParticleType.FLAME,
            "ParticleFire": ParticleType.FLAME,
            "ParticleBubble": ParticleType.DRIPPING,
            # Magic particles
            "ParticleSpell": ParticleType.SPELL,
            "ParticleWitch": ParticleType.SPELL,
            "ParticleDragon": ParticleType.DRAGON_DEATH,
            "ParticleGuardian": ParticleType.CRIT,
            "ParticleEndRod": ParticleType.END_ROD,
            # Block particles
            "ParticleBlock": ParticleType.BLOCK,
            "ParticleFallingDust": ParticleType.FALLING,
            "ParticleLanding": ParticleType.LANDING,
            # Item particles
            "ParticleItem": ParticleType.ITEM,
            "ParticleSlime": ParticleType.SLIME,
            "ParticleHeart": ParticleType.HEART,
            # Default
            "Particle": ParticleType.BASIC,
        }

        # Color mappings for common particles
        self.color_map = {
            "flame": "#FF6600",
            "smoke": "#888888",
            "portal": "#9900FF",
            "enchant": "#00FF00",
            "water": "#3399FF",
            "lava": "#FF3300",
            "fire": "#FF6600",
            "heart": "#FF0000",
            "slime": "#00FF00",
            "redstone": "#FF0000",
        }

    def convert_particle(self, java_particle: Dict[str, Any]) -> ParticleDefinition:
        """
        Convert a Java particle definition to Bedrock particle.

        Args:
            java_particle: Java particle dictionary

        Returns:
            ParticleDefinition object
        """
        particle_id = java_particle.get("id", "custom_particle")
        java_type = java_particle.get("type", "Particle")

        # Map particle type
        particle_type = self.map_particle_type(java_type)

        # Convert color
        color = java_particle.get("color")
        if color:
            color = self.convert_color(color)
        elif particle_type.value in self.color_map:
            color = self.color_map[particle_type.value]

        # Convert velocity
        velocity = java_particle.get("velocity")
        if velocity:
            velocity = self.convert_velocity(velocity)

        return ParticleDefinition(
            particle_id=particle_id,
            particle_type=particle_type,
            color=color,
            size=java_particle.get("size", 1.0),
            lifetime=java_particle.get("lifetime", 20),
            velocity=velocity,
            properties=java_particle.get("properties", {}),
        )

    def convert_particle_emitter(self, java_emitter: Dict[str, Any]) -> EmitterDefinition:
        """
        Convert a Java particle emitter to Bedrock emitter config.

        Args:
            java_emitter: Java emitter dictionary

        Returns:
            EmitterDefinition object
        """
        emitter_id = java_emitter.get("id", "custom_emitter")
        particle_id = java_emitter.get("particle_id", "custom_particle")
        rate = java_emitter.get("rate", 1.0)

        # Convert burst
        burst = None
        if "burst" in java_emitter:
            burst = self.convert_burst(java_emitter["burst"])

        # Convert interval
        interval = None
        if "interval" in java_emitter:
            interval = self.convert_interval(java_emitter["interval"])

        # Convert lifetime
        lifetime = None
        if "lifetime" in java_emitter:
            lifetime = self.convert_lifetime(java_emitter["lifetime"])

        # Convert box/shape
        shape = "point"
        extent = None
        if "box" in java_emitter:
            shape, extent = self.convert_box(java_emitter["box"])

        return EmitterDefinition(
            emitter_id=emitter_id,
            particle_id=particle_id,
            rate=rate,
            lifetime=lifetime,
            burst=burst,
            interval=interval,
            shape=shape,
            extent=extent,
        )

    def map_particle_type(self, java_type: str) -> ParticleType:
        """
        Map Java particle type to Bedrock particle type.

        Args:
            java_type: Java particle type string

        Returns:
            ParticleType enum value
        """
        return self.particle_type_map.get(java_type, ParticleType.BASIC)

    def convert_color(self, java_color: Any) -> str:
        """
        Convert Java color to Bedrock color definition.

        Args:
            java_color: Java color (hex string, RGB tuple, or color name)

        Returns:
            Hex color string
        """
        if isinstance(java_color, str):
            # Check if it's a named color
            if java_color.lower() in self.color_map:
                return self.color_map[java_color.lower()]
            # Check if it's already a hex color
            if java_color.startswith("#"):
                return java_color
            return f"#{java_color}"
        elif isinstance(java_color, (list, tuple)):
            # RGB tuple
            if len(java_color) >= 3:
                r, g, b = java_color[:3]
                return f"#{r:02x}{g:02x}{b:02x}"
        return "#FFFFFF"

    def convert_velocity(self, java_velocity: Dict[str, float]) -> Dict[str, float]:
        """
        Convert Java velocity to Bedrock motion.

        Args:
            java_velocity: Java velocity dictionary

        Returns:
            Bedrock motion dictionary
        """
        return {
            "x": java_velocity.get("x", 0.0),
            "y": java_velocity.get("y", 0.0),
            "z": java_velocity.get("z", 0.0),
        }

    def generate_particle_file(
        self, particle_id: str, definition: ParticleDefinition
    ) -> Dict[str, Any]:
        """
        Generate a Bedrock particle JSON file.

        Args:
            particle_id: Particle identifier
            definition: ParticleDefinition object

        Returns:
            Bedrock particle JSON definition
        """
        particle_json = {
            "format_version": "1.10.0",
            "particle_effect": {
                "description": {
                    "identifier": f"modporter:{particle_id}",
                    "basic_render_parameters": {
                        "material": "particles_alpha",
                        "texture": "textures/particle/particles",
                    },
                },
            },
        }

        # Add particle type specific properties
        if definition.particle_type == ParticleType.BLOCK:
            particle_json["particle_effect"]["components"] = {
                "minecraft:particle_appearance_block": {
                    "block": "minecraft:stone",
                }
            }
        elif definition.particle_type == ParticleType.ITEM:
            particle_json["particle_effect"]["components"] = {
                "minecraft:particle_appearance_item": {
                    "item": "minecraft:stick",
                }
            }
        elif definition.color:
            particle_json["particle_effect"]["components"] = {
                "minecraft:particle_color": {
                    "color": definition.color,
                }
            }

        # Add lifetime
        if definition.lifetime:
            particle_json["particle_effect"]["components"] = particle_json["particle_effect"].get(
                "components", {}
            )
            particle_json["particle_effect"]["components"]["minecraft:particle_lifetime"] = {
                "max_lifetime": definition.lifetime
            }

        # Add motion if specified
        if definition.velocity:
            particle_json["particle_effect"]["components"] = particle_json["particle_effect"].get(
                "components", {}
            )
            particle_json["particle_effect"]["components"]["minecraft:particle_motion"] = {
                "vector": definition.velocity
            }

        return particle_json

    def attach_to_entity(self, particle_id: str, entity_id: str) -> Dict[str, Any]:
        """
        Generate entity component to attach particle.

        Args:
            particle_id: Particle identifier
            entity_id: Entity identifier

        Returns:
            Bedrock entity component JSON
        """
        return {
            "format_version": "1.16.0",
            "minecraft:entity": {
                "description": {
                    "identifier": entity_id,
                },
                "components": {
                    "minecraft:particle_effect": {
                        "particle_effect": f"modporter:{particle_id}",
                    }
                },
            },
        }

    def attach_to_block(self, particle_id: str, block_id: str) -> Dict[str, Any]:
        """
        Generate block component to attach particle.

        Args:
            particle_id: Particle identifier
            block_id: Block identifier

        Returns:
            Bedrock block component JSON
        """
        return {
            "format_version": "1.16.0",
            "minecraft:block": {
                "description": {
                    "identifier": block_id,
                },
                "components": {
                    "minecraft:particle_effect": {
                        "particle_effect": f"modporter:{particle_id}",
                    }
                },
            },
        }


class ParticleEmitterConverter:
    """
    Converter for Java particle emitters to Bedrock format.

    Handles emitter properties, burst configurations, emission rates,
    and particle attachment to entities/blocks.
    """

    def __init__(self):
        self.particle_converter = ParticleConverter()

    def convert_emitter(self, java_emitter: Any) -> EmitterDefinition:
        """
        Convert a Java particle emitter to Bedrock emitter config.

        Args:
            java_emitter: Java emitter (string identifier or dict)

        Returns:
            EmitterDefinition object
        """
        if isinstance(java_emitter, str):
            # Simple string-based conversion
            java_emitter = {"id": f"{java_emitter}_emitter", "particle_id": java_emitter}

        return self.particle_converter.convert_particle_emitter(java_emitter)

    def convert_burst(self, java_burst: Dict[str, Any]) -> EmitterBurst:
        """
        Convert Java burst configuration.

        Args:
            java_burst: Java burst dictionary

        Returns:
            EmitterBurst object
        """
        return EmitterBurst(
            particles=java_burst.get("particles", 10),
            duration=java_burst.get("duration", 0.0),
            count=java_burst.get("count", 1),
        )

    def convert_interval(self, java_interval: Dict[str, Any]) -> EmitterInterval:
        """
        Convert Java interval configuration.

        Args:
            java_interval: Java interval dictionary

        Returns:
            EmitterInterval object
        """
        return EmitterInterval(
            min_particles=java_interval.get("min_particles", 1),
            max_particles=java_interval.get("max_particles", 1),
            interval=java_interval.get("interval", 1.0),
        )

    def convert_rate(self, emission_rate: float) -> float:
        """
        Convert emission rate to emission interval.

        Args:
            emission_rate: Particles per second

        Returns:
            Interval in seconds
        """
        if emission_rate <= 0:
            return 1.0
        return 1.0 / emission_rate

    def convert_lifetime(self, lifetime: int) -> int:
        """
        Convert lifetime to max age.

        Args:
            lifetime: Lifetime in ticks

        Returns:
            Max age in ticks
        """
        return max(1, lifetime)

    def convert_box(self, box: Dict[str, float]) -> tuple:
        """
        Convert Java box to Bedrock shape/extent.

        Args:
            box: Java box dictionary with x, y, z dimensions

        Returns:
            Tuple of (shape, extent)
        """
        shape = "box"
        extent = {
            "x": box.get("x", 1.0),
            "y": box.get("y", 1.0),
            "z": box.get("z", 1.0),
        }
        return shape, extent

    def entity_particle_component(self, particle_id: str, entity_id: str) -> Dict[str, Any]:
        """
        Generate entity particle component.

        Args:
            particle_id: Particle identifier
            entity_id: Entity identifier

        Returns:
            Entity component JSON
        """
        return self.particle_converter.attach_to_entity(particle_id, entity_id)

    def block_particle_component(self, particle_id: str, block_id: str) -> Dict[str, Any]:
        """
        Generate block particle component.

        Args:
            particle_id: Particle identifier
            block_id: Block identifier

        Returns:
            Block component JSON
        """
        return self.particle_converter.attach_to_block(particle_id, block_id)


# Convenience functions
def convert_particle(java_particle: Dict[str, Any]) -> ParticleDefinition:
    """Convert Java particle to Bedrock particle definition."""
    converter = ParticleConverter()
    return converter.convert_particle(java_particle)


def convert_emitter(java_emitter: Dict[str, Any]) -> EmitterDefinition:
    """Convert Java emitter to Bedrock emitter definition."""
    converter = ParticleEmitterConverter()
    return converter.convert_emitter(java_emitter)


def generate_particle_json(particle_id: str, java_particle: Dict[str, Any]) -> Dict[str, Any]:
    """Generate Bedrock particle JSON file."""
    converter = ParticleConverter()
    definition = converter.convert_particle(java_particle)
    return converter.generate_particle_file(particle_id, definition)
