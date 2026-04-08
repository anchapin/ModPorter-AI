"""
Source adapters for fetching documentation from external sources.

This module provides adapters for:
- Forge documentation
- Fabric documentation
- Bedrock API reference
"""

from .base import BaseSourceAdapter, RawDocument, DocumentType

__all__ = ["BaseSourceAdapter", "RawDocument", "DocumentType"]

# Import source adapters
try:
    from .forge_docs import ForgeDocsAdapter
    __all__.append("ForgeDocsAdapter")
except ImportError:
    pass

try:
    from .fabric_docs import FabricDocsAdapter
    __all__.append("FabricDocsAdapter")
except ImportError:
    pass

try:
    from .bedrock_docs import BedrockDocsAdapter
    __all__.append("BedrockDocsAdapter")
except ImportError:
    pass
