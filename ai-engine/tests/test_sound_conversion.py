"""
Unit tests for Sound Conversion

Tests the conversion of Java sound events, music discs, and audio files
to Bedrock's sounds.json format.
"""

import pytest
import sys
import json
from pathlib import Path

# Add ai-engine to path
ai_engine_root = Path(__file__).parent.parent
sys.path.insert(0, str(ai_engine_root))

from converters.sound_converter import (
    SoundConverter,
    SoundCategory,
    MusicDiscConverter,
    SoundEvent,
    SoundPool,
    JukeboxSong,
)
from knowledge.patterns.sound_patterns import (
    SoundPatternLibrary,
    SoundCategory as PatternCategory,
    SoundPattern,
    get_sound_pattern,
    search_sound_patterns,
    get_sound_stats,
)


class TestSoundCategoryMapping:
    """Test cases for Java to Bedrock sound category mapping."""

    def test_category_mapping_complete(self):
        """Test that all Java categories map to Bedrock."""
        from converters.sound_converter import JAVA_SOUND_CATEGORY_MAP

        expected_categories = [
            "AMBIENT",
            "BLOCKS",
            "CREATIVE",
            "HOSTILE",
            "ITEM",
            "MASTER",
            "MUSIC",
            "NEUTRAL",
            "PLAYERS",
            "VOICE",
            "WEATHER",
        ]

        for category in expected_categories:
            assert category in JAVA_SOUND_CATEGORY_MAP, f"Missing mapping for {category}"

    def test_java_to_bedrock_category(self):
        """Test category conversion from Java to Bedrock."""
        converter = SoundConverter()

        # Test each category mapping
        java_categories = ["AMBIENT", "BLOCKS", "HOSTILE", "ITEM", "MUSIC", "NEUTRAL"]

        for java_cat in java_categories:
            java_event = {"name": "test", "sound_id": "test", "category": java_cat}
            result = converter.convert_sound_event(java_event)
            assert result.category is not None

    def test_custom_category_handling(self):
        """Test handling of custom/unknown categories."""
        converter = SoundConverter()

        java_event = {"name": "custom_sound", "sound_id": "custom", "category": "CUSTOM"}

        result = converter.convert_sound_event(java_event)
        # Should default to NEUTRAL for unknown categories
        assert result.category == SoundCategory.NEUTRAL


class TestSoundEventConversion:
    """Test cases for sound event conversion."""

    def test_simple_sound_event(self):
        """Test conversion of a simple sound event."""
        converter = SoundConverter()

        java_event = {
            "name": "block.stone.break",
            "sound_id": "dig.stone",
            "category": "BLOCKS",
            "volume": 1.0,
            "pitch": 1.0,
        }

        result = converter.convert_sound_event(java_event)

        assert result.name == "block.stone.break"
        assert result.sound_id == "dig.stone"
        assert result.category == SoundCategory.BLOCKS
        assert result.volume == 1.0
        assert result.pitch == 1.0

    def test_sound_with_variant(self):
        """Test sound event with variant (pitch/volume variance)."""
        converter = SoundConverter()

        java_event = {
            "name": "entity.zombie.ambient",
            "sound_id": "mob.zombie.say",
            "category": "HOSTILE",
            "volume": 0.5,
            "pitch": 0.8,
            "pitch_variance": 0.1,
            "volume_variance": 0.1,
        }

        result = converter.convert_sound_event(java_event)

        assert result.volume == 0.5
        assert result.pitch == 0.8
        assert result.pitch_variance == 0.1
        assert result.volume_variance == 0.1

    def test_sound_pool_conversion(self):
        """Test sound pool conversion to Bedrock format."""
        converter = SoundConverter()

        java_pool = {
            "name": "footsteps",
            "sounds": ["step.stone", "step.wood", "step.sand"],
            "category": "BLOCKS",
            "volume": 0.5,
            "pitch": 1.0,
        }

        result = converter.convert_sound_pool(java_pool)

        assert result.name == "footsteps"
        assert len(result.sounds) == 3
        assert result.category == SoundCategory.BLOCKS
        assert result.volume == 0.5

    def test_sound_mappings_exist(self):
        """Test that common sound mappings are defined."""
        converter = SoundConverter()

        # Verify key mappings exist
        expected_mappings = [
            "block.break",
            "block.place",
            "entity.hurt",
            "entity.death",
            "music.menu",
            "music.game",
        ]

        for mapping in expected_mappings:
            assert mapping in converter.sound_mappings

    def test_sound_annotation_conversion(self):
        """Test conversion of Java @SoundEvent annotation."""
        converter = SoundConverter()

        annotation = {
            "value": "block.wood.break",
            "category": "BLOCKS",
            "volume": 0.8,
            "pitch": 1.2,
        }

        result = converter.convert_sound_annotation(annotation)

        assert result.name == "block.wood.break"
        assert result.category == SoundCategory.BLOCKS

    def test_sounds_json_generation(self):
        """Test generation of complete sounds.json manifest."""
        converter = SoundConverter()

        sound_events = [
            SoundEvent("test1", "test1", SoundCategory.BLOCKS, 1.0, 1.0),
            SoundEvent("test2", "test2", SoundCategory.ITEM, 0.8, 1.2),
        ]

        manifest = converter.generate_sounds_manifest(sound_events)

        assert "format_version" in manifest
        assert "sound_definitions" in manifest
        assert "test1" in manifest["sound_definitions"]
        assert "test2" in manifest["sound_definitions"]


class TestMusicDiscConversion:
    """Test cases for music disc/jukebox conversion."""

    def test_jukebox_song_conversion(self):
        """Test conversion of a jukebox song."""
        converter = MusicDiscConverter()

        result = converter.convert_jukebox_song("music_disc_13", "music.game", 185)

        assert "record_item" in result
        assert "music_trigger" in result
        assert "jukebox_triggers" in result

    def test_record_item_generation(self):
        """Test generation of record item definition."""
        converter = MusicDiscConverter()

        record = converter.generate_record_item("music_disc_13", "music.game", 180)

        assert "minecraft:item" in record
        assert "minecraft:record" in record["minecraft:item"]["components"]
        assert (
            record["minecraft:item"]["components"]["minecraft:record"]["sound_event"]
            == "music.game"
        )

    def test_music_trigger_events(self):
        """Test jukebox trigger events."""
        converter = MusicDiscConverter()

        triggers = converter.add_music_triggers()

        assert "jukebox_play" in triggers
        assert "jukebox_stop" in triggers

    def test_note_block_sound_conversion(self):
        """Test conversion of note block instrument."""
        converter = MusicDiscConverter()

        instrument = {"id": "custom_bell", "sound": "note.bell", "pitch_offset": 0}

        result = converter.convert_note_block_sound(instrument)

        assert "minecraft:instrument" in result
        assert "notes" in result["minecraft:instrument"]

    def test_instrument_registry_conversion(self):
        """Test conversion of full instrument registry."""
        converter = MusicDiscConverter()

        instruments = [
            {"id": "harp", "sound": "note.harp", "pitch_offset": 0},
            {"id": "bell", "sound": "note.bell", "pitch_offset": 12},
        ]

        result = converter.convert_instrument_registry(instruments)

        assert "instrument_tracks" in result


class TestSoundsJsonGeneration:
    """Test cases for sounds.json generation."""

    def test_sounds_json_structure(self):
        """Test sounds.json has correct structure."""
        converter = SoundConverter()

        sounds = [
            SoundEvent("test", "test", SoundCategory.BLOCKS),
        ]

        manifest = converter.generate_sounds_manifest(sounds)

        assert manifest["format_version"] == [1, 20, 0]
        assert isinstance(manifest["sound_definitions"], dict)

    def test_sound_banks(self):
        """Test sound bank generation with variants."""
        converter = SoundConverter()

        pools = [
            SoundPool("variant_sounds", ["sound1", "sound2", "sound3"], SoundCategory.BLOCKS),
        ]

        manifest = converter.generate_sounds_manifest([], pools)

        assert "variant_sounds" in manifest["sound_definitions"]
        sounds_list = manifest["sound_definitions"]["variant_sounds"]["sounds"]
        assert len(sounds_list) == 3

    def test_volume_pitch_mapping(self):
        """Test volume and pitch are correctly mapped."""
        converter = SoundConverter()

        sound = SoundEvent("pitch_test", "pitch_test", SoundCategory.BLOCKS, volume=0.7, pitch=1.5)

        sounds = [sound]
        manifest = converter.generate_sounds_manifest(sounds)

        sound_def = manifest["sound_definitions"]["pitch_test"]
        assert sound_def["sounds"][0]["volume"] == 0.7
        assert sound_def["sounds"][0]["pitch"] == 1.5

    def test_stream_flag_for_music(self):
        """Test stream flag is set for music sounds."""
        converter = SoundConverter()

        sound = SoundEvent(
            "music_test", "music_test", SoundCategory.MUSIC, volume=1.0, pitch=1.0, stream=True
        )

        sounds = [sound]
        manifest = converter.generate_sounds_manifest(sounds)

        sound_def = manifest["sound_definitions"]["music_test"]
        assert sound_def["sounds"][0].get("stream", False) == True


class TestSoundPatternLibrary:
    """Test cases for SoundPatternLibrary."""

    def test_pattern_library_initialization(self):
        """Test pattern library loads with patterns."""
        lib = SoundPatternLibrary()

        assert len(lib.patterns) >= 25, "Should have at least 25 patterns"

    def test_pattern_search(self):
        """Test searching patterns by Java reference."""
        lib = SoundPatternLibrary()

        results = lib.search_by_java("stone")

        assert len(results) > 0, "Should find stone patterns"

    def test_category_filtering(self):
        """Test filtering patterns by category."""
        lib = SoundPatternLibrary()

        block_patterns = lib.get_by_category(PatternCategory.BLOCK)

        assert len(block_patterns) > 0
        assert all(p.category == PatternCategory.BLOCK for p in block_patterns)

    def test_add_pattern(self):
        """Test adding new patterns."""
        lib = SoundPatternLibrary()

        new_pattern = SoundPattern(
            java_sound_reference="test.custom.sound",
            bedrock_sound_event="test.custom.sound",
            category=PatternCategory.CUSTOM,
            conversion_notes="Custom test pattern",
        )

        lib.add_pattern(new_pattern)

        found = lib.get_pattern_by_java_reference("test.custom.sound")
        assert found is not None

    def test_stats(self):
        """Test getting library statistics."""
        lib = SoundPatternLibrary()

        stats = lib.get_stats()

        assert stats["total"] >= 25
        assert "by_category" in stats
        assert stats["stream_count"] >= 3
        assert stats["music_count"] >= 3


class TestIntegration:
    """Integration tests for sound conversion."""

    def test_full_conversion_workflow(self):
        """Test complete sound conversion workflow."""
        # Create converter
        converter = SoundConverter()

        # Convert Java events
        java_events = [
            {"name": "block.stone.break", "sound_id": "dig.stone", "category": "BLOCKS"},
            {"name": "entity.zombie.hurt", "sound_id": "mob.zombie.hurt", "category": "HOSTILE"},
            {"name": "music.game", "sound_id": "music.game", "category": "MUSIC"},
        ]

        sounds = [converter.convert_sound_event(e) for e in java_events]

        # Generate manifest
        manifest = converter.generate_sounds_manifest(sounds)

        assert "sound_definitions" in manifest
        assert len(manifest["sound_definitions"]) == 3

    def test_music_disc_with_pattern_lookup(self):
        """Test music disc conversion with pattern library."""
        converter = MusicDiscConverter()

        # Get pattern from library
        pattern = get_sound_pattern("music.game")

        # Convert music disc
        result = converter.convert_jukebox_song(
            "music_disc_custom", pattern.bedrock_sound_event if pattern else "music.game", 180
        )

        assert result is not None

    def test_pattern_search_integration(self):
        """Test pattern search returns useful results."""
        results = search_sound_patterns("entity")

        assert len(results) > 0
        # All results should contain 'entity' in reference
        for r in results:
            assert "entity" in r.java_sound_reference.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
