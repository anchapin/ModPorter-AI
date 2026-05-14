"""AI Engine service-layer package.

Houses thin LangChain/LangGraph LCEL chains and runnables that the
FastAPI/orchestration layer composes. Replaces the legacy
``ai-engine/crew`` package (issue #1201).

Public surface:

- ``services.rag_service``: LCEL RAG chain (replaces ``RAGCrew``).
- ``services.report_formatter``: PRD Feature 3 conversion-report builder.
- ``services.mvp_block_pipeline``: ``convert_block_mvp`` /
  ``convert_blocks_batch_mvp`` (replaces the same-named methods on the
  legacy crew).
"""

from services.mvp_block_pipeline import convert_block_mvp, convert_blocks_batch_mvp
from services.report_formatter import create_failure_response, format_conversion_report
from services.rag_service import ainvoke as rag_ainvoke, build_rag_chain, invoke as rag_invoke

__all__ = [
    "convert_block_mvp",
    "convert_blocks_batch_mvp",
    "create_failure_response",
    "format_conversion_report",
    "build_rag_chain",
    "rag_invoke",
    "rag_ainvoke",
]
