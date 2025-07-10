import pytest
from pathlib import Path
from PIL import Image
import json
from src.agents.asset_converter import AssetConverterAgent
import numpy as np # Added for MockSentenceTransformer

@pytest.fixture(scope="module")
def agent():
    """Provides an instance of the AssetConverterAgent."""
    return AssetConverterAgent()

@pytest.fixture
def tmp_path_factory(tmp_path_factory):
    """Ensures tmp_path is available if needed, though pytest's built-in tmp_path is usually per-test."""
    return tmp_path_factory

@pytest.fixture
def dummy_16x16_png(tmp_path: Path) -> str:
    file_path = tmp_path / "dummy_16x16.png"
    img = Image.new("RGBA", (16, 16), color="blue")
    img.save(file_path, "PNG")
    return str(file_path)

@pytest.fixture
def dummy_17x17_png(tmp_path: Path) -> str:
    file_path = tmp_path / "dummy_17x17.png"
    img = Image.new("RGBA", (17, 17), color="red")
    img.save(file_path, "PNG")
    return str(file_path)

@pytest.fixture
def dummy_2048x2048_png(tmp_path: Path) -> str:
    file_path = tmp_path / "dummy_2048x2048.png"
    # Create a smaller image for test speed if actual size doesn't matter beyond numbers
    img = Image.new("RGBA", (256, 256), color="green")
    # We will mock its .size property if needed, or let conversion logic use this smaller one
    # For the sake of testing the agent's resizing logic based on reported dimensions,
    # it's better to mock Image.open().size if the agent reads size before path.
    # However, the agent opens then gets size. So, we'll use a small image
    # and rely on the agent's logic to read its actual (smaller) size.
    # The test will override agent's constraints for max_resolution.
    img.save(file_path, "PNG")
    return str(file_path)

@pytest.fixture
def dummy_animated_png_with_mcmeta(tmp_path: Path):
    png_path = tmp_path / "animated_texture.png"
    mcmeta_path = tmp_path / "animated_texture.png.mcmeta"

    img = Image.new("RGBA", (16, 48), color="purple") # 16x16 frames, 3 frames vertically
    img.save(png_path, "PNG")

    mcmeta_content = {
        "animation": {
            "interpolate": False,
            "frametime": 5,
            "frames": [0, 1, 2]
        }
    }
    with open(mcmeta_path, 'w') as f:
        json.dump(mcmeta_content, f)

    return str(png_path)

@pytest.fixture
def dummy_java_block_model(tmp_path: Path) -> str:
    file_path = tmp_path / "dummy_block_model.json"
    model_content = {
        "textures": {
            "particle": "block/stone",
            "all": "block/stone"
        },
        "elements": [
            {
                "from": [0, 0, 0],
                "to": [16, 16, 16],
                "faces": {
                    "down": {"uv": [0, 0, 16, 16], "texture": "#all", "cullface": "down"},
                    "up": {"uv": [0, 0, 16, 16], "texture": "#all", "cullface": "up"},
                    "north": {"uv": [0, 0, 16, 16], "texture": "#all", "cullface": "north"},
                    "south": {"uv": [0, 0, 16, 16], "texture": "#all", "cullface": "south"},
                    "west": {"uv": [0, 0, 16, 16], "texture": "#all", "cullface": "west"},
                    "east": {"uv": [0, 0, 16, 16], "texture": "#all", "cullface": "east"}
                }
            }
        ]
    }
    with open(file_path, 'w') as f:
        json.dump(model_content, f)
    return str(file_path)

@pytest.fixture
def dummy_java_rotated_block_model(tmp_path: Path) -> str:
    file_path = tmp_path / "dummy_rotated_block_model.json"
    model_content = {
        "elements": [
            {
                "from": [4, 0, 4], "to": [12, 16, 12],
                "rotation": {"origin": [8, 8, 8], "axis": "y", "angle": 45},
                "faces": {"north": {"uv": [0,0,8,16], "texture": "#texture"}}
            }
        ]
    }
    with open(file_path, 'w') as f:
        json.dump(model_content, f)
    return str(file_path)

@pytest.fixture
def dummy_item_generated_model(tmp_path: Path) -> str:
    file_path = tmp_path / "dummy_item_generated.json"
    model_content = {
        "parent": "item/generated",
        "textures": {
            "layer0": "item/my_item_texture"
        }
    }
    with open(file_path, 'w') as f:
        json.dump(model_content, f)
    return str(file_path)

# For audio, creating actual valid files is tricky without external tools.
# We will mock pydub's loading methods for initial tests.
# If we had dummy files:
# @pytest.fixture
# def dummy_wav_audio(tmp_path: Path) -> str:
#     file_path = tmp_path / "dummy.wav"
#     # Minimal WAV file bytes (actual valid WAV needed)
#     # For now, just create an empty file, tests will need to mock AudioSegment.from_wav
#     file_path.write_bytes(b"RIFF....WAVEfmt ....")
#     return str(file_path)

# @pytest.fixture
# def dummy_ogg_audio(tmp_path: Path) -> str:
#     file_path = tmp_path / "dummy.ogg"
#     # Minimal OGG file bytes (actual valid OGG needed)
#     file_path.write_bytes(b"OggS....")
#     return str(file_path)

# Placeholder for tests that need to mock pydub AudioSegment loading
class MockAudioSegment:
    def __init__(self, duration_ms, channels=1, frame_rate=22050):
        self.duration_seconds = duration_ms / 1000.0
        self.channels = channels
        self.frame_rate = frame_rate
        # Add any other attributes or methods pydub.AudioSegment might have that your code uses

    def __len__(self):
        return int(self.duration_seconds * 1000)

    @staticmethod
    def from_wav(file_path):
        # In a real scenario, you might check file_path or return different mocks
        return MockAudioSegment(1000) # Mock 1 second duration

    @staticmethod
    def from_ogg(file_path):
        return MockAudioSegment(2000) # Mock 2 seconds duration

    def export(self, out_f, format):
        # Mock export, does nothing but satisfies the call
        return out_f

# --- Added MockSentenceTransformer and fixture ---
# Mock SentenceTransformer for tests to avoid actual model loading/downloads
class MockSentenceTransformer:
    def __init__(self, model_name_or_path):
        if model_name_or_path == "invalid-model-name": # Simulate loading failure
            raise Exception("Mock model loading failed")
        self.model_name = model_name_or_path
        self.embedding_dim = 384 # Default for all-MiniLM-L6-v2

    def encode(self, sentences, convert_to_numpy=True):
        if not sentences:
            return np.array([]) if convert_to_numpy else []

        if self.model_name == "mock-model-invalid-output": # Simulate model producing wrong type
            return ["not_an_embedding"] * len(sentences)

        embeddings = []
        for s in sentences:
            val = sum(ord(c) for c in s) % 256 # Simple hash-based deterministic 'embedding'
            embedding_vector = np.full((self.embedding_dim,), val, dtype=np.float32)
            embeddings.append(embedding_vector)

        if convert_to_numpy:
            return np.array(embeddings)
        else:
            return [e.tolist() for e in embeddings]

@pytest.fixture
def mock_sentence_transformer_fixture(monkeypatch):
    # Replace the actual SentenceTransformer with the mock in the embedding_generator module
    # Note: The path to SentenceTransformer within embedding_generator.py is crucial.
    # If EmbeddingGenerator imports it as `from sentence_transformers import SentenceTransformer`,
    # then we need to patch `src.utils.embedding_generator.SentenceTransformer`.
    monkeypatch.setattr("src.utils.embedding_generator.SentenceTransformer", MockSentenceTransformer)
    # Also patch the availability flag to True so the tests can run
    monkeypatch.setattr("src.utils.embedding_generator.SENTENCE_TRANSFORMERS_AVAILABLE", True)

# You might need to add project root to sys.path here if not handled by pytest/IDE,
# e.g., by uncommenting and adjusting the sys.path modification lines from the prompt.
# import sys
# import os
# sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
