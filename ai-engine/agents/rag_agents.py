"""
RAG agents module for retrieval-augmented generation tasks.

This module provides LangChain-based runnables for search and
summarization tasks. It replaces the previous LangChain agent runnable wrappers
(see issue #1201 — LangChain/LangGraph migration).

Prefer ``services.rag_service`` for production use; this module
exists for backwards compatibility with callers that still ask for
named agent runnables.
"""

from __future__ import annotations

import logging
from typing import Any, List, Optional

logger = logging.getLogger(__name__)


_RESEARCH_PROMPT = (
    "You are an expert researcher skilled at finding and organizing "
    "information from available sources. Use the provided context to "
    "answer the user's question accurately and concisely.\n\n"
    "Context:\n{context}\n\nQuestion: {query}\n\nAnswer:"
)

_SUMMARIZE_PROMPT = (
    "You are an expert at distilling complex information into clear, "
    "concise summaries. Summarize the following content in a way that "
    "preserves the key technical details.\n\nContent:\n{content}\n\nSummary:"
)


class RAGAgents:
    """RAG agents for search and summarization, returning LangChain runnables.

    The returned objects are ``langchain_core.runnables.Runnable`` instances
    suitable for composition into LCEL chains. Tools, when supplied, are
    bound to the chat model via ``llm.bind_tools(tools)`` so the runnable
    can perform tool-calling.
    """

    def __init__(self) -> None:
        pass

    def search_agent(
        self,
        llm: Any,
        tools: Optional[List[Any]] = None,
    ) -> Any:
        """Create a search-oriented runnable.

        Args:
            llm: A LangChain-compatible chat model
                (``langchain_core.language_models.BaseChatModel``).
            tools: Optional list of LangChain tools to bind to the model
                for tool-calling.

        Returns:
            A LangChain runnable that accepts ``{"context": str, "query": str}``
            and returns a string answer.
        """
        from langchain_core.output_parsers import StrOutputParser
        from langchain_core.prompts import ChatPromptTemplate

        prompt = ChatPromptTemplate.from_template(_RESEARCH_PROMPT)
        bound = llm.bind_tools(tools) if tools and hasattr(llm, "bind_tools") else llm
        return prompt | bound | StrOutputParser()

    def summarization_agent(self, llm: Any) -> Any:
        """Create a summarization runnable.

        Args:
            llm: A LangChain-compatible chat model.

        Returns:
            A LangChain runnable that accepts ``{"content": str}``
            and returns a string summary.
        """
        from langchain_core.output_parsers import StrOutputParser
        from langchain_core.prompts import ChatPromptTemplate

        prompt = ChatPromptTemplate.from_template(_SUMMARIZE_PROMPT)
        return prompt | llm | StrOutputParser()
