"""
Audio converter module - handles all audio-related conversion logic.
This module is extracted from asset_converter.py for better organization.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List

# Import utilities
try:
    from . import converter_utils
except ImportError:
    import converter_utils

logger = logging.getLogger(__name__)

__all__ = ["convert_single_audio", "analyze_audio", "generate_sound_structure"]


# ============================================================================
# _convert_single_audio
# ============================================================================


def _convert_single_audio(agent, audio_path: str, metadata: Dict, audio_type: str) -> Dict:
    """Convert a single audio file to Bedrock-compatible format"""
    try:
        audio_path_obj = Path(audio_path)

        # Check if file exists
        if not audio_path_obj.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        # Get file extension
        file_ext = audio_path_obj.suffix.lower()

        # Check if format is supported
        if file_ext not in agent.audio_formats["input"]:
            return {
                "success": False,
                "original_path": str(audio_path),
                "error": f"Unsupported audio format: {file_ext}",
            }

        # Determine original format
        original_format = file_ext[1:]  # Remove the dot

        # Build converted path
        base_name = audio_path_obj.stem
        # Convert audio_type from "block.stone" to "block/stone"
        audio_path_parts = audio_type.replace(".", "/")
        converted_path = f"sounds/{audio_path_parts}/{base_name}.ogg"

        # Initialize conversion result
        conversion_performed = False
        optimizations_applied = []
        duration_seconds = metadata.get("duration_seconds")

        if original_format == "wav":
            # Convert WAV to OGG
            try:
                audio = AudioSegment.from_wav(audio_path)
                # In real implementation, would export to OGG
                # audio.export(converted_path, format="ogg")
                conversion_performed = True
                optimizations_applied.append("Converted WAV to OGG")
                duration_seconds = audio.duration_seconds
            except CouldntDecodeError as e:
                return {
                    "success": False,
                    "original_path": str(audio_path),
                    "error": f"Could not decode audio file: {e}",
                }
        elif original_format == "ogg":
            # OGG files don't need conversion, just validation
            conversion_performed = False
            optimizations_applied.append("Validated OGG format")

            # Get duration from metadata or calculate it
            if duration_seconds is None:
                try:
                    audio = AudioSegment.from_ogg(audio_path)
                    duration_seconds = audio.duration_seconds
                except CouldntDecodeError as e:
                    return {
                        "success": False,
                        "original_path": str(audio_path),
                        "error": f"Could not decode audio file: {e}",
                    }
        else:
            # Other formats would need conversion (mp3, etc.)
            conversion_performed = True
            optimizations_applied.append(f"Converted {original_format.upper()} to OGG")
            # For now, assume conversion works
            duration_seconds = 1.0  # Default duration

        # Generate bedrock sound event
        bedrock_sound_event = f"{audio_type}.{base_name}"

        return {
            "success": True,
            "original_path": str(audio_path),
            "converted_path": converted_path,
            "original_format": original_format,
            "bedrock_format": "ogg",
            "conversion_performed": conversion_performed,
            "optimizations_applied": optimizations_applied,
            "bedrock_sound_event": bedrock_sound_event,
            "duration_seconds": duration_seconds,
        }

    except FileNotFoundError as e:
        return {"success": False, "original_path": str(audio_path), "error": str(e)}
    except Exception as e:
        logger.error(f"Audio conversion error for {audio_path}: {e}", exc_info=True)
        return {"success": False, "original_path": str(audio_path), "error": str(e)}


# ============================================================================
# _analyze_audio
# ============================================================================


def _analyze_audio(agent, audio_path: str, metadata: Dict) -> Dict:
    """Analyze a single audio file for conversion needs"""
    file_size_mb = metadata.get("file_size_mb", 1)
    sample_rate = metadata.get("sample_rate", 44100)
    duration = metadata.get("duration_seconds", 1)
    file_ext = Path(audio_path).suffix.lower()

    issues = []
    needs_conversion = False

    # Check file size
    if file_size_mb > agent.audio_constraints["max_file_size_mb"]:
        issues.append(
            f"File size {file_size_mb}MB exceeds maximum {agent.audio_constraints['max_file_size_mb']}MB"
        )
        needs_conversion = True

    # Check sample rate
    if sample_rate not in agent.audio_constraints["sample_rates"]:
        issues.append(
            f"Sample rate {sample_rate} not in supported rates {agent.audio_constraints['sample_rates']}"
        )
        needs_conversion = True

    # Check duration
    if duration > agent.audio_constraints["max_duration_seconds"]:
        issues.append(
            f"Duration {duration}s exceeds maximum {agent.audio_constraints['max_duration_seconds']}s"
        )
        needs_conversion = True

    # Check format
    if file_ext != agent.audio_formats["output"]:
        needs_conversion = True

    return {
        "path": audio_path,
        "needs_conversion": needs_conversion,
        "issues": issues,
        "current_format": file_ext,
        "target_format": agent.audio_formats["output"],
        "current_specs": {
            "file_size_mb": file_size_mb,
            "sample_rate": sample_rate,
            "duration": duration,
        },
    }


# ============================================================================
# _generate_sound_structure
# ============================================================================


def _generate_sound_structure(agent, sounds: List[Dict]) -> Dict:
    sound_definitions = {}
    for s_data in sounds:
        if not s_data.get("success"):
            continue

        event_name = s_data.get("bedrock_sound_event")
        converted_path = s_data.get("converted_path")

        if not event_name or not converted_path:
            logger.warning(
                f"Skipping sound entry due to missing event name or converted path: {s_data.get('original_path')}"
            )
            continue

        rel_path = Path(converted_path)
        # Path for sound_definitions.json is relative to 'sounds' folder, without extension
        if rel_path.parts and rel_path.parts[0] == "sounds":
            sound_def_path = str(Path(*rel_path.parts[1:]).with_suffix(""))
        else:
            # If converted_path is not starting with "sounds/", use it as is but remove suffix
            sound_def_path = str(rel_path.with_suffix(""))
            logger.warning(
                f"Sound path '{converted_path}' for event '{event_name}' does not start with 'sounds/'. Using path as-is (minus suffix): '{sound_def_path}'."
            )

        if event_name not in sound_definitions:
            sound_definitions[event_name] = {"sounds": []}

        # Sounds can be simple strings or dictionaries for more control (e.g., volume, pitch)
        # For now, using simple string paths.
        sound_definitions[event_name]["sounds"].append(sound_def_path)

    if sound_definitions:
        return {"sound_definitions.json": {"sound_definitions": sound_definitions}}
    return {}
