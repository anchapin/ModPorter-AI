"""
Base source adapter interface and data models.

Provides abstract interface and data structures for documentation source adapters.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Any, Optional


class DocumentType(Enum):
    """Document type classification for ingestion."""

    MARKDOWN = "markdown"
    HTML = "html"
    PDF = "pdf"
    CODE = "code"


@dataclass
class RawDocument:
    """Raw document fetched from a source.

    Attributes:
        content: Raw document content (markdown, HTML, etc.)
        source_url: URL where the document was fetched
        doc_type: Type of document (markdown, HTML, PDF, code)
        metadata: Optional metadata extracted from source
        title: Document title (if available)
    """

    content: str
    source_url: str
    doc_type: DocumentType
    metadata: Dict[str, Any]
    title: Optional[str] = None

    def __post_init__(self):
        """Ensure metadata is a dict."""
        if self.metadata is None:
            self.metadata = {}


class BaseSourceAdapter(ABC):
    """Abstract base class for documentation source adapters.

    Source adapters are responsible for:
    - Fetching documentation from external sources
    - Validating configuration
    - Returning standardized RawDocument objects
    """

    @abstractmethod
    async def fetch(self, config: Dict[str, Any]) -> List[RawDocument]:
        """
        Fetch documents from the source.

        Args:
            config: Source-specific configuration
                - May include version, sections, namespaces, etc.

        Returns:
            List of RawDocument objects

        Raises:
            Exception: If fetch fails (should be logged, not crash)
        """
        pass

    @abstractmethod
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate source configuration before fetching.

        Args:
            config: Configuration to validate

        Returns:
            True if config is valid, False otherwise
        """
        pass
