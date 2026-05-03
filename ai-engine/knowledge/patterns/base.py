"""
Base pattern classes for conversion pattern library.

Defines the core data structures and interfaces for storing and retrieving
Java→Bedrock conversion patterns.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class ComplexityLevel(Enum):
    """Pattern complexity levels."""

    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"


@dataclass
class ConversionPattern:
    """
    Represents a single conversion pattern.

    A pattern contains Java and Bedrock code examples for a specific
    conversion scenario (e.g., item registration, block definition).
    """

    id: str
    name: str
    description: str
    java_example: str
    bedrock_example: str
    category: str  # e.g., "item", "block", "entity", "recipe"
    tags: List[str] = field(default_factory=list)
    complexity: str = "simple"  # "simple", "medium", "complex"
    success_rate: float = 0.0  # 0.0-1.0, based on actual conversions

    def __post_init__(self):
        """Validate pattern data."""
        if not self.id:
            raise ValueError("Pattern ID cannot be empty")
        if not self.java_example:
            raise ValueError("Java example cannot be empty")
        if not self.bedrock_example:
            raise ValueError("Bedrock example cannot be empty")
        if self.complexity not in ["simple", "medium", "complex"]:
            raise ValueError(f"Invalid complexity: {self.complexity}")
        if not 0.0 <= self.success_rate <= 1.0:
            raise ValueError(f"Success rate must be 0.0-1.0, got {self.success_rate}")

    def to_dict(self) -> Dict:
        """Convert pattern to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "java_example": self.java_example,
            "bedrock_example": self.bedrock_example,
            "category": self.category,
            "tags": self.tags,
            "complexity": self.complexity,
            "success_rate": self.success_rate,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "ConversionPattern":
        """Create pattern from dictionary."""
        return cls(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            java_example=data["java_example"],
            bedrock_example=data["bedrock_example"],
            category=data["category"],
            tags=data.get("tags", []),
            complexity=data.get("complexity", "simple"),
            success_rate=data.get("success_rate", 0.0),
        )


class PatternLibrary:
    """
    Library of conversion patterns.

    Provides storage, retrieval, and search functionality for
    Java→Bedrock conversion patterns.
    """

    def __init__(self):
        """Initialize empty pattern library."""
        self.patterns: Dict[str, ConversionPattern] = {}

    def add_pattern(self, pattern: ConversionPattern) -> None:
        """
        Add a pattern to the library.

        Args:
            pattern: Pattern to add

        Raises:
            ValueError: If pattern ID already exists
        """
        if pattern.id in self.patterns:
            raise ValueError(f"Pattern ID {pattern.id} already exists")
        self.patterns[pattern.id] = pattern

    def get_pattern(self, pattern_id: str) -> Optional[ConversionPattern]:
        """
        Get a pattern by ID.

        Args:
            pattern_id: Pattern identifier

        Returns:
            Pattern if found, None otherwise
        """
        return self.patterns.get(pattern_id)

    def search(
        self,
        query: str,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 10,
    ) -> List[ConversionPattern]:
        """
        Search for patterns by query text, category, and tags.

        Args:
            query: Search query (searches name, description, examples)
            category: Filter by category (optional)
            tags: Filter by tags (optional, patterns must have all tags)
            limit: Maximum results to return

        Returns:
            List of matching patterns, sorted by relevance
        """
        query_lower = query.lower()

        # Filter and score patterns
        scored_patterns = []
        for pattern in self.patterns.values():
            # Apply category filter
            if category and pattern.category != category:
                continue

            # Apply tags filter
            if tags and not all(tag in pattern.tags for tag in tags):
                continue

            # Calculate relevance score
            score = 0.0
            if query_lower in pattern.name.lower():
                score += 10  # Name match is highest priority
            if query_lower in pattern.description.lower():
                score += 5  # Description match
            if query_lower in pattern.java_example.lower():
                score += 3  # Java code match
            if query_lower in pattern.bedrock_example.lower():
                score += 3  # Bedrock code match
            if any(query_lower in tag.lower() for tag in pattern.tags):
                score += 2  # Tag match

            if score > 0:
                scored_patterns.append((pattern, score))

        # Sort by score descending
        scored_patterns.sort(key=lambda x: x[1], reverse=True)

        # Return top patterns
        return [pattern for pattern, _ in scored_patterns[:limit]]

    def get_by_category(self, category: str) -> List[ConversionPattern]:
        """
        Get all patterns in a category.

        Args:
            category: Category name

        Returns:
            List of patterns in the category
        """
        return [pattern for pattern in self.patterns.values() if pattern.category == category]

    def get_stats(self) -> Dict[str, int]:
        """
        Get library statistics.

        Returns:
            Dictionary with total patterns and counts by category
        """
        stats = {"total": len(self.patterns)}

        # Count by category
        category_counts: Dict[str, int] = {}
        for pattern in self.patterns.values():
            category_counts[pattern.category] = category_counts.get(pattern.category, 0) + 1

        stats["by_category"] = category_counts

        # Count by complexity
        complexity_counts: Dict[str, int] = {}
        for pattern in self.patterns.values():
            complexity_counts[pattern.complexity] = complexity_counts.get(pattern.complexity, 0) + 1

        stats["by_complexity"] = complexity_counts

        return stats

    def update_success_rate(self, pattern_id: str, success: bool) -> None:
        """
        Update success rate for a pattern based on conversion result.

        Args:
            pattern_id: Pattern identifier
            success: Whether the conversion succeeded

        Raises:
            ValueError: If pattern not found
        """
        pattern = self.get_pattern(pattern_id)
        if not pattern:
            raise ValueError(f"Pattern {pattern_id} not found")

        # Update success rate using exponential moving average
        alpha = 0.1  # Learning rate
        new_value = 1.0 if success else 0.0
        pattern.success_rate = alpha * new_value + (1 - alpha) * pattern.success_rate
