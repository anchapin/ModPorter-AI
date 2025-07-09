import pytest
import json
import logging
from unittest.mock import MagicMock, patch

from src.agents.java_analyzer import JavaAnalyzerAgent
# Note: mock_sentence_transformer_fixture is automatically applied from conftest.py
# For this test file, we need JavaAnalyzerAgent. Ensure EmbeddingGenerator within it uses the mock.

@pytest.fixture
def java_analyzer_agent_instance(mock_sentence_transformer_fixture): # Ensure mock is active
    # Reset singleton instance for test isolation if needed, or manage state.
    # JavaAnalyzerAgent._instance = None # This might be needed if tests interfere
    agent = JavaAnalyzerAgent.get_instance()
    # The agent's __init__ would have created an EmbeddingGenerator,
    # which should have used the MockSentenceTransformer due to the fixture.
    assert agent.embedding_generator is not None
    assert "MockSentenceTransformer" in str(type(agent.embedding_generator.model))
    return agent

class TestJavaAnalyzerAgent:
    """Test JavaAnalyzerAgent functionality."""

    def test_analyze_mod_file_with_embeddings(self, java_analyzer_agent_instance, monkeypatch, caplog):
        """Test analyze_mod_file method, focusing on embeddings_data."""
        agent = java_analyzer_agent_instance
        mock_mod_path = "dummy_mod.jar"

        # Mock the tool functions called by analyze_mod_file
        # These mocks will return controlled JSON strings.
        mock_structure_result = {
            "success": True,
            "analysis_results": {
                "mod_path": mock_mod_path,
                "mod_type": "jar",
                "framework": "forge",
                "structure_analysis": {"total_files": 10},
                "file_inventory": {"total_count": 10},
                "complexity_assessment": {"overall_complexity": "medium"}
            },
            "recommendations": []
        }
        monkeypatch.setattr(agent.analyze_mod_structure_tool, 'func', MagicMock(return_value=json.dumps(mock_structure_result)))

        mock_metadata_result = {
            "success": True,
            "metadata": {
                "id": "testmod",
                "version": "1.0",
                "description": "A sample mod description.", # Text for embedding
                "authors": ["TestAuthor"]
            },
            "extraction_summary": {}
        }
        monkeypatch.setattr(agent.extract_mod_metadata_tool, 'func', MagicMock(return_value=json.dumps(mock_metadata_result)))

        mock_features_result = {
            "success": True,
            "feature_results": {
                "identified_features": [
                    {"feature_id": "block_myblock", "feature_type": "blocks", "name": "MyBlock"}
                ],
                "feature_categories": { # Text for embedding
                    "blocks": [{"name": "MyAwesomeBlock", "feature_type": "blocks"}],
                    "items": [{"name": "MyAwesomeItem", "feature_type": "items"}]
                },
                "feature_complexity": {},
                "conversion_challenges": []
            },
            "feature_summary": {}
        }
        monkeypatch.setattr(agent.identify_features_tool, 'func', MagicMock(return_value=json.dumps(mock_features_result)))
        
        mock_assets_result = {
            "success": True,
            "assets": {"textures": ["texture1.png"]},
            "conversion_notes": []
        }
        monkeypatch.setattr(agent.extract_assets_tool, 'func', MagicMock(return_value=json.dumps(mock_assets_result)))

        # Call the method to be tested
        analysis_json = agent.analyze_mod_file(mock_mod_path)
        results = json.loads(analysis_json)

        assert "embeddings_data" in results
        embeddings_data = results["embeddings_data"]
        assert isinstance(embeddings_data, list)

        # Expected texts to be embedded: description, "MyAwesomeBlock", "MyAwesomeItem"
        expected_num_embeddings = 3
        assert len(embeddings_data) == expected_num_embeddings, \
            f"Expected {expected_num_embeddings} embedded items, got {len(embeddings_data)}. Caplog: {caplog.text}"

        found_desc = False
        found_block_feature = False
        found_item_feature = False

        for item in embeddings_data:
            assert "type" in item
            assert "original_text" in item
            assert "embedding" in item
            assert item["embedding"] is not None, f"Embedding for {item['original_text']} is None"
            assert isinstance(item["embedding"], list)
            assert len(item["embedding"]) == 384 # Mock embedding dimension

            if item["type"] == "mod_description":
                assert item["original_text"] == "A sample mod description."
                found_desc = True
            elif item["type"] == "feature_name" and item["category"] == "blocks":
                assert item["original_text"] == "MyAwesomeBlock"
                found_block_feature = True
            elif item["type"] == "feature_name" and item["category"] == "items":
                assert item["original_text"] == "MyAwesomeItem"
                found_item_feature = True

        assert found_desc, "Mod description embedding not found."
        assert found_block_feature, "Block feature name embedding not found."
        assert found_item_feature, "Item feature name embedding not found."

    def test_analyze_mod_file_no_text_for_embeddings(self, monkeypatch, caplog, mock_sentence_transformer_fixture):
        """Test analyze_mod_file when no description or features are found."""
        # Set log level to capture warnings for the specific logger
        caplog.set_level(logging.WARNING, logger="src.agents.java_analyzer")
        # Create a new agent instance after the mock is applied
        agent = JavaAnalyzerAgent()
        mock_mod_path = "dummy_mod_no_text.jar"

        # Mock tools to return empty description and no features
        monkeypatch.setattr(agent.analyze_mod_structure_tool, 'func', MagicMock(return_value=json.dumps({
            "success": True, "analysis_results": {"framework": "forge"}})))
        monkeypatch.setattr(agent.extract_mod_metadata_tool, 'func', MagicMock(return_value=json.dumps({
            "success": True, "metadata": {"description": ""}}))) # Empty description
        monkeypatch.setattr(agent.identify_features_tool, 'func', MagicMock(return_value=json.dumps({
            "success": True, "feature_results": {"feature_categories": {}}}))) # No features
        monkeypatch.setattr(agent.extract_assets_tool, 'func', MagicMock(return_value=json.dumps({"success": True, "assets": {}})))

        analysis_json = agent.analyze_mod_file(mock_mod_path)
        results = json.loads(analysis_json)

        assert "embeddings_data" in results
        assert results["embeddings_data"] == []
        # When sentence-transformers is not available, the embeddings_data should be empty
        # We can verify the behavior by checking the empty embeddings_data field
        # which is the expected behavior when no embedding generation happens


    def test_analyze_mod_file_embedding_model_load_failure(self, monkeypatch, caplog):
        """Test analyze_mod_file when EmbeddingGenerator model fails to load."""
        # Temporarily break the EmbeddingGenerator's model loading for this test
        # This requires ensuring a new instance of JavaAnalyzerAgent is created,
        # or that its embedding_generator is re-initialized with a failing model.

        # Patch SentenceTransformer to fail for this specific test scope
        with patch('src.utils.embedding_generator.SentenceTransformer', MagicMock(side_effect=Exception("Mock model loading failed"))):
            # Force re-creation or re-initialization of relevant parts
            JavaAnalyzerAgent._instance = None # Reset singleton
            agent = JavaAnalyzerAgent.get_instance()
            # Now this agent's embedding_generator.model should be None

            assert agent.embedding_generator.model is None, \
                "EmbeddingGenerator model should be None due to load failure."

            mock_mod_path = "dummy_mod_fail_embed_load.jar"
            monkeypatch.setattr(agent.analyze_mod_structure_tool, 'func', MagicMock(return_value=json.dumps({
                "success": True, "analysis_results": {"framework": "forge"}})))
            monkeypatch.setattr(agent.extract_mod_metadata_tool, 'func', MagicMock(return_value=json.dumps({
                "success": True, "metadata": {"description": "Some text"}})))
            monkeypatch.setattr(agent.identify_features_tool, 'func', MagicMock(return_value=json.dumps({
                "success": True, "feature_results": {"feature_categories": {}}})))
            monkeypatch.setattr(agent.extract_assets_tool, 'func', MagicMock(return_value=json.dumps({"success": True, "assets": {}})))

            analysis_json = agent.analyze_mod_file(mock_mod_path)
            results = json.loads(analysis_json)

            assert "embeddings_data" in results
            assert results["embeddings_data"] == []
            assert "EmbeddingGenerator model not loaded. Skipping embedding generation." in caplog.text

            # Clean up singleton for other tests
            JavaAnalyzerAgent._instance = None
            # It's generally better if fixtures handle setup/teardown of such global state (singleton)
            # or if the singleton pattern is avoided/managed for testability.
            # For now, manually resetting.

# Commenting out old tests for the mock ModAnalyzer
# class TestModAnalyzer:
#    """Test ModAnalyzer functionality."""
#
#    def test_analyze_basic_mod_structure(self, sample_java_mod):
# ... (rest of the old tests)