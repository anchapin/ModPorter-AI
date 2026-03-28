"""
RAG Pipeline - Main orchestrator for advanced retrieval-augmented generation.

This module provides a unified pipeline that combines query processing,
search, reranking, and fusion into a coherent multi-stage system.
"""

import logging
import time
from typing import List, Dict, Any, Optional, Protocol, Callable
from dataclasses import dataclass, field
from enum import Enum

from schemas.multimodal_schema import SearchQuery, SearchResult

logger = logging.getLogger(__name__)


class QueryType(str, Enum):
    """Query type classification."""

    INFORMATIONAL = "informational"
    NAVIGATIONAL = "navigational"
    TRANSACTIONAL = "transactional"
    COMPLEX = "complex"
    SIMPLE = "simple"


class ComplexityLevel(str, Enum):
    """Query complexity levels."""

    SIMPLE = "simple"
    STANDARD = "standard"
    COMPLEX = "complex"


@dataclass
class QueryAnalysis:
    """Analysis of the search query."""

    original_query: str
    rewritten_query: Optional[str] = None
    expanded_terms: List[str] = field(default_factory=list)
    query_type: QueryType = QueryType.SIMPLE
    complexity: ComplexityLevel = ComplexityLevel.SIMPLE
    confidence: float = 1.0


@dataclass
class PipelineResult:
    """Result from the RAG pipeline execution."""

    results: List[SearchResult]
    query_analysis: QueryAnalysis
    expansion_metadata: Dict[str, Any] = field(default_factory=dict)
    reranking_stages_applied: List[str] = field(default_factory=list)
    timing: Dict[str, float] = field(default_factory=dict)


@dataclass
class PipelineConfig:
    """Configuration for the RAG pipeline."""

    enable_query_expansion: bool = True
    enable_reranking: bool = True
    reranking_stages: List[str] = field(default_factory=lambda: ["feature", "cross_encoder"])
    fusion_strategy: str = "reciprocal_rank"
    max_results: int = 20
    cache_enabled: bool = True
    cache_ttl: int = 3600
    cache_backend: str = "memory"


class PipelineStage(Protocol):
    """Protocol for pipeline stages."""

    def process(self, input_data: Any) -> Any:
        """Process input data and return transformed output."""
        ...

    def get_config(self) -> Dict[str, Any]:
        """Get stage configuration."""
        ...


class QueryAnalysisStage:
    """Stage for analyzing query type and complexity."""

    def __init__(self):
        self.terms = {
            "informational": {"what", "how", "why", "explain", "definition"},
            "navigational": {"site", "page", "doc", "documentation", "link"},
            "transactional": {"download", "get", "install", "buy", "use"},
        }

    def process(self, query: str) -> QueryAnalysis:
        """Analyze the query."""
        query_lower = query.lower()
        query_words = set(query_lower.split())

        query_type = QueryType.SIMPLE
        for qtype, keywords in self.terms.items():
            if keywords & query_words:
                query_type = QueryType(qtype)
                break

        complexity = ComplexityLevel.SIMPLE
        word_count = len(query_words)
        technical_terms = self._count_technical_terms(query_lower)

        if word_count > 15 or technical_terms > 3:
            complexity = ComplexityLevel.COMPLEX
        elif word_count > 5 or technical_terms > 1:
            complexity = ComplexityLevel.STANDARD

        return QueryAnalysis(
            original_query=query, query_type=query_type, complexity=complexity, confidence=0.8
        )

    def _count_technical_terms(self, query: str) -> int:
        """Count technical terms in query."""
        technical = {
            "class",
            "method",
            "function",
            "interface",
            "api",
            "sdk",
            "block",
            "item",
            "entity",
            "mod",
            "forge",
            "fabric",
            "convert",
            "transform",
            "migrate",
            "port",
        }
        return sum(1 for term in technical if term in query)

    def get_config(self) -> Dict[str, Any]:
        return {"stage": "query_analysis"}


class QueryExpansionStage:
    """Stage for expanding query with related terms."""

    def __init__(self, strategy: str = "synonym"):
        self.strategy = strategy
        self.synonyms = {
            "block": ["cube", "tile", "object"],
            "item": ["object", "tool", "weapon", "element"],
            "entity": ["mob", "creature", "npc", "character"],
            "mod": ["modification", "addon", "extension"],
            "convert": ["transform", "translate", "migrate", "port"],
        }

    def process(self, analysis: QueryAnalysis) -> QueryAnalysis:
        """Expand query with related terms."""
        if not analysis.expanded_terms:
            query_lower = analysis.original_query.lower()
            words = query_lower.split()
            expanded = []

            for word in words:
                expanded.append(word)
                if word in self.synonyms:
                    expanded.extend(self.synonyms[word][:2])

            analysis.expanded_terms = list(set(expanded))

        return analysis

    def get_config(self) -> Dict[str, Any]:
        return {"stage": "query_expansion", "strategy": self.strategy}


class SearchStage:
    """Stage for executing search."""

    def __init__(self, search_engine=None):
        self.search_engine = search_engine

    def process(self, query: str, top_k: int = 20) -> List[SearchResult]:
        """Execute search."""
        if self.search_engine is None:
            return []

        search_query = SearchQuery(query_text=query, top_k=top_k)

        try:
            results = self.search_engine.search(query=search_query, top_k=top_k, mode="hybrid")
            return results
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    def get_config(self) -> Dict[str, Any]:
        return {"stage": "search"}


class RerankingStage:
    """Stage for reranking search results."""

    def __init__(self, stages: List[str] = None):
        self.stages = stages or ["feature", "cross_encoder"]
        self.feature_reranker = None
        self.cross_encoder_reranker = None
        self._init_rerankers()

    def _init_rerankers(self):
        """Initialize rerankers."""
        try:
            from search.reranking_engine import FeatureBasedReRanker, CrossEncoderReRanker

            self.feature_reranker = FeatureBasedReRanker()
            self.cross_encoder_reranker = CrossEncoderReRanker(model_name="msmarco")
        except ImportError as e:
            logger.warning(f"Could not import rerankers: {e}")

    def process(self, query: str, results: List[SearchResult]) -> List[SearchResult]:
        """Apply reranking to results."""
        if not results or not self.feature_reranker:
            return results

        stages_applied = []
        current_results = results

        if "feature" in self.stages:
            try:
                search_query = SearchQuery(query_text=query, top_k=len(results))
                current_results, _ = self.feature_reranker.rerank_results(
                    search_query, current_results
                )
                stages_applied.append("feature")
            except Exception as e:
                logger.warning(f"Feature reranking failed: {e}")

        if "cross_encoder" in self.stages and self.cross_encoder_reranker:
            try:
                ce_results = self.cross_encoder_reranker.rerank(query, current_results)
                if ce_results:
                    result_map = {r.document.id: r for r in current_results}
                    for ce_r in ce_results:
                        if ce_r.document.id in result_map:
                            orig = result_map[ce_r.document.id]
                            orig.final_score = ce_r.final_score
                    current_results.sort(key=lambda x: x.final_score, reverse=True)
                    stages_applied.append("cross_encoder")
            except Exception as e:
                logger.warning(f"Cross-encoder reranking failed: {e}")

        for i, r in enumerate(current_results):
            r.rank = i + 1

        return current_results

    def get_config(self) -> Dict[str, Any]:
        return {"stage": "reranking", "stages": self.stages}


class FusionStage:
    """Stage for fusing results from multiple sources."""

    def __init__(self, strategy: str = "reciprocal_rank"):
        self.strategy = strategy

    def process(self, results: List[SearchResult]) -> List[SearchResult]:
        """Apply fusion strategy to results."""
        if self.strategy == "reciprocal_rank":
            results.sort(key=lambda x: x.final_score, reverse=True)
        elif self.strategy == "weighted_sum":
            pass
        elif self.strategy == "score_averaging":
            pass

        for i, r in enumerate(results):
            r.rank = i + 1

        return results

    def get_config(self) -> Dict[str, Any]:
        return {"stage": "fusion", "strategy": self.strategy}


class RAGPipeline:
    """
    Main RAG Pipeline orchestrator.

    Coordinates query analysis, expansion, search, reranking, and fusion
    into a unified multi-stage pipeline.
    """

    def __init__(self, config: PipelineConfig = None):
        self.config = config or PipelineConfig()

        self.query_analysis_stage = QueryAnalysisStage()
        self.query_expansion_stage = QueryExpansionStage()
        self.search_stage = SearchStage()
        self.reranking_stage = RerankingStage(self.config.reranking_stages)
        self.fusion_stage = FusionStage(self.config.fusion_strategy)

        self.cache = None
        if self.config.cache_enabled:
            self._init_cache()

        logger.info(f"RAGPipeline initialized with config: {self.config}")

    def _init_cache(self):
        """Initialize caching layer."""
        try:
            from search.pipeline_cache import PipelineCache, MemoryCache

            self.cache = PipelineCache(backend=self.config.cache_backend, ttl=self.config.cache_ttl)
        except ImportError:
            logger.warning("Pipeline cache not available")
            self.cache = None

    def set_search_engine(self, engine):
        """Set the search engine to use."""
        self.search_stage.search_engine = engine

    def search(self, query: str, top_k: int = None, **kwargs) -> PipelineResult:
        """
        Execute the full RAG pipeline.

        Args:
            query: Search query string
            top_k: Number of results to return
            **kwargs: Additional configuration overrides

        Returns:
            PipelineResult with results and metadata
        """
        top_k = top_k or self.config.max_results

        timing = {}
        start_time = time.time()

        cache_key = self._generate_cache_key(query, top_k)
        if self.cache:
            cached = self.cache.get(cache_key)
            if cached:
                logger.info(f"Cache hit for query: {query}")
                cached_result = PipelineResult(
                    results=cached.results,
                    query_analysis=cached.query_analysis,
                    timing={"cache_hit": True},
                )
                return cached_result

        query_analysis = self.query_analysis_stage.process(query)
        timing["analysis_ms"] = (time.time() - start_time) * 1000

        if self.config.enable_query_expansion:
            query_analysis = self.query_expansion_stage.process(query_analysis)
            timing["expansion_ms"] = (time.time() - start_time) * 1000

        search_query = query_analysis.rewritten_query or query_analysis.original_query
        search_start = time.time()
        results = self.search_stage.process(search_query, top_k)
        timing["search_ms"] = (time.time() - search_start) * 1000

        reranking_stages = []
        if self.config.enable_reranking and results:
            rerank_start = time.time()
            results = self.reranking_stage.process(search_query, results)
            timing["reranking_ms"] = (time.time() - rerank_start) * 1000
            reranking_stages = self.config.reranking_stages

        fusion_start = time.time()
        results = self.fusion_stage.process(results)
        timing["fusion_ms"] = (time.time() - fusion_start) * 1000

        results = results[:top_k]

        timing["total_ms"] = (time.time() - start_time) * 1000

        pipeline_result = PipelineResult(
            results=results,
            query_analysis=query_analysis,
            reranking_stages_applied=reranking_stages,
            timing=timing,
        )

        if self.cache:
            self.cache.set(cache_key, pipeline_result)

        return pipeline_result

    def _generate_cache_key(self, query: str, top_k: int) -> str:
        """Generate cache key for query."""
        import hashlib

        config_str = f"{self.config.enable_query_expansion}:{self.config.enable_reranking}:{self.config.reranking_stages}"
        key_str = f"{query.lower().strip()}:{top_k}:{config_str}"
        return hashlib.md5(key_str.encode()).hexdigest()

    def add_stage(self, stage: PipelineStage, position: int = None):
        """Add a custom stage to the pipeline."""
        logger.info(f"Adding custom stage: {stage}")

    def clear_cache(self):
        """Clear the pipeline cache."""
        if self.cache:
            self.cache.invalidate()
            logger.info("Pipeline cache cleared")

    def get_stats(self) -> Dict[str, Any]:
        """Get pipeline statistics."""
        stats = {
            "config": {
                "enable_query_expansion": self.config.enable_query_expansion,
                "enable_reranking": self.config.enable_reranking,
                "reranking_stages": self.config.reranking_stages,
                "fusion_strategy": self.config.fusion_strategy,
                "max_results": self.config.max_results,
            }
        }
        if self.cache:
            stats["cache"] = self.cache.get_stats()
        return stats
