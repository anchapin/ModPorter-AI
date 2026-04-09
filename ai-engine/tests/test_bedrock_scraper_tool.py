"""
Unit tests for BedrockScraperTool.
"""

import pytest
import json
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from tools.bedrock_scraper_tool import (
    BedrockScraperTool,
    scrape_bedrock_docs,
    extract_bedrock_api_examples,
    process_bedrock_schemas,
)
from schemas.multimodal_schema import MultiModalDocument, ContentType


@pytest.fixture
def mock_scraper():
    """Mock BedrockDocsScraper."""
    with patch("tools.bedrock_scraper_tool.BedrockDocsScraper") as mock_class:
        mock_instance = mock_class.return_value
        mock_instance.scrape_documentation = AsyncMock(
            return_value=[
                MultiModalDocument(
                    id="doc1",
                    content_hash="hash1",
                    source_path="https://test.com/doc1",
                    content_type=ContentType.TEXT,
                    content_text="Test content 1",
                    content_metadata={"title": "Test 1"},
                    chunk_index=0,
                    total_chunks=1,
                    processing_status="completed",
                    indexed_at=None,
                    project_context=None,
                )
            ]
        )
        mock_instance.scrape_site = AsyncMock(
            return_value=[
                MultiModalDocument(
                    id="site_doc1",
                    content_hash="hash2",
                    source_path="https://specific.com/1",
                    content_type=ContentType.TEXT,
                    content_text="Site content 1",
                    content_metadata={"title": "Site 1"},
                    chunk_index=0,
                    total_chunks=1,
                    processing_status="completed",
                    indexed_at=None,
                    project_context=None,
                )
            ]
        )
        mock_instance.extract_api_examples = AsyncMock(
            return_value=[
                MultiModalDocument(
                    id="api1",
                    content_hash="hash3",
                    source_path="https://test.com/api1",
                    content_type=ContentType.CODE,
                    content_text="API Example 1",
                    content_metadata={"title": "API 1"},
                    chunk_index=0,
                    total_chunks=1,
                    processing_status="completed",
                    indexed_at=None,
                    project_context=None,
                )
            ]
        )
        mock_instance.process_json_schemas = AsyncMock(
            return_value=[
                MultiModalDocument(
                    id="schema1",
                    content_hash="hash4",
                    source_path="https://test.com/schema1",
                    content_type=ContentType.CONFIGURATION,
                    content_text='{"type": "object"}',
                    content_metadata={"title": "Schema 1"},
                    chunk_index=0,
                    total_chunks=1,
                    processing_status="completed",
                    indexed_at=None,
                    project_context=None,
                )
            ]
        )
        mock_instance.close = AsyncMock()
        yield mock_instance


class TestBedrockScraperTool:
    """Test cases for BedrockScraperTool."""

    def test_tool_initialization(self):
        """Test tool initialization."""
        tool = BedrockScraperTool(max_depth=3, rate_limit=2.0)
        assert tool.name == "Bedrock Documentation Scraper"
        assert tool.max_depth == 3
        assert tool.rate_limit == 2.0

    def test_run_scrape_all(self, mock_scraper):
        """Test scrape_all action."""
        tool = BedrockScraperTool()
        result = tool._run(json.dumps({"action": "scrape_all"}))
        result_data = json.loads(result)

        assert result_data["success"] is True
        assert result_data["total_documents"] == 1
        assert result_data["action"] == "scrape_all"
        mock_scraper.scrape_documentation.assert_called_once()

    def test_run_scrape_site(self, mock_scraper):
        """Test scrape_site action."""
        tool = BedrockScraperTool()
        result = tool._run(
            json.dumps({"action": "scrape_site", "site_url": "https://specific.com"})
        )
        result_data = json.loads(result)

        assert result_data["success"] is True
        assert result_data["site_url"] == "https://specific.com"
        mock_scraper.scrape_site.assert_called_once_with("https://specific.com", max_depth=2)

    def test_run_scrape_site_missing_url(self):
        """Test scrape_site action with missing URL."""
        tool = BedrockScraperTool()
        result = tool._run(json.dumps({"action": "scrape_site"}))
        result_data = json.loads(result)

        assert "error" in result_data
        assert "site_url required" in result_data["error"]

    def test_run_extract_api_examples(self, mock_scraper):
        """Test extract_api_examples action."""
        tool = BedrockScraperTool()
        result = tool._run("extract_api_examples")
        result_data = json.loads(result)

        assert result_data["success"] is True
        assert result_data["total_examples"] == 1
        mock_scraper.extract_api_examples.assert_called_once()

    def test_run_process_schemas(self, mock_scraper):
        """Test process_schemas action."""
        tool = BedrockScraperTool()
        result = tool._run("process_schemas")
        result_data = json.loads(result)

        assert result_data["success"] is True
        assert result_data["total_schemas"] == 1
        mock_scraper.process_json_schemas.assert_called_once()

    def test_run_unknown_action(self):
        """Test unknown action."""
        tool = BedrockScraperTool()
        result = tool._run("unknown_action")
        result_data = json.loads(result)

        assert "error" in result_data
        assert "Unknown action" in result_data["error"]

    def test_run_exception_handling(self, mock_scraper):
        """Test exception handling in _run."""
        mock_scraper.scrape_documentation.side_effect = Exception("Network error")
        tool = BedrockScraperTool()
        result = tool._run("scrape_all")
        result_data = json.loads(result)

        assert "error" in result_data
        assert "Network error" in result_data["error"]


class TestUtilityFunctions:
    """Test utility functions for BedrockScraperTool."""

    def test_scrape_bedrock_docs_utility(self):
        """Test scrape_bedrock_docs utility."""
        with patch("tools.bedrock_scraper_tool.BedrockScraperTool") as mock_tool_class:
            mock_instance = mock_tool_class.return_value
            mock_instance._run.return_value = '{"success": true}'
            result = scrape_bedrock_docs("scrape_all")
            assert result == '{"success": true}'
            mock_instance._run.assert_called_with("scrape_all")

    def test_extract_bedrock_api_examples_utility(self):
        """Test extract_bedrock_api_examples utility."""
        with patch("tools.bedrock_scraper_tool.BedrockScraperTool") as mock_tool_class:
            mock_instance = mock_tool_class.return_value
            mock_instance._run.return_value = '{"success": true}'
            result = extract_bedrock_api_examples()
            assert result == '{"success": true}'
            mock_instance._run.assert_called_with("extract_api_examples")

    def test_process_bedrock_schemas_utility(self):
        """Test process_bedrock_schemas utility."""
        with patch("tools.bedrock_scraper_tool.BedrockScraperTool") as mock_tool_class:
            mock_instance = mock_tool_class.return_value
            mock_instance._run.return_value = '{"success": true}'
            result = process_bedrock_schemas()
            assert result == '{"success": true}'
            mock_instance._run.assert_called_with("process_schemas")

    def test_utility_functions_integration(self):
        """Integration test for utility functions in CI environment."""
        with patch("tools.bedrock_scraper_tool.BedrockScraperTool") as mock_tool_class:
            mock_instance = mock_tool_class.return_value
            mock_instance._run.return_value = '{"success": true, "total_documents": 0}'
            result = scrape_bedrock_docs("scrape_all")
            assert '"success": true' in result
