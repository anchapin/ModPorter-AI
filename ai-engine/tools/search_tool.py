"""Typed ``BaseTool`` implementations for the RAG workflow (issue #1201, Phase 8 A).

This module exposes seven LangChain ``BaseTool`` subclasses backed by the
shared ``VectorDBClient``. Each tool declares a Pydantic ``args_schema`` so
chat models with native tool-calling can invoke it with structured arguments
instead of a JSON-encoded ``query_data: str`` blob.

Backwards compatibility:

* ``SearchTool`` is preserved as a facade. ``SearchTool.get_instance()`` still
  vends a process-wide singleton; ``SearchTool().get_tools()`` returns the
  seven typed ``BaseTool`` instances; ``SearchTool().semantic_search`` exposes
  the default ``SemanticSearchTool`` so the RAG service can route through
  the typed ``BaseTool`` branch of ``services.rag_service._make_search_step``.
"""

from __future__ import annotations

import asyncio
import importlib
import json
import logging
from typing import Any, ClassVar, Dict, List, Optional

from langchain_core.tools import BaseTool
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr

from utils.config import Config
from utils.vector_db_client import VectorDBClient

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pydantic args schemas
# ---------------------------------------------------------------------------


class SemanticSearchInput(BaseModel):
    """Args for ``SemanticSearchTool``."""

    model_config = ConfigDict(extra="forbid")
    query: str = Field(min_length=1, description="Free-text search query.")
    limit: int = Field(default=10, ge=1, le=50, description="Maximum results.")
    document_source: Optional[str] = Field(default=None, description="Optional source filter.")


class DocumentSearchInput(BaseModel):
    """Args for ``DocumentSearchTool``."""

    model_config = ConfigDict(extra="forbid")
    document_source: str = Field(min_length=1, description="Document source identifier.")
    content_type: Optional[str] = Field(
        default=None, description="Optional content-type filter applied client-side."
    )
    limit: int = Field(default=10, ge=1, le=50)


class SimilaritySearchInput(BaseModel):
    """Args for ``SimilaritySearchTool``."""

    model_config = ConfigDict(extra="forbid")
    content: str = Field(min_length=1, description="Reference content to match against.")
    threshold: float = Field(default=0.8, ge=0.0, le=1.0)
    limit: int = Field(default=10, ge=1, le=50)


class BedrockApiSearchInput(BaseModel):
    """Args for ``BedrockApiSearchTool``."""

    model_config = ConfigDict(extra="forbid")
    query: str = Field(min_length=1, description="Bedrock API search query.")
    api_category: Optional[str] = Field(
        default=None,
        description="Optional Bedrock category, e.g. 'Scripting API', 'Gametest Framework'.",
    )
    limit: int = Field(default=10, ge=1, le=50)


class ComponentLookupInput(BaseModel):
    """Args for ``ComponentLookupTool``."""

    model_config = ConfigDict(extra="forbid")
    component_name: str = Field(
        min_length=1,
        description="Bedrock component identifier, e.g. 'minecraft:behavior.float_wander'.",
    )
    limit: int = Field(default=5, ge=1, le=50)


class ConversionExamplesInput(BaseModel):
    """Args for ``ConversionExamplesTool``."""

    model_config = ConfigDict(extra="forbid")
    query: str = Field(min_length=1, description="Element / mechanic to convert.")
    limit: int = Field(default=5, ge=1, le=50)


class SchemaValidationLookupInput(BaseModel):
    """Args for ``SchemaValidationLookupTool``."""

    model_config = ConfigDict(extra="forbid")
    schema_name: str = Field(
        min_length=1, description="Bedrock JSON schema topic, e.g. 'entity definition'."
    )
    limit: int = Field(default=3, ge=1, le=50)


# ---------------------------------------------------------------------------
# Shared async helpers (single source of truth — no JSON re-encoding round-trip)
# ---------------------------------------------------------------------------


async def _semantic_search_payload(
    vector_client: VectorDBClient,
    *,
    query: str,
    limit: int,
    document_source: Optional[str] = None,
) -> str:
    """Run a semantic search and serialise the canonical response shape."""
    try:
        results = await vector_client.search_documents(
            query_text=query, top_k=limit, document_source_filter=document_source
        )
    except Exception as exc:
        logger.error("Semantic search execution failed: %s", exc)
        return json.dumps({"error": f"Semantic search failed: {exc}", "query": query})

    if not results and Config.SEARCH_FALLBACK_ENABLED:
        fallback = _attempt_fallback_search(query, limit)
        if fallback:
            results = fallback
            logger.info("Fallback search returned %d results", len(results))

    return json.dumps({"query": query, "results": results, "total_results": len(results)})


async def _document_search_payload(
    vector_client: VectorDBClient,
    *,
    document_source: str,
    content_type: Optional[str],
    limit: int,
) -> str:
    """Run a document-source search and serialise the canonical response shape."""
    try:
        results = await vector_client.search_documents(
            query_text=document_source, top_k=limit, document_source_filter=document_source
        )
        if content_type and results:
            results = [
                r
                for r in results
                if r.get("metadata", {}).get("content_type") == content_type
                or r.get("content_type") == content_type
            ]
    except Exception as exc:
        logger.error("Document search failed: %s", exc)
        return json.dumps(
            {"error": f"Document search failed: {exc}", "document_source": document_source}
        )

    if not results and Config.SEARCH_FALLBACK_ENABLED:
        fallback = _attempt_fallback_search(document_source, limit)
        if fallback:
            results = fallback
            logger.info("Fallback search returned %d results", len(results))

    return json.dumps(
        {
            "document_source": document_source,
            "content_type": content_type,
            "results": results,
            "total_results": len(results),
        }
    )


async def _similarity_search_payload(
    vector_client: VectorDBClient,
    *,
    content: str,
    threshold: float,
    limit: int,
) -> str:
    """Run a similarity search and serialise the canonical response shape."""
    try:
        results = await vector_client.search_documents(query_text=content, top_k=limit)
        if threshold > 0 and results:
            results = [r for r in results if r.get("similarity_score", 0.0) >= threshold]
    except Exception as exc:
        logger.error("Similarity search failed: %s", exc)
        return json.dumps(
            {"error": f"Similarity search failed: {exc}", "content_preview": content[:100]}
        )

    if not results and Config.SEARCH_FALLBACK_ENABLED:
        fallback = _attempt_fallback_search(content[:100], limit)
        if fallback:
            results = fallback
            logger.info("Fallback search returned %d results", len(results))

    preview = content[:100] + "..." if len(content) > 100 else content
    return json.dumps(
        {
            "reference_content": preview,
            "threshold": threshold,
            "results": results,
            "total_results": len(results),
        }
    )


def _attempt_fallback_search(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Attempt to use the configured fallback search tool.

    Mirrors the legacy behaviour: dynamically imports ``tools.<FALLBACK_SEARCH_TOOL>``,
    instantiates ``<PascalCase>``, and adapts the result into the standard schema.
    Returns ``[]`` on any failure so callers can surface "no results" cleanly.
    """
    if not Config.SEARCH_FALLBACK_ENABLED:
        logger.info("Fallback search is disabled")
        return []

    tool_name = Config.FALLBACK_SEARCH_TOOL
    module_path = f"tools.{tool_name}"
    class_name = "".join(part.capitalize() for part in tool_name.split("_"))
    logger.info("Attempting fallback search with %s.%s", module_path, class_name)

    try:
        module = importlib.import_module(module_path)
        fallback_class = getattr(module, class_name)
        fallback_instance = fallback_class()
        fallback_result = fallback_instance._run(query)
    except ImportError as exc:
        logger.error("Fallback module '%s' not found: %s", module_path, exc)
        return []
    except AttributeError as exc:
        logger.error("Fallback class '%s' not found in '%s': %s", class_name, module_path, exc)
        return []
    except Exception as exc:
        # Re-raise SearchServiceError so callers distinguish service failure from
        # genuinely empty results; everything else returns []. The import is local
        # to avoid pulling web_search_tool at module-load time.
        try:
            from tools.web_search_tool import SearchServiceError

            if isinstance(exc, SearchServiceError):
                raise
        except ImportError:
            pass
        logger.error("Error during fallback to %s: %s", tool_name, exc)
        return []

    if isinstance(fallback_result, str):
        return [
            {
                "id": "fallback_0",
                "content": fallback_result,
                "document_source": "fallback_search",
                "similarity_score": 0.7,
                "metadata": {
                    "indexed_at": "2025-01-09T00:00:00Z",
                    "content_type": "text",
                    "source": "fallback",
                },
            }
        ][:limit]
    return []


# ---------------------------------------------------------------------------
# Typed BaseTool subclasses
# ---------------------------------------------------------------------------


class _BaseSearchTool(BaseTool):
    """Common scaffolding: holds an injected ``VectorDBClient``.

    The injected client is stored as a ``PrivateAttr`` so it is not a Pydantic
    field and cannot accidentally appear in ``args_schema``.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)
    _vector_client: VectorDBClient = PrivateAttr()

    def __init__(self, vector_client: Optional[VectorDBClient] = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._vector_client = vector_client if vector_client is not None else VectorDBClient()

    @property
    def vector_client(self) -> VectorDBClient:
        """Public accessor for the injected client (used by tests)."""
        return self._vector_client

    @staticmethod
    def _run_async(coro: Any) -> Any:
        """Drive an awaitable from a sync caller; refuse if a loop is running."""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coro)
        raise RuntimeError(
            "Sync invoke() called from inside a running event loop; use ainvoke() instead."
        )


class SemanticSearchTool(_BaseSearchTool):
    """Perform semantic search across indexed documents."""

    name: str = "semantic_search"
    description: str = (
        "Perform semantic search across indexed documents. "
        "Args: query (str, required), limit (int 1-50, default 10), "
        "document_source (optional str)."
    )
    args_schema: ClassVar[type[BaseModel]] = SemanticSearchInput

    async def _arun(  # type: ignore[override]
        self,
        query: str,
        limit: int = 10,
        document_source: Optional[str] = None,
    ) -> str:
        return await _semantic_search_payload(
            self._vector_client,
            query=query,
            limit=limit,
            document_source=document_source,
        )

    def _run(  # type: ignore[override]
        self,
        query: str,
        limit: int = 10,
        document_source: Optional[str] = None,
    ) -> str:
        return self._run_async(
            self._arun(query=query, limit=limit, document_source=document_source)
        )


class DocumentSearchTool(_BaseSearchTool):
    """Search for documents by source identifier."""

    name: str = "document_search"
    description: str = (
        "Search for specific documents by source. "
        "Args: document_source (str, required), content_type (optional str), "
        "limit (int 1-50, default 10)."
    )
    args_schema: ClassVar[type[BaseModel]] = DocumentSearchInput

    async def _arun(  # type: ignore[override]
        self,
        document_source: str,
        content_type: Optional[str] = None,
        limit: int = 10,
    ) -> str:
        return await _document_search_payload(
            self._vector_client,
            document_source=document_source,
            content_type=content_type,
            limit=limit,
        )

    def _run(  # type: ignore[override]
        self,
        document_source: str,
        content_type: Optional[str] = None,
        limit: int = 10,
    ) -> str:
        return self._run_async(
            self._arun(document_source=document_source, content_type=content_type, limit=limit)
        )


class SimilaritySearchTool(_BaseSearchTool):
    """Find documents similar to a given content snippet."""

    name: str = "similarity_search"
    description: str = (
        "Find documents similar to a content snippet. "
        "Args: content (str, required), threshold (float 0.0-1.0, default 0.8), "
        "limit (int 1-50, default 10)."
    )
    args_schema: ClassVar[type[BaseModel]] = SimilaritySearchInput

    async def _arun(  # type: ignore[override]
        self,
        content: str,
        threshold: float = 0.8,
        limit: int = 10,
    ) -> str:
        return await _similarity_search_payload(
            self._vector_client, content=content, threshold=threshold, limit=limit
        )

    def _run(  # type: ignore[override]
        self,
        content: str,
        threshold: float = 0.8,
        limit: int = 10,
    ) -> str:
        return self._run_async(self._arun(content=content, threshold=threshold, limit=limit))


class BedrockApiSearchTool(_BaseSearchTool):
    """Search Bedrock Edition API documentation via semantic search."""

    name: str = "bedrock_api_search"
    description: str = (
        "Search Bedrock Edition API documentation. "
        "Args: query (str, required), api_category (optional str, e.g. 'Scripting API'), "
        "limit (int 1-50, default 10)."
    )
    args_schema: ClassVar[type[BaseModel]] = BedrockApiSearchInput

    async def _arun(  # type: ignore[override]
        self,
        query: str,
        api_category: Optional[str] = None,
        limit: int = 10,
    ) -> str:
        category_part = f" {api_category}" if api_category else ""
        formatted_query = f"Bedrock API{category_part} {query}".strip()
        logger.info("Bedrock API search for: %s", formatted_query)
        return await _semantic_search_payload(
            self._vector_client, query=formatted_query, limit=limit
        )

    def _run(  # type: ignore[override]
        self,
        query: str,
        api_category: Optional[str] = None,
        limit: int = 10,
    ) -> str:
        return self._run_async(self._arun(query=query, api_category=api_category, limit=limit))


class ComponentLookupTool(_BaseSearchTool):
    """Lookup documentation for a specific Bedrock component."""

    name: str = "component_lookup"
    description: str = (
        "Lookup Bedrock component documentation. "
        "Args: component_name (str, required), limit (int 1-50, default 5)."
    )
    args_schema: ClassVar[type[BaseModel]] = ComponentLookupInput

    async def _arun(  # type: ignore[override]
        self,
        component_name: str,
        limit: int = 5,
    ) -> str:
        formatted_query = f"Bedrock component documentation for {component_name}"
        logger.info("Component lookup for: %s", formatted_query)
        return await _semantic_search_payload(
            self._vector_client, query=formatted_query, limit=limit
        )

    def _run(  # type: ignore[override]
        self,
        component_name: str,
        limit: int = 5,
    ) -> str:
        return self._run_async(self._arun(component_name=component_name, limit=limit))


class ConversionExamplesTool(_BaseSearchTool):
    """Search Java→Bedrock conversion examples."""

    name: str = "conversion_examples"
    description: str = (
        "Search Java→Bedrock conversion examples. "
        "Args: query (str, required), limit (int 1-50, default 5)."
    )
    args_schema: ClassVar[type[BaseModel]] = ConversionExamplesInput

    async def _arun(  # type: ignore[override]
        self,
        query: str,
        limit: int = 5,
    ) -> str:
        formatted_query = f"Java to Bedrock conversion example for {query}"
        logger.info("Conversion examples search for: %s", formatted_query)
        return await _semantic_search_payload(
            self._vector_client, query=formatted_query, limit=limit
        )

    def _run(  # type: ignore[override]
        self,
        query: str,
        limit: int = 5,
    ) -> str:
        return self._run_async(self._arun(query=query, limit=limit))


class SchemaValidationLookupTool(_BaseSearchTool):
    """Lookup Bedrock JSON schema information."""

    name: str = "schema_validation_lookup"
    description: str = (
        "Lookup Bedrock JSON schema documentation. "
        "Args: schema_name (str, required), limit (int 1-50, default 3)."
    )
    args_schema: ClassVar[type[BaseModel]] = SchemaValidationLookupInput

    async def _arun(  # type: ignore[override]
        self,
        schema_name: str,
        limit: int = 3,
    ) -> str:
        formatted_query = f"Bedrock JSON schema for {schema_name}"
        logger.info("Schema validation lookup for: %s", formatted_query)
        return await _semantic_search_payload(
            self._vector_client, query=formatted_query, limit=limit
        )

    def _run(  # type: ignore[override]
        self,
        schema_name: str,
        limit: int = 3,
    ) -> str:
        return self._run_async(self._arun(schema_name=schema_name, limit=limit))


# ---------------------------------------------------------------------------
# Backwards-compatible facade
# ---------------------------------------------------------------------------


class SearchTool:
    """Process-wide facade preserved so existing call sites keep working.

    ``get_tools()`` returns ``BaseTool`` instances; ``get_instance()`` returns
    a process-wide singleton; ``semantic_search`` exposes the default typed
    semantic-search tool so the RAG service can dispatch via Path 1
    (``BaseTool.ainvoke``).
    """

    _instance: Optional[SearchTool] = None

    def __init__(self, vector_client: Optional[VectorDBClient] = None) -> None:
        self.vector_client = vector_client if vector_client is not None else VectorDBClient()
        self._semantic = SemanticSearchTool(vector_client=self.vector_client)
        self._document = DocumentSearchTool(vector_client=self.vector_client)
        self._similarity = SimilaritySearchTool(vector_client=self.vector_client)
        self._bedrock_api = BedrockApiSearchTool(vector_client=self.vector_client)
        self._component = ComponentLookupTool(vector_client=self.vector_client)
        self._conversion = ConversionExamplesTool(vector_client=self.vector_client)
        self._schema = SchemaValidationLookupTool(vector_client=self.vector_client)
        logger.info("SearchTool initialised with typed BaseTool implementations")

    @classmethod
    def get_instance(cls) -> SearchTool:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_tools(self) -> List[BaseTool]:
        return [
            self._semantic,
            self._document,
            self._similarity,
            self._bedrock_api,
            self._component,
            self._conversion,
            self._schema,
        ]

    @property
    def semantic_search(self) -> SemanticSearchTool:
        """Default semantic-search tool (typed ``BaseTool`` instance)."""
        return self._semantic

    @property
    def document_search(self) -> DocumentSearchTool:
        return self._document

    @property
    def similarity_search(self) -> SimilaritySearchTool:
        return self._similarity

    @property
    def bedrock_api_search(self) -> BedrockApiSearchTool:
        return self._bedrock_api

    @property
    def component_lookup(self) -> ComponentLookupTool:
        return self._component

    @property
    def conversion_examples(self) -> ConversionExamplesTool:
        return self._conversion

    @property
    def schema_validation_lookup(self) -> SchemaValidationLookupTool:
        return self._schema

    async def close(self) -> None:
        """Close the underlying vector database connection if applicable."""
        client = getattr(self, "vector_client", None)
        if client is None:
            return
        close_method = getattr(client, "close", None)
        if close_method is None:
            return
        if asyncio.iscoroutinefunction(close_method):
            await close_method()
        else:
            close_method()
        logger.info("SearchTool connections closed")


__all__ = [
    "SearchTool",
    "SemanticSearchTool",
    "DocumentSearchTool",
    "SimilaritySearchTool",
    "BedrockApiSearchTool",
    "ComponentLookupTool",
    "ConversionExamplesTool",
    "SchemaValidationLookupTool",
    "SemanticSearchInput",
    "DocumentSearchInput",
    "SimilaritySearchInput",
    "BedrockApiSearchInput",
    "ComponentLookupInput",
    "ConversionExamplesInput",
    "SchemaValidationLookupInput",
]


if __name__ == "__main__":  # pragma: no cover - manual smoke

    async def _demo() -> None:
        tool = SemanticSearchTool()
        for query in (
            "What are the latest advancements in AI?",
            "Tell me about Minecraft modding.",
        ):
            print(f"Query: {query}")
            print(await tool.ainvoke({"query": query}))
            print()

    asyncio.run(_demo())
