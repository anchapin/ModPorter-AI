"""
Sound Converter for converting Java sound events to Bedrock format.

Converts Java sound events, sound pools, music discs, and ambient sounds
to Bedrock's sounds.json format and audio file structure.
"""

import json
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class SoundCategory(Enum):
    """Bedrock sound categories."""

    AMBIENT = "minecraft:ambient"
    BLOCKS = "minecraft:block"
    HOSTILE = "minecraft:hostile"
    ITEM = "minecraft:item"
    MUSIC = "minecraft:music"
    NEUTRAL = "minecraft:neutral"
    PLAYERS = "minecraft:player"
    WEATHER = "minecraft:weather"


# Java SoundCategory to Bedrock mapping
JAVA_SOUND_CATEGORY_MAP = {
    "AMBIENT": SoundCategory.AMBIENT,
    "BLOCKS": SoundCategory.BLOCKS,
    "CREATIVE": SoundCategory.BLOCKS,
    "HOSTILE": SoundCategory.HOSTILE,
    "ITEM": SoundCategory.ITEM,
    "MASTER": SoundCategory.NEUTRAL,
    "MUSIC": SoundCategory.MUSIC,
    "NEUTRAL": SoundCategory.NEUTRAL,
    "PLAYERS": SoundCategory.PLAYERS,
    "VOICE": SoundCategory.NEUTRAL,
    "WEATHER": SoundCategory.WEATHER,
}


@dataclass
class SoundEvent:
    """Represents a sound event definition."""

    name: str
    sound_id: str
    category: SoundCategory
    volume: float = 1.0
    pitch: float = 1.0
    pitch_variance: float = 0.0
    volume_variance: float = 0.0
    weight: int = 1
    stream: bool = False
    preload: bool = False
    attenuation_distance: int = 16


@dataclass
class SoundPool:
    """Represents a sound pool with multiple sound variants."""

    name: str
    sounds: List[str] = field(default_factory=list)
    category: SoundCategory = SoundCategory.BLOCKS
    volume: float = 1.0
    pitch: float = 1.0


@dataclass
class JukeboxSong:
    """Represents a music disc/jukebox song."""

    registry_name: str
    sound_event: str
    duration_ticks: int
    description: str = ""
    analog_output: bool = False


class SoundConverter:
    """
    Converter for Java sound events to Bedrock sounds.json format.

    Handles sound event definitions, sound pools, and audio file mapping.
    """

    def __init__(self):
        # Base sounds.json template
        self.sounds_template = {"format_version": [1, 20, 0], "sound_definitions": {}}

        # Common Java to Bedrock sound mappings
        self.sound_mappings = {
            # Block sounds
            "block.break": "dig.stone",
            "block.place": "step.stone",
            "block.hit": "hit.stone",
            "block.step": "step.stone",
            "block.fall": "fall.stone",
            # Item sounds
            "item.break": "break.item",
            "item.use": "use.item",
            "item.pickup": "pickup.item",
            "item.drop": "drop.item",
            # Entity sounds
            "entity.hurt": "hurt",
            "entity.death": "death",
            "entity.ambient": "ambient",
            "entity.step": "step",
            "entity.attack": "attack",
            # Ambient sounds
            "ambient.cave": "ambient.cave",
            "ambient.underwater": "ambient.underwater",
            "ambient.nether": "ambient.nether",
            # Weather sounds
            "weather.rain": "weather.rain",
            "weather.thunder": "weather.thunder",
            # Music
            "music.menu": "music.menu",
            "music.game": "music.game",
            "music.creative": "music.creative",
            "music.end": "music.end",
        }

        # Sound category mappings
        self.category_mappings = JAVA_SOUND_CATEGORY_MAP

    def convert_sound_event(self, java_event: Dict[str, Any]) -> SoundEvent:
        """
        Convert a Java SoundEvent to Bedrock format.

        Args:
            java_event: Java sound event dictionary

        Returns:
            SoundEvent object
        """
        name = java_event.get("name", java_event.get("id", "unknown"))
        sound_id = java_event.get("sound_id", name)

        # Map category
        java_category = java_event.get("category", "MASTER")
        category = self.category_mappings.get(java_category, SoundCategory.NEUTRAL)

        return SoundEvent(
            name=name,
            sound_id=sound_id,
            category=category,
            volume=java_event.get("volume", 1.0),
            pitch=java_event.get("pitch", 1.0),
            pitch_variance=java_event.get("pitch_variance", 0.0),
            volume_variance=java_event.get("volume_variance", 0.0),
            weight=java_event.get("weight", 1),
            stream=java_event.get("stream", False),
            preload=java_event.get("preload", False),
            attenuation_distance=java_event.get("attenuation_distance", 16),
        )

    def convert_sound_pool(self, java_pool: Dict[str, Any]) -> SoundPool:
        """
        Convert a Java SoundPool to Bedrock format.

        Args:
            java_pool: Java sound pool dictionary

        Returns:
            SoundPool object
        """
        name = java_pool.get("name", java_pool.get("id", "unknown"))

        # Get sounds from pool
        sounds = java_pool.get("sounds", [])
        if isinstance(sounds, str):
            sounds = [sounds]

        # Map category
        java_category = java_pool.get("category", "BLOCKS")
        category = self.category_mappings.get(java_category, SoundCategory.BLOCKS)

        return SoundPool(
            name=name,
            sounds=sounds,
            category=category,
            volume=java_pool.get("volume", 1.0),
            pitch=java_pool.get("pitch", 1.0),
        )

    def convert_music_disc(self, java_record: Dict[str, Any]) -> JukeboxSong:
        """
        Convert a Java music disc to Bedrock format.

        Args:
            java_record: Java music disc/song dictionary

        Returns:
            JukeboxSong object
        """
        registry_name = java_record.get("registry_name", java_record.get("id", "unknown"))
        sound_event = java_record.get("sound_event", "music.game")
        duration = java_record.get("duration", java_record.get("duration_ticks", 185))

        return JukeboxSong(
            registry_name=registry_name,
            sound_event=sound_event,
            duration_ticks=duration,
            description=java_record.get("description", ""),
            analog_output=java_record.get("analog_output", False),
        )

    def convert_ambient_sound(self, java_ambient: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert a Java ambient sound to Bedrock format.

        Args:
            java_ambient: Java ambient sound dictionary

        Returns:
            Bedrock ambient sound definition
        """
        name = java_ambient.get("name", java_ambient.get("id", "ambient"))
        sound_id = java_ambient.get("sound_id", name)

        # Map to Bedrock ambient sound definition
        return {
            "name": sound_id,
            "volume": java_ambient.get("volume", 1.0),
            "pitch": java_ambient.get("pitch", 1.0),
            "is_global": java_ambient.get("is_global", False),
        }

    def generate_sounds_manifest(
        self,
        sounds: List[SoundEvent],
        sound_pools: Optional[List[SoundPool]] = None,
    ) -> Dict[str, Any]:
        """
        Generate sounds.json manifest from sound definitions.

        Args:
            sounds: List of SoundEvent objects
            sound_pools: Optional list of SoundPool objects

        Returns:
            Complete sounds.json dictionary
        """
        manifest = {"format_version": [1, 20, 0], "sound_definitions": {}}

        # Add individual sounds
        for sound in sounds:
            sound_def = self._build_sound_definition(sound)
            manifest["sound_definitions"][sound.sound_id] = sound_def

        # Add sound pools
        if sound_pools:
            for pool in sound_pools:
                pool_def = self._build_pool_definition(pool)
                manifest["sound_definitions"][pool.name] = pool_def

        return manifest

    def _build_sound_definition(self, sound: SoundEvent) -> Dict[str, Any]:
        """Build a sound definition entry."""
        sounds_list = []

        # Build sound entry
        sound_entry = {
            "name": sound.sound_id,
        }

        # Add volume and pitch
        if sound.volume != 1.0:
            sound_entry["volume"] = sound.volume
        if sound.pitch != 1.0:
            sound_entry["pitch"] = sound.pitch

        # Add variance if present
        if sound.pitch_variance > 0:
            sound_entry["pitch"] = (
                f"{sound.pitch - sound.pitch_variance}:{sound.pitch + sound.pitch_variance}"
            )
        if sound.volume_variance > 0:
            sound_entry["volume"] = (
                f"{sound.volume - sound.volume_variance}:{sound.volume + sound.volume_variance}"
            )

        # Add flags
        if sound.stream:
            sound_entry["stream"] = True
        if sound.preload:
            sound_entry["preload"] = True

        sounds_list.append(sound_entry)

        return {
            "sounds": sounds_list,
            "category": sound.category.value,
        }

    def _build_pool_definition(self, pool: SoundPool) -> Dict[str, Any]:
        """Build a sound pool definition entry."""
        sounds_list = []

        for sound_file in pool.sounds:
            sound_entry = {"name": sound_file}
            if pool.volume != 1.0:
                sound_entry["volume"] = pool.volume
            if pool.pitch != 1.0:
                sound_entry["pitch"] = pool.pitch
            sounds_list.append(sound_entry)

        return {
            "sounds": sounds_list,
            "category": pool.category.value,
        }

    def extract_sounds_from_jar(self, jar_path: str) -> List[str]:
        """
        Extract audio file references from a mod JAR.

        Args:
            jar_path: Path to the mod JAR file

        Returns:
            List of audio file paths found in the JAR
        """
        import zipfile

        audio_files = []
        audio_extensions = [".ogg", ".wav", ".mp3"]

        try:
            with zipfile.ZipFile(jar_path, "r") as jar:
                for file_info in jar.filelist:
                    filename = file_info.filename.lower()
                    if any(filename.endswith(ext) for ext in audio_extensions):
                        audio_files.append(file_info.filename)
        except Exception as e:
            logger.warning(f"Failed to extract sounds from JAR: {e}")

        return audio_files

    def convert_sound_annotation(self, annotation: Dict[str, Any]) -> SoundEvent:
        """
        Convert a Java @SoundEvent annotation to Bedrock format.

        Args:
            annotation: Annotation dictionary

        Returns:
            SoundEvent object
        """
        java_event = {
            "name": annotation.get("value", annotation.get("id", "unknown")),
            "sound_id": annotation.get("value", "unknown"),
            "category": annotation.get("category", "MASTER"),
            "volume": annotation.get("volume", 1.0),
            "pitch": annotation.get("pitch", 1.0),
        }

        return self.convert_sound_event(java_event)


class MusicDiscConverter:
    """
    Converter for Java music discs and jukebox songs to Bedrock format.
    Handles record items and music triggers.
    """

    def __init__(self):
        self.sound_converter = SoundConverter()

    def convert_jukebox_song(
        self, registry_name: str, sound_event: str, duration_ticks: int
    ) -> Dict[str, Any]:
        """
        Convert a jukebox song to Bedrock record item + music configuration.

        Args:
            registry_name: Java registry name (e.g., 'music_disc_13')
            sound_event: Sound event to play
            duration_ticks: Duration in ticks

        Returns:
            Dictionary with record item and music config
        """
        # Convert registry name to Bedrock identifier
        bedock_id = registry_name.replace("music_disc_", "record_")
        if ":" not in bedock_id:
            bedock_id = f"custom:{bedock_id}"

        return {
            "record_item": {
                "minecraft:item": {
                    "description": {"identifier": bedock_id},
                    "components": {
                        "minecraft:max_stack_size": 1,
                        "minecraft:record": {
                            "sound_event": sound_event,
                            "duration": duration_ticks / 20.0,  # Convert ticks to seconds
                        },
                        "minecraft:display_name": {
                            "value": self._generate_record_name(registry_name)
                        },
                    },
                }
            },
            "music_trigger": {
                "minecraft:play_sound": {
                    "on": {"event": "minecraft:record_played", "target": "self"},
                    "sound": sound_event,
                    "volume": 4.0,
                    "pitch": 1.0,
                }
            },
            "jukebox_triggers": {
                "minecraft:jukebox_play": {
                    "minecraft:play_sound": {"sound": sound_event, "volume": 4.0}
                },
                "minecraft:record_play": {
                    "minecraft:play_sound": {"sound": sound_event, "volume": 4.0}
                },
            },
        }

    def generate_record_item(
        self, registry_name: str, sound_event: str, duration: int
    ) -> Dict[str, Any]:
        """
        Generate a Bedrock record item definition.

        Args:
            registry_name: Registry name
            sound_event: Sound event to play
            duration: Duration in seconds

        Returns:
            Bedrock item definition
        """
        bedock_id = registry_name.replace("music_disc_", "record_")
        if ":" not in bedock_id:
            bedock_id = f"custom:{bedock_id}"

        return {
            "format_version": "1.19.0",
            "minecraft:item": {
                "description": {"identifier": bedock_id},
                "components": {
                    "minecraft:max_stack_size": 1,
                    "minecraft:record": {"sound_event": sound_event, "duration": float(duration)},
                    "minecraft:icon": {"texture": bedock_id.replace(":", "_")},
                    "minecraft:display_name": {"value": self._generate_record_name(registry_name)},
                },
            },
        }

    def add_music_triggers(self) -> Dict[str, Any]:
        """
        Generate jukebox trigger events for music playback.

        Returns:
            Dictionary with jukebox event triggers
        """
        return {
            "jukebox_play": {"minecraft:play_sound": {"sound": "music.record", "volume": 4.0}},
            "jukebox_stop": {"minecraft:stop_sound": {"sound": "music.record"}},
        }

    def convert_note_block_sound(self, java_instrument: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert a note block instrument to Bedrock format.

        Args:
            java_instrument: Java instrument definition

        Returns:
            Bedrock note block sound definition
        """
        instrument_id = java_instrument.get("id", "custom_note")
        sound_event = java_instrument.get("sound", "note.harp")
        pitch_offset = java_instrument.get("pitch_offset", 0)

        # Generate all 24 note variations
        notes = {}
        for i in range(24):
            base_pitch = 0.5 + (i * 0.033707)  # Bedrock formula
            notes[f"note_{i}"] = {
                "sound": sound_event,
                "pitch": base_pitch + (pitch_offset * 0.033707),
            }

        return {
            "format_version": "1.19.0",
            "minecraft:instrument": {
                "description": {"identifier": f"custom:instrument_{instrument_id}"},
                "notes": notes,
            },
        }

    def convert_instrument_registry(self, instruments: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Convert a full instrument registry to Bedrock format.

        Args:
            instruments: List of instrument definitions

        Returns:
            Complete instrument registry
        """
        registry = {"format_version": "1.19.0", "instrument_tracks": {}}

        for instrument in instruments:
            instrument_id = instrument.get("id", "custom")
            track = self.convert_note_block_sound(instrument)
            registry["instrument_tracks"][f"custom:instrument_{instrument_id}"] = track

        return registry

    def extract_audio_from_jar(self, jar_path: str) -> List[str]:
        """
        Extract audio files from a mod JAR.

        Args:
            jar_path: Path to JAR file

        Returns:
            List of audio file paths
        """
        return self.sound_converter.extract_sounds_from_jar(jar_path)

    def validate_audio_format(self, file_path: str) -> bool:
        """
        Validate if an audio file is in a supported format.

        Args:
            file_path: Path to audio file

        Returns:
            True if format is supported
        """
        supported_formats = [".ogg", ".wav", ".mp3"]
        return any(file_path.lower().endswith(ext) for ext in supported_formats)

    def convert_audio_to_ogg(self, input_path: str, output_path: str) -> bool:
        """
        Convert audio file to OGG format (requires ffmpeg).

        Args:
            input_path: Input file path
            output_path: Output OGG file path

        Returns:
            True if conversion successful
        """
        import subprocess

        try:
            result = subprocess.run(
                ["ffmpeg", "-i", input_path, "-y", "-acodec", "libvorbis", output_path],
                capture_output=True,
                timeout=60,
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            logger.warning("FFmpeg not available for audio conversion")
            return False

    def _generate_record_name(self, registry_name: str) -> str:
        """Generate display name for a record."""
        # Remove prefix and capitalize
        name = registry_name.replace("music_disc_", "").replace("_", " ")
        return name.title()
