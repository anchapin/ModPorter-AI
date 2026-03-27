"""
Dynamic context manager for RAG system.

This module provides:
- DynamicContextSizer: Adjusts context window based on query complexity
- ContextManager: Manages multi-turn conversation context
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum

from search.query_complexity_analyzer import ComplexityLevel


class ContextStrategy(Enum):
    """Strategy for context window sizing."""

    FIXED = "fixed"
    DYNAMIC = "dynamic"
    ADAPTIVE = "adaptive"


@dataclass
class ContextConfig:
    """Configuration for context window sizing."""

    max_tokens: int
    overlap_tokens: int
    min_chunks: int
    max_chunks: int

    def __repr__(self) -> str:
        return (
            f"ContextConfig(tokens={self.max_tokens}, chunks={self.min_chunks}-{self.max_chunks})"
        )


@dataclass
class Turn:
    """Represents a single conversation turn."""

    user_query: str
    assistant_response: str
    timestamp: float = 0.0
    complexity: Optional[ComplexityLevel] = None
    context_used: Optional[Dict[str, Any]] = None


class DynamicContextSizer:
    """
    Dynamically adjusts context window size based on query complexity.

    Configuration by complexity level:
    - SIMPLE: max_tokens=1000, min_chunks=2, max_chunks=5
    - STANDARD: max_tokens=2000, min_chunks=3, max_chunks=10
    - COMPLEX: max_tokens=4000, min_chunks=5, max_chunks=20
    """

    # Default configurations per complexity level
    DEFAULT_CONFIGS = {
        ComplexityLevel.SIMPLE: ContextConfig(
            max_tokens=1000, overlap_tokens=50, min_chunks=2, max_chunks=5
        ),
        ComplexityLevel.STANDARD: ContextConfig(
            max_tokens=2000, overlap_tokens=75, min_chunks=3, max_chunks=10
        ),
        ComplexityLevel.COMPLEX: ContextConfig(
            max_tokens=4000, overlap_tokens=100, min_chunks=5, max_chunks=20
        ),
    }

    def __init__(self, custom_configs: Optional[Dict[ComplexityLevel, ContextConfig]] = None):
        """
        Initialize the context sizer.

        Args:
            custom_configs: Optional custom configurations per complexity level
        """
        self.configs = self.DEFAULT_CONFIGS.copy()
        if custom_configs:
            self.configs.update(custom_configs)

    def get_config(self, complexity: ComplexityLevel) -> ContextConfig:
        """
        Get context configuration for a complexity level.

        Args:
            complexity: The query complexity level

        Returns:
            ContextConfig for the given complexity
        """
        return self.configs.get(complexity, self.DEFAULT_CONFIGS[ComplexityLevel.STANDARD])

    def calculate_chunks(
        self,
        available_chunks: List[Any],
        config: ContextConfig,
        relevance_scores: Optional[List[float]] = None,
    ) -> List[Any]:
        """
        Select and order chunks based on context config.

        Args:
            available_chunks: List of available chunks
            config: Context configuration
            relevance_scores: Optional relevance scores for prioritization

        Returns:
            Selected and ordered list of chunks
        """
        if not available_chunks:
            return []

        # Ensure we don't exceed max_chunks
        max_chunks = min(config.max_chunks, len(available_chunks))

        # If no relevance scores, take first chunks (position-based)
        if relevance_scores is None:
            selected = available_chunks[:max_chunks]
        else:
            # Sort by relevance scores (descending) if provided
            if len(relevance_scores) != len(available_chunks):
                # Fall back to position-based if mismatch
                selected = available_chunks[:max_chunks]
            else:
                # Combine position and relevance for final selection
                scored_chunks = list(zip(available_chunks, relevance_scores))
                # Sort by relevance score descending
                scored_chunks.sort(key=lambda x: x[1], reverse=True)
                selected = [chunk for chunk, _ in scored_chunks[:max_chunks]]

        # Ensure minimum chunks
        if len(selected) < config.min_chunks and len(available_chunks) >= config.min_chunks:
            # Add more chunks if needed to meet minimum
            remaining = [c for c in available_chunks if c not in selected]
            needed = config.min_chunks - len(selected)
            selected.extend(remaining[:needed])

        return selected

    def adjust_config(
        self,
        complexity: ComplexityLevel,
        token_budget: Optional[int] = None,
        chunk_budget: Optional[int] = None,
    ) -> ContextConfig:
        """
        Adjust configuration based on available budget.

        Args:
            complexity: Base complexity level
            token_budget: Optional token budget override
            chunk_budget: Optional chunk budget override

        Returns:
            Adjusted ContextConfig
        """
        config = self.get_config(complexity)

        if token_budget is not None:
            config.max_tokens = min(config.max_tokens, token_budget)

        if chunk_budget is not None:
            config.max_chunks = min(config.max_chunks, chunk_budget)
            config.min_chunks = min(config.min_chunks, config.max_chunks)

        return config


class ContextManager:
    """
    Manages multi-turn conversation context.

    Features:
    - Maintains conversation history
    - Respects token budget when trimming
    - Provides context window for RAG queries
    """

    DEFAULT_MAX_TURNS = 5
    DEFAULT_TOKEN_BUDGET = 8000

    def __init__(
        self,
        max_turns: int = DEFAULT_MAX_TURNS,
        token_budget: int = DEFAULT_TOKEN_BUDGET,
        context_sizer: Optional[DynamicContextSizer] = None,
    ):
        """
        Initialize the context manager.

        Args:
            max_turns: Maximum number of conversation turns to keep
            token_budget: Maximum tokens for conversation history
            context_sizer: Optional context sizer for dynamic sizing
        """
        self.max_turns = max_turns
        self.token_budget = token_budget
        self.context_sizer = context_sizer or DynamicContextSizer()
        self.turns: List[Turn] = []
        self._total_tokens = 0

    def add_turn(
        self,
        user_query: str,
        assistant_response: str,
        complexity: Optional[ComplexityLevel] = None,
        context_used: Optional[Dict[str, Any]] = None,
        timestamp: float = 0.0,
    ) -> None:
        """
        Add a conversation turn.

        Args:
            user_query: The user's query
            assistant_response: The assistant's response
            complexity: Query complexity level (optional)
            context_used: Context information used (optional)
            timestamp: Turn timestamp (optional)
        """
        # Estimate tokens (rough: 1 token ≈ 4 chars)
        query_tokens = len(user_query) // 4
        response_tokens = len(assistant_response) // 4
        turn_tokens = query_tokens + response_tokens

        turn = Turn(
            user_query=user_query,
            assistant_response=assistant_response,
            complexity=complexity,
            context_used=context_used,
            timestamp=timestamp,
        )

        self.turns.append(turn)
        self._total_tokens += turn_tokens

        # Trim if exceeding limits
        self._trim_if_needed()

    def _trim_if_needed(self) -> None:
        """Trim conversation history if exceeding limits."""
        # Check turn count limit
        while len(self.turns) > self.max_turns:
            removed = self.turns.pop(0)
            self._total_tokens -= (len(removed.user_query) + len(removed.assistant_response)) // 4

        # Check token budget
        while self._total_tokens > self.token_budget and len(self.turns) > 1:
            removed = self.turns.pop(0)
            self._total_tokens -= (len(removed.user_query) + len(removed.assistant_response)) // 4

    def get_context_window(
        self, include_recent: Optional[int] = None, include_all: bool = False
    ) -> List[Turn]:
        """
        Get the context window of conversation turns.

        Args:
            include_recent: Number of recent turns to include (None = use max_turns)
            include_all: If True, include all turns regardless of limit

        Returns:
            List of conversation turns
        """
        if include_all:
            return self.turns.copy()

        if include_recent is not None:
            return self.turns[-include_recent:] if include_recent > 0 else []

        return self.turns.copy()

    def get_context_text(self, include_recent: Optional[int] = None) -> str:
        """
        Get context as formatted text.

        Args:
            include_recent: Number of recent turns to include

        Returns:
            Formatted context string
        """
        turns = self.get_context_window(include_recent=include_recent)

        if not turns:
            return ""

        lines = ["Conversation History:"]
        for i, turn in enumerate(turns, 1):
            lines.append(f"\n--- Turn {i} ---")
            lines.append(f"User: {turn.user_query}")
            lines.append(f"Assistant: {turn.assistant_response}")

        return "\n".join(lines)

    def get_relevant_context(self, query: str, max_turns: Optional[int] = None) -> List[Turn]:
        """
        Get context turns most relevant to current query.

        Uses simple keyword matching to find relevant turns.

        Args:
            query: Current query
            max_turns: Maximum turns to return

        Returns:
            List of relevant turns
        """
        if not self.turns:
            return []

        # Score each turn by keyword overlap
        query_words = set(query.lower().split())
        scored_turns = []

        for turn in self.turns:
            turn_words = set(turn.user_query.lower().split())
            overlap = len(query_words & turn_words)
            scored_turns.append((turn, overlap))

        # Sort by relevance score
        scored_turns.sort(key=lambda x: x[1], reverse=True)

        # Take top N
        relevant = [t for t, _ in scored_turns[: max_turns or len(scored_turns)]]

        # Maintain chronological order
        relevant.sort(key=lambda t: t.timestamp)

        return relevant

    def clear(self) -> None:
        """Clear conversation history."""
        self.turns.clear()
        self._total_tokens = 0

    def get_stats(self) -> Dict[str, Any]:
        """Get context manager statistics."""
        return {
            "turn_count": len(self.turns),
            "total_tokens": self._total_tokens,
            "max_turns": self.max_turns,
            "token_budget": self.token_budget,
            "avg_turn_tokens": self._total_tokens // max(len(self.turns), 1),
        }

    def __len__(self) -> int:
        """Return number of turns."""
        return len(self.turns)

    def __repr__(self) -> str:
        return f"ContextManager(turns={len(self.turns)}, tokens={self._total_tokens}/{self.token_budget})"
