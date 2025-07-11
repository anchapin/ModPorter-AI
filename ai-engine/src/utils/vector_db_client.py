import httpx
import hashlib
import os
import logging # Using standard logging
from typing import Optional, List, Dict, Any # Added List, Dict, Any
from dataclasses import dataclass
import asyncio # Added for example main

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Default embedding dimension (e.g., for OpenAI text-embedding-ada-002)
# This could be made configurable if different models are used.
DEFAULT_EMBEDDING_DIMENSION = 1536

from ..utils.embedding_generator import EmbeddingGenerator
@dataclass
class Document:
    """Represents a document for indexing or retrieval."""
    content: str
    source: str
    content_hash: Optional[str] = None
    
    def __post_init__(self):
        """Generate content hash if not provided."""
        if self.content_hash is None:
            self.content_hash = hashlib.md5(self.content.encode("utf-8")).hexdigest()

class VectorDBClient:
    def __init__(self, base_url: str = None, timeout: float = 30.0):
        if base_url is None:
            base_url = os.environ.get("BACKEND_API_URL", "http://backend:8000/api/v1")

        self.base_url = base_url
        self.client = httpx.AsyncClient(base_url=self.base_url, timeout=timeout)
        self.embedding_generator = EmbeddingGenerator()
        logger.info(f"VectorDBClient initialized with base URL: {self.base_url}")

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

            text_to_embed = [document_content] # generate_embeddings expects a list
            embeddings_list = await self.embedding_generator.generate_embeddings(text_to_embed)

            if not embeddings_list or embeddings_list[0] is None:
                logger.error(f"Failed to generate embeddings for document source '{document_source}'.")
                return False

            actual_vector = embeddings_list[0].tolist() # Convert numpy array to list
            actual_dimension = self.embedding_generator.get_embedding_dimension()

            if actual_dimension and len(actual_vector) != actual_dimension:
                 logger.warning(f"Generated embedding dimension {len(actual_vector)} does not match expected dimension {actual_dimension} from generator for source '{document_source}'.")
            # If DEFAULT_EMBEDDING_DIMENSION is still critical for the backend, ensure model compatibility.
            # For now, we trust the dimension from the generator.

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
            text_to_embed = [query_text]
            embeddings_list = await self.embedding_generator.generate_embeddings(text_to_embed)

            if not embeddings_list or embeddings_list[0] is None:
                logger.error(f"Failed to generate query embedding for: '{query_text[:100]}...'")
                return []
            query_embedding = embeddings_list[0].tolist()

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
