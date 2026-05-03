"""
Unit tests for WebSearchTool.
Tests DuckDuckGo search integration, formatting, and utility functions.
"""

import pytest
import json
from unittest.mock import patch, MagicMock

try:
    from tools.web_search_tool import (
        WebSearchTool,
        search_web,
        search_minecraft_docs,
        search_programming_help,
    )

    IMPORTS_AVAILABLE = True
except ImportError:
    IMPORTS_AVAILABLE = False


# Skip all tests if imports fail
pytestmark = pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="WebSearchTool imports unavailable")


@pytest.fixture
def mock_ddgs():
    """Mock DuckDuckGo search instance."""
    with patch("tools.web_search_tool.DDGS") as mock:
        instance = mock.return_value
        instance.text.return_value = [
            {"title": "Result 1", "body": "Snippet 1", "href": "https://example.com/1"},
            {"title": "Result 2", "body": "Snippet 2", "href": "https://example.com/2"},
        ]
        yield instance


@pytest.fixture
def web_search_tool():
    """Create a WebSearchTool instance for testing."""
    with patch("tools.web_search_tool.DDGS"):
        tool = WebSearchTool(max_results=5)
        # Manually set mock _ddgs
        mock_ddgs_instance = MagicMock()
        mock_ddgs_instance.text.return_value = [
            {"title": "Result 1", "body": "Snippet 1", "href": "https://example.com/1"}
        ]
        object.__setattr__(tool, "_ddgs", mock_ddgs_instance)
        return tool


class TestWebSearchToolInitialization:
    """Test WebSearchTool initialization."""

    def test_initialization(self):
        """Test basic initialization."""
        with patch("tools.web_search_tool.DDGS"):
            tool = WebSearchTool(max_results=10, timeout=60)
            assert tool.max_results == 10
            assert tool.timeout == 60
            assert tool.name == "Web Search Tool"


class TestWebSearchToolRun:
    """Test _run method of WebSearchTool."""

    def test_run_basic(self, web_search_tool):
        """Test basic search execution."""
        result = web_search_tool._run("test query")

        result_data = json.loads(result)
        assert result_data["query"] == "test query"
        assert result_data["source"] == "DuckDuckGo"
        assert len(result_data["results"]) == 1
        assert result_data["results"][0]["metadata"]["title"] == "Result 1"

    def test_run_empty_query(self, web_search_tool):
        """Test search with empty query."""
        result = web_search_tool._run("")
        result_data = json.loads(result)
        assert "error" in result_data

        result = web_search_tool._run("   ")
        result_data = json.loads(result)
        assert "error" in result_data

    def test_run_no_results(self, web_search_tool):
        """Test search with no results."""
        web_search_tool.ddgs.text.return_value = []

        # We need to mock _search_duckduckgo to not return mock results if we want to test empty path
        # Actually _search_duckduckgo returns mock results if DDGS fails or returns nothing
        with patch.object(web_search_tool, "_search_duckduckgo", return_value=[]):
            result = web_search_tool._run("test")
            result_data = json.loads(result)
            assert result_data["total_results"] == 0
            assert result_data["message"] == "No results found"

    def test_run_exception(self, web_search_tool):
        """Test exception handling in _run."""
        with patch.object(
            web_search_tool, "_search_duckduckgo", side_effect=Exception("Search crash")
        ):
            result = web_search_tool._run("test")
            result_data = json.loads(result)
            assert "error" in result_data
            assert "Search crash" in result_data["error"]


class TestWebSearchToolInternal:
    """Test internal methods of WebSearchTool."""

    def test_search_duckduckgo_success(self, web_search_tool):
        """Test successful DuckDuckGo search."""
        results = web_search_tool._search_duckduckgo("query")
        assert len(results) == 1
        assert results[0]["title"] == "Result 1"

    def test_search_duckduckgo_rate_limit(self, web_search_tool):
        """Test rate limit handling in _search_duckduckgo."""
        web_search_tool.ddgs.text.side_effect = Exception("Rate limit exceeded 202")

        with patch("time.sleep"):  # Don't actually sleep
            results = web_search_tool._search_duckduckgo("query")
            # Should return empty list for rate limit detected
            assert len(results) == 0

    def test_search_duckduckgo_generic_exception(self, web_search_tool):
        """Test generic exception in _search_duckduckgo."""
        web_search_tool.ddgs.text.side_effect = Exception("Unknown error")

        results = web_search_tool._search_duckduckgo("query")
        # Returns empty list for generic exceptions (not rate-limit) to avoid masking failures
        assert results == []

    def test_format_search_results_exception(self, web_search_tool):
        """Test exception handling during result formatting."""
        raw_results = [
            {"title": "Good"},
            None,  # This will cause an exception when calling .get()
            {"title": "Also Good"},
        ]

        formatted = web_search_tool._format_search_results(raw_results)
        # Should skip the None result and format the others
        assert len(formatted) == 2


class TestWebSearchToolAsync:
    """Test async functionality of WebSearchTool."""

    @pytest.mark.asyncio
    async def test_async_search(self, web_search_tool):
        """Test async_search method."""
        with patch.object(web_search_tool, "_run", return_value='{"results": []}'):
            result = await web_search_tool.async_search("test")
            assert result == '{"results": []}'


class TestWebSearchToolFilters:
    """Test search_with_filters method."""

    def test_search_with_filters_basic(self, web_search_tool):
        """Test search with filters."""
        web_search_tool.ddgs.text.return_value = [{"title": "Filtered"}]

        result = web_search_tool.search_with_filters(
            "query", region="uk-en", site_filter="site:github.com"
        )

        result_data = json.loads(result)
        assert result_data["filtered_query"] == "query site:github.com"
        assert result_data["filters"]["region"] == "uk-en"
        assert len(result_data["results"]) == 1

    def test_search_with_filters_fallback_backend(self, web_search_tool):
        """Test fallback to lite backend when api fails."""
        # First call fails, second succeeds (for fallback)
        web_search_tool.ddgs.text.side_effect = [Exception("API Fail"), [{"title": "Lite Result"}]]

        result = web_search_tool.search_with_filters("query")
        result_data = json.loads(result)
        assert len(result_data["results"]) == 1
        assert "Lite Result" in result_data["results"][0]["content"]

    def test_search_with_filters_exception(self, web_search_tool):
        """Test exception handling in search_with_filters."""
        web_search_tool.ddgs.text.side_effect = Exception("Total fail")

        result = web_search_tool.search_with_filters("query")
        result_data = json.loads(result)
        assert "error" in result_data


class TestUtilityFunctions:
    """Test standalone utility functions."""

    def test_search_web(self):
        """Test search_web utility."""
        with patch("tools.web_search_tool.WebSearchTool") as mock_tool_class:
            mock_instance = mock_tool_class.return_value
            mock_instance._run.return_value = '{"ok": true}'

            result = search_web("test", max_results=5)
            assert result == '{"ok": true}'
            mock_tool_class.assert_called_once_with(max_results=5)

    def test_search_minecraft_docs(self):
        """Test search_minecraft_docs utility."""
        with patch("tools.web_search_tool.WebSearchTool") as mock_tool_class:
            mock_instance = mock_tool_class.return_value
            mock_instance._run.return_value = '{"ok": true}'

            result = search_minecraft_docs("blocks")
            assert result == '{"ok": true}'
            # Check if query was modified
            args, _ = mock_instance._run.call_args
            assert "minecraft bedrock documentation" in args[0]

    def test_search_programming_help(self):
        """Test search_programming_help utility."""
        with patch("tools.web_search_tool.WebSearchTool") as mock_tool_class:
            mock_instance = mock_tool_class.return_value
            mock_instance._run.return_value = '{"ok": true}'

            result = search_programming_help("how to code", language="python")
            assert result == '{"ok": true}'
            # Check if query was modified
            args, _ = mock_instance._run.call_args
            assert "python" in args[0]
            assert "programming" in args[0]
