"""
Unit tests for the SearchTool implementation.
"""

import unittest
import json
from unittest.mock import Mock, patch
from src.tools.search_tool import SearchTool


class TestSearchTool(unittest.TestCase):
    """Test class for SearchTool functionality."""

    def setUp(self):
        """Set up test fixtures."""
        # Clear the singleton instance before each test
        SearchTool._instance = None

    def test_search_tool_singleton(self):
        """Test that SearchTool follows singleton pattern."""
        tool1 = SearchTool.get_instance()
        tool2 = SearchTool.get_instance()
        
        self.assertIs(tool1, tool2)
        self.assertIsInstance(tool1, SearchTool)

    def test_get_tools_returns_expected_tools(self):
        """Test that get_tools returns the correct list of tools."""
        tool = SearchTool.get_instance()
        tools = tool.get_tools()
        
        self.assertEqual(len(tools), 3)
        self.assertIn(SearchTool.semantic_search, tools)
        self.assertIn(SearchTool.document_search, tools)
        self.assertIn(SearchTool.similarity_search, tools)

    def test_semantic_search_with_string_query(self):
        """Test semantic search with a simple string query."""
        query = "test query"
        result = SearchTool.semantic_search.func(query)
        
        result_data = json.loads(result)
        self.assertIn("query", result_data)
        self.assertIn("results", result_data)
        self.assertIn("total_results", result_data)
        self.assertEqual(result_data["query"], query)
        self.assertEqual(result_data["total_results"], len(result_data["results"]))

    def test_semantic_search_with_json_query(self):
        """Test semantic search with JSON query data."""
        query_data = {
            "query": "advanced search",
            "limit": 5,
            "document_source": "test_source"
        }
        result = SearchTool.semantic_search.func(json.dumps(query_data))
        
        result_data = json.loads(result)
        self.assertEqual(result_data["query"], "advanced search")
        self.assertLessEqual(result_data["total_results"], 5)

    def test_semantic_search_empty_query(self):
        """Test semantic search with empty query returns error."""
        result = SearchTool.semantic_search.func("")
        
        result_data = json.loads(result)
        self.assertIn("error", result_data)
        self.assertIn("Query is required", result_data["error"])

    def test_semantic_search_ai_advancements_query(self):
        """Test semantic search with AI advancements query returns specific results."""
        query = "AI advancements"
        result = SearchTool.semantic_search.func(query)
        
        result_data = json.loads(result)
        self.assertIn("query", result_data)
        self.assertIn("results", result_data)
        self.assertEqual(result_data["query"], query)
        self.assertEqual(len(result_data["results"]), 3)  # AI advancements returns 3 results
        
        # Check that the results contain AI-related content
        first_result = result_data["results"][0]
        self.assertIn("language models", first_result["content"])
        self.assertEqual(first_result["similarity_score"], 0.92)

    def test_semantic_search_minecraft_modding_query(self):
        """Test semantic search with Minecraft modding query returns specific results."""
        query = "Minecraft modding"
        result = SearchTool.semantic_search.func(query)
        
        result_data = json.loads(result)
        self.assertIn("query", result_data)
        self.assertIn("results", result_data)
        self.assertEqual(result_data["query"], query)
        self.assertEqual(len(result_data["results"]), 3)  # Minecraft modding returns 3 results
        
        # Check that the results contain Minecraft-related content
        first_result = result_data["results"][0]
        self.assertIn("Minecraft Forge", first_result["content"])
        self.assertEqual(first_result["similarity_score"], 0.95)

    def test_document_search_with_source(self):
        """Test document search with document source."""
        source = "test_document_source"
        result = SearchTool.document_search.func(source)
        
        result_data = json.loads(result)
        self.assertIn("document_source", result_data)
        self.assertIn("results", result_data)
        self.assertEqual(result_data["document_source"], source)

    def test_document_search_empty_source(self):
        """Test document search with empty source returns error."""
        result = SearchTool.document_search.func("")
        
        result_data = json.loads(result)
        self.assertIn("error", result_data)
        self.assertIn("Document source is required", result_data["error"])

    def test_similarity_search_with_content(self):
        """Test similarity search with content."""
        content = "This is test content for similarity search"
        result = SearchTool.similarity_search.func(content)
        
        result_data = json.loads(result)
        self.assertIn("reference_content", result_data)
        self.assertIn("threshold", result_data)
        self.assertIn("results", result_data)
        self.assertEqual(result_data["threshold"], 0.8)  # default threshold

    def test_similarity_search_empty_content(self):
        """Test similarity search with empty content returns error."""
        result = SearchTool.similarity_search.func("")
        
        result_data = json.loads(result)
        self.assertIn("error", result_data)
        self.assertIn("Content is required", result_data["error"])

    def test_search_tool_handles_json_decode_error(self):
        """Test that SearchTool handles malformed JSON gracefully."""
        malformed_json = "{'invalid': json}"
        result = SearchTool.semantic_search.func(malformed_json)
        
        result_data = json.loads(result)
        # Should treat as simple string query
        self.assertEqual(result_data["query"], malformed_json)

    @patch('src.tools.search_tool.logger')
    def test_search_tool_logs_operations(self, mock_logger):
        """Test that SearchTool logs operations properly."""
        SearchTool.semantic_search.func("test query")
        
        # Check that info log was called (at least once for search completion)
        mock_logger.info.assert_called()
        # Find the call with "Semantic search completed" message
        search_completion_calls = [call for call in mock_logger.info.call_args_list 
                                   if "Semantic search completed" in str(call)]
        self.assertTrue(len(search_completion_calls) >= 1)

    def test_search_results_structure(self):
        """Test that search results have expected structure."""
        result = SearchTool.semantic_search.func("test")
        result_data = json.loads(result)
        
        self.assertIn("results", result_data)
        if result_data["results"]:
            first_result = result_data["results"][0]
            self.assertIn("id", first_result)
            self.assertIn("content", first_result)
            self.assertIn("document_source", first_result)
            self.assertIn("similarity_score", first_result)
            self.assertIn("metadata", first_result)

    def test_private_methods_return_expected_format(self):
        """Test private methods return expected data format."""
        tool = SearchTool.get_instance()
        
        # Test semantic search
        results = tool._perform_semantic_search("test query", limit=2)
        self.assertIsInstance(results, list)
        self.assertLessEqual(len(results), 2)
        
        # Test document search
        results = tool._search_by_document_source("test_source")
        self.assertIsInstance(results, list)
        
        # Test similarity search
        results = tool._find_similar_documents("test content", threshold=0.5)
        self.assertIsInstance(results, list)

    def test_error_handling_in_private_methods(self):
        """Test error handling in private methods."""
        tool = SearchTool.get_instance()
        
        # Mock an exception scenario
        with patch.object(tool, '_perform_semantic_search', side_effect=Exception("Test error")):
            result = SearchTool.semantic_search.func("test query")
            result_data = json.loads(result)
            self.assertIn("error", result_data)

    def test_document_source_filtering(self):
        """Test that document source filtering works correctly."""
        tool = SearchTool.get_instance()
        
        # Test with a document source that should be filtered
        results = tool._perform_semantic_search("test query", document_source="specific_source")
        self.assertIsInstance(results, list)
        
        # In the generic case, results should be filtered
        if results:
            for result in results:
                self.assertIn("specific_source", result.get("document_source", ""))

    def test_search_tool_initialization(self):
        """Test SearchTool initialization and vector client setup."""
        tool = SearchTool.get_instance()
        
        # Check that the tool has the necessary attributes
        self.assertTrue(hasattr(tool, 'vector_client'))
        self.assertTrue(hasattr(tool, 'get_tools'))
        self.assertTrue(hasattr(tool, '_perform_semantic_search'))
        self.assertTrue(hasattr(tool, '_search_by_document_source'))
        self.assertTrue(hasattr(tool, '_find_similar_documents'))

    def test_search_tool_close_method(self):
        """Test SearchTool close method."""
        tool = SearchTool.get_instance()
        
        # Test that close method exists and can be called
        self.assertTrue(hasattr(tool, 'close'))
        # Since this is an async method, we can't directly test it here
        # but we can verify it exists and is callable


if __name__ == '__main__':
    unittest.main()