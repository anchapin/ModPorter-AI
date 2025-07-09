import httpx
import hashlib
import os
import logging # Using standard logging

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Default embedding dimension (e.g., for OpenAI text-embedding-ada-002)
# This could be made configurable if different models are used.
DEFAULT_EMBEDDING_DIMENSION = 1536

class VectorDBClient:
    def __init__(self, base_url: str = None, timeout: float = 30.0):
        if base_url is None:
            base_url = os.environ.get("BACKEND_API_URL", "http://backend:8000/api/v1")

        self.base_url = base_url
        self.client = httpx.AsyncClient(base_url=self.base_url, timeout=timeout)
        logger.info(f"VectorDBClient initialized with base URL: {self.base_url}")

    async def index_document(
        self, document_content: str, document_source: str
    ) -> bool:
        """
        Calculates a hash for the document content, generates a (dummy) embedding,
        and sends it to the backend to be indexed.

        Args:
            document_content: The actual text content of the document.
            document_source: An identifier for the source of the document
                             (e.g., filename, URL).

        Returns:
            True if indexing was successful (e.g., backend responded with 201),
            False otherwise.
        """
        try:
            content_hash = hashlib.md5(document_content.encode("utf-8")).hexdigest()

            # Placeholder for actual embedding generation
            # TODO: Replace with actual call to an embedding model/service
            dummy_vector = [0.1] * DEFAULT_EMBEDDING_DIMENSION

            payload = {
                "embedding": dummy_vector,
                "document_source": document_source,
                "content_hash": content_hash,
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

    async def close(self):
        """Closes the underlying HTTPX client."""
        await self.client.aclose()
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

    await client.close()

if __name__ == "__main__":
    import asyncio
    # This is a simple way to run the async main function.
    # In a real application, you'd integrate this into your async event loop.
    # print("Running VectorDBClient main example...")
    # asyncio.run(main())
    # Commenting out the asyncio.run(main()) as it's for direct testing
    # and might cause issues if not run in the right context or if backend is not up.
    pass
