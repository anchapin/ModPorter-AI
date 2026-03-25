"""
Document indexing module for intelligent chunking, metadata extraction,
and hierarchical indexing.

This module provides:
- Chunking strategies (FixedSize, Semantic, Recursive)
- Metadata extraction for documents
- Hierarchical indexing support
"""

from .chunking_strategies import (
    ChunkingStrategy,
    FixedSizeChunking,
    SemanticChunking,
    RecursiveChunking,
    ChunkingStrategyFactory,
    Chunk,
)
from .metadata_extractor import (
    DocumentMetadataExtractor,
    ChunkMetadata,
    DocumentMetadata,
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
]
