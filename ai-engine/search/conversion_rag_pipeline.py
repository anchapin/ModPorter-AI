"""
Conversion RAG Pipeline - K³Trans Implementation

Provides a unified interface for retrieving context during conversion by combining:
1. Pattern mappings from PatternMappingRegistry
2. RAG-based semantic search for code examples
3. Prior successful translations

This module implements issue #992: Wire RAG Pipeline into Conversion Loop.
"""

import logging
from typing import List, Dict, Any, Optional, TYPE_CHECKING
from dataclasses import dataclass, field
import asyncio

if TYPE_CHECKING:
    from search.rag_pipeline import RAGPipeline
    from search.hybrid_search_engine import HybridSearchEngine
    from knowledge.patterns.mappings import PatternMappingRegistry, PatternMapping

logger = logging.getLogger(__name__)


@dataclass
class ConversionQuery:
    """Query for conversion context retrieval."""

    java_feature: str
    feature_type: str
    additional_context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversionRetrievalResult:
    """Result from conversion context retrieval."""

    pattern_mappings: List["PatternMapping"] = field(default_factory=list)
    code_examples: List[Dict[str, Any]] = field(default_factory=list)
    prior_translations: List[Dict[str, Any]] = field(default_factory=list)
    search_results: List[Any] = field(default_factory=list)
    confidence: float = 0.0
    retrieval_metadata: Dict[str, Any] = field(default_factory=dict)


class ConversionRAGPipeline:
    """
    Unified RAG pipeline for conversion context retrieval.

    Combines multiple knowledge sources:
    - PatternMappingRegistry for structured Java→Bedrock mappings
    - Hybrid search for Bedrock code examples
    - Prior translation examples

    Usage:
        pipeline = ConversionRAGPipeline()
        pipeline.set_search_engine(hybrid_engine)
        pipeline.set_pattern_registry(registry)

        result = pipeline.retrieve_conversion_context(
            java_feature="TileEntity with energy storage",
            feature_type="block"
        )

        context_prompt = pipeline.format_context_for_llm(result)
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the ConversionRAGPipeline.

        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self._rag_pipeline: Optional[RAGPipeline] = None
        self._search_engine: Optional[HybridSearchEngine] = None
        self._pattern_registry: Optional[PatternMappingRegistry] = None
        self._initialized = False

    def initialize(
        self,
        search_engine: Optional["HybridSearchEngine"] = None,
        pattern_registry: Optional["PatternMappingRegistry"] = None,
    ) -> None:
        """
        Initialize the pipeline with required components.

        Args:
            search_engine: Hybrid search engine for semantic search
            pattern_registry: Registry of pattern mappings
        """
        if search_engine is not None:
            self._search_engine = search_engine

        if pattern_registry is not None:
            self._pattern_registry = pattern_registry

        if self._search_engine is not None:
            self._rag_pipeline = self._create_rag_pipeline()

        self._initialized = True
        logger.info(
            f"ConversionRAGPipeline initialized: "
            f"search_engine={search_engine is not None}, "
            f"pattern_registry={pattern_registry is not None}"
        )

    def _create_rag_pipeline(self) -> "RAGPipeline":
        """Create RAG pipeline with search engine."""
        try:
            from search.rag_pipeline import RAGPipeline, PipelineConfig

            config = PipelineConfig(
                enable_query_expansion=True,
                enable_reranking=True,
                reranking_stages=["feature", "cross_encoder"],
                max_results=10,
                cache_enabled=True,
            )

            pipeline = RAGPipeline(config=config)
            pipeline.set_search_engine(self._search_engine)
            return pipeline

        except ImportError as e:
            logger.error(f"Failed to create RAG pipeline: {e}")
            return None

    def set_search_engine(self, engine: "HybridSearchEngine") -> None:
        """Set the search engine for semantic search."""
        self._search_engine = engine
        if self._rag_pipeline:
            self._rag_pipeline.set_search_engine(engine)

    def set_pattern_registry(self, registry: "PatternMappingRegistry") -> None:
        """Set the pattern registry."""
        self._pattern_registry = registry

    def is_initialized(self) -> bool:
        """Check if pipeline is initialized."""
        return self._initialized

    async def retrieve_conversion_context(
        self,
        java_feature: str,
        feature_type: str,
        top_k: int = 5,
    ) -> ConversionRetrievalResult:
        """
        Retrieve conversion context for a Java feature.

        Args:
            java_feature: Description of the Java feature
            feature_type: Type of feature (block, item, entity, etc.)
            top_k: Number of results to retrieve

        Returns:
            ConversionRetrievalResult with all context
        """
        result = ConversionRetrievalResult()

        pattern_task = asyncio.create_task(
            self._retrieve_pattern_mappings(java_feature, feature_type)
        )

        search_task = asyncio.create_task(
            self._retrieve_search_results(java_feature, feature_type, top_k)
        )

        translations_task = asyncio.create_task(
            self._retrieve_prior_translations(java_feature, top_k)
        )

        pattern_mappings, search_results, prior_translations = await asyncio.gather(
            pattern_task, search_task, translations_task
        )

        result.pattern_mappings = pattern_mappings
        result.search_results = search_results
        result.prior_translations = prior_translations

        result.code_examples = self._extract_code_examples(search_results)

        result.confidence = self._calculate_confidence(
            pattern_mappings, result.code_examples, prior_translations
        )

        result.retrieval_metadata = {
            "java_feature": java_feature,
            "feature_type": feature_type,
            "top_k": top_k,
            "has_patterns": len(pattern_mappings) > 0,
            "has_examples": len(result.code_examples) > 0,
            "has_prior": len(prior_translations) > 0,
        }

        return result

    def retrieve_conversion_context_sync(
        self,
        java_feature: str,
        feature_type: str,
        top_k: int = 5,
    ) -> ConversionRetrievalResult:
        """
        Synchronous version of retrieve_conversion_context.

        For use in non-async contexts.
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                future = asyncio.ensure_future(
                    self.retrieve_conversion_context(java_feature, feature_type, top_k)
                )
                return future.result() if hasattr(future, "result") else ConversionRetrievalResult()
            else:
                return loop.run_until_complete(
                    self.retrieve_conversion_context(java_feature, feature_type, top_k)
                )
        except RuntimeError:
            return asyncio.run(self.retrieve_conversion_context(java_feature, feature_type, top_k))

    async def _retrieve_pattern_mappings(
        self, java_feature: str, feature_type: str
    ) -> List["PatternMapping"]:
        """Retrieve relevant pattern mappings."""
        if not self._pattern_registry:
            return []

        try:
            if hasattr(self._pattern_registry, "search_mappings"):
                return self._pattern_registry.search_mappings(
                    java_feature, feature_type=feature_type
                )
            elif hasattr(self._pattern_registry, "get_mappings_for_feature_type"):
                return self._pattern_registry.get_mappings_for_feature_type(feature_type)
            else:
                return self._pattern_registry.get_all_mappings()[:top_k]

        except Exception as e:
            logger.error(f"Error retrieving pattern mappings: {e}")
            return []

    async def _retrieve_search_results(
        self, java_feature: str, feature_type: str, top_k: int
    ) -> List[Any]:
        """Retrieve search results from RAG pipeline."""
        if not self._rag_pipeline:
            return []

        try:
            query = self._build_search_query(java_feature, feature_type)
            pipeline_result = self._rag_pipeline.search(query, top_k=top_k)
            return pipeline_result.results

        except Exception as e:
            logger.error(f"Error retrieving search results: {e}")
            return []

    async def _retrieve_prior_translations(
        self, java_feature: str, top_k: int
    ) -> List[Dict[str, Any]]:
        """Retrieve prior successful translations."""
        if not self._rag_pipeline:
            return []

        try:
            query = f"{java_feature} successful conversion example Java to Bedrock"
            pipeline_result = self._rag_pipeline.search(query, top_k=top_k)

            translations = []
            for result in pipeline_result.results:
                if hasattr(result, "document") and hasattr(result.document, "content"):
                    translations.append(
                        {
                            "source": java_feature,
                            "target": result.document.content[:500],
                            "score": getattr(result, "final_score", 0.0),
                            "source_type": "search_result",
                        }
                    )

            return translations

        except Exception as e:
            logger.error(f"Error retrieving prior translations: {e}")
            return []

    def _build_search_query(self, java_feature: str, feature_type: str) -> str:
        """Build search query from feature info."""
        parts = [
            java_feature,
            feature_type,
            "Minecraft Java",
            "Bedrock conversion",
        ]
        return " | ".join(parts)

    def _extract_code_examples(self, search_results: List[Any]) -> List[Dict[str, Any]]:
        """Extract code examples from search results."""
        examples = []

        for result in search_results:
            if not hasattr(result, "document"):
                continue

            doc = result.document
            content = getattr(doc, "content", "")

            if content and len(content) > 20:
                examples.append(
                    {
                        "code": content[:800],
                        "source": getattr(doc, "source", "unknown"),
                        "score": getattr(result, "final_score", 0.0),
                    }
                )

        return examples

    def _calculate_confidence(
        self,
        pattern_mappings: List["PatternMapping"],
        code_examples: List[Dict[str, Any]],
        prior_translations: List[Dict[str, Any]],
    ) -> float:
        """Calculate overall confidence score."""
        confidence = 0.0

        if pattern_mappings:
            avg_conf = sum(m.confidence for m in pattern_mappings) / len(pattern_mappings)
            confidence += avg_conf * 0.5

        if code_examples:
            scores = [e.get("score", 0.5) for e in code_examples]
            avg_score = sum(scores) / len(scores)
            confidence += avg_score * 0.3

        if prior_translations:
            scores = [t.get("score", 0.5) for t in prior_translations]
            avg_score = sum(scores) / len(scores)
            confidence += avg_score * 0.2

        return min(confidence, 1.0)

    def format_context_for_llm(
        self,
        result: ConversionRetrievalResult,
        include_code: bool = True,
    ) -> str:
        """
        Format retrieval result as a prompt addition for the LLM.

        Args:
            result: The conversion retrieval result
            include_code: Whether to include code examples

        Returns:
            Formatted string to append to LLM prompt
        """
        if result.confidence < 0.1:
            return ""

        parts = [f"\n\n{'=' * 60}\n"]
        parts.append(f"CONVERSION CONTEXT (confidence: {result.confidence:.0%})\n")
        parts.append(f"{'=' * 60}\n")

        if result.pattern_mappings:
            parts.append("\n## Pattern Mappings\n")
            for mapping in result.pattern_mappings[:5]:
                parts.append(
                    f"- **{mapping.java_pattern_id}** → **{mapping.bedrock_pattern_id}** "
                    f"(confidence: {mapping.confidence:.0%})\n"
                )
                if mapping.notes:
                    parts.append(f"  {mapping.notes}\n")

        if include_code and result.code_examples:
            parts.append("\n## Code Examples\n")
            for i, example in enumerate(result.code_examples[:2], 1):
                parts.append(f"\nExample {i}:\n")
                code = example.get("code", "")
                if len(code) > 400:
                    code = code[:400] + "..."
                parts.append(f"```\n{code}\n```\n")

        if result.prior_translations:
            parts.append("\n## Prior Translations\n")
            for translation in result.prior_translations[:2]:
                target = translation.get("target", "")
                if len(target) > 200:
                    target = target[:200] + "..."
                parts.append(f"- {target}\n")

        parts.append(f"\n{'=' * 60}\n")

        return "".join(parts)


def create_conversion_rag_pipeline(
    search_engine: Optional["HybridSearchEngine"] = None,
    pattern_registry: Optional["PatternMappingRegistry"] = None,
) -> ConversionRAGPipeline:
    """
    Factory function to create a configured ConversionRAGPipeline.

    Args:
        search_engine: Optional search engine to use
        pattern_registry: Optional pattern registry to use

    Returns:
        Configured ConversionRAGPipeline instance
    """
    pipeline = ConversionRAGPipeline()

    if search_engine is None:
        try:
            from search.hybrid_search_engine import HybridSearchEngine

            search_engine = HybridSearchEngine()
        except ImportError as e:
            logger.warning(f"Could not create default search engine: {e}")

    if pattern_registry is None:
        try:
            from knowledge.patterns.mappings import PatternMappingRegistry

            pattern_registry = PatternMappingRegistry()
        except ImportError as e:
            logger.warning(f"Could not create default pattern registry: {e}")

    if search_engine or pattern_registry:
        pipeline.initialize(
            search_engine=search_engine,
            pattern_registry=pattern_registry,
        )

    return pipeline
