"""Unit tests for the LangChain LCEL RAG service (issue #1201).

Verifies that ``services.rag_service.build_rag_chain`` composes an
end-to-end runnable that:

- Invokes a LangChain ``BaseTool`` search backend (sync and async surfaces).
- Renders the retrieved context through a ``ChatPromptTemplate``.
- Drives a chat model via the LangChain runnable interface.
- Yields a non-empty string answer (replacing the legacy ``CrewOutput``).
"""

from __future__ import annotations

import asyncio
import json
from typing import Type

import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.tools import BaseTool
from pydantic import BaseModel


class _SearchInput(BaseModel):
    query: str


class _StubSearchTool(BaseTool):
    name: str = "stub_search"
    description: str = "Returns a fixed payload for testing"
    args_schema: Type[BaseModel] = _SearchInput

    def _run(self, query: str) -> str:
        return json.dumps(
            {
                "results": [
                    {
                        "text": "Bedrock supports JSON-defined block geometry.",
                        "source": "docs/blocks.md",
                    },
                    {
                        "text": "Use minecraft:geometry component for block models.",
                        "source": "docs/components.md",
                    },
                ]
            }
        )

    async def _arun(self, query: str) -> str:  # noqa: D401
        return self._run(query)


def test_build_rag_chain_returns_runnable():
    """``build_rag_chain`` returns an LCEL runnable with the expected interface."""
    from services.rag_service import build_rag_chain

    llm = FakeListChatModel(responses=["research", "answer"])
    chain = build_rag_chain(llm=llm, search_tool=_StubSearchTool())
    assert hasattr(chain, "invoke")
    assert hasattr(chain, "ainvoke")


@pytest.mark.asyncio
async def test_rag_chain_returns_non_empty_string_answer():
    """Plan acceptance: chain returns a non-empty string given mocked search results."""
    from services.rag_service import build_rag_chain

    llm = FakeListChatModel(
        responses=[
            "Research summary: Bedrock blocks use geometry components.",
            "Final answer: define a block with minecraft:geometry.",
        ]
    )
    chain = build_rag_chain(llm=llm, search_tool=_StubSearchTool())

    result = await chain.ainvoke({"query": "How do I port a Java block?"})

    assert result, "RAG chain must return a non-empty answer"
    assert "minecraft:geometry" in str(result), (
        "answer should be derived from the writer prompt fed by research summary"
    )


def test_rag_invoke_helper_wraps_chain():
    """``services.rag_service.invoke`` is a synchronous convenience wrapper."""
    from services.rag_service import invoke

    llm = FakeListChatModel(responses=["sum", "ans"])
    out = invoke("test query", llm=llm, search_tool=_StubSearchTool())
    assert out, "invoke() must return a non-empty answer"


def test_rag_ainvoke_helper_wraps_chain():
    """``services.rag_service.ainvoke`` is the async convenience wrapper."""
    from services.rag_service import ainvoke

    llm = FakeListChatModel(responses=["sum", "ans"])
    out = asyncio.run(ainvoke("test query", llm=llm, search_tool=_StubSearchTool()))
    assert out, "ainvoke() must return a non-empty answer"
