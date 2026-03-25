"""
Benchmarking script for document indexing throughput.

Measures chunks/second performance for different chunking strategies.
"""

import time
import sys
import os

# Add ai-engine to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from indexing.chunking_strategies import (
    ChunkingStrategyFactory,
    ChunkingStrategy,
)
from indexing.metadata_extractor import DocumentMetadataExtractor


def generate_test_document(num_paragraphs: int = 100, words_per_paragraph: int = 50) -> str:
    """Generate a test document with specified number of paragraphs."""
    paragraphs = []
    for i in range(num_paragraphs):
        words = [f"word{j}" for j in range(words_per_paragraph)]
        para = f"Paragraph {i}: " + " ".join(words) + "."
        paragraphs.append(para)
    
    # Add headings
    doc = "# Test Document\n\n"
    for i, para in enumerate(paragraphs):
        if i % 10 == 0:
            doc += f"\n## Section {i // 10}\n\n"
        doc += para + "\n\n"
    
    return doc


def benchmark_chunking(
    strategy_name: str,
    document: str,
    chunk_size: int = 512,
    overlap: int = 50,
    iterations: int = 5
) -> dict:
    """Benchmark a specific chunking strategy."""
    times = []
    
    for _ in range(iterations):
        strategy = ChunkingStrategyFactory.create(strategy_name)
        
        start = time.perf_counter()
        chunks = strategy.chunk(document, chunk_size=chunk_size, overlap=overlap)
        end = time.perf_counter()
        
        times.append(end - start)
    
    avg_time = sum(times) / len(times)
    chunks_per_second = len(chunks) / avg_time if avg_time > 0 else 0
    
    return {
        "strategy": strategy_name,
        "chunks_created": len(chunks),
        "avg_time_seconds": avg_time,
        "chunks_per_second": chunks_per_second,
    }


def benchmark_metadata_extraction(document: str, iterations: int = 50) -> dict:
    """Benchmark metadata extraction."""
    extractor = DocumentMetadataExtractor()
    times = []
    
    for _ in range(iterations):
        start = time.perf_counter()
        metadata = extractor.extract(document)
        end = time.perf_counter()
        times.append(end - start)
    
    avg_time = sum(times) / len(times)
    
    return {
        "operation": "metadata_extraction",
        "avg_time_seconds": avg_time,
        "extractions_per_second": 1 / avg_time if avg_time > 0 else 0,
    }


def run_benchmarks():
    """Run all benchmarks."""
    print("=" * 60)
    print("Document Indexing Benchmark")
    print("=" * 60)
    
    # Generate test document
    print("\nGenerating test document...")
    document = generate_test_document(num_paragraphs=100, words_per_paragraph=50)
    print(f"Document size: {len(document)} characters")
    print(f"Word count: {len(document.split())} words")
    
    # Benchmark chunking strategies
    print("\n" + "-" * 40)
    print("Chunking Strategy Benchmarks")
    print("-" * 40)
    
    strategies = ["fixed", "semantic", "recursive"]
    results = []
    
    for strategy in strategies:
        result = benchmark_chunking(strategy, document, iterations=10)
        results.append(result)
        print(f"\n{result['strategy'].capitalize()} Chunking:")
        print(f"  Chunks created: {result['chunks_created']}")
        print(f"  Avg time: {result['avg_time_seconds']*1000:.2f} ms")
        print(f"  Throughput: {result['chunks_per_second']:.1f} chunks/second")
    
    # Check if we meet the target
    print("\n" + "-" * 40)
    print("Performance Target Check")
    print("-" * 40)
    target = 100  # chunks/second
    for result in results:
        status = "✓ PASS" if result['chunks_per_second'] >= target else "✗ FAIL"
        print(f"  {result['strategy']}: {result['chunks_per_second']:.1f} chunks/s - {status}")
    
    # Benchmark metadata extraction
    print("\n" + "-" * 40)
    print("Metadata Extraction Benchmark")
    print("-" * 40)
    
    meta_result = benchmark_metadata_extraction(document, iterations=50)
    print(f"\nMetadata Extraction:")
    print(f"  Avg time: {meta_result['avg_time_seconds']*1000:.2f} ms")
    print(f"  Throughput: {meta_result['extractions_per_second']:.1f} extractions/second")
    
    print("\n" + "=" * 60)
    print("Benchmark Complete")
    print("=" * 60)


if __name__ == "__main__":
    run_benchmarks()
