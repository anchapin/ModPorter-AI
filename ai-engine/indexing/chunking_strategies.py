"""
Chunking strategies for intelligent document segmentation.

Provides three strategies:
- FixedSizeChunking: Split by character/token count
- SemanticChunking: Split at semantic boundaries (paragraphs, code blocks)
- RecursiveChunking: Hierarchical splitting using separators
"""

import re
import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any


class ChunkingStrategy(Enum):
    """Available chunking strategies."""

    FIXED = "fixed"
    SEMANTIC = "semantic"
    RECURSIVE = "recursive"


@dataclass
class Chunk:
    """Represents a document chunk with metadata."""

    content: str
    index: int
    total_chunks: int
    heading_context: List[str] = field(default_factory=list)
    original_heading: Optional[str] = None
    char_start: int = 0
    char_end: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def content_hash(self) -> str:
        """Generate unique hash for content deduplication."""
        return hashlib.md5(self.content.encode()).hexdigest()


class BaseChunkingStrategy(ABC):
    """Abstract base class for chunking strategies."""

    @abstractmethod
    def chunk(self, text: str, **kwargs) -> List[Chunk]:
        """
        Split text into chunks.

        Args:
            text: Input text to chunk
            **kwargs: Strategy-specific parameters

        Returns:
            List of Chunk objects
        """
        pass

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count (rough approximation: 1 token ≈ 4 chars)."""
        return len(text) // 4


class FixedSizeChunking(BaseChunkingStrategy):
    """
    Fixed-size chunking strategy.

    Splits text into chunks of fixed character/token count.
    """

    def chunk(self, text: str, chunk_size: int = 512, overlap: int = 50, **kwargs) -> List[Chunk]:
        """
        Split text into fixed-size chunks.

        Args:
            text: Input text
            chunk_size: Target chunk size in tokens (default: 512)
            overlap: Number of overlapping tokens between chunks (default: 50)

        Returns:
            List of Chunk objects
        """
        if not text:
            return []

        # Convert token size to character approximation
        char_size = chunk_size * 4
        char_overlap = overlap * 4

        chunks: List[Chunk] = []
        start = 0
        text_length = len(text)
        index = 0

        while start < text_length:
            end = min(start + char_size, text_length)

            # Try to break at word boundary if not at end
            if end < text_length:
                # Find last whitespace or newline
                last_space = max(
                    text.rfind(" ", start, end),
                    text.rfind("\n", start, end),
                    text.rfind(". ", start, end),
                )
                if last_space > start:
                    end = last_space + 1

            chunk_text = text[start:end]
            if chunk_text.strip():
                chunk = Chunk(
                    content=chunk_text,
                    index=index,
                    total_chunks=0,  # Will be updated after all chunks created
                    char_start=start,
                    char_end=end,
                    metadata={"strategy": ChunkingStrategy.FIXED.value},
                )
                chunks.append(chunk)

            index += 1
            start = end - char_overlap if end < text_length else text_length

        # Update total_chunks
        total = len(chunks)
        for chunk in chunks:
            chunk.total_chunks = total

        return chunks


class SemanticChunking(BaseChunkingStrategy):
    """
    Semantic chunking strategy.

    Splits text at semantic boundaries while respecting:
    - Paragraph boundaries
    - Code block boundaries
    - Heading hierarchy
    """

    def chunk(self, text: str, chunk_size: int = 512, overlap: int = 50, **kwargs) -> List[Chunk]:
        """
        Split text at semantic boundaries.

        Args:
            text: Input text
            chunk_size: Target chunk size in tokens (default: 512)
            overlap: Number of overlapping tokens between chunks (default: 50)

        Returns:
            List of Chunk objects
        """
        if not text:
            return []

        char_size = chunk_size * 4
        char_overlap = overlap * 4

        # Extract heading context throughout the text
        headings = self._extract_headings(text)

        # Split by semantic boundaries
        segments = self._split_by_semantics(text)

        chunks: List[Chunk] = []
        current_chunk = ""
        current_headings: List[str] = []
        start_pos = 0
        chunk_index = 0

        for segment in segments:
            segment_heading = headings.get(segment[:50], "")

            # Check if adding this segment would exceed chunk size
            if len(current_chunk) + len(segment) > char_size and current_chunk:
                # Save current chunk
                chunk = Chunk(
                    content=current_chunk.strip(),
                    index=chunk_index,
                    total_chunks=0,
                    heading_context=current_headings.copy(),
                    original_heading=current_headings[-1] if current_headings else None,
                    char_start=start_pos,
                    char_end=start_pos + len(current_chunk),
                    metadata={"strategy": ChunkingStrategy.SEMANTIC.value},
                )
                chunks.append(chunk)

                # Handle overlap
                overlap_text = current_chunk[-char_overlap:] if char_overlap > 0 else ""

                # Start new chunk
                chunk_index += 1
                current_chunk = overlap_text + segment
                start_pos = start_pos + len(current_chunk) - len(overlap_text)
                current_headings = [segment_heading] if segment_heading else []
            else:
                current_chunk += segment
                if segment_heading and segment_heading not in current_headings:
                    current_headings.append(segment_heading)

        # Add final chunk
        if current_chunk.strip():
            chunk = Chunk(
                content=current_chunk.strip(),
                index=chunk_index,
                total_chunks=0,
                heading_context=current_headings.copy(),
                original_heading=current_headings[-1] if current_headings else None,
                char_start=start_pos,
                char_end=start_pos + len(current_chunk),
                metadata={"strategy": ChunkingStrategy.SEMANTIC.value},
            )
            chunks.append(chunk)

        # Update total_chunks
        total = len(chunks)
        for chunk in chunks:
            chunk.total_chunks = total

        return chunks

    def _extract_headings(self, text: str) -> Dict[str, str]:
        """Extract headings and their content associations."""
        headings = {}
        current_heading = ""

        for line in text.split("\n"):
            stripped = line.strip()
            # Match markdown headings (# ## ### etc)
            heading_match = re.match(r"^(#{1,6})\s+(.+)$", stripped)
            if heading_match:
                current_heading = heading_match.group(2)
            elif current_heading and stripped:
                # Associate this content with the current heading
                if current_heading not in headings:
                    headings[stripped[:50]] = current_heading

        return headings

    def _split_by_semantics(self, text: str) -> List[str]:
        """Split text at semantic boundaries."""
        segments = []

        # Split by code blocks first (preserve them as atomic units)
        code_pattern = r"(```[\s\S]*?```|`[^`]+`)"
        parts = re.split(code_pattern, text)

        for part in parts:
            if not part.strip():
                continue

            # Check if it's a code block
            if part.startswith("```") or part.startswith("`"):
                segments.append(part)
            else:
                # Split by paragraphs (double newline)
                paragraphs = re.split(r"\n\s*\n", part)
                for para in paragraphs:
                    if para.strip():
                        segments.append(para.strip() + "\n")

        return segments


class RecursiveChunking(BaseChunkingStrategy):
    """
    Recursive chunking strategy.

    Hierarchically splits text using separators:
    1. Headings (# ## ###)
    2. Paragraphs (double newline)
    3. Sentences (periods)
    4. Words (whitespace)
    """

    DEFAULT_SEPARATORS = [
        "\n## ",
        "\n### ",
        "\n#### ",
        "\n##### ",
        "\n###### ",  # Headings
        "\n\n",  # Paragraphs
        ". ",
        "? ",
        "! ",  # Sentences
        " ",  # Words
    ]

    def chunk(
        self,
        text: str,
        chunk_size: int = 512,
        overlap: int = 50,
        separators: Optional[List[str]] = None,
        **kwargs,
    ) -> List[Chunk]:
        """
        Split text recursively using hierarchical separators.

        Args:
            text: Input text
            chunk_size: Target chunk size in tokens (default: 512)
            overlap: Number of overlapping tokens between chunks (default: 50)
            separators: Custom separators (default: DEFAULT_SEPARATORS)

        Returns:
            List of Chunk objects
        """
        if not text:
            return []

        char_size = chunk_size * 4
        char_overlap = overlap * 4
        sep_list = separators or self.DEFAULT_SEPARATORS

        # Build hierarchical chunks
        chunks = self._recursive_split(text, sep_list, char_size, [])

        # Post-process: merge small chunks and handle overlap
        merged_chunks = self._merge_and_overlap(chunks, char_overlap)

        # Assign indices
        total = len(merged_chunks)
        for i, chunk in enumerate(merged_chunks):
            chunk.index = i
            chunk.total_chunks = total

        return merged_chunks

    def _recursive_split(
        self, text: str, separators: List[str], max_size: int, heading_context: List[str]
    ) -> List[Chunk]:
        """Recursively split text using separators."""
        if not text or not separators:
            if text.strip():
                return [
                    Chunk(
                        content=text.strip(),
                        index=0,
                        total_chunks=0,
                        heading_context=heading_context.copy(),
                        char_start=0,
                        char_end=len(text),
                        metadata={"strategy": ChunkingStrategy.RECURSIVE.value},
                    )
                ]
            return []

        separator = separators[0]
        remaining_separators = separators[1:]

        # Check if text is small enough
        if len(text) <= max_size:
            return [
                Chunk(
                    content=text.strip(),
                    index=0,
                    total_chunks=0,
                    heading_context=heading_context.copy(),
                    char_start=0,
                    char_end=len(text),
                    metadata={"strategy": ChunkingStrategy.RECURSIVE.value},
                )
            ]

        # Split by current separator
        parts = text.split(separator)
        chunks = []
        current = ""
        current_headings = heading_context.copy()

        # Extract heading if this separator is a heading
        if separator.startswith("\n#"):
            for part in parts:
                if part.startswith("#"):
                    current_headings.append(part.strip("#").strip())
                    continue

                test_chunk = current + separator + part if current else part
                if len(test_chunk) > max_size and current:
                    chunks.extend(
                        self._recursive_split(
                            current, remaining_separators, max_size, current_headings
                        )
                    )
                    current = part
                else:
                    current = test_chunk

            if current:
                chunks.extend(
                    self._recursive_split(current, remaining_separators, max_size, current_headings)
                )
        else:
            for part in parts:
                test_chunk = current + separator + part if current else part
                if len(test_chunk) > max_size and current:
                    chunks.extend(
                        self._recursive_split(
                            current, remaining_separators, max_size, current_headings
                        )
                    )
                    current = part
                else:
                    current = test_chunk

            if current:
                chunks.extend(
                    self._recursive_split(current, remaining_separators, max_size, current_headings)
                )

        return chunks

    def _merge_and_overlap(self, chunks: List[Chunk], overlap: int) -> List[Chunk]:
        """Merge small chunks and add overlap."""
        if not chunks:
            return []

        merged = []
        current = chunks[0]

        for next_chunk in chunks[1:]:
            if len(current.content) < 200:  # Merge small chunks
                current = Chunk(
                    content=current.content + "\n" + next_chunk.content,
                    index=current.index,
                    total_chunks=0,
                    heading_context=current.heading_context,
                    char_start=current.char_start,
                    char_end=next_chunk.char_end,
                    metadata=current.metadata,
                )
            else:
                merged.append(current)
                current = next_chunk

        merged.append(current)
        return merged


class ChunkingStrategyFactory:
    """Factory for creating chunking strategy instances."""

    _strategies = {
        ChunkingStrategy.FIXED: FixedSizeChunking,
        ChunkingStrategy.SEMANTIC: SemanticChunking,
        ChunkingStrategy.RECURSIVE: RecursiveChunking,
    }

    @classmethod
    def create(cls, strategy: str, **kwargs) -> BaseChunkingStrategy:
        """
        Create a chunking strategy instance.

        Args:
            strategy: Strategy name ("fixed", "semantic", "recursive")
            **kwargs: Additional parameters for the strategy

        Returns:
            ChunkingStrategy instance

        Raises:
            ValueError: If strategy is not recognized
        """
        strategy_enum = ChunkingStrategy(strategy.lower())
        strategy_class = cls._strategies.get(strategy_enum)

        if not strategy_class:
            raise ValueError(f"Unknown strategy: {strategy}")

        return strategy_class()

    @classmethod
    def get_available_strategies(cls) -> List[str]:
        """Get list of available strategy names."""
        return [s.value for s in ChunkingStrategy]
