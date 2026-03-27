"""
Performance benchmarking for semantic search pipeline.

Measures latency for hybrid search, re-ranking, and query expansion
to validate the < 500ms performance target.
"""

import time
import asyncio
import statistics
from typing import Dict, List, Tuple
import sys
from pathlib import Path

# Add ai-engine to path
ai_engine_root = Path(__file__).parent.parent
sys.path.insert(0, str(ai_engine_root))

from search.hybrid_search_engine import HybridSearchEngine, SearchMode, RankingStrategy
from search.reranking_engine import CrossEncoderReRanker
from search.query_expansion import QueryExpansionEngine
from schemas.multimodal_schema import SearchQuery, MultiModalDocument, ContentType

# Import fixtures
sys.path.insert(0, str(Path(__file__).parent.parent / "tests"))
from fixtures.search_fixtures import mock_documents, mock_embeddings, test_queries


class SearchBenchmark:
    """Benchmark suite for search pipeline performance."""

    def __init__(self):
        self.engine = None
        self.reranker = None
        self.expander = None
        self.documents = None
        self.embeddings = None
        self.queries = None

    def setup(self):
        """Initialize search engines and test data."""
        print("Initializing search engines...")
        self.engine = HybridSearchEngine()
        self.reranker = CrossEncoderReRanker(model_name="msmarco")
        self.expander = QueryExpansionEngine()

        print("Loading test data...")
        # Import fixtures
        from fixtures.search_fixtures import mock_documents, mock_embeddings, test_queries

        self.documents = mock_documents()
        self.embeddings = mock_embeddings()
        self.queries = test_queries()

        # Build BM25 index
        if hasattr(self.engine, 'build_index'):
            self.engine.build_index(self.documents)
            print("BM25 index built")

        print(f"Setup complete: {len(self.documents)} documents, {len(self.queries)} test queries")

    def benchmark_query_expansion(self, num_runs: int = 10) -> Dict[str, float]:
        """Benchmark query expansion latency."""
        print(f"\n=== Query Expansion Benchmark ({num_runs} runs) ===")

        latencies = []
        for query_name, query_data in self.queries.items():
            for _ in range(num_runs):
                start_time = time.time()
                expanded = self.expander.expand_query(
                    SearchQuery(query_text=query_data["query"]),
                    strategies=["domain_expansion", "synonym_expansion"],
                    max_expansion_terms=10,
                )
                latency_ms = (time.time() - start_time) * 1000
                latencies.append(latency_ms)

        avg_latency = statistics.mean(latencies)
        median_latency = statistics.median(latencies)
        p95_latency = statistics.quantiles(latencies, n=20)[18]  # 95th percentile
        min_latency = min(latencies)
        max_latency = max(latencies)

        print(f"Average: {avg_latency:.2f}ms")
        print(f"Median: {median_latency:.2f}ms")
        print(f"95th percentile: {p95_latency:.2f}ms")
        print(f"Min: {min_latency:.2f}ms")
        print(f"Max: {max_latency:.2f}ms")

        return {
            "avg_ms": avg_latency,
            "median_ms": median_latency,
            "p95_ms": p95_latency,
            "min_ms": min_latency,
            "max_ms": max_latency,
        }

    async def benchmark_hybrid_search(self, num_runs: int = 10) -> Dict[str, float]:
        """Benchmark hybrid search latency."""
        print(f"\n=== Hybrid Search Benchmark ({num_runs} runs) ===")

        latencies = []
        results_counts = []

        # Use mock query embedding
        import random
        random.seed(123)
        query_embedding = [random.uniform(-1, 1) for _ in range(384)]
        norm = sum(x**2 for x in query_embedding) ** 0.5
        query_embedding = [x / norm for x in query_embedding]

        for query_name, query_data in self.queries.items():
            for _ in range(num_runs):
                start_time = time.time()
                search_results = await self.engine.search(
                    query=SearchQuery(query_text=query_data["query"], top_k=10),
                    documents=self.documents,
                    embeddings=self.embeddings,
                    query_embedding=query_embedding,
                    search_mode=SearchMode.HYBRID,
                    ranking_strategy=RankingStrategy.WEIGHTED_SUM,
                )
                latency_ms = (time.time() - start_time) * 1000
                latencies.append(latency_ms)
                results_counts.append(len(search_results))

        avg_latency = statistics.mean(latencies)
        median_latency = statistics.median(latencies)
        p95_latency = statistics.quantiles(latencies, n=20)[18]
        min_latency = min(latencies)
        max_latency = max(latencies)
        avg_results = statistics.mean(results_counts)

        print(f"Average: {avg_latency:.2f}ms")
        print(f"Median: {median_latency:.2f}ms")
        print(f"95th percentile: {p95_latency:.2f}ms")
        print(f"Min: {min_latency:.2f}ms")
        print(f"Max: {max_latency:.2f}ms")
        print(f"Avg results: {avg_results:.1f}")

        return {
            "avg_ms": avg_latency,
            "median_ms": median_latency,
            "p95_ms": p95_latency,
            "min_ms": min_latency,
            "max_ms": max_latency,
            "avg_results": avg_results,
        }

    def benchmark_reranking(self, num_candidates: int = 50, num_runs: int = 10) -> Dict[str, float]:
        """Benchmark cross-encoder re-ranking latency."""
        print(f"\n=== Re-ranking Benchmark ({num_runs} runs, {num_candidates} candidates) ===")

        # First, get search results to re-rank
        import random
        random.seed(123)
        query_embedding = [random.uniform(-1, 1) for _ in range(384)]
        norm = sum(x**2 for x in query_embedding) ** 0.5
        query_embedding = [x / norm for x in query_embedding]

        # Get search results asynchronously
        search_results = asyncio.run(self.engine.search(
            query=SearchQuery(query_text="custom block creation", top_k=num_candidates),
            documents=self.documents,
            embeddings=self.embeddings,
            query_embedding=query_embedding,
            search_mode=SearchMode.HYBRID,
        ))

        latencies = []
        for _ in range(num_runs):
            start_time = time.time()
            reranked_results = self.reranker.rerank(
                query="custom block creation",
                results=search_results[:num_candidates],
                top_k=10,
            )
            latency_ms = (time.time() - start_time) * 1000
            latencies.append(latency_ms)

        avg_latency = statistics.mean(latencies)
        median_latency = statistics.median(latencies)
        p95_latency = statistics.quantiles(latencies, n=20)[18]
        min_latency = min(latencies)
        max_latency = max(latencies)

        print(f"Average: {avg_latency:.2f}ms")
        print(f"Median: {median_latency:.2f}ms")
        print(f"95th percentile: {p95_latency:.2f}ms")
        print(f"Min: {min_latency:.2f}ms")
        print(f"Max: {max_latency:.2f}ms")

        return {
            "avg_ms": avg_latency,
            "median_ms": median_latency,
            "p95_ms": p95_latency,
            "min_ms": min_latency,
            "max_ms": max_latency,
        }

    async def benchmark_full_pipeline(self, num_runs: int = 10) -> Dict[str, float]:
        """
        Benchmark full search pipeline: expansion -> hybrid -> rerank.

        This is the critical test validating the < 500ms target.
        """
        print(f"\n=== Full Pipeline Benchmark ({num_runs} runs) ===")
        print("Pipeline: Query Expansion -> Hybrid Search -> Re-ranking")

        latencies = []
        breakdown = {
            "expansion_ms": [],
            "search_ms": [],
            "rerank_ms": [],
        }

        import random
        random.seed(123)
        query_embedding = [random.uniform(-1, 1) for _ in range(384)]
        norm = sum(x**2 for x in query_embedding) ** 0.5
        query_embedding = [x / norm for x in query_embedding]

        for query_name, query_data in list(self.queries.items())[:num_runs]:
            start_time = time.time()

            # Step 1: Query expansion
            step_start = time.time()
            expanded = self.expander.expand_query(
                SearchQuery(query_text=query_data["query"]),
                strategies=["domain_expansion", "synonym_expansion"],
                max_expansion_terms=10,
            )
            expansion_ms = (time.time() - step_start) * 1000
            breakdown["expansion_ms"].append(expansion_ms)

            # Step 2: Hybrid search
            step_start = time.time()
            search_results = await self.engine.search(
                query=SearchQuery(query_text=expanded.expanded_query, top_k=50),
                documents=self.documents,
                embeddings=self.embeddings,
                query_embedding=query_embedding,
                search_mode=SearchMode.HYBRID,
            )
            search_ms = (time.time() - step_start) * 1000
            breakdown["search_ms"].append(search_ms)

            # Step 3: Re-ranking
            step_start = time.time()
            reranked_results = self.reranker.rerank(
                query=expanded.expanded_query,
                results=search_results[:50],
                top_k=10,
            )
            rerank_ms = (time.time() - step_start) * 1000
            breakdown["rerank_ms"].append(rerank_ms)

            total_ms = (time.time() - start_time) * 1000
            latencies.append(total_ms)

        avg_latency = statistics.mean(latencies)
        median_latency = statistics.median(latencies)
        p95_latency = statistics.quantiles(latencies, n=20)[18]
        min_latency = min(latencies)
        max_latency = max(latencies)

        avg_expansion = statistics.mean(breakdown["expansion_ms"])
        avg_search = statistics.mean(breakdown["search_ms"])
        avg_rerank = statistics.mean(breakdown["rerank_ms"])

        print(f"\nTotal Latency:")
        print(f"  Average: {avg_latency:.2f}ms")
        print(f"  Median: {median_latency:.2f}ms")
        print(f"  95th percentile: {p95_latency:.2f}ms")
        print(f"  Min: {min_latency:.2f}ms")
        print(f"  Max: {max_latency:.2f}ms")

        print(f"\nBreakdown (Average):")
        print(f"  Query Expansion: {avg_expansion:.2f}ms ({avg_expansion/avg_latency*100:.1f}%)")
        print(f"  Hybrid Search: {avg_search:.2f}ms ({avg_search/avg_latency*100:.1f}%)")
        print(f"  Re-ranking: {avg_rerank:.2f}ms ({avg_rerank/avg_latency*100:.1f}%)")

        # Performance target validation
        print(f"\nPerformance Target (< 500ms):")
        if median_latency < 500:
            print(f"  ✅ PASS: Median latency {median_latency:.2f}ms < 500ms")
        else:
            print(f"  ❌ FAIL: Median latency {median_latency:.2f}ms >= 500ms")

        if p95_latency < 500:
            print(f"  ✅ PASS: 95th percentile {p95_latency:.2f}ms < 500ms")
        else:
            print(f"  ⚠️  WARN: 95th percentile {p95_latency:.2f}ms >= 500ms")

        return {
            "avg_ms": avg_latency,
            "median_ms": median_latency,
            "p95_ms": p95_latency,
            "min_ms": min_latency,
            "max_ms": max_latency,
            "breakdown": {
                "expansion_ms": avg_expansion,
                "search_ms": avg_search,
                "rerank_ms": avg_rerank,
            },
        }

    def print_summary(self, results: Dict[str, Dict[str, float]]):
        """Print benchmark summary."""
        print("\n" + "=" * 60)
        print("BENCHMARK SUMMARY")
        print("=" * 60)

        for benchmark_name, metrics in results.items():
            print(f"\n{benchmark_name}:")
            print(f"  Median: {metrics['median_ms']:.2f}ms")
            print(f"  95th %ile: {metrics['p95_ms']:.2f}ms")
            if "breakdown" in metrics:
                print(f"  Breakdown:")
                for step, latency in metrics["breakdown"].items():
                    print(f"    {step}: {latency:.2f}ms")

        print("\n" + "=" * 60)
        print("Performance Targets:")
        print("  Full Pipeline Median: < 500ms")
        print("  Full Pipeline 95th %ile: < 500ms")
        print("=" * 60)


async def main():
    """Run all benchmarks."""
    benchmark = SearchBenchmark()

    # Setup
    benchmark.setup()

    # Run benchmarks
    results = {}

    # Benchmark 1: Query expansion
    results["Query Expansion"] = benchmark.benchmark_query_expansion(num_runs=10)

    # Benchmark 2: Hybrid search
    results["Hybrid Search"] = await benchmark.benchmark_hybrid_search(num_runs=10)

    # Benchmark 3: Re-ranking
    results["Re-ranking (50 candidates)"] = benchmark.benchmark_reranking(
        num_candidates=50, num_runs=10
    )

    # Benchmark 4: Full pipeline (critical test)
    results["Full Pipeline"] = await benchmark.benchmark_full_pipeline(num_runs=10)

    # Print summary
    benchmark.print_summary(results)

    # Return results for programmatic access
    return results


if __name__ == "__main__":
    results = asyncio.run(main())
