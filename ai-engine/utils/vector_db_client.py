import httpx
import hashlib
import os
import logging
from typing import Optional, List, Dict, Any
from utils.embedding_generator import (
    LocalEmbeddingGenerator,
    OpenAIEmbeddingGenerator,
    EmbeddingGenerator,
    EmbeddingCache,
    get_embedding_config,
)

logger = logging.getLogger(__name__)


class VectorDBClient:
    """
    Vector database client that generates real embeddings using either
    local sentence-transformers or OpenAI models, then stores/searches
    via the backend embeddings API.

    Supports:
    - Local embeddings (sentence-transformers/all-MiniLM-L6-v2) - default, no API key needed
    - OpenAI embeddings (text-embedding-ada-002) - requires OPENAI_API_KEY
    - Auto mode: tries OpenAI first, falls back to local
    - Embedding caching for performance
    - Backend /embeddings/generate endpoint as remote fallback
    """

    def __init__(self, base_url: str = None, timeout: float = 30.0, provider: str = None):
        if base_url is None:
            base_url = os.environ.get("BACKEND_API_URL", "http://backend:8000/api/v1")

        self.base_url = base_url
        self.client = httpx.AsyncClient(base_url=self.base_url, timeout=timeout)

        # Initialize embedding generator based on provider config
        config = get_embedding_config()
        self._provider = provider or config.get("provider", "auto")
        self.embedding_generator = self._create_embedding_generator()

        # Initialize embedding cache for performance
        self._cache = EmbeddingCache(
            max_size=config.get("cache_size", 10000),
            ttl_seconds=config.get("cache_ttl", 3600),
        )

        logger.info(
            f"VectorDBClient initialized with base URL: {self.base_url}, "
            f"embedding provider: {self._provider}, "
            f"model: {self.embedding_generator.model_name}"
        )

    def _create_embedding_generator(self) -> EmbeddingGenerator:
        """Create the appropriate embedding generator based on provider setting."""
        if self._provider == "openai":
            gen = OpenAIEmbeddingGenerator()
            if gen._client is not None:
                return gen
            logger.warning("OpenAI client unavailable, falling back to local embeddings")
            return LocalEmbeddingGenerator()
        elif self._provider == "local":
            return LocalEmbeddingGenerator()
        else:  # auto
            gen = OpenAIEmbeddingGenerator()
            if gen._client is not None:
                logger.info("Using OpenAI embedding generator (auto-detected)")
                return gen
            logger.info("OpenAI unavailable, using local embedding generator")
            return LocalEmbeddingGenerator()

    async def index_document(
        self, document_content: str, document_source: str
    ) -> bool:
        """
        Calculates a hash for the document content, generates an embedding,
        and sends it to the backend to be indexed.

        Args:
            document_content: The actual text content of the document (assumed to be a chunk).
            document_source: An identifier for the source of the document
                             (e.g., filename, URL).

        Returns:
            True if indexing was successful (e.g., backend responded with 201 or 200),
            False otherwise.
        """
        try:
            content_hash = hashlib.md5(document_content.encode("utf-8")).hexdigest()

            # Check cache first
            cached = self._cache.get(document_content, self.embedding_generator.model_name)
            if cached is not None:
                actual_vector = cached.tolist()
                logger.debug(f"Using cached embedding for source '{document_source}'")
            else:
                # Generate real embedding using configured provider
                result = self.embedding_generator.generate_embedding(document_content)

                if result is None:
                    logger.error(f"Failed to generate embedding for document source '{document_source}'.")
                    return False

                # Cache the embedding for future use
                self._cache.put(document_content, self.embedding_generator.model_name, result.embedding)
                actual_vector = result.embedding.tolist()

            expected_dimension = self.embedding_generator.dimensions
            if expected_dimension and len(actual_vector) != expected_dimension:
                logger.warning(
                    f"Generated embedding dimension {len(actual_vector)} does not match "
                    f"expected dimension {expected_dimension} for source '{document_source}'."
                )

            payload = {
                "embedding": actual_vector,
                "document_source": document_source,
                "content_hash": content_hash,
                # "dimension": actual_dimension, # Optionally send dimension if backend uses it
            }

            # The backend endpoint for this will be created in a later step
            # e.g. /api/v1/embeddings/
            response = await self.client.post("/embeddings/", json=payload)

            if response.status_code == 201: # HTTP 201 Created
                logger.info(
                    f"Successfully indexed document from source '{document_source}' with hash '{content_hash}'."
                )
                return True
            elif response.status_code == 200: # Handle if backend returns 200 OK on existing hash
                logger.info(
                    f"Document from source '{document_source}' with hash '{content_hash}' likely already exists or was updated."
                )
                return True
            else:
                logger.error(
                    f"Failed to index document from source '{document_source}'. "
                    f"Status: {response.status_code}, Response: {response.text}"
                )
                return False
        except httpx.RequestError as e:
            logger.error(
                f"HTTP request error while trying to index document from source '{document_source}': {e}"
            )
            return False
        except Exception as e:
            logger.error(
                f"An unexpected error occurred while indexing document from source '{document_source}': {e}"
            )
            return False

    async def search_documents(
        self, query_text: str, top_k: int = 10, document_source_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Generates an embedding for the query text and searches for similar documents
        in the vector database via the backend.

        Args:
            query_text: The text to search for.
            top_k: The maximum number of results to return.
            document_source_filter: Optional string to filter results by document source.

        Returns:
            A list of search result dictionaries, or an empty list if an error occurs.
        """
        logger.info(f"Searching for: '{query_text[:100]}...' with top_k={top_k}")
        try:
            # Check cache for query embedding
            cached = self._cache.get(query_text, self.embedding_generator.model_name)
            if cached is not None:
                query_embedding = cached.tolist()
                logger.debug("Using cached query embedding")
            else:
                # Generate real embedding for the query
                result = self.embedding_generator.generate_embedding(query_text)

                if result is None:
                    logger.error(f"Failed to generate query embedding for: '{query_text[:100]}...'")
                    return []

                self._cache.put(query_text, self.embedding_generator.model_name, result.embedding)
                query_embedding = result.embedding.tolist()

            payload = {
                "query_embedding": query_embedding,
                "top_k": top_k,
            }
            if document_source_filter:
                payload["document_source_filter"] = document_source_filter

            response = await self.client.post("/embeddings/search/", json=payload)
            response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

            return response.json().get("results", [])
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error during search for '{query_text[:100]}...': {e.response.status_code} - {e.response.text}")
        except httpx.RequestError as e:
            logger.error(f"Request error during search for '{query_text[:100]}...': {e}")
        except Exception as e:
            logger.error(f"An unexpected error occurred during search for '{query_text[:100]}...': {e}")
        return []

    async def get_embedding(self, text: str) -> Optional[List[float]]:
        """
        Generate an embedding for the given text.
        
        This method provides direct access to embedding generation functionality,
        supporting both OpenAI and local embedding models.
        
        Args:
            text: The text content to generate an embedding for.
            
        Returns:
            A list of floats representing the embedding vector, or None if
            embedding generation failed.
        """
        try:
            # Check cache first
            cached = self._cache.get(text, self.embedding_generator.model_name)
            if cached is not None:
                logger.debug("Using cached embedding")
                return cached.tolist()
            
            # Generate embedding using the configured provider
            result = self.embedding_generator.generate_embedding(text)
            
            if result is None:
                logger.error(f"Failed to generate embedding for text: {text[:50]}...")
                return None
            
            # Cache the embedding
            self._cache.put(text, self.embedding_generator.model_name, result.embedding)
            
            logger.info(f"Generated embedding of dimension {len(result.embedding)} using {self.embedding_generator.model_name}")
            return result.embedding.tolist()
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return None

    async def close(self):
        """Closes the underlying HTTPX client."""
        await self.client.aclose()
        # If EmbeddingGenerator had an async close method, it would be called here:
        # For example: if hasattr(self.embedding_generator, 'close') and asyncio.iscoroutinefunction(self.embedding_generator.close):
        #    await self.embedding_generator.close()
        logger.info("VectorDBClient closed.")

# Example usage (primarily for testing this client directly)
async def main():
    # This main function is for demonstration and won't be part of the library's public API
    # It requires the backend service to be running and the /embeddings/ endpoint to be available.
    print("Initializing VectorDBClient for test...")
    client = VectorDBClient()

    test_content = "This is a sample document for testing the VectorDBClient."
    test_source = "test_document.txt"

    print(f"Attempting to index document: '{test_source}'")
    success = await client.index_document(test_content, test_source)

    if success:
        print(f"Document '{test_source}' indexed successfully (or already existed).")
    else:
        print(f"Failed to index document '{test_source}'.")

    # Test search (assuming the document above was indexed or similar documents exist)
    print("\nAttempting to search for documents similar to 'sample document'...")
    search_query = "sample query that might be similar to the test document"
    search_results = await client.search_documents(search_query, top_k=5)

    if search_results:
        print(f"Found {len(search_results)} search results for '{search_query}':")
        for i, result in enumerate(search_results):
            print(f"  Result {i+1}: Source: {result.get('document_source')}, Score: {result.get('similarity_score'):.4f}, Content: '{result.get('content','')[:100]}...'")
    else:
        print(f"No search results found for '{search_query}' or an error occurred.")

    await client.close()

if __name__ == "__main__":
    # This is a simple way to run the async main function.
    # In a real application, you'd integrate this into your async event loop.
    # print("Running VectorDBClient main example...")
    # import asyncio # Already imported at the top
    # asyncio.run(main())
    # Commenting out the asyncio.run(main()) as it's for direct testing
    # and might cause issues if not run in the right context or if backend is not up.
    pass
