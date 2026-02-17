"""
RAG Embedding Generation Module.

This module provides embedding generation capabilities for the RAG system,
connecting to vector database for knowledge retrieval.
"""

import hashlib
import json
import logging
import os
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)

# Constants for embedding validation
SUPPORTED_DIMENSIONS = {1536, 384, 768, 512, 256}
DEFAULT_DIMENSION = 1536
CACHE_MAX_SIZE = 10000
CACHE_TTL_SECONDS = 3600  # 1 hour



@dataclass
class EmbeddingResult:
    """Result from embedding generation."""
    embedding: np.ndarray
    model: str
    dimensions: int
    token_count: Optional[int] = None


class EmbeddingGenerator(ABC):
    """Abstract base class for embedding generators."""
    
    @abstractmethod
    def generate_embedding(self, text: str) -> Optional[EmbeddingResult]:
        """Generate embedding for text."""
        pass
    
    @abstractmethod
    def generate_embeddings(self, texts: List[str]) -> List[Optional[EmbeddingResult]]:
        """Generate embeddings for multiple texts."""
        pass
    
    @property
    @abstractmethod
    def dimensions(self) -> int:
        """Get embedding dimensions."""
        pass
    
    @property
    @abstractmethod
    def model_name(self) -> str:
        """Get model name."""
        pass


class OpenAIEmbeddingGenerator(EmbeddingGenerator):
    """OpenAI embedding generator using text-embedding-ada-002."""
    
    def __init__(self, model: str = "text-embedding-ada-002", dimensions: int = 1536):
        self.model = model
        self._dimensions = dimensions
        self._client = None
        self._init_client()
    
    def _init_client(self):
        """Initialize OpenAI client."""
        try:
            from openai import OpenAI
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                self._client = OpenAI(api_key=api_key)
                logger.info("OpenAI embedding client initialized")
            else:
                logger.warning("OPENAI_API_KEY not set, OpenAI embeddings unavailable")
        except ImportError:
            logger.warning("OpenAI package not installed")
    
    def generate_embedding(self, text: str) -> Optional[EmbeddingResult]:
        """Generate embedding for text using OpenAI."""
        if not self._client:
            return None
        
        try:
            response = self._client.embeddings.create(
                model=self.model,
                input=text
            )
            embedding = np.array(response.data[0].embedding)
            return EmbeddingResult(
                embedding=embedding,
                model=self.model,
                dimensions=self._dimensions,
                token_count=response.usage.total_tokens
            )
        except Exception as e:
            logger.error(f"Error generating OpenAI embedding: {e}")
            return None
    
    def generate_embeddings(self, texts: List[str]) -> List[Optional[EmbeddingResult]]:
        """Generate embeddings for multiple texts."""
        if not self._client:
            return [None] * len(texts)
        
        try:
            response = self._client.embeddings.create(
                model=self.model,
                input=texts
            )
            results = []
            for data in response.data:
                embedding = np.array(data.embedding)
                results.append(EmbeddingResult(
                    embedding=embedding,
                    model=self.model,
                    dimensions=self._dimensions
                ))
            return results
        except Exception as e:
            logger.error(f"Error generating OpenAI embeddings: {e}")
            return [None] * len(texts)
    
    @property
    def dimensions(self) -> int:
        return self._dimensions
    
    @property
    def model_name(self) -> str:
        return self.model


class LocalEmbeddingGenerator(EmbeddingGenerator):
    """Local embedding generator using sentence-transformers or similar."""
    
    def __init__(self, model: str = "all-MiniLM-L6-v2", dimensions: int = 384):
        self._model_name = model
        self._dimensions = dimensions
        self._model = None
        self._init_model()
    
    def _init_model(self):
        """Initialize local model."""
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
            self._dimensions = self._model.get_sentence_embedding_dimension()
            logger.info(f"Local embedding model loaded: {self.model_name}")
        except ImportError:
            logger.warning("sentence-transformers not installed")
        except Exception as e:
            logger.error(f"Error loading local model: {e}")
    
    def generate_embedding(self, text: str) -> Optional[EmbeddingResult]:
        """Generate embedding using local model."""
        if not self._model:
            return self._generate_fallback_embedding(text)
        
        try:
            embedding = self._model.encode(text, convert_to_numpy=True)
            return EmbeddingResult(
                embedding=embedding,
                model=self.model_name,
                dimensions=self._dimensions
            )
        except Exception as e:
            logger.error(f"Error generating local embedding: {e}")
            return self._generate_fallback_embedding(text)
    
    def generate_embeddings(self, texts: List[str]) -> List[Optional[EmbeddingResult]]:
        """Generate embeddings for multiple texts."""
        if not self._model:
            return [self._generate_fallback_embedding(t) for t in texts]
        
        try:
            embeddings = self._model.encode(texts, convert_to_numpy=True, show_progress_bar=True)
            return [
                EmbeddingResult(
                    embedding=emb,
                    model=self.model_name,
                    dimensions=self._dimensions
                )
                for emb in embeddings
            ]
        except Exception as e:
            logger.error(f"Error generating local embeddings: {e}")
            return [self._generate_fallback_embedding(t) for t in texts]
    
    def _generate_fallback_embedding(self, text: str) -> EmbeddingResult:
        """Generate a simple fallback embedding (for testing)."""
        # Simple hash-based embedding for testing
        hash_val = hash(text) % (2**32)
        np.random.seed(hash_val)
        embedding = np.random.randn(self._dimensions).astype(np.float32)
        embedding = embedding / np.linalg.norm(embedding)  # Normalize
        
        return EmbeddingResult(
            embedding=embedding,
            model=f"{self.model_name}-fallback",
            dimensions=self._dimensions
        )
    
    @property
    def dimensions(self) -> int:
        return self._dimensions
    
    @property
    def model_name(self) -> str:
        return self._model_name


class EmbeddingStorage:
    """Store embeddings in vector database."""
    
    def __init__(self, table_name: str = "embeddings"):
        self.table_name = table_name
        self._connection = None
        self._init_db()
    
    def _init_db(self):
        """Initialize database connection."""
        # Try PostgreSQL with pgvector
        db_url = os.getenv("DATABASE_URL")
        if db_url:
            try:
                import psycopg2
                from psycopg2 import sql
                # Note: In production, would need pgvector extension
                self._connection = psycopg2.connect(db_url)
                logger.info("PostgreSQL embedding storage initialized")
            except Exception as e:
                logger.warning(f"Could not connect to PostgreSQL: {e}")
        else:
            logger.warning("DATABASE_URL not set, using in-memory storage")
            self._memory_storage = []
    
    def store_embedding(self, document_id: str, content: str, embedding: np.ndarray,
                      metadata: Optional[Dict] = None) -> bool:
        """Store an embedding."""
        try:
            if self._connection:
                return self._store_postgres(document_id, content, embedding, metadata)
            else:
                return self._store_memory(document_id, content, embedding, metadata)
        except Exception as e:
            logger.error(f"Error storing embedding: {e}")
            return False
    
    def _store_postgres(self, document_id: str, content: str, embedding: np.ndarray,
                       metadata: Optional[Dict]) -> bool:
        """Store in PostgreSQL."""
        try:
            cursor = self._connection.cursor()
            
            # Insert or update
            cursor.execute(f"""
                INSERT INTO {self.table_name} (document_id, content, embedding, metadata)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (document_id) 
                DO UPDATE SET content = EXCLUDED.content, 
                             embedding = EXCLUDED.embedding,
                             metadata = EXCLUDED.metadata,
                             updated_at = CURRENT_TIMESTAMP
            """, (document_id, content, embedding.tolist(), json.dumps(metadata or {})))
            
            self._connection.commit()
            return True
        except Exception as e:
            logger.error(f"Error storing in PostgreSQL: {e}")
            return False
    
    def _store_memory(self, document_id: str, content: str, embedding: np.ndarray,
                    metadata: Optional[Dict]) -> bool:
        """Store in memory (fallback)."""
        self._memory_storage.append({
            'document_id': document_id,
            'content': content,
            'embedding': embedding,
            'metadata': metadata or {}
        })
        return True
    
    def search_similar(self, query_embedding: np.ndarray, top_k: int = 5,
                      filters: Optional[Dict] = None) -> List[Dict]:
        """Search for similar embeddings."""
        try:
            if self._connection:
                return self._search_postgres(query_embedding, top_k, filters)
            else:
                return self._search_memory(query_embedding, top_k, filters)
        except Exception as e:
            logger.error(f"Error searching: {e}")
            return []
    
    def _search_postgres(self, query_embedding: np.ndarray, top_k: int,
                        filters: Optional[Dict]) -> List[Dict]:
        """Search in PostgreSQL using cosine similarity."""
        try:
            cursor = self._connection.cursor()
            
            # Simple L2 distance search (would use cosine similarity with pgvector)
            query_str = f"""
                SELECT document_id, content, embedding, metadata,
                       embedding <=> %s::vector AS distance
                FROM {self.table_name}
                ORDER BY distance
                LIMIT %s
            """
            
            cursor.execute(query_str, (query_embedding.tolist(), top_k))
            results = []
            
            for row in cursor.fetchall():
                results.append({
                    'document_id': row[0],
                    'content': row[1],
                    'embedding': np.array(row[2]),
                    'metadata': row[3],
                    'distance': row[4]
                })
            
            return results
        except Exception as e:
            logger.error(f"Error searching PostgreSQL: {e}")
            return []
    
    def _search_memory(self, query_embedding: np.ndarray, top_k: int,
                     filters: Optional[Dict]) -> List[Dict]:
        """Search in memory."""
        if not self._memory_storage:
            return []
        
        # Compute similarities
        similarities = []
        for item in self._memory_storage:
            embedding = item['embedding']
            # Cosine similarity
            sim = np.dot(query_embedding, embedding) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(embedding) + 1e-8
            )
            similarities.append((sim, item))
        
        # Sort by similarity
        similarities.sort(key=lambda x: x[0], reverse=True)
        
        return [
            {
                'document_id': item['document_id'],
                'content': item['content'],
                'embedding': item['embedding'],
                'metadata': item['metadata'],
                'similarity': sim
            }
            for sim, item in similarities[:top_k]
        ]


class RAGEmbeddingService:
    """
    Main service for RAG embedding generation and storage.
    """
    
    def __init__(self, provider: str = "local"):
        """
        Initialize RAG embedding service.
        
        Args:
            provider: Embedding provider ('openai', 'local', or 'auto')
        """
        self.provider = provider
        self._embedding_generator = None
        self._storage = None
        self._init_services()
    
    def _init_services(self):
        """Initialize embedding generator and storage."""
        # Initialize embedding generator
        if self.provider == "openai":
            self._embedding_generator = OpenAIEmbeddingGenerator()
        elif self.provider == "local":
            self._embedding_generator = LocalEmbeddingGenerator()
        else:  # auto
            # Try OpenAI first, fall back to local
            try:
                self._embedding_generator = OpenAIEmbeddingGenerator()
                if not self._embedding_generator._client:
                    raise ValueError("OpenAI client not available")
            except Exception:
                logger.info("Falling back to local embedding generator")
                self._embedding_generator = LocalEmbeddingGenerator()
        
        # Initialize storage
        self._storage = EmbeddingStorage()
        
        logger.info(f"RAG embedding service initialized with {self.provider} provider")
    
    def generate_and_store(self, document_id: str, content: str,
                          metadata: Optional[Dict] = None) -> bool:
        """
        Generate embedding for content and store it.
        
        Args:
            document_id: Unique document identifier
            content: Text content to embed
            metadata: Optional metadata
            
        Returns:
            True if successful
        """
        result = self._embedding_generator.generate_embedding(content)
        
        if result is None:
            logger.error("Failed to generate embedding")
            return False
        
        return self._storage.store_embedding(
            document_id, content, result.embedding, metadata
        )
    
    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        Search for similar content.
        
        Args:
            query: Search query
            top_k: Number of results
            
        Returns:
            List of similar documents
        """
        # Generate query embedding
        result = self._embedding_generator.generate_embedding(query)
        
        if result is None:
            logger.error("Failed to generate query embedding")
            return []
        
        # Search
        return self._storage.search_similar(result.embedding, top_k)
    
    def batch_process(self, documents: List[Dict], 
                     id_field: str = "id",
                     content_field: str = "content",
                     metadata_field: str = "metadata") -> Dict:
        """
        Process multiple documents.
        
        Args:
            documents: List of document dicts
            id_field: Field name for document ID
            content_field: Field name for content
            metadata_field: Field name for metadata
            
        Returns:
            Processing results
        """
        results = {
            'success': 0,
            'failed': 0,
            'total': len(documents)
        }
        
        for doc in documents:
            doc_id = doc.get(id_field, f"doc_{results['success'] + results['failed']}")
            content = doc.get(content_field, "")
            metadata = doc.get(metadata_field, {})
            
            if self.generate_and_store(doc_id, content, metadata):
                results['success'] += 1
            else:
                results['failed'] += 1
        
        return results


def create_rag_embedding_service(provider: str = "auto") -> RAGEmbeddingService:
    """Factory function to create RAG embedding service."""
    return RAGEmbeddingService(provider=provider)


class EmbeddingCache:
    """Thread-safe LRU cache for embeddings with TTL support."""
    
    def __init__(self, max_size: int = CACHE_MAX_SIZE, ttl_seconds: int = CACHE_TTL_SECONDS):
        self._cache: Dict[str, tuple] = {}
        self._max_size = max_size
        self._ttl_seconds = ttl_seconds
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0
    
    def _get_cache_key(self, text: str, model: str) -> str:
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        return f"{model}:{text_hash}"
    
    def get(self, text: str, model: str) -> Optional[np.ndarray]:
        key = self._get_cache_key(text, model)
        with self._lock:
            if key in self._cache:
                embedding, timestamp = self._cache[key]
                if time.time() - timestamp < self._ttl_seconds:
                    self._hits += 1
                    return embedding
                else:
                    del self._cache[key]
            self._misses += 1
            return None
    
    def put(self, text: str, model: str, embedding: np.ndarray):
        key = self._get_cache_key(text, model)
        with self._lock:
            if len(self._cache) >= self._max_size:
                oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k][1])
                del self._cache[oldest_key]
            self._cache[key] = (embedding.copy(), time.time())
    
    def clear(self):
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0
    
    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            total = self._hits + self._misses
            hit_rate = self._hits / total if total > 0 else 0
            return {
                'size': len(self._cache),
                'max_size': self._max_size,
                'hits': self._hits,
                'misses': self._misses,
                'hit_rate': hit_rate
            }


def validate_embedding_dimensions(embedding: np.ndarray, expected_dimensions: int) -> bool:
    if embedding is None:
        return False
    if not isinstance(embedding, np.ndarray):
        return False
    actual_dims = embedding.shape[0] if embedding.ndim > 0 else 0
    return actual_dims == expected_dimensions


def get_embedding_config() -> Dict[str, Any]:
    return {
        'provider': os.getenv('EMBEDDING_PROVIDER', 'auto'),
        'openai_model': os.getenv('OPENAI_EMBEDDING_MODEL', 'text-embedding-ada-002'),
        'local_model': os.getenv('LOCAL_EMBEDDING_MODEL', 'all-MiniLM-L6-v2'),
        'dimensions': int(os.getenv('EMBEDDING_DIMENSIONS', str(DEFAULT_DIMENSION))),
        'cache_enabled': os.getenv('EMBEDDING_CACHE_ENABLED', 'true').lower() == 'true',
        'cache_size': int(os.getenv('EMBEDDING_CACHE_SIZE', str(CACHE_MAX_SIZE))),
        'cache_ttl': int(os.getenv('EMBEDDING_CACHE_TTL', str(CACHE_TTL_SECONDS)))
    }
