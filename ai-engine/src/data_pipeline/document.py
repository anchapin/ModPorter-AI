from dataclasses import dataclass, field

@dataclass
class Document:
    """Represents a document with content and metadata."""
    content: str
    metadata: dict[str, any] = field(default_factory=dict)
