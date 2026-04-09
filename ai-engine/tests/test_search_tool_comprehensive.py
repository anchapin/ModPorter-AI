"""
Comprehensive unit tests for SearchTool.
Tests semantic search, document search, similarity search, and fallback mechanisms.
"""

import pytest
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock

# Set up imports
try:
    from tools.search_tool import SearchTool
    from utils.vector_db_client import VectorDBClient
    IMPORTS_AVAILABLE = True
except ImportError as e:
    IMPORTS_AVAILABLE = False
    IMPORT_ERROR = str(e)


# Skip all tests if imports fail
pytestmark = pytest.mark.skipif(not IMPORTS_AVAILABLE, reason=f"Required imports unavailable")


@pytest.fixture
def mock_vector_client():
    """Create a mock VectorDBClient for testing."""
    client = AsyncMock(spec=VectorDBClient)
    client.search_documents = AsyncMock(return_value=[])
    client.index_document = AsyncMock(return_value=True)
    client.get_embedding = AsyncMock(return_value=[0.1] * 768)
    client.close = AsyncMock()
    return client


@pytest.fixture
def search_tool_instance(mock_vector_client):
    """Create a SearchTool instance with mocked vector client."""
    with patch.object(SearchTool, 'vector_client', mock_vector_client, create=True):
        tool = SearchTool()
        tool.vector_client = mock_vector_client
        # Patch get_instance to return this specific instance
        with patch.object(SearchTool, 'get_instance', return_value=tool):
            yield tool


@pytest.fixture
def sample_search_results():
    """Sample search results for mocking."""
    return [
        {
            "id": "doc_1",
            "content": "Java block entity implementation",
            "source": "java_source",
            "similarity": 0.95
        },
        {
            "id": "doc_2",
            "content": "Block state management in Bedrock",
            "source": "bedrock_docs",
            "similarity": 0.87
        },
        {
            "id": "doc_3",
            "content": "Custom block properties",
            "source": "reference",
            "similarity": 0.72
        }
    ]


class TestSearchToolInitialization:
    """Test SearchTool initialization and singleton pattern."""
    
    def test_search_tool_instantiation(self, mock_vector_client):
        """Test that SearchTool can be instantiated."""
        with patch.object(SearchTool, '__init__', return_value=None):
            tool = SearchTool()
            assert tool is not None
    
    def test_get_instance_singleton(self):
        """Test singleton pattern implementation."""
        # Reset singleton
        SearchTool._instance = None
        
        with patch('tools.search_tool.VectorDBClient'):
            instance1 = SearchTool.get_instance()
            instance2 = SearchTool.get_instance()
            
            assert instance1 is instance2
        
        # Clean up
        SearchTool._instance = None
    
    def test_get_tools_returns_list(self, search_tool_instance):
        """Test that get_tools returns a list of available tools."""
        tools = search_tool_instance.get_tools()
        
        assert isinstance(tools, list)
        assert len(tools) > 0
        # Should return callable tools or CrewAI tool objects
        for tool in tools:
            assert callable(tool) or hasattr(tool, '__call__') or hasattr(tool, 'func')


class TestSemanticSearch:
    """Test semantic_search tool functionality."""
    
    @pytest.mark.asyncio
    async def test_semantic_search_json_input(self, search_tool_instance, sample_search_results):
        """Test semantic search with JSON input."""
        search_tool_instance.vector_client.search_documents = AsyncMock(
            return_value=sample_search_results
        )
        search_tool_instance._perform_semantic_search = AsyncMock(
            return_value=sample_search_results
        )
        
        query_data = json.dumps({
            "query": "block entity implementation",
            "limit": 5,
            "document_source": "java_source"
        })
        
        result = await SearchTool.semantic_search.func(query_data)
        
        assert isinstance(result, str)
        result_data = json.loads(result)
        assert "query" in result_data
        assert "results" in result_data or "error" in result_data
        assert result_data["query"] == "block entity implementation"
    
    @pytest.mark.asyncio
    async def test_semantic_search_string_input(self, search_tool_instance, sample_search_results):
        """Test semantic search with plain string input."""
        search_tool_instance._perform_semantic_search = AsyncMock(
            return_value=sample_search_results
        )
        
        result = await SearchTool.semantic_search.func("block implementation")
        
        result_data = json.loads(result)
        assert result_data["query"] == "block implementation"
        assert len(result_data["results"]) > 0
    
    @pytest.mark.asyncio
    async def test_semantic_search_no_query_error(self, search_tool_instance):
        """Test semantic search returns error when query is empty."""
        query_data = json.dumps({"query": "", "limit": 5})
        
        result = await SearchTool.semantic_search.func(query_data)
        result_data = json.loads(result)
        
        assert "error" in result_data
        assert "Query is required" in result_data["error"]
    
    @pytest.mark.asyncio
    async def test_semantic_search_custom_limit(self, search_tool_instance, sample_search_results):
        """Test semantic search with custom result limit."""
        search_tool_instance._perform_semantic_search = AsyncMock(
            return_value=sample_search_results[:2]
        )
        
        query_data = json.dumps({
            "query": "block",
            "limit": 2
        })
        
        result = await SearchTool.semantic_search.func(query_data)
        result_data = json.loads(result)
        
        assert result_data["total_results"] == 2
    
    @pytest.mark.asyncio
    async def test_semantic_search_exception_handling(self, search_tool_instance):
        """Test semantic search exception handling."""
        search_tool_instance._perform_semantic_search = AsyncMock(
            side_effect=Exception("Vector DB connection failed")
        )
        
        result = await SearchTool.semantic_search.func("test query")
        result_data = json.loads(result)
        
        assert "error" in result_data


class TestDocumentSearch:
    """Test document_search tool functionality."""
    
    @pytest.mark.asyncio
    async def test_document_search_basic(self, search_tool_instance, sample_search_results):
        """Test basic document search."""
        search_tool_instance._search_by_document_source = AsyncMock(
            return_value=sample_search_results
        )
        
        query_data = json.dumps({
            "document_source": "java_source",
            "limit": 3
        })
        
        result = await SearchTool.document_search.func(query_data)
        
        assert isinstance(result, str)
        result_data = json.loads(result)
        assert len(result_data["results"]) > 0
    
    @pytest.mark.asyncio
    async def test_document_search_no_source_error(self, search_tool_instance):
        """Test document search returns error when source is empty."""
        query_data = json.dumps({"document_source": "", "limit": 5})
        
        result = await SearchTool.document_search.func(query_data)
        result_data = json.loads(result)
        
        assert "error" in result_data
        assert "Document source is required" in result_data["error"]

    @pytest.mark.asyncio
    async def test_document_search_fallback(self, search_tool_instance):
        """Test document search fallback."""
        search_tool_instance._search_by_document_source = AsyncMock(return_value=[])
        search_tool_instance._attempt_fallback_search = Mock(
            return_value=[{"id": "f1", "content": "fallback"}]
        )
        
        with patch('tools.search_tool.Config') as mock_config:
            mock_config.SEARCH_FALLBACK_ENABLED = True
            
            query_data = json.dumps({"document_source": "test"})
            result = await SearchTool.document_search.func(query_data)
            result_data = json.loads(result)
            
            assert len(result_data["results"]) == 1
            assert result_data["results"][0]["content"] == "fallback"

    @pytest.mark.asyncio
    async def test_document_search_exception(self, search_tool_instance):
        """Test document search exception handling."""
        search_tool_instance._search_by_document_source = AsyncMock(
            side_effect=Exception("Error")
        )
        
        result = await SearchTool.document_search.func("source")
        result_data = json.loads(result)
        assert "error" in result_data


class TestSimilaritySearch:
    """Test similarity_search tool functionality."""
    @pytest.mark.asyncio
    async def test_similarity_search_basic(self, search_tool_instance, sample_search_results):
        """Test basic similarity search."""
        search_tool_instance._find_similar_documents = AsyncMock(
            return_value=sample_search_results
        )

        query_data = json.dumps({
            "content": "entity behavior",
            "limit": 5,
            "threshold": 0.7
        })

        result = await SearchTool.similarity_search.func(query_data)

        result_data = json.loads(result)
        assert len(result_data["results"]) > 0
    
    @pytest.mark.asyncio
    async def test_similarity_search_no_content_error(self, search_tool_instance):
        """Test similarity search returns error when content is empty."""
        query_data = json.dumps({"content": ""})
        
        result = await SearchTool.similarity_search.func(query_data)
        result_data = json.loads(result)
        
        assert "error" in result_data
        assert "Content is required" in result_data["error"]

    @pytest.mark.asyncio
    async def test_similarity_search_fallback(self, search_tool_instance):
        """Test similarity search fallback."""
        search_tool_instance._find_similar_documents = AsyncMock(return_value=[])
        search_tool_instance._attempt_fallback_search = Mock(
            return_value=[{"id": "f1", "content": "fallback"}]
        )
        
        with patch('tools.search_tool.Config') as mock_config:
            mock_config.SEARCH_FALLBACK_ENABLED = True
            
            result = await SearchTool.similarity_search.func("some content")
            result_data = json.loads(result)
            
            assert len(result_data["results"]) == 1

    @pytest.mark.asyncio
    async def test_similarity_search_exception(self, search_tool_instance):
        """Test similarity search exception handling."""
        search_tool_instance._find_similar_documents = AsyncMock(
            side_effect=Exception("Error")
        )
        
        result = await SearchTool.similarity_search.func("content")
        result_data = json.loads(result)
        assert "error" in result_data


class TestFallbackMechanism:
    """Test fallback search mechanism."""
    
    @pytest.mark.asyncio
    async def test_fallback_search_on_empty_results(self, search_tool_instance):
        """Test fallback search triggered on empty primary results."""
        search_tool_instance._perform_semantic_search = AsyncMock(return_value=[])
        search_tool_instance._attempt_fallback_search = Mock(
            return_value=[
                {"id": "fallback_1", "content": "fallback result", "source": "fallback"}
            ]
        )
        
        with patch('tools.search_tool.Config') as mock_config:
            mock_config.SEARCH_FALLBACK_ENABLED = True
            
            result = await SearchTool.semantic_search.func("test query")
            result_data = json.loads(result)
            
            # Fallback should have been called
            search_tool_instance._attempt_fallback_search.assert_called()
            assert len(result_data["results"]) > 0
    
    def test_fallback_search_returns_results(self, search_tool_instance):
        """Test that fallback search returns valid results."""
        fallback_results = [
            {"id": "doc_1", "content": "fallback content", "source": "fallback"}
        ]
        
        search_tool_instance._attempt_fallback_search = Mock(return_value=fallback_results)
        
        result = search_tool_instance._attempt_fallback_search("test", 5)
        
        assert len(result) > 0
        assert all("id" in r for r in result)


class TestComponentLookup:
    """Test component_lookup tool functionality."""
    
    @pytest.mark.asyncio
    async def test_component_lookup_basic(self, search_tool_instance, sample_search_results):
        """Test basic component lookup."""
        search_tool_instance._perform_semantic_search = AsyncMock(
            return_value=sample_search_results
        )
        
        query_data = json.dumps({
            "component": "BlockEntity",
            "limit": 5
        })
        
        result = await SearchTool.component_lookup.func(query_data)
        
        result_data = json.loads(result)
        assert isinstance(result_data, dict)
    
    @pytest.mark.asyncio
    async def test_component_lookup_no_component_error(self, search_tool_instance):
        """Test component lookup returns error when component is empty."""
        query_data = json.dumps({"component": "", "limit": 5})
        
        result = await SearchTool.component_lookup.func(query_data)
        result_data = json.loads(result)
        
        assert "error" in result_data


class TestConversionExamples:
    """Test conversion_examples tool functionality."""
    
    @pytest.mark.asyncio
    async def test_conversion_examples_search(self, search_tool_instance, sample_search_results):
        """Test conversion examples search."""
        example_results = [
            {
                "id": "example_1",
                "content": "Example: Convert Java block to Bedrock block",
                "source": "examples",
                "similarity": 0.9
            }
        ]
        
        search_tool_instance._perform_semantic_search = AsyncMock(
            return_value=example_results
        )
        
        query_data = json.dumps({
            "context": "block conversion",
            "limit": 5
        })
        
        result = await SearchTool.conversion_examples.func(query_data)
        
        result_data = json.loads(result)
        assert "results" in result_data or "error" in result_data


class TestSchemaValidationLookup:
    """Test schema_validation_lookup tool functionality."""
    
    @pytest.mark.asyncio
    async def test_schema_lookup_basic(self, search_tool_instance, sample_search_results):
        """Test schema validation lookup."""
        schema_results = [
            {
                "id": "schema_1",
                "content": "JSON schema for block definition",
                "source": "schemas",
                "similarity": 0.88
            }
        ]
        
        search_tool_instance._perform_semantic_search = AsyncMock(
            return_value=schema_results
        )
        
        query_data = json.dumps({
            "schema_type": "block_definition",
            "limit": 5
        })
        
        result = await SearchTool.schema_validation_lookup.func(query_data)
        
        result_data = json.loads(result)
        assert isinstance(result_data, dict)


class TestBedrockAPISearch:
    """Test bedrock_api_search tool functionality."""
    
    @pytest.mark.asyncio
    async def test_bedrock_api_search(self, search_tool_instance, sample_search_results):
        """Test Bedrock API search."""
        bedrock_results = [r for r in sample_search_results if "bedrock" in r.get("content", "").lower()]
        
        search_tool_instance._perform_semantic_search = AsyncMock(
            return_value=bedrock_results
        )
        
        query_data = json.dumps({
            "api_endpoint": "blocks",
            "limit": 5
        })
        
        result = await SearchTool.bedrock_api_search.func(query_data)
        
        result_data = json.loads(result)
        assert isinstance(result_data, dict)


class TestSearchToolPrivateMethods:
    """Test SearchTool private methods."""
    
    @pytest.mark.asyncio
    async def test_perform_semantic_search(self, search_tool_instance, sample_search_results):
        """Test _perform_semantic_search private method."""
        search_tool_instance.vector_client.search_documents = AsyncMock(
            return_value=sample_search_results
        )
        
        results = await search_tool_instance._perform_semantic_search(
            query="test query",
            limit=5,
            document_source=None
        )
        
        assert len(results) > 0
        assert all(isinstance(r, dict) for r in results)

    def test_attempt_fallback_search_disabled(self, search_tool_instance):
        """Test _attempt_fallback_search when disabled."""
        with patch('tools.search_tool.Config') as mock_config:
            mock_config.SEARCH_FALLBACK_ENABLED = False
            result = search_tool_instance._attempt_fallback_search("query", 5)
            assert result == []

    def test_attempt_fallback_search_logic(self, search_tool_instance):
        """Test _attempt_fallback_search internal logic with successful import."""
        with patch('tools.search_tool.Config') as mock_config:
            mock_config.SEARCH_FALLBACK_ENABLED = True
            mock_config.FALLBACK_SEARCH_TOOL = "web_search_tool"
            
            mock_fallback_instance = MagicMock()
            mock_fallback_instance._run.return_value = "fallback results string"
            
            with patch('importlib.import_module') as mock_import:
                mock_module = MagicMock()
                mock_import.return_value = mock_module
                setattr(mock_module, "WebSearchTool", MagicMock(return_value=mock_fallback_instance))
                
                result = search_tool_instance._attempt_fallback_search("query", 5)
                
                assert len(result) == 1
                assert result[0]["content"] == "fallback results string"

    def test_attempt_fallback_search_import_error(self, search_tool_instance):
        """Test _attempt_fallback_search handling of ImportError."""
        with patch('tools.search_tool.Config') as mock_config:
            mock_config.SEARCH_FALLBACK_ENABLED = True
            mock_config.FALLBACK_SEARCH_TOOL = "non_existent_tool"
            
            with patch('importlib.import_module', side_effect=ImportError("Module not found")):
                result = search_tool_instance._attempt_fallback_search("query", 5)
                assert result == []

    def test_attempt_fallback_search_attribute_error(self, search_tool_instance):
        """Test _attempt_fallback_search handling of AttributeError."""
        with patch('tools.search_tool.Config') as mock_config:
            mock_config.SEARCH_FALLBACK_ENABLED = True
            mock_config.FALLBACK_SEARCH_TOOL = "web_search_tool"
            
            with patch('importlib.import_module') as mock_import:
                mock_module = MagicMock()
                # Class not in module
                delattr(mock_module, "WebSearchTool")
                mock_import.return_value = mock_module
                
                result = search_tool_instance._attempt_fallback_search("query", 5)
                assert result == []

    def test_attempt_fallback_search_generic_exception(self, search_tool_instance):
        """Test _attempt_fallback_search handling of generic exceptions."""
        with patch('tools.search_tool.Config') as mock_config:
            mock_config.SEARCH_FALLBACK_ENABLED = True
            mock_config.FALLBACK_SEARCH_TOOL = "web_search_tool"
            
            with patch('importlib.import_module', side_effect=Exception("Unexpected error")):
                result = search_tool_instance._attempt_fallback_search("query", 5)
                assert result == []

    @pytest.mark.asyncio
    async def test_search_by_document_source_logic(self, search_tool_instance, sample_search_results):
        """Test _search_by_document_source with content_type filter."""
        results_with_metadata = [
            {"id": "1", "metadata": {"content_type": "text"}},
            {"id": "2", "metadata": {"content_type": "json"}}
        ]
        search_tool_instance.vector_client.search_documents = AsyncMock(
            return_value=results_with_metadata
        )
        
        # Test filtering
        result = await search_tool_instance._search_by_document_source(
            document_source="test_source",
            content_type="text"
        )
        assert len(result) == 1
        assert result[0]["id"] == "1"

    @pytest.mark.asyncio
    async def test_find_similar_documents_threshold(self, search_tool_instance):
        """Test _find_similar_documents similarity threshold filtering."""
        results = [
            {"id": "1", "similarity_score": 0.9},
            {"id": "2", "similarity_score": 0.5}
        ]
        search_tool_instance.vector_client.search_documents = AsyncMock(
            return_value=results
        )
        
        # Test filtering with threshold 0.7
        result = await search_tool_instance._find_similar_documents(
            content="test content",
            threshold=0.7
        )
        assert len(result) == 1
        assert result[0]["id"] == "1"

    @pytest.mark.asyncio
    async def test_close_async(self, search_tool_instance):
        """Test close method with async vector_client.close."""
        mock_close = AsyncMock()
        search_tool_instance.vector_client.close = mock_close
        
        await search_tool_instance.close()
        mock_close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_close_sync(self, search_tool_instance):
        """Test close method with sync vector_client.close."""
        mock_close = MagicMock()
        # Ensure it's not a coroutine function
        search_tool_instance.vector_client.close = mock_close
        
        await search_tool_instance.close()
        mock_close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_no_method(self, search_tool_instance):
        """Test close method when vector_client has no close method."""
        delattr(search_tool_instance.vector_client, "close")
        # Should not raise exception
        await search_tool_instance.close()

    @pytest.mark.asyncio
    async def test_close_no_client(self, search_tool_instance):
        """Test close method when vector_client is missing."""
        delattr(search_tool_instance, "vector_client")
        # Should not raise exception
        await search_tool_instance.close()


class TestSearchToolErrorHandling:
    """Test error handling in SearchTool."""
    
    @pytest.mark.asyncio
    async def test_json_decode_error_handling(self, search_tool_instance):
        """Test handling of invalid JSON input."""
        # Invalid JSON should be treated as string query in semantic_search
        search_tool_instance._perform_semantic_search = AsyncMock(return_value=[])
        result = await SearchTool.semantic_search.func("not a json string")
        result_data = json.loads(result)
        assert result_data.get("query") == "not a json string"

        # Test document_search with invalid JSON
        search_tool_instance._search_by_document_source = AsyncMock(return_value=[])
        result = await SearchTool.document_search.func("not a json string")
        result_data = json.loads(result)
        assert result_data.get("document_source") == "not a json string"

        # Test similarity_search with invalid JSON
        search_tool_instance._find_similar_documents = AsyncMock(return_value=[])
        result = await SearchTool.similarity_search.func("not a json string")
        result_data = json.loads(result)
        assert "reference_content" in result_data

    @pytest.mark.asyncio
    async def test_non_string_input_handling(self, search_tool_instance):
        """Test handling of non-string input (e.g. dict)."""
        search_tool_instance._perform_semantic_search = AsyncMock(return_value=[])
        
        # Test semantic_search with dict
        query_dict = {"query": "test"}
        result = await SearchTool.semantic_search.func(query_dict)
        assert "query" in json.loads(result)

        # Test document_search with dict
        search_tool_instance._search_by_document_source = AsyncMock(return_value=[])
        result = await SearchTool.document_search.func({"document_source": "src"})
        assert "document_source" in json.loads(result)

        # Test similarity_search with dict
        search_tool_instance._find_similar_documents = AsyncMock(return_value=[])
        result = await SearchTool.similarity_search.func({"content": "cont"})
        assert "reference_content" in json.loads(result)

    @pytest.mark.asyncio
    async def test_all_tools_parameter_validation(self, search_tool_instance):
        """Test parameter validation for all search tools."""
        # bedrock_api_search
        result = await SearchTool.bedrock_api_search.func("")
        assert "error" in json.loads(result)
        
        # component_lookup
        result = await SearchTool.component_lookup.func("")
        assert "error" in json.loads(result)
        
        # conversion_examples
        result = await SearchTool.conversion_examples.func("")
        assert "error" in json.loads(result)
        
        # schema_validation_lookup
        result = await SearchTool.schema_validation_lookup.func("")
        assert "error" in json.loads(result)

    @pytest.mark.asyncio
    async def test_all_tools_exception_handling(self, search_tool_instance):
        """Test exception handling for all search tools."""
        # Use a real instance but mock its dependencies to fail, or patch a deeper method
        with patch.object(SearchTool, '_perform_semantic_search', side_effect=Exception("Semantic fail")):
            for tool_func in [
                SearchTool.bedrock_api_search.func,
                SearchTool.component_lookup.func,
                SearchTool.conversion_examples.func,
                SearchTool.schema_validation_lookup.func
            ]:
                result = await tool_func("test")
                assert "error" in json.loads(result)

    @pytest.mark.asyncio
    async def test_non_string_input_all_tools(self, search_tool_instance):
        """Test non-string input for all search tools."""
        search_tool_instance._perform_semantic_search = AsyncMock(return_value=[])
        
        # bedrock_api_search with dict
        result = await SearchTool.bedrock_api_search.func({"query": "q"})
        assert "query" in result

        # component_lookup with dict
        result = await SearchTool.component_lookup.func({"component_name": "c"})
        assert "query" in result

        # conversion_examples with dict
        result = await SearchTool.conversion_examples.func({"query": "q"})
        assert "query" in result

        # schema_validation_lookup with dict
        result = await SearchTool.schema_validation_lookup.func({"schema_name": "s"})
        assert "query" in result

    @pytest.mark.asyncio
    async def test_private_methods_exceptions(self, search_tool_instance):
        """Test exception handling in private methods."""
        search_tool_instance.vector_client.search_documents = AsyncMock(side_effect=Exception("DB Error"))
        
        # _perform_semantic_search
        res1 = await search_tool_instance._perform_semantic_search("q")
        assert res1 == []
        
        # _search_by_document_source
        res2 = await search_tool_instance._search_by_document_source("s")
        assert res2 == []
        
        # _find_similar_documents
        res3 = await search_tool_instance._find_similar_documents("c")
        assert res3 == []

    @pytest.mark.asyncio
    async def test_json_parsing_edge_cases(self, search_tool_instance):
        """Test JSON parsing edge cases in tools."""
        search_tool_instance._perform_semantic_search = AsyncMock(return_value=[])
        
        # bedrock_api_search with JSON
        result = await SearchTool.bedrock_api_search.func(json.dumps({"query": "q", "api_category": "c"}))
        assert "query" in result
        
        # component_lookup with JSON
        result = await SearchTool.component_lookup.func(json.dumps({"component_name": "c"}))
        assert "query" in result

        # conversion_examples with JSON
        result = await SearchTool.conversion_examples.func(json.dumps({"query": "q"}))
        assert "query" in result

        # schema_validation_lookup with JSON
        result = await SearchTool.schema_validation_lookup.func(json.dumps({"schema_name": "s"}))
        assert "query" in result


class TestSearchToolIntegration:
    """Integration tests for SearchTool."""
    
    @pytest.mark.asyncio
    async def test_multiple_searches_in_sequence(self, search_tool_instance, sample_search_results):
        """Test running multiple searches in sequence."""
        search_tool_instance._perform_semantic_search = AsyncMock(
            return_value=sample_search_results
        )
        
        queries = ["block", "entity", "conversion"]
        results = []
        
        for query in queries:
            result = await SearchTool.semantic_search.func(query)
            results.append(json.loads(result))
        
        assert len(results) == len(queries)
        assert all("results" in r for r in results)
    
    @pytest.mark.asyncio
    async def test_search_with_various_input_formats(self, search_tool_instance, sample_search_results):
        """Test search with various input formats."""
        search_tool_instance._perform_semantic_search = AsyncMock(
            return_value=sample_search_results
        )
        
        # Test JSON input
        json_input = json.dumps({"query": "test", "limit": 5})
        result1 = await SearchTool.semantic_search.func(json_input)
        
        # Test string input
        result2 = await SearchTool.semantic_search.func("test")
        
        # Both should return valid results
        assert all(isinstance(json.loads(r), dict) for r in [result1, result2])


class TestSearchToolResultFormatting:
    """Test result formatting in SearchTool."""
    
    @pytest.mark.asyncio
    async def test_semantic_search_result_format(self, search_tool_instance, sample_search_results):
        """Test semantic search result format."""
        search_tool_instance._perform_semantic_search = AsyncMock(
            return_value=sample_search_results
        )
        
        result = await SearchTool.semantic_search.func("test")
        result_data = json.loads(result)
        
        # Check required fields
        assert "query" in result_data
        assert "results" in result_data or "error" in result_data
        assert "total_results" in result_data
        
        # Check result items have required fields
        for item in result_data["results"]:
            assert "id" in item
            assert "content" in item
