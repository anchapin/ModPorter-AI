"""LangChain LCEL replacement for the legacy ``RAGCrew`` (issue #1201).

Exposes a deterministic researcher → writer chain composed of:
- ``SearchTool`` invoked with the user query (free-form input).
- A "researcher" prompt that turns search snippets into a structured summary.
- A "writer" prompt that turns the summary into the final user-facing answer.

The chain produces a plain ``str`` (not the legacy ``CrewOutput``).

Public entry points:
    build_rag_chain(llm=None, search_tool=None) -> Runnable
    invoke(query, *, llm=None, search_tool=None) -> str
    ainvoke(query, *, llm=None, search_tool=None) -> awaitable str

A custom ``llm`` may be passed for tests; otherwise the chain calls
``utils.rate_limiter.get_llm_backend()`` lazily on first invocation.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import (
    Runnable,
    RunnableLambda,
    RunnableParallel,
)

logger = logging.getLogger(__name__)

_PROMPT_DIR = Path(__file__).resolve().parent.parent / "prompts"
_RESEARCHER_PROMPT_FILE = _PROMPT_DIR / "rag_researcher.md"
_WRITER_PROMPT_FILE = _PROMPT_DIR / "rag_writer.md"


def _load_prompt(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def _format_search_results(raw: Any) -> str:
    """Render whatever the search tool returns as a human-readable context block."""
    if raw is None:
        return "(no results)"
    if isinstance(raw, str):
        # Search tools commonly emit JSON blobs as strings.
        try:
            parsed = json.loads(raw)
        except (ValueError, TypeError):
            return raw
        return _format_search_results(parsed)
    if isinstance(raw, dict):
        results = raw.get("results")
        if results is not None:
            return _format_search_results(results)
        return json.dumps(raw, indent=2, default=str)
    if isinstance(raw, list):
        if not raw:
            return "(no results)"
        chunks = []
        for i, item in enumerate(raw, start=1):
            if isinstance(item, dict):
                text = (
                    item.get("text")
                    or item.get("content")
                    or item.get("summary")
                    or json.dumps(item, default=str)
                )
                source = item.get("source") or item.get("url") or item.get("path") or ""
                header = f"[{i}] {source}".rstrip()
                chunks.append(f"{header}\n{text}")
            else:
                chunks.append(f"[{i}] {item}")
        return "\n\n".join(chunks)
    return str(raw)


def _resolve_search_tool(search_tool: Optional[Any]) -> Any:
    """Resolve to a search tool; default is the typed ``SemanticSearchTool``.

    After the typed-args-schema migration (Phase 8 A, issue #1201), the default
    semantic-search tool is itself a LangChain ``BaseTool``. Returning it
    directly routes the RAG search step through the primary ``BaseTool``
    branch in ``_make_search_step`` (Path 1) instead of the legacy descriptor
    branch (Path 2).
    """
    if search_tool is not None:
        return search_tool
    from tools.search_tool import SearchTool

    return SearchTool.get_instance().semantic_search


def _resolve_llm(llm: Optional[Any]) -> Any:
    if llm is not None:
        return llm
    from utils.rate_limiter import get_llm_backend

    return get_llm_backend()


def _make_search_step(search_tool: Optional[Any]) -> Runnable:
    """Return a Runnable that takes ``{query: str}`` and yields a context string.

    Supports three shapes:

    1. A LangChain ``BaseTool`` (preferred) — invoked via ``ainvoke`` /
       ``invoke`` with the typed args dict.
    2. The legacy ``tools.search_tool.SearchTool`` wrapper, whose
       ``semantic_search`` is a ``@tool``-decorated ``StructuredTool``
       — invoked through the descriptor's ``ainvoke``.
    3. Anything else exposing a ``search`` / callable interface — used as
       a last-resort sync fallback.
    """
    import inspect

    async def _search(payload: dict) -> str:
        query = payload["query"]
        tool = _resolve_search_tool(search_tool)

        # 1. LangChain BaseTool surface — async first.
        from langchain_core.tools import BaseTool as _LCBaseTool

        if isinstance(tool, _LCBaseTool):
            ainvoke = getattr(tool, "ainvoke", None)
            if ainvoke is not None:
                try:
                    raw = await ainvoke({"query": query})
                    return _format_search_results(raw)
                except Exception as e:  # pragma: no cover - depends on backend
                    logger.debug(f"BaseTool.ainvoke failed: {e}; falling through to sync invoke")
            invoke = getattr(tool, "invoke", None)
            if invoke is not None:
                try:
                    raw = invoke({"query": query})
                    return _format_search_results(raw)
                except Exception as e:  # pragma: no cover
                    logger.debug(f"BaseTool.invoke failed: {e}")

        # 2. Legacy SearchTool wrapper: prefer the @tool-decorated
        #    semantic_search descriptor (a StructuredTool) over the
        #    instance method.
        semantic = getattr(tool, "semantic_search", None) or getattr(
            type(tool), "semantic_search", None
        )
        if isinstance(semantic, _LCBaseTool):
            # The typed ``SemanticSearchTool`` accepts ``query``; older
            # ``query_data``-shaped descriptors (if any remain) are tried as
            # a final compatibility step.
            for kwargs in ({"query": query}, {"query_data": query}):
                try:
                    raw = await semantic.ainvoke(kwargs)
                    return _format_search_results(raw)
                except Exception as e:  # pragma: no cover
                    logger.debug(f"semantic_search.ainvoke({kwargs}) failed: {e}")

        # 3. Sync fallbacks for arbitrary search backends.
        for attr in ("search", "_run"):
            method = getattr(tool, attr, None)
            if method is None:
                continue
            try:
                raw = method(query)
                if inspect.isawaitable(raw):
                    raw = await raw
                return _format_search_results(raw)
            except Exception as e:  # pragma: no cover
                logger.debug(f"search tool method {attr} failed: {e}")
                continue

        logger.warning(
            "SearchTool exposed no recognised invocation method; returning empty context"
        )
        return "(no results)"

    return RunnableLambda(_search)


def build_rag_chain(
    llm: Optional[Any] = None,
    search_tool: Optional[Any] = None,
) -> Runnable:
    """Construct the researcher → writer LCEL chain.

    The resulting chain accepts ``{"query": str}`` (or a bare ``str`` via
    convenience wrappers below) and returns a string answer.
    """
    researcher_prompt = ChatPromptTemplate.from_template(_load_prompt(_RESEARCHER_PROMPT_FILE))
    writer_prompt = ChatPromptTemplate.from_template(_load_prompt(_WRITER_PROMPT_FILE))

    # Build a helper that resolves the LLM lazily so tests can swap it.
    def _bind_llm(_payload: dict) -> Any:
        return _resolve_llm(llm)

    # Stage 1: search → context string
    search_step = _make_search_step(search_tool)

    # Stage 2: researcher synthesises the search context
    researcher_step = (
        RunnableParallel(
            context=search_step,
            query=RunnableLambda(lambda payload: payload["query"]),
        )
        | researcher_prompt
        | RunnableLambda(lambda msg: _resolve_llm(llm).invoke(msg))
        | StrOutputParser()
    )

    # Stage 3: writer turns research summary into final answer
    writer_step = (
        RunnableParallel(
            research=researcher_step,
            query=RunnableLambda(lambda payload: payload["query"]),
        )
        | writer_prompt
        | RunnableLambda(lambda msg: _resolve_llm(llm).invoke(msg))
        | StrOutputParser()
    )

    return writer_step


def invoke(
    query: str,
    *,
    llm: Optional[Any] = None,
    search_tool: Optional[Any] = None,
) -> str:
    """Run the RAG chain synchronously and return the final answer string.

    The underlying chain has an async search step, so this helper drives
    it through ``asyncio.run`` (or ``loop.run_until_complete`` if a loop
    is already running) for callers in synchronous contexts.
    """
    import asyncio

    coro = ainvoke(query, llm=llm, search_tool=search_tool)
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No running loop — use asyncio.run.
        return asyncio.run(coro)
    # Inside an async context (e.g. uvicorn worker calling sync code) —
    # delegate via a fresh task on the running loop.
    return loop.run_until_complete(coro)


async def ainvoke(
    query: str,
    *,
    llm: Optional[Any] = None,
    search_tool: Optional[Any] = None,
) -> str:
    """Run the RAG chain asynchronously and return the final answer string."""
    chain = build_rag_chain(llm=llm, search_tool=search_tool)
    return await chain.ainvoke({"query": query})


__all__ = ["build_rag_chain", "invoke", "ainvoke"]
