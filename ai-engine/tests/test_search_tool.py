"""
Tests for the SearchTool implementation.
"""

import pytest
import json
from unittest.mock import Mock, patch
from src.tools.search_tool import SearchTool


class TestSearchTool:
    """Test class for SearchTool functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        # Clear the singleton instance before each test
        SearchTool._instance = None

    def test_search_tool_singleton(self):
        """Test that SearchTool follows singleton pattern."""
        tool1 = SearchTool.get_instance()
        tool2 = SearchTool.get_instance()
        
        assert tool1 is tool2
        assert isinstance(tool1, SearchTool)

    def test_get_tools_returns_expected_tools(self):
        """Test that get_tools returns the correct list of tools."""
        tool = SearchTool.get_instance()
        tools = tool.get_tools()
        
        assert len(tools) == 3
        assert SearchTool.semantic_search in tools
        assert SearchTool.document_search in tools
        assert SearchTool.similarity_search in tools

    def test_semantic_search_with_string_query(self):
        """Test semantic search with a simple string query."""
        query = "test query"
        result = SearchTool.semantic_search.func(query)
        
        result_data = json.loads(result)
        assert "query" in result_data
        assert "results" in result_data
        assert "total_results" in result_data
        assert result_data["query"] == query
        assert result_data["total_results"] == len(result_data["results"])

    def test_semantic_search_with_json_query(self):
        """Test semantic search with JSON query data."""
        query_data = {
            "query": "advanced search",
            "limit": 5,
            "document_source": "test_source"
        }
        result = SearchTool.semantic_search.func(json.dumps(query_data))
        
        result_data = json.loads(result)
        assert result_data["query"] == "advanced search"
        assert result_data["total_results"] <= 5

    def test_semantic_search_empty_query(self):
        """Test semantic search with empty query returns error."""
        result = SearchTool.semantic_search.func("")
        
        result_data = json.loads(result)
        assert "error" in result_data
        assert "Query is required" in result_data["error"]

    def test_document_search_with_source(self):
        """Test document search with document source."""
        source = "test_document_source"
        result = SearchTool.document_search.func(source)
        
        result_data = json.loads(result)
        assert "document_source" in result_data
        assert "results" in result_data
        assert result_data["document_source"] == source

    def test_document_search_with_json_data(self):
        """Test document search with JSON data."""
        query_data = {
            "document_source": "complex_source",
            "content_type": "text"
        }
        result = SearchTool.document_search.func(json.dumps(query_data))
        
        result_data = json.loads(result)
        assert result_data["document_source"] == "complex_source"
        assert result_data["content_type"] == "text"

    def test_document_search_empty_source(self):
        """Test document search with empty source returns error."""
        result = SearchTool.document_search.func("")
        
        result_data = json.loads(result)
        assert "error" in result_data
        assert "Document source is required" in result_data["error"]

    def test_similarity_search_with_content(self):
        """Test similarity search with content."""
        content = "This is test content for similarity search"
        result = SearchTool.similarity_search.func(content)
        
        result_data = json.loads(result)
        assert "reference_content" in result_data
        assert "threshold" in result_data
        assert "results" in result_data
        assert result_data["threshold"] == 0.8  # default threshold

    def test_similarity_search_with_json_data(self):
        """Test similarity search with JSON data."""
        query_data = {
            "content": "Test content",
            "threshold": 0.9,
            "limit": 5
        }
        result = SearchTool.similarity_search.func(json.dumps(query_data))
        
        result_data = json.loads(result)
        assert result_data["threshold"] == 0.9
        assert result_data["total_results"] <= 5

    def test_similarity_search_empty_content(self):
        """Test similarity search with empty content returns error."""
        result = SearchTool.similarity_search.func("")
        
        result_data = json.loads(result)
        assert "error" in result_data
        assert "Content is required" in result_data["error"]

    def test_search_tool_handles_json_decode_error(self):
        """Test that SearchTool handles malformed JSON gracefully."""
        malformed_json = "{'invalid': json}"
        result = SearchTool.semantic_search.func(malformed_json)
        
        result_data = json.loads(result)
        # Should treat as simple string query
        assert result_data["query"] == malformed_json

    @patch('src.tools.search_tool.logger')
    def test_search_tool_logs_operations(self, mock_logger):
        """Test that SearchTool logs operations properly."""
        SearchTool.semantic_search.func("test query")
        
        # Check that info log was called
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]
        assert "Semantic search completed" in call_args

    def test_search_results_structure(self):
        """Test that search results have expected structure."""
        result = SearchTool.semantic_search.func("test")
        result_data = json.loads(result)
        
        assert "results" in result_data
        if result_data["results"]:
            first_result = result_data["results"][0]
            assert "id" in first_result
            assert "content" in first_result
            assert "document_source" in first_result
            assert "similarity_score" in first_result
            assert "metadata" in first_result

    @pytest.mark.asyncio
    async def test_close_method(self):
        """Test that close method works properly."""
        tool = SearchTool.get_instance()
        
        # Mock the vector_client
        tool.vector_client = Mock()
        tool.vector_client.close = Mock(return_value=None)
        
        await tool.close()
        
        # Verify close was called on vector client
        tool.vector_client.close.assert_called_once()

    def test_private_methods_return_expected_format(self):
        """Test private methods return expected data format."""
        tool = SearchTool.get_instance()
        
        # Test semantic search
        results = tool._perform_semantic_search("test query", limit=2)
        assert isinstance(results, list)
        assert len(results) <= 2
        
        # Test document search
        results = tool._search_by_document_source("test_source")
        assert isinstance(results, list)
        
        # Test similarity search
        results = tool._find_similar_documents("test content", threshold=0.5)
        assert isinstance(results, list)

    def test_error_handling_in_private_methods(self):
        """Test error handling in private methods."""
        tool = SearchTool.get_instance()
        
        # Mock an exception scenario
        with patch.object(tool, '_perform_semantic_search', side_effect=Exception("Test error")):
            result = SearchTool.semantic_search.func("test query")
            result_data = json.loads(result)
            assert "error" in result_data