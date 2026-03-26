"""
RAG Service for ModPorter AI

Retrieval-Augmented Generation service for Java→Bedrock code conversion.
Provides semantic search, hybrid search, and context building for AI models.
"""

import logging
import json
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class RAGService:
    """RAG service for code conversion examples."""
    
    def __init__(self):
        self._examples = []
        self._embeddings = {}
        self._initialized = False
    
    def load_examples(self, examples: List[Dict[str, Any]]):
        """
        Load conversion examples into RAG database.
        
        Args:
            examples: List of conversion examples with java_code, bedrock_code, metadata
        """
        self._examples = examples
        logger.info(f"Loaded {len(examples)} conversion examples")
    
    def add_example(
        self,
        java_code: str,
        bedrock_code: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Add a conversion example.
        
        Args:
            java_code: Java source code
            bedrock_code: Bedrock JavaScript/JSON code
            metadata: Example metadata (difficulty, features, etc.)
        
        Returns:
            Example ID
        """
        import uuid
        
        example_id = str(uuid.uuid4())
        example = {
            "id": example_id,
            "java_code": java_code,
            "bedrock_code": bedrock_code,
            "metadata": metadata or {},
            "created_at": datetime.utcnow().isoformat(),
        }
        
        self._examples.append(example)
        logger.debug(f"Added example {example_id}")
        
        return example_id
    
    def search(
        self,
        query: str,
        top_k: int = 5,
        min_score: float = 0.5,
    ) -> List[Dict[str, Any]]:
        """
        Search for similar conversion examples.
        
        Args:
            query: Search query (Java code or description)
            top_k: Number of results to return
            min_score: Minimum similarity score
        
        Returns:
            List of similar examples with scores
        """
        # Simple keyword-based search for now
        # Will be enhanced with semantic search in Task 1.3.3
        results = []
        query_lower = query.lower()
        
        for example in self._examples:
            # Search in Java code
            java_match = query_lower in example["java_code"].lower()
            
            # Search in metadata
            metadata_str = json.dumps(example.get("metadata", {})).lower()
            metadata_match = query_lower in metadata_str
            
            if java_match or metadata_match:
                score = 0.8 if java_match else 0.6
                if score >= min_score:
                    results.append({
                        "example": example,
                        "score": score,
                        "match_type": "java" if java_match else "metadata",
                    })
        
        # Sort by score and return top_k
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]
    
    def get_example(self, example_id: str) -> Optional[Dict[str, Any]]:
        """Get example by ID."""
        for example in self._examples:
            if example["id"] == example_id:
                return example
        return None
    
    def get_all_examples(self) -> List[Dict[str, Any]]:
        """Get all examples."""
        return self._examples.copy()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get RAG database statistics."""
        return {
            "total_examples": len(self._examples),
            "timestamp": datetime.utcnow().isoformat(),
        }


# Singleton instance
_rag_service = None


def get_rag_service() -> RAGService:
    """Get or create RAG service singleton."""
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service
