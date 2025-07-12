import pytest
import json
from unittest.mock import MagicMock, patch

from src.agents.java_analyzer import JavaAnalyzerAgent
# Note: mock_sentence_transformer_fixture is automatically applied from conftest.py
# For this test file, we need JavaAnalyzerAgent. Ensure EmbeddingGenerator within it uses the mock.

@pytest.fixture
def java_analyzer_agent_instance(mock_sentence_transformer_fixture): # Ensure mock is active
    # Reset singleton instance for test isolation if needed, or manage state.
    JavaAnalyzerAgent._instance = None # This might be needed if tests interfere
    agent = JavaAnalyzerAgent.get_instance()
    # The agent's __init__ would have created an EmbeddingGenerator,
    # which should have used the MockSentenceTransformer due to the fixture.
    assert agent.embedding_generator is not None
    assert "MockSentenceTransformer" in str(type(agent.embedding_generator.model))
    return agent

class TestJavaAnalyzerAgent:
    """Test JavaAnalyzerAgent functionality."""

    def test_analyze_mod_file_with_fabric_mod(self, java_analyzer_agent_instance, tmp_path):
        """Test analyze_mod_file method with a real fabric mod file."""
        import zipfile
        
        agent = java_analyzer_agent_instance
        
        # Create a realistic fabric mod JAR file
        mod_file = tmp_path / "testmod.jar"
        with zipfile.ZipFile(mod_file, 'w') as zf:
            # Add fabric.mod.json
            fabric_manifest = {
                "schemaVersion": 1,
                "id": "testmod",
                "version": "1.0.0",
                "name": "TestMod",
                "description": "A test mod for unit testing",
                "authors": ["TestAuthor"],
                "environment": "*",
                "depends": {
                    "minecraft": "1.19.4",
                    "fabricloader": ">=0.14.0"
                }
            }
            zf.writestr("fabric.mod.json", json.dumps(fabric_manifest))
            
            # Add some assets
            zf.writestr("assets/testmod/textures/block/test_block.png", "fake_png_data")
            zf.writestr("assets/testmod/textures/item/test_item.png", "fake_png_data")
            zf.writestr("assets/testmod/models/block/test_block.json", '{"parent": "block/cube_all"}')
            zf.writestr("assets/testmod/sounds/test_sound.ogg", "fake_ogg_data")
            
            # Add some Java source files (even though they won't be parsed)
            zf.writestr("com/example/testmod/TestMod.java", "public class TestMod {}")
        
        # Call the method to be tested
        analysis_json = agent.analyze_mod_file(str(mod_file))
        results = json.loads(analysis_json)
        
        # Verify the basic structure
        assert "mod_info" in results
        assert "assets" in results
        assert "features" in results
        assert "structure" in results
        assert "metadata" in results
        assert "errors" in results
        assert "embeddings_data" in results
        
        # Verify mod info extraction
        mod_info = results["mod_info"]
        assert mod_info["name"] == "testmod"
        assert mod_info["framework"] == "fabric"
        assert mod_info["version"] == "1.0.0"
        
        # Verify assets analysis
        assets = results["assets"]
        assert "textures" in assets
        assert "models" in assets
        assert "sounds" in assets
        assert len(assets["textures"]) == 2  # test_block.png, test_item.png
        assert len(assets["models"]) == 1    # test_block.json
        assert len(assets["sounds"]) == 1    # test_sound.ogg
        
        # Verify structure analysis
        structure = results["structure"]
        assert structure["type"] == "jar"
        assert structure["files"] > 0
        
        # Verify no errors
        assert len(results["errors"]) == 0

    def test_analyze_mod_file_with_invalid_file(self, java_analyzer_agent_instance):
        """Test analyze_mod_file when file doesn't exist."""
        agent = java_analyzer_agent_instance
        nonexistent_file = "/path/to/nonexistent/file.jar"
        
        # Call the method with non-existent file
        analysis_json = agent.analyze_mod_file(nonexistent_file)
        results = json.loads(analysis_json)
        
        # Verify error handling
        assert "mod_info" in results
        assert "errors" in results
        assert len(results["errors"]) > 0
        assert "embeddings_data" in results
        assert results["embeddings_data"] == []


    def test_analyze_mod_file_embedding_model_load_failure(self, caplog, tmp_path):
        """Test analyze_mod_file when EmbeddingGenerator model fails to load."""
        import zipfile

        # Patch both the availability flag and SentenceTransformer to fail for this specific test scope
        with patch('src.utils.embedding_generator.SENTENCE_TRANSFORMERS_AVAILABLE', True), \
             patch('src.utils.embedding_generator.SentenceTransformer', MagicMock(side_effect=Exception("Mock model loading failed"))):
            # Force re-creation of JavaAnalyzerAgent with failed embedding model
            JavaAnalyzerAgent._instance = None # Reset singleton
            agent = JavaAnalyzerAgent.get_instance()
            # Now this agent's embedding_generator.model should be None

            assert agent.embedding_generator.model is None, \
                "EmbeddingGenerator model should be None due to load failure."

            # Create a real test JAR file that will succeed in analysis but fail in embedding
            mod_file = tmp_path / "testmod_fail_embed.jar"
            with zipfile.ZipFile(mod_file, 'w') as zf:
                # Add fabric.mod.json
                fabric_manifest = {
                    "schemaVersion": 1,
                    "id": "testmod_fail_embed",
                    "version": "1.0.0",
                    "name": "TestMod Fail Embed",
                    "description": "A test mod for embedding failure testing",
                    "authors": ["TestAuthor"],
                    "environment": "*"
                }
                zf.writestr("fabric.mod.json", json.dumps(fabric_manifest))
                # Add some assets
                zf.writestr("assets/testmod/textures/block/test_block.png", "fake_png_data")

            # Call the method - should work but skip embeddings
            analysis_json = agent.analyze_mod_file(str(mod_file))
            results = json.loads(analysis_json)

            # Verify basic analysis worked
            assert "mod_info" in results
            assert "embeddings_data" in results
            assert results["embeddings_data"] == []

            # Verify the embedding failure was logged during EmbeddingGenerator initialization
            assert "Failed to load SentenceTransformer model 'all-MiniLM-L6-v2': Mock model loading failed" in caplog.text

            # Clean up singleton for other tests
            JavaAnalyzerAgent._instance = None

# Commenting out old tests for the mock ModAnalyzer
# class TestModAnalyzer:
#    """Test ModAnalyzer functionality."""
#
#    def test_analyze_basic_mod_structure(self, sample_java_mod):
# ... (rest of the old tests)