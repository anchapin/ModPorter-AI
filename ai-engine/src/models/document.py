from dataclasses import dataclass, field
from typing import Dict, Optional
import hashlib

@dataclass
class Document:
    content: str
    source: str # URL or identifier of the source
    doc_type: str = "generic" # e.g., "api_reference", "tutorial", "schema"
    metadata: Dict[str, any] = field(default_factory=dict)
    content_hash: Optional[str] = None

    def __post_init__(self):
        if self.content_hash is None and self.content:
            self.content_hash = hashlib.md5(self.content.encode("utf-8")).hexdigest()
