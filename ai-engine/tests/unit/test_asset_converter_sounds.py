import pytest
from pathlib import Path
import json
from unittest.mock import patch

from ai_engine.src.agents.asset_converter import AssetConverterAgent
from ai_engine.tests.unit.conftest import MockAudioSegment # Import the mock

# Uses agent fixture from conftest.py

@pytest.fixture
def dummy_wav_file(tmp_path: Path) -> str:
    p = tmp_path / "test.wav"
    p.write_text("dummy wav content") # Content doesn't matter due to mocking
    return str(p)

@pytest.fixture
def dummy_ogg_file(tmp_path: Path) -> str:
    p = tmp_path / "test.ogg"
    p.write_text("dummy ogg content") # Content doesn't matter
    return str(p)

@pytest.fixture
def dummy_txt_file(tmp_path: Path) -> str:
    p = tmp_path / "test.txt"
    p.write_text("dummy text content")
    return str(p)

# Patch AudioSegment for all tests in this file
@pytest.fixture(autouse=True)
def mock_pydub_loading():
    with patch('pydub.AudioSegment', MockAudioSegment) as mock_audio_segment:
        yield mock_audio_segment

def test_convert_single_audio_wav_input(agent: AssetConverterAgent, dummy_wav_file: str):
    result = agent._convert_single_audio(dummy_wav_file, {}, "block.stone")

    assert result["success"]
    assert result["original_path"] == dummy_wav_file
    assert Path(result["converted_path"]).name == "test.ogg" # Always converts to ogg
    assert "sounds/block/stone/test.ogg" in result["converted_path"].replace("\\", "/") # OS agnostic path check
    assert result["original_format"] == "wav"
    assert result["bedrock_format"] == "ogg"
    assert result["conversion_performed"] == True
    assert "Converted WAV to OGG" in result["optimizations_applied"]
    assert result["bedrock_sound_event"] == "block.stone.test"
    assert result["duration_seconds"] == 1.0 # From MockAudioSegment.from_wav

def test_convert_single_audio_ogg_input(agent: AssetConverterAgent, dummy_ogg_file: str):
    result = agent._convert_single_audio(dummy_ogg_file, {"duration_seconds": 2.5}, "mob.pig") # Metadata duration

    assert result["success"]
    assert result["original_path"] == dummy_ogg_file
    assert Path(result["converted_path"]).name == "test.ogg"
    assert "sounds/mob/pig/test.ogg" in result["converted_path"].replace("\\", "/")
    assert result["original_format"] == "ogg"
    assert result["bedrock_format"] == "ogg"
    assert result["conversion_performed"] == False # No conversion needed
    assert "Validated OGG format" in result["optimizations_applied"]
    assert result["bedrock_sound_event"] == "mob.pig.test"
    assert result["duration_seconds"] == 2.5 # Used metadata

def test_convert_single_audio_ogg_input_get_duration(agent: AssetConverterAgent, dummy_ogg_file: str):
    # Test without duration in metadata to force pydub calculation
    result = agent._convert_single_audio(dummy_ogg_file, {}, "random.event")
    assert result["success"]
    assert result["duration_seconds"] == 2.0 # From MockAudioSegment.from_ogg

def test_convert_single_audio_unsupported_format(agent: AssetConverterAgent, dummy_txt_file: str):
    result = agent._convert_single_audio(dummy_txt_file, {}, "ui")
    assert not result["success"]
    assert "Unsupported audio format: .txt" in result["error"]
    assert result.get("fallback_suggestion") is None # Fallback is added by public method, not _convert_single

def test_convert_single_audio_file_not_found(agent: AssetConverterAgent):
    result = agent._convert_single_audio("non_existent.wav", {}, "player")
    assert not result["success"]
    assert "Audio file not found" in result["error"]

def test_convert_single_audio_decode_error(agent: AssetConverterAgent, dummy_wav_file: str, mock_pydub_loading):
    # Configure the mock to raise CouldntDecodeError
    mock_pydub_loading.from_wav.side_effect = CouldntDecodeError("Mocked decode error")

    result = agent._convert_single_audio(dummy_wav_file, {}, "ambient")
    assert not result["success"]
    assert "Could not decode audio file" in result["error"]
    assert "Mocked decode error" in result["error"]

def test_generate_sound_structure(agent: AssetConverterAgent):
    sounds_data = [
        {
            'success': True, 'original_path': 'path/to/sound1.wav',
            'converted_path': 'sounds/block/stone/dig1.ogg',
            'bedrock_sound_event': 'block.stone.dig',
            'original_format': 'wav', 'bedrock_format': 'ogg', 'conversion_performed': True
        },
        {
            'success': True, 'original_path': 'path/to/sound2.ogg',
            'converted_path': 'sounds/mob/pig/say1.ogg',
            'bedrock_sound_event': 'mob.pig.say',
            'original_format': 'ogg', 'bedrock_format': 'ogg', 'conversion_performed': False
        },
        { # Another sound for the same event
            'success': True, 'original_path': 'path/to/sound3.wav',
            'converted_path': 'sounds/block/stone/dig2.ogg',
            'bedrock_sound_event': 'block.stone.dig',
            'original_format': 'wav', 'bedrock_format': 'ogg', 'conversion_performed': True
        },
        {'success': False, 'original_path': 'path/to/bad.mp3', 'error': 'some error'}
    ]
    structure = agent._generate_sound_structure(sounds_data)

    assert "sound_definitions.json" in structure
    sound_defs_content = structure["sound_definitions.json"]
    assert "sound_definitions" in sound_defs_content

    defs = sound_defs_content["sound_definitions"]
    assert "block.stone.dig" in defs
    assert "mob.pig.say" in defs

    stone_dig_event = defs["block.stone.dig"]
    assert isinstance(stone_dig_event["sounds"], list)
    assert len(stone_dig_event["sounds"]) == 2
    # Paths should be relative to sounds/ and no extension
    assert "block/stone/dig1" in stone_dig_event["sounds"]
    assert "block/stone/dig2" in stone_dig_event["sounds"]

    pig_say_event = defs["mob.pig.say"]
    assert isinstance(pig_say_event["sounds"], list)
    assert len(pig_say_event["sounds"]) == 1
    assert "mob/pig/say1" in pig_say_event["sounds"]

def test_generate_sound_structure_empty(agent: AssetConverterAgent):
    structure = agent._generate_sound_structure([])
    assert not structure # Expect empty dict

def test_generate_sound_structure_only_failed(agent: AssetConverterAgent):
    sounds_data = [
        {'success': False, 'original_path': 'path/to/bad.mp3', 'error': 'some error'}
    ]
    structure = agent._generate_sound_structure(sounds_data)
    assert not structure
