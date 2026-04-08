"""
Performance benchmarking for document indexing.

Measures indexing throughput, chunking performance, and end-to-end
document processing speed to ensure ≥100 chunks/second target.
"""

import time
import sys
import os
from typing import List, Dict, Any
from dataclasses import dataclass

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from indexing.chunking_strategies import (
    ChunkingStrategyFactory,
    SemanticChunking,
)
from indexing.metadata_extractor import DocumentMetadataExtractor


@dataclass
class BenchmarkResult:
    """Result of a single benchmark run."""
    test_name: str
    duration_ms: float
    chunks_per_second: float
    total_chunks: int
    metadata: Dict[str, Any]


class IndexingBenchmark:
    """Benchmark document indexing performance."""

    def __init__(self):
        self.results: List[BenchmarkResult] = []

    def run_all_benchmarks(self) -> List[BenchmarkResult]:
        """Run all indexing benchmarks."""
        print("=" * 60)
        print("Document Indexing Performance Benchmarks")
        print("=" * 60)

        self.results = []

        # Benchmark 1: Chunking strategies
        self._benchmark_chunking_strategies()

        # Benchmark 2: Metadata extraction
        self._benchmark_metadata_extraction()

        # Benchmark 3: End-to-end indexing
        self._benchmark_end_to_end_indexing()

        # Print summary
        self._print_summary()

        return self.results

    def _benchmark_chunking_strategies(self):
        """Benchmark different chunking strategies."""
        print("\n--- Chunking Strategy Performance ---")

        # Generate test document (approximately 10,000 words)
        test_doc = self._generate_test_document(word_count=10000)

        strategies = [
            ("fixed", {"chunk_size": 512, "overlap": 50}),
            ("semantic", {"chunk_size": 512, "overlap": 50}),
            ("recursive", {"chunk_size": 512, "overlap": 50}),
        ]

        for strategy_name, params in strategies:
            strategy = ChunkingStrategyFactory.create(strategy_name)

            # Warm-up run
            strategy.chunk(test_doc[:1000], **params)

            # Benchmark run
            start = time.time()
            chunks = strategy.chunk(test_doc, **params)
            duration = (time.time() - start) * 1000  # Convert to ms

            chunks_per_sec = len(chunks) / (duration / 1000) if duration > 0 else 0

            result = BenchmarkResult(
                test_name=f"Chunking: {strategy_name}",
                duration_ms=duration,
                chunks_per_second=chunks_per_sec,
                total_chunks=len(chunks),
                metadata=params,
            )
            self.results.append(result)

            print(f"  {strategy_name}:")
            print(f"    Time: {duration:.2f}ms")
            print(f"    Chunks: {len(chunks)}")
            print(f"    Throughput: {chunks_per_sec:.0f} chunks/sec")

    def _benchmark_metadata_extraction(self):
        """Benchmark metadata extraction."""
        print("\n--- Metadata Extraction Performance ---")

        test_doc = self._generate_test_document(word_count=5000)
        extractor = DocumentMetadataExtractor()

        # Warm-up
        extractor.extract(test_doc[:1000])

        # Benchmark
        start = time.time()
        metadata = extractor.extract(test_doc, source="benchmark-doc")
        duration = (time.time() - start) * 1000

        print(f"  Metadata Extraction:")
        print(f"    Time: {duration:.2f}ms")
        print(f"    Document Type: {metadata.document_type.value}")
        print(f"    Tags Extracted: {len(metadata.tags)}")
        print(f"    Headings Found: {len(metadata.heading_hierarchy)}")

    def _benchmark_end_to_end_indexing(self):
        """Benchmark complete indexing pipeline."""
        print("\n--- End-to-End Indexing Performance ---")

        # Test documents of varying sizes
        test_cases = [
            ("Small Document", 1000),
            ("Medium Document", 5000),
            ("Large Document", 10000),
            ("Very Large Document", 25000),
        ]

        for doc_name, word_count in test_cases:
            test_doc = self._generate_test_document(word_count)

            # Extract metadata
            extractor = DocumentMetadataExtractor()
            start = time.time()
            _ = extractor.extract(test_doc, source="benchmark")
            extract_time = (time.time() - start) * 1000

            # Chunk document
            strategy = SemanticChunking()
            start = time.time()
            chunks = strategy.chunk(test_doc, chunk_size=512, overlap=50)
            chunk_time = (time.time() - start) * 1000

            # Calculate throughput
            total_time = (extract_time + chunk_time) / 1000  # Convert to seconds
            throughput = len(chunks) / total_time if total_time > 0 else 0

            result = BenchmarkResult(
                test_name=f"E2E: {doc_name}",
                duration_ms=extract_time + chunk_time,
                chunks_per_second=throughput,
                total_chunks=len(chunks),
                metadata={
                    "word_count": word_count,
                    "extract_time_ms": extract_time,
                    "chunk_time_ms": chunk_time,
                },
            )
            self.results.append(result)

            print(f"  {doc_name} ({word_count} words):")
            print(f"    Total Time: {extract_time + chunk_time:.2f}ms")
            print(f"    Extract Time: {extract_time:.2f}ms")
            print(f"    Chunk Time: {chunk_time:.2f}ms")
            print(f"    Chunks Created: {len(chunks)}")
            print(f"    Throughput: {throughput:.0f} chunks/sec")

            # Check if meets target
            if throughput >= 100:
                print(f"    ✓ Meets target (≥100 chunks/sec)")
            else:
                print(f"    ✗ Below target (≥100 chunks/sec)")

    def _generate_test_document(self, word_count: int) -> str:
        """Generate a test document with specified word count."""
        # Sample paragraphs with realistic structure
        paragraphs = [
            "Minecraft modding is an exciting way to customize your gameplay experience. "
            "By creating mods, you can add new blocks, items, mobs, and even entire dimensions to the game. "
            "The process begins with setting up a development environment using tools like Forge or Fabric.",

            "Java programming is the foundation of Minecraft modding. "
            "Understanding object-oriented programming concepts such as classes, inheritance, and polymorphism "
            "is essential for creating complex mods. Many modders start with simple block additions before "
            "moving on to more advanced features like custom entities and AI.",

            "```java\npublic class CustomBlock extends Block {\n    public CustomBlock() {\n        super(Properties.create(Material.ROCK));\n    }\n}\n```",

            "When developing mods, it's important to consider performance optimization. "
            "Efficient code ensures that your mod doesn't cause lag or framerate issues for players. "
            "Common optimization techniques include caching, lazy loading, and minimizing unnecessary calculations.",

            "## Advanced Modding Topics\n\n"
            "Once you've mastered the basics, you can explore advanced topics like:\n"
            "- Custom rendering and shaders\n"
            "- Network packets and multiplayer support\n"
            "- Custom data serializers\n"
            "- Dimension and biome creation",

            "Testing your mods thoroughly is crucial before release. "
            "Use JUnit for unit testing and consider integration testing with actual Minecraft instances. "
            "Many modders also find it helpful to get feedback from the community through beta testing programs.",
        ]

        # Generate document by repeating paragraphs
        document = ""
        words_added = 0
        para_index = 0

        while words_added < word_count:
            para = paragraphs[para_index % len(paragraphs)]
            document += para + "\n\n"
            words_added += len(para.split())
            para_index += 1

        return document

    def _print_summary(self):
        """Print benchmark summary."""
        print("\n" + "=" * 60)
        print("Benchmark Summary")
        print("=" * 60)

        # Calculate averages
        e2e_results = [r for r in self.results if r.test_name.startswith("E2E:")]
        if e2e_results:
            avg_throughput = sum(r.chunks_per_second for r in e2e_results) / len(e2e_results)
            print(f"\nAverage End-to-End Throughput: {avg_throughput:.0f} chunks/sec")

            if avg_throughput >= 100:
                print("✓ Performance target met (≥100 chunks/sec)")
            else:
                print("✗ Performance target not met (≥100 chunks/sec)")

        # Find slowest component
        if self.results:
            slowest = min(self.results, key=lambda r: r.chunks_per_second)
            print(f"\nSlowest Component: {slowest.test_name}")
            print(f"  Throughput: {slowest.chunks_per_second:.0f} chunks/sec")

        print("\n--- Detailed Results ---")
        for result in self.results:
            print(f"\n{result.test_name}:")
            print(f"  Duration: {result.duration_ms:.2f}ms")
            print(f"  Throughput: {result.chunks_per_second:.0f} chunks/sec")
            print(f"  Chunks: {result.total_chunks}")


def main():
    """Run benchmarks and check performance targets."""
    benchmark = IndexingBenchmark()
    results = benchmark.run_all_benchmarks()

    # Check if all E2E benchmarks meet target
    e2e_results = [r for r in results if r.test_name.startswith("E2E:")]
    if e2e_results:
        all_meet_target = all(r.chunks_per_second >= 100 for r in e2e_results)

        print("\n" + "=" * 60)
        if all_meet_target:
            print("✓ ALL BENCHMARKS PASSED")
            print("Indexing throughput meets ≥100 chunks/sec target")
            return 0
        else:
            print("✗ SOME BENCHMARKS FAILED")
            print("Some tests below ≥100 chunks/sec target")
            return 1

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
