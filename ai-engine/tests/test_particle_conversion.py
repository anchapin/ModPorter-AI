"""
Unit tests for Particle System Conversion.

Tests the conversion of Java particles, particle emitters, and effects
to Bedrock's particle definitions and entity/block attachments.
"""

import pytest
import sys
from pathlib import Path

# Add ai-engine to path
ai_engine_root = Path(__file__).parent.parent
sys.path.insert(0, str(ai_engine_root))

from converters.particle_converter import (
    ParticleConverter,
    ParticleEmitterConverter,
    ParticleType,
)
from knowledge.patterns.particle_patterns import (
    ParticlePatternLibrary,
    ParticleCategory,
    get_particle_pattern,
    get_particle_stats,
)


class TestParticleTypeMapping:
    """Test cases for particle type mapping."""

    def test_particle_converter_initialization(self):
        """Test ParticleConverter initializes correctly."""
        converter = ParticleConverter()
        assert converter is not None
        assert len(converter.particle_type_map) > 0

    def test_map_particle_type_flame(self):
        """Test mapping flame particle type."""
        converter = ParticleConverter()
        result = converter.map_particle_type("ParticleFlame")
        assert result == ParticleType.FLAME

    def test_map_particle_type_smoke(self):
        """Test mapping smoke particle type."""
        converter = ParticleConverter()
        result = converter.map_particle_type("ParticleSmoke")
        assert result == ParticleType.SMOKE

    def test_map_particle_type_explosion(self):
        """Test mapping explosion particle type."""
        converter = ParticleConverter()
        result = converter.map_particle_type("ParticleExplosion")
        assert result == ParticleType.EXPLOSION

    def test_map_particle_type_unknown(self):
        """Test mapping unknown particle type defaults to BASIC."""
        converter = ParticleConverter()
        result = converter.map_particle_type("UnknownParticle")
        assert result == ParticleType.BASIC


class TestParticleConversion:
    """Test cases for particle conversion."""

    def test_convert_particle_basic(self):
        """Test basic particle conversion."""
        converter = ParticleConverter()
        java_particle = {"id": "test_particle", "type": "ParticleFlame"}
        result = converter.convert_particle(java_particle)

        assert result.particle_id == "test_particle"
        assert result.particle_type == ParticleType.FLAME

    def test_convert_particle_with_color(self):
        """Test particle conversion with color."""
        converter = ParticleConverter()
        java_particle = {
            "id": "color_particle",
            "type": "ParticleRedstone",
            "color": "#FF0000",
        }
        result = converter.convert_particle(java_particle)

        assert result.color == "#FF0000"

    def test_convert_particle_with_velocity(self):
        """Test particle conversion with velocity."""
        converter = ParticleConverter()
        java_particle = {
            "id": "velocity_particle",
            "type": "ParticleFlame",
            "velocity": {"x": 1.0, "y": 2.0, "z": 3.0},
        }
        result = converter.convert_particle(java_particle)

        assert result.velocity is not None
        assert result.velocity["x"] == 1.0

    def test_convert_color_hex(self):
        """Test color conversion from hex."""
        converter = ParticleConverter()
        result = converter.convert_color("#FF5500")
        assert result == "#FF5500"

    def test_convert_color_rgb(self):
        """Test color conversion from RGB tuple."""
        converter = ParticleConverter()
        result = converter.convert_color((255, 85, 0))
        assert result == "#ff5500"

    def test_convert_velocity(self):
        """Test velocity conversion."""
        converter = ParticleConverter()
        java_velocity = {"x": 1.5, "y": 2.5, "z": 3.5}
        result = converter.convert_velocity(java_velocity)

        assert result["x"] == 1.5
        assert result["y"] == 2.5
        assert result["z"] == 3.5


class TestEmitterConversion:
    """Test cases for emitter conversion."""

    def test_emitter_converter_initialization(self):
        """Test ParticleEmitterConverter initializes correctly."""
        converter = ParticleEmitterConverter()
        assert converter is not None

    def test_convert_emitter_string(self):
        """Test converting emitter from string."""
        converter = ParticleEmitterConverter()
        result = converter.convert_emitter("fire")

        assert result.emitter_id == "fire_emitter"
        assert result.particle_id == "fire"

    def test_convert_emitter_dict(self):
        """Test converting emitter from dictionary."""
        converter = ParticleEmitterConverter()
        java_emitter = {
            "id": "custom_emitter",
            "particle_id": "flame",
            "rate": 5.0,
        }
        result = converter.convert_emitter(java_emitter)

        assert result.emitter_id == "custom_emitter"
        assert result.particle_id == "flame"
        assert result.rate == 5.0

    def test_convert_burst(self):
        """Test burst configuration conversion."""
        converter = ParticleEmitterConverter()
        java_burst = {"particles": 20, "duration": 1.0, "count": 3}
        result = converter.convert_burst(java_burst)

        assert result.particles == 20
        assert result.duration == 1.0
        assert result.count == 3

    def test_convert_interval(self):
        """Test interval configuration conversion."""
        converter = ParticleEmitterConverter()
        java_interval = {"min_particles": 1, "max_particles": 3, "interval": 0.5}
        result = converter.convert_interval(java_interval)

        assert result.min_particles == 1
        assert result.max_particles == 3
        assert result.interval == 0.5

    def test_convert_rate(self):
        """Test emission rate conversion."""
        converter = ParticleEmitterConverter()
        result = converter.convert_rate(10.0)
        assert result == 0.1

    def test_convert_lifetime(self):
        """Test lifetime conversion."""
        converter = ParticleEmitterConverter()
        result = converter.convert_lifetime(100)
        assert result == 100

    def test_convert_box(self):
        """Test box conversion to shape/extent."""
        converter = ParticleEmitterConverter()
        box = {"x": 2.0, "y": 3.0, "z": 4.0}
        shape, extent = converter.convert_box(box)

        assert shape == "box"
        assert extent["x"] == 2.0


class TestParticlePatterns:
    """Test cases for particle pattern library."""

    def test_pattern_library_initialization(self):
        """Test pattern library loads with patterns."""
        lib = ParticlePatternLibrary()
        assert len(lib.patterns) >= 25, "Should have at least 25 patterns"

    def test_pattern_search(self):
        """Test searching patterns by Java class."""
        lib = ParticlePatternLibrary()
        results = lib.search_by_java("ParticleFlame")
        assert len(results) > 0

    def test_category_filtering(self):
        """Test filtering patterns by category."""
        lib = ParticlePatternLibrary()
        ambient_patterns = lib.get_by_category(ParticleCategory.AMBIENT)
        assert len(ambient_patterns) > 0
        assert all(p.category == ParticleCategory.AMBIENT for p in ambient_patterns)

    def test_exact_pattern_lookup(self):
        """Test exact pattern lookup by Java class."""
        pattern = get_particle_pattern("ParticleFlame")
        assert pattern is not None
        assert pattern.bedrock_particle_id == "minecraft:flame"

    def test_stats(self):
        """Test getting library statistics."""
        stats = get_particle_stats()
        assert stats["total"] >= 25
        assert "by_category" in stats
        assert "ambient" in stats["by_category"]


class TestIntegration:
    """Integration tests for particle conversion."""

    def test_full_particle_conversion(self):
        """Test complete particle conversion workflow."""
        converter = ParticleConverter()

        # Convert particle
        java_particle = {
            "id": "flame_particle",
            "type": "ParticleFlame",
            "color": "#FF6600",
            "size": 2.0,
            "lifetime": 30,
        }
        particle_def = converter.convert_particle(java_particle)

        # Generate particle file
        particle_json = converter.generate_particle_file(particle_def.particle_id, particle_def)

        assert "particle_effect" in particle_json
        assert "description" in particle_json["particle_effect"]

    def test_entity_particle_attachment(self):
        """Test particle attachment to entity."""
        converter = ParticleConverter()
        result = converter.attach_to_entity("flame_particle", "minecraft:fireball")

        assert "minecraft:entity" in result
        assert "minecraft:particle_effect" in result["minecraft:entity"]["components"]

    def test_block_particle_attachment(self):
        """Test particle attachment to block."""
        converter = ParticleConverter()
        result = converter.attach_to_block("flame_particle", "modporter:magma_block")

        assert "minecraft:block" in result
        assert "minecraft:particle_effect" in result["minecraft:block"]["components"]

    def test_emitter_with_particle_pattern(self):
        """Test emitter conversion combined with pattern lookup."""
        # Get pattern
        pattern = get_particle_pattern("ParticleFlame")
        assert pattern is not None

        # Use emitter converter
        emitter_converter = ParticleEmitterConverter()
        emitter = emitter_converter.convert_emitter(pattern.bedrock_particle_id)

        assert emitter is not None
        assert emitter.particle_id == pattern.bedrock_particle_id


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
