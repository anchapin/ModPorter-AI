"""
Document indexing module for intelligent chunking, metadata extraction,
and hierarchical indexing.

This module provides:
- Chunking strategies (FixedSize, Semantic, Recursive)
- Metadata extraction for documents
- Hierarchical indexing support
- Chunk prioritization for relevance ranking
"""

from .chunk_prioritizer import (
    ChunkPrioritizer,
    RelevanceScore,
)
from .chunking_strategies import (
    Chunk,
    ChunkingStrategy,
    ChunkingStrategyFactory,
    FixedSizeChunking,
    RecursiveChunking,
    SemanticChunking,
)
from .metadata_extractor import (
    ChunkMetadata,
    DocumentMetadata,
    DocumentMetadataExtractor,
)

__all__ = [
    "ChunkingStrategy",
    "FixedSizeChunking",
    "SemanticChunking",
    "RecursiveChunking",
    "ChunkingStrategyFactory",
    "Chunk",
    "DocumentMetadataExtractor",
    "ChunkMetadata",
    "DocumentMetadata",
    "ChunkPrioritizer",
    "RelevanceScore",
]
