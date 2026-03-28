"""
Knowledge base module for RAG system.

This module contains:
- Pattern library: Java→Bedrock conversion patterns
- Community contributions: User-submitted patterns and validation
- Knowledge expansion: Documentation and API references
- Cross-reference detection: Concept graph relationships
"""

from knowledge.schema import ConceptNode, ConceptRelationship, ConceptType, RelationshipType
from knowledge.cross_reference import CrossReferenceDetector, DetectedConcept, RelationshipCandidate

__all__ = [
    "ConceptNode",
    "ConceptRelationship",
    "ConceptType",
    "RelationshipType",
    "CrossReferenceDetector",
    "DetectedConcept",
    "RelationshipCandidate",
]
