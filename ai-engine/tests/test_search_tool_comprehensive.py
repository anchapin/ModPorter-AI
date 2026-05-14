"""Comprehensive unit tests for the typed ``SearchTool`` family (issue #1201, Phase 8 A).

This rewrite targets the ``BaseTool`` subclasses introduced when the legacy
``@tool``-decorated single-string-arg pattern was retired. Each test now
drives the public ``ainvoke({...})`` surface with structured arguments, and
mocks the underlying ``VectorDBClient.search_documents`` instead of the
removed private ``_perform_*`` wrappers.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

try:
    from tools.search_tool import (
        BedrockApiSearchTool,
        ComponentLookupTool,
        ConversionExamplesTool,
        DocumentSearchTool,
        SchemaValidationLookupTool,
        SearchTool,
        SemanticSearchTool,
        SimilaritySearchTool,
        _attempt_fallback_search,
        _document_search_payload,
        _semantic_search_payload,
        _similarity_search_payload,
    )
    from utils.vector_db_client import VectorDBClient

    IMPORTS_AVAILABLE = True
except ImportError as exc:  # pragma: no cover - environmental
    IMPORTS_AVAILABLE = False
    IMPORT_ERROR = str(exc)


pytestmark = pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Required imports unavailable")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_vector_client() -> AsyncMock:
    """An async-spec'd ``VectorDBClient`` mock with a default empty result set."""
    client = AsyncMock(spec=VectorDBClient)
    client.search_documents = AsyncMock(return_value=[])
    client.index_document = AsyncMock(return_value=True)
    client.get_embedding = AsyncMock(return_value=[0.1] * 768)
    client.close = AsyncMock()
    return client


@pytest.fixture
def sample_search_results() -> List[Dict[str, Any]]:
    """Sample vector-DB results."""
    return [
        {
            "id": "doc_1",
            "content": "Java block entity implementation",
            "source": "java_source",
            "similarity_score": 0.95,
        },
        {
            "id": "doc_2",
            "content": "Block state management in Bedrock",
            "source": "bedrock_docs",
            "similarity_score": 0.87,
        },
        {
            "id": "doc_3",
            "content": "Custom block properties",
            "source": "reference",
            "similarity_score": 0.72,
        },
    ]


@pytest.fixture
def disable_fallback() -> Any:
    """Force ``Config.SEARCH_FALLBACK_ENABLED = False`` for the duration of a test."""
    with patch("tools.search_tool.Config") as mock_config:
        mock_config.SEARCH_FALLBACK_ENABLED = False
        yield mock_config


@pytest.fixture
def enable_fallback() -> Any:
    """Force ``Config.SEARCH_FALLBACK_ENABLED = True`` for the duration of a test."""
    with patch("tools.search_tool.Config") as mock_config:
        mock_config.SEARCH_FALLBACK_ENABLED = True
        mock_config.FALLBACK_SEARCH_TOOL = "web_search_tool"
        yield mock_config


# ---------------------------------------------------------------------------
# Facade
# ---------------------------------------------------------------------------


class TestSearchToolFacade:
    """Tests for the ``SearchTool`` facade and singleton behaviour."""

    def test_get_tools_returns_seven_basetool_instances(self) -> None:
        from langchain_core.tools import BaseTool

        SearchTool._instance = None
        with patch("tools.search_tool.VectorDBClient"):
            facade = SearchTool()
            tools = facade.get_tools()

        assert len(tools) == 7
        assert all(isinstance(t, BaseTool) for t in tools)
        names = {t.name for t in tools}
        assert names == {
            "semantic_search",
            "document_search",
            "similarity_search",
            "bedrock_api_search",
            "component_lookup",
            "conversion_examples",
            "schema_validation_lookup",
        }
        SearchTool._instance = None

    def test_get_instance_singleton(self) -> None:
        SearchTool._instance = None
        with patch("tools.search_tool.VectorDBClient"):
            i1 = SearchTool.get_instance()
            i2 = SearchTool.get_instance()
        assert i1 is i2
        SearchTool._instance = None

    def test_facade_exposes_typed_basetool_properties(self) -> None:
        SearchTool._instance = None
        with patch("tools.search_tool.VectorDBClient"):
            facade = SearchTool()
        assert isinstance(facade.semantic_search, SemanticSearchTool)
        assert isinstance(facade.document_search, DocumentSearchTool)
        assert isinstance(facade.similarity_search, SimilaritySearchTool)
        assert isinstance(facade.bedrock_api_search, BedrockApiSearchTool)
        assert isinstance(facade.component_lookup, ComponentLookupTool)
        assert isinstance(facade.conversion_examples, ConversionExamplesTool)
        assert isinstance(facade.schema_validation_lookup, SchemaValidationLookupTool)
        SearchTool._instance = None


# ---------------------------------------------------------------------------
# SemanticSearchTool
# ---------------------------------------------------------------------------


class TestSemanticSearchTool:
    """Tests for ``SemanticSearchTool.ainvoke``."""

    @pytest.mark.asyncio
    async def test_returns_canonical_payload(
        self, mock_vector_client: AsyncMock, sample_search_results: List[Dict[str, Any]]
    ) -> None:
        mock_vector_client.search_documents.return_value = sample_search_results
        tool = SemanticSearchTool(vector_client=mock_vector_client)

        raw = await tool.ainvoke(
            {"query": "block entity implementation", "limit": 5, "document_source": "java_source"}
        )

        payload = json.loads(raw)
        assert payload["query"] == "block entity implementation"
        assert payload["total_results"] == 3
        assert payload["results"] == sample_search_results
        mock_vector_client.search_documents.assert_awaited_once_with(
            query_text="block entity implementation", top_k=5, document_source_filter="java_source"
        )

    @pytest.mark.asyncio
    async def test_default_limit_is_ten(self, mock_vector_client: AsyncMock) -> None:
        tool = SemanticSearchTool(vector_client=mock_vector_client)
        await tool.ainvoke({"query": "anything"})
        mock_vector_client.search_documents.assert_awaited_once_with(
            query_text="anything", top_k=10, document_source_filter=None
        )

    @pytest.mark.asyncio
    async def test_vector_client_exception_returns_error_payload(
        self, mock_vector_client: AsyncMock
    ) -> None:
        mock_vector_client.search_documents.side_effect = Exception("Vector DB connection failed")
        tool = SemanticSearchTool(vector_client=mock_vector_client)

        raw = await tool.ainvoke({"query": "test"})
        payload = json.loads(raw)

        assert "error" in payload
        assert "Vector DB connection failed" in payload["error"]
        assert payload["query"] == "test"

    @pytest.mark.asyncio
    async def test_fallback_triggers_when_results_empty(
        self, mock_vector_client: AsyncMock, enable_fallback: Any
    ) -> None:
        mock_vector_client.search_documents.return_value = []
        tool = SemanticSearchTool(vector_client=mock_vector_client)

        with patch(
            "tools.search_tool._attempt_fallback_search",
            return_value=[{"id": "fb", "content": "fb content"}],
        ) as mock_fb:
            raw = await tool.ainvoke({"query": "x", "limit": 4})

        mock_fb.assert_called_once_with("x", 4)
        payload = json.loads(raw)
        assert payload["total_results"] == 1
        assert payload["results"][0]["content"] == "fb content"

    @pytest.mark.asyncio
    async def test_fallback_skipped_when_disabled(
        self, mock_vector_client: AsyncMock, disable_fallback: Any
    ) -> None:
        mock_vector_client.search_documents.return_value = []
        tool = SemanticSearchTool(vector_client=mock_vector_client)

        with patch("tools.search_tool._attempt_fallback_search") as mock_fb:
            raw = await tool.ainvoke({"query": "x"})

        mock_fb.assert_not_called()
        assert json.loads(raw)["total_results"] == 0

    def test_sync_invoke_outside_loop(
        self, mock_vector_client: AsyncMock, sample_search_results: List[Dict[str, Any]]
    ) -> None:
        mock_vector_client.search_documents.return_value = sample_search_results
        tool = SemanticSearchTool(vector_client=mock_vector_client)

        raw = tool.invoke({"query": "block"})
        assert json.loads(raw)["total_results"] == 3

    @pytest.mark.asyncio
    async def test_sync_invoke_inside_loop_raises(self, mock_vector_client: AsyncMock) -> None:
        tool = SemanticSearchTool(vector_client=mock_vector_client)
        with pytest.raises(RuntimeError, match="event loop"):
            tool.invoke({"query": "x"})


# ---------------------------------------------------------------------------
# DocumentSearchTool
# ---------------------------------------------------------------------------


class TestDocumentSearchTool:
    @pytest.mark.asyncio
    async def test_basic(
        self, mock_vector_client: AsyncMock, sample_search_results: List[Dict[str, Any]]
    ) -> None:
        mock_vector_client.search_documents.return_value = sample_search_results
        tool = DocumentSearchTool(vector_client=mock_vector_client)

        raw = await tool.ainvoke({"document_source": "java_source", "limit": 3})
        payload = json.loads(raw)

        assert payload["document_source"] == "java_source"
        assert payload["total_results"] == 3
        mock_vector_client.search_documents.assert_awaited_once_with(
            query_text="java_source", top_k=3, document_source_filter="java_source"
        )

    @pytest.mark.asyncio
    async def test_content_type_filter_applies_client_side(
        self, mock_vector_client: AsyncMock
    ) -> None:
        mock_vector_client.search_documents.return_value = [
            {"id": "1", "metadata": {"content_type": "text"}},
            {"id": "2", "metadata": {"content_type": "json"}},
            {"id": "3", "content_type": "text"},
        ]
        tool = DocumentSearchTool(vector_client=mock_vector_client)

        raw = await tool.ainvoke({"document_source": "src", "content_type": "text"})
        payload = json.loads(raw)

        ids = sorted(r["id"] for r in payload["results"])
        assert ids == ["1", "3"]

    @pytest.mark.asyncio
    async def test_vector_client_exception_returns_error(
        self, mock_vector_client: AsyncMock
    ) -> None:
        mock_vector_client.search_documents.side_effect = Exception("oops")
        tool = DocumentSearchTool(vector_client=mock_vector_client)

        raw = await tool.ainvoke({"document_source": "x"})
        payload = json.loads(raw)

        assert "error" in payload
        assert payload["document_source"] == "x"

    @pytest.mark.asyncio
    async def test_fallback_triggers_when_empty(
        self, mock_vector_client: AsyncMock, enable_fallback: Any
    ) -> None:
        mock_vector_client.search_documents.return_value = []
        tool = DocumentSearchTool(vector_client=mock_vector_client)

        with patch(
            "tools.search_tool._attempt_fallback_search",
            return_value=[{"id": "fb", "content": "fb"}],
        ):
            raw = await tool.ainvoke({"document_source": "x"})

        assert json.loads(raw)["total_results"] == 1


# ---------------------------------------------------------------------------
# SimilaritySearchTool
# ---------------------------------------------------------------------------


class TestSimilaritySearchTool:
    @pytest.mark.asyncio
    async def test_basic_returns_preview(
        self, mock_vector_client: AsyncMock, sample_search_results: List[Dict[str, Any]]
    ) -> None:
        mock_vector_client.search_documents.return_value = sample_search_results
        tool = SimilaritySearchTool(vector_client=mock_vector_client)

        raw = await tool.ainvoke({"content": "entity behavior", "threshold": 0.7, "limit": 5})
        payload = json.loads(raw)

        assert payload["reference_content"] == "entity behavior"
        assert payload["threshold"] == 0.7
        assert payload["total_results"] == 3

    @pytest.mark.asyncio
    async def test_long_content_is_truncated_in_preview(
        self, mock_vector_client: AsyncMock
    ) -> None:
        mock_vector_client.search_documents.return_value = [{"id": "1", "similarity_score": 0.9}]
        tool = SimilaritySearchTool(vector_client=mock_vector_client)
        long_content = "a" * 200

        raw = await tool.ainvoke({"content": long_content, "threshold": 0.0})
        payload = json.loads(raw)

        assert payload["reference_content"].endswith("...")
        assert len(payload["reference_content"]) == 103  # 100 chars + "..."

    @pytest.mark.asyncio
    async def test_threshold_filters_results(self, mock_vector_client: AsyncMock) -> None:
        mock_vector_client.search_documents.return_value = [
            {"id": "1", "similarity_score": 0.9},
            {"id": "2", "similarity_score": 0.5},
        ]
        tool = SimilaritySearchTool(vector_client=mock_vector_client)

        raw = await tool.ainvoke({"content": "x", "threshold": 0.7})
        payload = json.loads(raw)

        assert [r["id"] for r in payload["results"]] == ["1"]

    @pytest.mark.asyncio
    async def test_vector_client_exception_returns_error(
        self, mock_vector_client: AsyncMock
    ) -> None:
        mock_vector_client.search_documents.side_effect = Exception("nope")
        tool = SimilaritySearchTool(vector_client=mock_vector_client)

        raw = await tool.ainvoke({"content": "x"})
        payload = json.loads(raw)

        assert "error" in payload


# ---------------------------------------------------------------------------
# Wrapper tools (Bedrock/Component/Conversion/Schema)
# ---------------------------------------------------------------------------


class TestBedrockApiSearchTool:
    @pytest.mark.asyncio
    async def test_formats_query_with_category(self, mock_vector_client: AsyncMock) -> None:
        mock_vector_client.search_documents.return_value = []
        tool = BedrockApiSearchTool(vector_client=mock_vector_client)

        await tool.ainvoke({"query": "player events", "api_category": "Scripting API"})

        args = mock_vector_client.search_documents.await_args
        assert args.kwargs["query_text"] == "Bedrock API Scripting API player events"

    @pytest.mark.asyncio
    async def test_formats_query_without_category(self, mock_vector_client: AsyncMock) -> None:
        mock_vector_client.search_documents.return_value = []
        tool = BedrockApiSearchTool(vector_client=mock_vector_client)

        await tool.ainvoke({"query": "player events"})

        args = mock_vector_client.search_documents.await_args
        assert args.kwargs["query_text"] == "Bedrock API player events"


class TestComponentLookupTool:
    @pytest.mark.asyncio
    async def test_formats_query(self, mock_vector_client: AsyncMock) -> None:
        mock_vector_client.search_documents.return_value = []
        tool = ComponentLookupTool(vector_client=mock_vector_client)

        await tool.ainvoke({"component_name": "minecraft:behavior.float_wander"})

        args = mock_vector_client.search_documents.await_args
        assert (
            args.kwargs["query_text"]
            == "Bedrock component documentation for minecraft:behavior.float_wander"
        )
        assert args.kwargs["top_k"] == 5  # default for this tool


class TestConversionExamplesTool:
    @pytest.mark.asyncio
    async def test_formats_query(self, mock_vector_client: AsyncMock) -> None:
        mock_vector_client.search_documents.return_value = []
        tool = ConversionExamplesTool(vector_client=mock_vector_client)

        await tool.ainvoke({"query": "potion effects"})

        args = mock_vector_client.search_documents.await_args
        assert args.kwargs["query_text"] == "Java to Bedrock conversion example for potion effects"
        assert args.kwargs["top_k"] == 5


class TestSchemaValidationLookupTool:
    @pytest.mark.asyncio
    async def test_formats_query(self, mock_vector_client: AsyncMock) -> None:
        mock_vector_client.search_documents.return_value = []
        tool = SchemaValidationLookupTool(vector_client=mock_vector_client)

        await tool.ainvoke({"schema_name": "entity definition"})

        args = mock_vector_client.search_documents.await_args
        assert args.kwargs["query_text"] == "Bedrock JSON schema for entity definition"
        assert args.kwargs["top_k"] == 3  # default for this tool


# ---------------------------------------------------------------------------
# Pydantic args-schema validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "tool_cls, bad_args, error_field",
    [
        # Empty / missing required string
        (SemanticSearchTool, {"query": ""}, "query"),
        (DocumentSearchTool, {"document_source": ""}, "document_source"),
        (SimilaritySearchTool, {"content": ""}, "content"),
        (BedrockApiSearchTool, {"query": ""}, "query"),
        (ComponentLookupTool, {"component_name": ""}, "component_name"),
        (ConversionExamplesTool, {"query": ""}, "query"),
        (SchemaValidationLookupTool, {"schema_name": ""}, "schema_name"),
        # Out-of-range numerics
        (SemanticSearchTool, {"query": "x", "limit": 0}, "limit"),
        (SemanticSearchTool, {"query": "x", "limit": 999}, "limit"),
        (SimilaritySearchTool, {"content": "x", "threshold": 1.5}, "threshold"),
        (SimilaritySearchTool, {"content": "x", "threshold": -0.1}, "threshold"),
        # Forbidden extra field
        (SemanticSearchTool, {"query": "x", "unexpected_field": 1}, "unexpected_field"),
    ],
)
def test_typed_tool_rejects_invalid_args(
    tool_cls: type, bad_args: Dict[str, Any], error_field: str, mock_vector_client: AsyncMock
) -> None:
    """Pydantic ``args_schema`` validates every required field and constraint."""
    tool = tool_cls(vector_client=mock_vector_client)
    with pytest.raises(ValidationError) as exc_info:
        tool.invoke(bad_args)
    assert error_field in str(exc_info.value)


# ---------------------------------------------------------------------------
# Fallback mechanism (module-level helper)
# ---------------------------------------------------------------------------


class TestAttemptFallbackSearch:
    def test_disabled_returns_empty(self, disable_fallback: Any) -> None:
        assert _attempt_fallback_search("q", 5) == []

    def test_successful_import_wraps_string_result(self, enable_fallback: Any) -> None:
        fake_instance = MagicMock()
        fake_instance._run.return_value = "fallback results string"
        fake_module = MagicMock()
        setattr(fake_module, "WebSearchTool", MagicMock(return_value=fake_instance))

        with patch("importlib.import_module", return_value=fake_module):
            result = _attempt_fallback_search("q", 5)

        assert len(result) == 1
        assert result[0]["content"] == "fallback results string"
        assert result[0]["document_source"] == "fallback_search"

    def test_import_error_returns_empty(self, enable_fallback: Any) -> None:
        with patch("importlib.import_module", side_effect=ImportError("boom")):
            assert _attempt_fallback_search("q", 5) == []

    def test_attribute_error_returns_empty(self, enable_fallback: Any) -> None:
        # Use a real module-like object so getattr() raises AttributeError naturally
        class _Empty:  # noqa: D401
            pass

        with patch("importlib.import_module", return_value=_Empty()):
            assert _attempt_fallback_search("q", 5) == []

    def test_generic_exception_returns_empty(self, enable_fallback: Any) -> None:
        with patch("importlib.import_module", side_effect=RuntimeError("boom")):
            assert _attempt_fallback_search("q", 5) == []

    def test_search_service_error_propagates(self, enable_fallback: Any) -> None:
        from tools.web_search_tool import SearchServiceError

        fake_instance = MagicMock()
        fake_instance._run.side_effect = SearchServiceError("upstream failure")
        fake_module = MagicMock()
        setattr(fake_module, "WebSearchTool", MagicMock(return_value=fake_instance))

        with patch("importlib.import_module", return_value=fake_module):
            with pytest.raises(SearchServiceError):
                _attempt_fallback_search("q", 5)

    def test_non_string_result_returns_empty(self, enable_fallback: Any) -> None:
        fake_instance = MagicMock()
        fake_instance._run.return_value = ["not a string"]
        fake_module = MagicMock()
        setattr(fake_module, "WebSearchTool", MagicMock(return_value=fake_instance))

        with patch("importlib.import_module", return_value=fake_module):
            assert _attempt_fallback_search("q", 5) == []


# ---------------------------------------------------------------------------
# Module-level payload helpers (direct unit tests)
# ---------------------------------------------------------------------------


class TestPayloadHelpers:
    @pytest.mark.asyncio
    async def test_semantic_payload_serialises_results(
        self, mock_vector_client: AsyncMock, sample_search_results: List[Dict[str, Any]]
    ) -> None:
        mock_vector_client.search_documents.return_value = sample_search_results
        raw = await _semantic_search_payload(
            mock_vector_client, query="q", limit=10, document_source=None
        )
        payload = json.loads(raw)
        assert payload["query"] == "q"
        assert payload["total_results"] == 3

    @pytest.mark.asyncio
    async def test_document_payload_includes_metadata(self, mock_vector_client: AsyncMock) -> None:
        mock_vector_client.search_documents.return_value = [{"id": "1"}]
        raw = await _document_search_payload(
            mock_vector_client, document_source="src", content_type="text", limit=10
        )
        payload = json.loads(raw)
        assert payload["document_source"] == "src"
        assert payload["content_type"] == "text"

    @pytest.mark.asyncio
    async def test_similarity_payload_truncates_preview(
        self, mock_vector_client: AsyncMock
    ) -> None:
        mock_vector_client.search_documents.return_value = []
        raw = await _similarity_search_payload(
            mock_vector_client, content="x" * 200, threshold=0.0, limit=5
        )
        payload = json.loads(raw)
        assert len(payload["reference_content"]) == 103
        assert payload["reference_content"].endswith("...")


# ---------------------------------------------------------------------------
# SearchTool.close()
# ---------------------------------------------------------------------------


class TestSearchToolClose:
    @pytest.mark.asyncio
    async def test_close_async_client(self) -> None:
        client = AsyncMock(spec=VectorDBClient)
        client.close = AsyncMock()
        SearchTool._instance = None
        with patch("tools.search_tool.VectorDBClient", return_value=client):
            facade = SearchTool()
            facade.vector_client = client  # ensure direct reference
        await facade.close()
        client.close.assert_awaited_once()
        SearchTool._instance = None

    @pytest.mark.asyncio
    async def test_close_sync_client(self) -> None:
        client = MagicMock(spec=VectorDBClient)
        # MagicMock.close is a sync MagicMock by default
        SearchTool._instance = None
        with patch("tools.search_tool.VectorDBClient", return_value=client):
            facade = SearchTool()
            facade.vector_client = client
        await facade.close()
        client.close.assert_called_once()
        SearchTool._instance = None

    @pytest.mark.asyncio
    async def test_close_no_client_is_noop(self) -> None:
        SearchTool._instance = None
        with patch("tools.search_tool.VectorDBClient"):
            facade = SearchTool()
        delattr(facade, "vector_client")
        await facade.close()  # should not raise
        SearchTool._instance = None

    @pytest.mark.asyncio
    async def test_close_client_without_close_method(self) -> None:
        client = MagicMock(spec=[])  # no close attribute
        SearchTool._instance = None
        with patch("tools.search_tool.VectorDBClient", return_value=client):
            facade = SearchTool()
            facade.vector_client = client
        await facade.close()  # should not raise
        SearchTool._instance = None
