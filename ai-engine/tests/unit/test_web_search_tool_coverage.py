"""
Comprehensive unit tests for tools/web_search_tool.py to improve coverage.
"""

import pytest
import json
import asyncio
from unittest.mock import MagicMock, patch, ANY
from tools.web_search_tool import (
    WebSearchTool,
    search_web,
    search_minecraft_docs,
    search_programming_help
)


class TestWebSearchToolCoverage:
    """Tests for WebSearchTool."""

    @pytest.fixture
    def mock_ddgs(self):
        """Mock DuckDuckGo search instance."""
        with patch('tools.web_search_tool.DDGS') as mock_cls:
            mock_inst = MagicMock()
            mock_cls.return_value = mock_inst
            yield mock_inst

    def test_init(self, mock_ddgs):
        """Test tool initialization."""
        tool = WebSearchTool(max_results=5, timeout=10)
        assert tool.max_results == 5
        assert tool.timeout == 10
        assert tool.name == "Web Search Tool"

    def test_run_empty_query(self):
        """Test _run with empty query."""
        tool = WebSearchTool()
        result_json = tool._run("")
        result = json.loads(result_json)
        assert "error" in result
        assert result["results"] == []

    def test_run_success(self, mock_ddgs):
        """Test successful _run."""
        mock_results = [
            {"title": "Result 1", "href": "http://1", "body": "Snippet 1"},
            {"title": "Result 2", "href": "http://2", "body": "Snippet 2"}
        ]
        mock_ddgs.text.return_value = iter(mock_results)
        
        tool = WebSearchTool(max_results=2)
        result_json = tool._run("test query")
        result = json.loads(result_json)
        
        assert result["query"] == "test query"
        assert len(result["results"]) == 2
        assert result["results"][0]["metadata"]["title"] == "Result 1"
        assert result["total_results"] == 2

    def test_search_duckduckgo_rate_limit(self, mock_ddgs):
        """Test rate limit handling in _search_duckduckgo."""
        mock_ddgs.text.side_effect = Exception("Rate limit 202")
        
        tool = WebSearchTool()
        # Mock time.sleep to avoid waiting
        with patch('time.sleep'):
            results = tool._search_duckduckgo("query")
            assert results == []

    def test_search_duckduckgo_fallback_mock(self, mock_ddgs):
        """Test fallback to empty list on generic exception."""
        mock_ddgs.text.side_effect = Exception("Some other error")
        
        tool = WebSearchTool()
        results = tool._search_duckduckgo("query")
        
        # Returns empty list for generic exceptions to avoid masking failures
        assert results == []

    def test_format_search_results_error_handling(self):
        """Test error handling during result formatting."""
        tool = WebSearchTool()
        # One valid result, one that causes error (missing keys handled by get but let's force something)
        raw_results = [
            {"title": "T1", "body": "B1", "href": "H1"},
            None # Will cause AttributeError in loop
        ]
        
        formatted = tool._format_search_results(raw_results)
        assert len(formatted) == 1
        assert formatted[0]["metadata"]["title"] == "T1"

    @pytest.mark.asyncio
    async def test_async_search(self, mock_ddgs):
        """Test async search wrapper."""
        mock_ddgs.text.return_value = iter([])
        tool = WebSearchTool()
        
        result_json = await tool.async_search("query")
        result = json.loads(result_json)
        assert result["query"] == "query"

    def test_search_with_filters(self, mock_ddgs):
        """Test search with filters."""
        mock_ddgs.text.return_value = iter([{"title": "F1", "body": "B1", "href": "H1"}])
        
        tool = WebSearchTool()
        result_json = tool.search_with_filters("query", site_filter="site:github.com")
        result = json.loads(result_json)
        
        assert result["filtered_query"] == "query site:github.com"
        assert result["filters"]["site_filter"] == "site:github.com"
        assert len(result["results"]) == 1
        
        # Verify call to ddgs.text
        mock_ddgs.text.assert_called_with(
            keywords="query site:github.com",
            max_results=ANY,
            backend="api",
            safesearch="moderate"
        )

    def test_search_with_filters_fallback(self, mock_ddgs):
        """Test fallback in search_with_filters when backend='api' fails."""
        # First call fails, second succeeds
        mock_ddgs.text.side_effect = [Exception("API fail"), iter([{"title": "Lite"}])]
        
        tool = WebSearchTool()
        result_json = tool.search_with_filters("query")
        result = json.loads(result_json)
        
        assert len(result["results"]) == 1
        assert result["results"][0]["metadata"]["title"] == "Lite"

    def test_utility_functions(self, mock_ddgs):
        """Test global utility functions."""
        mock_ddgs.text.return_value = iter([])
        
        # search_web
        search_web("query", max_results=5)
        # Verify it created a tool and ran it
        assert mock_ddgs.text.called
        
        # search_minecraft_docs
        mock_ddgs.text.reset_mock()
        search_minecraft_docs("redstone")
        # Check if query was enhanced
        args, kwargs = mock_ddgs.text.call_args
        assert "minecraft bedrock documentation" in args[0]
        
        # search_programming_help
        mock_ddgs.text.reset_mock()
        search_programming_help("asyncio", language="python")
        args, kwargs = mock_ddgs.text.call_args
        assert "python programming" in args[0]
        assert "stackoverflow.com" in args[0]
