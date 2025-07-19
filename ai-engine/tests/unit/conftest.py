import pytest
from unittest.mock import Mock

@pytest.fixture
def mock_audio_segment():
    """Mock audio segment."""
    return Mock()

@pytest.fixture
def agent():
    """Mock AssetConverterAgent."""
    mock_agent = Mock()


    return mock_agent

    # Mock _is_power_of_2
    mock_agent._is_power_of_2.side_effect = lambda x: (x & (x - 1) == 0) and x != 0

    # Mock _next_power_of_2
    def next_power_of_2_mock(n):
        if n == 0: return 1
        n -= 1
        n |= n >> 1
        n |= n >> 2
        n |= n >> 4
        n |= n >> 8
        n |= n >> 16
        return n + 1
    mock_agent._next_power_of_2.side_effect = next_power_of_2_mock

    # Mock _previous_power_of_2
    def previous_power_of_2_mock(n):
        if n == 0: return 0
        return 1 << (n.bit_length() - 1)
    mock_agent._previous_power_of_2.side_effect = previous_power_of_2_mock

    # Mock _generate_model_structure, _generate_sound_structure, _generate_texture_pack_structure
    mock_agent._generate_model_structure.return_value = {"geometry_files": [{"name": "model1", "converted_path": "models/block/model1.geo.json"}, {"name": "model2", "converted_path": "models/item/model2.geo.json"}]}
    mock_agent._generate_sound_structure.return_value = {"sound_definitions.json": {"format_version": "1.14.0", "sound_definitions": {"block.stone.dig": {"category": "block", "sounds": [{"name": "sounds/block/stone/dig1", "volume": 1.0}, {"name": "sounds/block/stone/dig2", "volume": 1.0}]}}}}
    mock_agent._generate_texture_pack_structure.return_value = {"pack_manifest.json": {}, "terrain_texture.json": {}} # Added terrain_texture.json


    return mock_agent

@pytest.fixture
def mock_embedding_generator(monkeypatch):
    """Mocks the EmbeddingGenerator class to prevent actual model loading."""
    mock_instance = Mock()
    mock_instance.model = Mock(model_name="mock-model")
    
    mock_instance.generate_embeddings.return_value = [[0.1, 0.2, 0.3]] # Return a list of lists for embeddings

    monkeypatch.setattr('src.utils.embedding_generator.EmbeddingGenerator', Mock(return_value=mock_instance))
    monkeypatch.setattr('src.utils.embedding_generator.SENTENCE_TRANSFORMERS_AVAILABLE', True)
    return mock_instance

@pytest.fixture
def dummy_java_block_model():
    """Dummy Java block model."""
    return "dummy_java_block_model"

@pytest.fixture
def dummy_java_rotated_block_model():
    """Dummy Java rotated block model."""
    return "dummy_java_rotated_block_model"

@pytest.fixture
def dummy_item_generated_model():
    """Dummy item generated model."""
    return "dummy_item_generated_model"

@pytest.fixture
def dummy_16x16_png():
    """Dummy 16x16 png."""
    return "dummy_16x16_png"

@pytest.fixture
def dummy_17x17_png():
    """Dummy 17x17 png."""
    return "dummy_17x17_png"

@pytest.fixture
def dummy_2048x2048_png():
    """Dummy 2048x2048 png."""
    return "dummy_2048x2048_png"

@pytest.fixture
def dummy_animated_png_with_mcmeta():
    """Dummy animated png with mcmeta."""
    return "dummy_animated_png_with_mcmeta"
