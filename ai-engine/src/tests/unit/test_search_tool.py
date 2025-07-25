"""
Unit tests for the SearchTool implementation.
"""

import unittest
import json
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from src.tools.search_tool import SearchTool
from src.utils.config import Config
from src.tools.web_search_tool import WebSearchTool


class TestSearchTool(unittest.TestCase):
    """Test class for SearchTool functionality."""

    def setUp(self):
        """Set up test fixtures."""
        # Clear the singleton instance before each test
        SearchTool._instance = None
        
        # Mock the vector database client to avoid network calls
        self.mock_vector_client_patcher = patch('src.tools.search_tool.VectorDBClient')
        self.mock_vector_client_class = self.mock_vector_client_patcher.start()
        self.mock_vector_client = MagicMock()
        self.mock_vector_client_class.return_value = self.mock_vector_client
        
        # Setup default mock search results
        self.default_search_results = [
            {
                "id": "test_id_1",
                "content": "This is about language models and AI advancements",
                "document_source": "ai_docs.txt",
                "similarity_score": 0.92,
                "metadata": {"category": "AI"}
            },
            {
                "id": "test_id_2", 
                "content": "Minecraft Forge modding framework documentation",
                "document_source": "minecraft_docs.txt",
                "similarity_score": 0.95,
                "metadata": {"category": "Gaming"}
            },
            {
                "id": "test_id_3",
                "content": "General programming concepts",
                "document_source": "programming_docs.txt", 
                "similarity_score": 0.85,
                "metadata": {"category": "Programming"}
            }
        ]
        
        # Setup async mock for semantic search
        async def mock_semantic_search(*args, **kwargs):
            query = kwargs.get('query', args[0] if args else '')
            limit = kwargs.get('limit', 10)
            
            # Return specific results based on query
            if 'AI advancements' in query:
                return [self.default_search_results[0]] * 3  # 3 AI results
            elif 'Minecraft modding' in query:
                return [self.default_search_results[1]] * 3  # 3 Minecraft results
            else:
                return self.default_search_results[:limit]
                
        self.mock_vector_client.semantic_search = AsyncMock(side_effect=mock_semantic_search)
        
        # Also mock other async methods
        self.mock_vector_client.search_by_document_source = AsyncMock(return_value=self.default_search_results[:10])
        self.mock_vector_client.find_similar_documents = AsyncMock(return_value=self.default_search_results[:10])
        
    def tearDown(self):
        """Clean up test fixtures."""
        self.mock_vector_client_patcher.stop()

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
        
        self.assertEqual(len(tools), 7)  # Updated to match actual implementation
        self.assertIn(SearchTool.semantic_search, tools)
        self.assertIn(SearchTool.document_search, tools)
        self.assertIn(SearchTool.similarity_search, tools)
        self.assertIn(SearchTool.bedrock_api_search, tools)
        self.assertIn(SearchTool.component_lookup, tools)
        self.assertIn(SearchTool.conversion_examples, tools)
        self.assertIn(SearchTool.schema_validation_lookup, tools)

    def test_semantic_search_with_string_query(self):
        """Test semantic search with a simple string query."""
        query = "test query"
        result = asyncio.run(SearchTool.semantic_search.func(query))
        
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
        result = asyncio.run(SearchTool.semantic_search.func(json.dumps(query_data)))
        
        result_data = json.loads(result)
        self.assertEqual(result_data["query"], "advanced search")
        self.assertLessEqual(result_data["total_results"], 5)

    def test_semantic_search_empty_query(self):
        """Test semantic search with empty query returns error."""
        result = asyncio.run(SearchTool.semantic_search.func(""))
        
        result_data = json.loads(result)
        self.assertIn("error", result_data)
        self.assertIn("Query is required", result_data["error"])

    @patch.object(SearchTool, '_perform_semantic_search')
    def test_semantic_search_ai_advancements_query(self, mock_semantic_search):
        """Test semantic search with AI advancements query returns specific results."""
        # Mock the semantic search to return specific AI results
        ai_results = [self.default_search_results[0]] * 3
        mock_semantic_search.return_value = ai_results
        
        query = "AI advancements"
        result = asyncio.run(SearchTool.semantic_search.func(query))
        
        result_data = json.loads(result)
        self.assertIn("query", result_data)
        self.assertIn("results", result_data)
        self.assertEqual(result_data["query"], query)
        self.assertEqual(len(result_data["results"]), 3)  # AI advancements returns 3 results
        
        # Check that the results contain AI-related content
        if result_data["results"]:
            first_result = result_data["results"][0]
            self.assertIn("language models", first_result["content"])
            self.assertEqual(first_result["similarity_score"], 0.92)

    @patch.object(SearchTool, '_perform_semantic_search')
    def test_semantic_search_minecraft_modding_query(self, mock_semantic_search):
        """Test semantic search with Minecraft modding query returns specific results."""
        # Mock the semantic search to return specific Minecraft results
        minecraft_results = [self.default_search_results[1]] * 3
        mock_semantic_search.return_value = minecraft_results
        
        query = "Minecraft modding"
        result = asyncio.run(SearchTool.semantic_search.func(query))
        
        result_data = json.loads(result)
        self.assertIn("query", result_data)
        self.assertIn("results", result_data)
        self.assertEqual(result_data["query"], query)
        self.assertEqual(len(result_data["results"]), 3)  # Minecraft modding returns 3 results
        
        # Check that the results contain Minecraft-related content
        if result_data["results"]:
            first_result = result_data["results"][0]
            self.assertIn("Minecraft Forge", first_result["content"])
            self.assertEqual(first_result["similarity_score"], 0.95)

    def test_document_search_with_source(self):
        """Test document search with document source."""
        source = "test_document_source"
        result = asyncio.run(SearchTool.document_search.func(source))
        
        result_data = json.loads(result)
        self.assertIn("document_source", result_data)
        self.assertIn("results", result_data)
        self.assertEqual(result_data["document_source"], source)

    def test_document_search_empty_source(self):
        """Test document search with empty source returns error."""
        result = asyncio.run(SearchTool.document_search.func(""))
        
        result_data = json.loads(result)
        self.assertIn("error", result_data)
        self.assertIn("Document source is required", result_data["error"])

    def test_similarity_search_with_content(self):
        """Test similarity search with content."""
        content = "This is test content for similarity search"
        result = asyncio.run(SearchTool.similarity_search.func(content))
        
        result_data = json.loads(result)
        self.assertIn("reference_content", result_data)
        self.assertIn("threshold", result_data)
        self.assertIn("results", result_data)
        self.assertEqual(result_data["threshold"], 0.8)  # default threshold

    def test_similarity_search_empty_content(self):
        """Test similarity search with empty content returns error."""
        result = asyncio.run(SearchTool.similarity_search.func(""))
        
        result_data = json.loads(result)
        self.assertIn("error", result_data)
        self.assertIn("Content is required", result_data["error"])

    def test_search_tool_handles_json_decode_error(self):
        """Test that SearchTool handles malformed JSON gracefully."""
        malformed_json = "{'invalid': json}"
        result = asyncio.run(SearchTool.semantic_search.func(malformed_json))
        
        result_data = json.loads(result)
        # Should treat as simple string query
        self.assertEqual(result_data["query"], malformed_json)

    @patch('src.tools.search_tool.logger')
    def test_search_tool_logs_operations(self, mock_logger):
        """Test that SearchTool logs operations properly."""
        asyncio.run(SearchTool.semantic_search.func("test query"))
        
        # Check that info log was called (at least once for search completion)
        mock_logger.info.assert_called()
        # Find the call with "Semantic search completed" message
        search_completion_calls = [call for call in mock_logger.info.call_args_list 
                                   if "Semantic search completed" in str(call)]
        self.assertTrue(len(search_completion_calls) >= 1)

    def test_search_results_structure(self):
        """Test that search results have expected structure."""
        result = asyncio.run(SearchTool.semantic_search.func("test"))
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
        
        # Test semantic search (async)
        results = asyncio.run(tool._perform_semantic_search("test query", limit=2))
        self.assertIsInstance(results, list)
        self.assertLessEqual(len(results), 2)
        
        # Test document search (async)
        results = asyncio.run(tool._search_by_document_source("test_source"))
        self.assertIsInstance(results, list)
        
        # Test similarity search (async)
        results = asyncio.run(tool._find_similar_documents("test content", threshold=0.5))
        self.assertIsInstance(results, list)

    def test_error_handling_in_private_methods(self):
        """Test error handling in private methods."""
        tool = SearchTool.get_instance()
        
        # Mock an exception scenario
        with patch.object(tool, '_perform_semantic_search', side_effect=Exception("Test error")):
            result = asyncio.run(SearchTool.semantic_search.func("test query"))
            result_data = json.loads(result)
            self.assertIn("error", result_data)

    @patch.object(SearchTool, '_perform_semantic_search')
    def test_fallback_search_when_primary_fails(self, mock_primary_search):
        """Test fallback search is triggered when primary search fails."""
        # Mock primary search to return empty results
        mock_primary_search.return_value = []
        
        # Mock fallback tool
        with patch('src.tools.search_tool.importlib.import_module') as mock_import:
            mock_fallback_tool = MagicMock(spec=WebSearchTool)
            mock_fallback_tool._run.return_value = "Fallback search result"
            
            MockFallbackClass = MagicMock(return_value=mock_fallback_tool)
            mock_module = MagicMock()
            setattr(mock_module, "WebSearchTool", MockFallbackClass)
            mock_import.return_value = mock_module
            
            # Enable fallback in config
            with patch.object(Config, 'SEARCH_FALLBACK_ENABLED', True), \
                 patch.object(Config, 'FALLBACK_SEARCH_TOOL', "web_search_tool"):
                
                result = asyncio.run(SearchTool.semantic_search.func("test query"))
                result_data = json.loads(result)
                
                # Should have fallback results
                self.assertGreater(result_data["total_results"], 0)
                self.assertIn("results", result_data)
                # Check that fallback metadata is present
                if result_data["results"]:
                    self.assertEqual(result_data["results"][0]["document_source"], "fallback_search")

    @patch.object(SearchTool, '_perform_semantic_search')
    def test_no_fallback_when_disabled(self, mock_primary_search):
        """Test fallback is not triggered when disabled."""
        # Mock primary search to return empty results
        mock_primary_search.return_value = []
        
        # Disable fallback in config
        with patch.object(Config, 'SEARCH_FALLBACK_ENABLED', False):
            result = asyncio.run(SearchTool.semantic_search.func("test query"))
            result_data = json.loads(result)
            
            # Should have no results
            self.assertEqual(result_data["total_results"], 0)
            self.assertEqual(result_data["results"], [])

    @patch.object(SearchTool, '_perform_semantic_search')
    def test_fallback_handles_import_error(self, mock_primary_search):
        """Test fallback handles import errors gracefully."""
        # Mock primary search to return empty results
        mock_primary_search.return_value = []
        
        # Mock import error
        with patch('src.tools.search_tool.importlib.import_module', side_effect=ImportError("Module not found")):
            with patch.object(Config, 'SEARCH_FALLBACK_ENABLED', True), \
                 patch.object(Config, 'FALLBACK_SEARCH_TOOL', "non_existent_tool"):
                
                result = asyncio.run(SearchTool.semantic_search.func("test query"))
                result_data = json.loads(result)
                
                # Should have no results due to failed fallback
                self.assertEqual(result_data["total_results"], 0)
                self.assertEqual(result_data["results"], [])

    @patch.object(SearchTool, '_perform_semantic_search')
    def test_fallback_handles_attribute_error(self, mock_primary_search):
        """Test fallback handles missing class errors gracefully."""
        # Mock primary search to return empty results
        mock_primary_search.return_value = []
        
        # Mock attribute error (class not found)
        with patch('src.tools.search_tool.importlib.import_module') as mock_import:
            mock_module = MagicMock()
            mock_import.return_value = mock_module
            
            # Mock getattr to raise AttributeError
            with patch('src.tools.search_tool.getattr', side_effect=AttributeError("Class not found")):
                with patch.object(Config, 'SEARCH_FALLBACK_ENABLED', True), \
                     patch.object(Config, 'FALLBACK_SEARCH_TOOL', "invalid_tool"):
                    
                    result = asyncio.run(SearchTool.semantic_search.func("test query"))
                    result_data = json.loads(result)
                    
                    # Should have no results due to failed fallback
                    self.assertEqual(result_data["total_results"], 0)
                    self.assertEqual(result_data["results"], [])

    def test_fallback_search_method_exists(self):
        """Test that the fallback search method exists and is callable."""
        tool = SearchTool.get_instance()
        self.assertTrue(hasattr(tool, '_attempt_fallback_search'))
        self.assertTrue(callable(getattr(tool, '_attempt_fallback_search')))

    @patch.object(SearchTool, '_search_by_document_source')
    def test_document_search_fallback(self, mock_document_search):
        """Test fallback works for document search."""
        # Mock document search to return empty results
        mock_document_search.return_value = []
        
        # Mock fallback tool
        with patch('src.tools.search_tool.importlib.import_module') as mock_import:
            mock_fallback_tool = MagicMock(spec=WebSearchTool)
            mock_fallback_tool._run.return_value = "Fallback document search result"
            
            MockFallbackClass = MagicMock(return_value=mock_fallback_tool)
            mock_module = MagicMock()
            setattr(mock_module, "WebSearchTool", MockFallbackClass)
            mock_import.return_value = mock_module
            
            # Enable fallback in config
            with patch.object(Config, 'SEARCH_FALLBACK_ENABLED', True), \
                 patch.object(Config, 'FALLBACK_SEARCH_TOOL', "web_search_tool"):
                
                result = asyncio.run(SearchTool.document_search.func("test_source"))
                result_data = json.loads(result)
                
                # Should have fallback results
                self.assertGreater(result_data["total_results"], 0)

    @patch.object(SearchTool, '_find_similar_documents')
    def test_similarity_search_fallback(self, mock_similarity_search):
        """Test fallback works for similarity search."""
        # Mock similarity search to return empty results
        mock_similarity_search.return_value = []
        
        # Mock fallback tool
        with patch('src.tools.search_tool.importlib.import_module') as mock_import:
            mock_fallback_tool = MagicMock(spec=WebSearchTool)
            mock_fallback_tool._run.return_value = "Fallback similarity search result"
            
            MockFallbackClass = MagicMock(return_value=mock_fallback_tool)
            mock_module = MagicMock()
            setattr(mock_module, "WebSearchTool", MockFallbackClass)
            mock_import.return_value = mock_module
            
            # Enable fallback in config
            with patch.object(Config, 'SEARCH_FALLBACK_ENABLED', True), \
                 patch.object(Config, 'FALLBACK_SEARCH_TOOL', "web_search_tool"):
                
                result = asyncio.run(SearchTool.similarity_search.func("test content"))
                result_data = json.loads(result)
                
                # Should have fallback results
                self.assertGreater(result_data["total_results"], 0)

    def test_document_source_filtering(self):
        """Test that document source filtering works correctly."""
        tool = SearchTool.get_instance()
        
        # Test with a document source that should be filtered (now async)
        results = asyncio.run(tool._perform_semantic_search("test query", document_source="specific_source"))
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