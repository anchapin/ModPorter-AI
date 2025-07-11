import logging
from typing import List, Union
import os
import numpy as np # Add if numpy is used for embeddings

logger = logging.getLogger(__name__)

# Optional import for sentence-transformers
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SentenceTransformer = None
    SENTENCE_TRANSFORMERS_AVAILABLE = False # This flag specifically tracks SentenceTransformer availability
    logger.warning("sentence_transformers library not found. SentenceTransformer models will be unavailable.")

# Attempt to import openai
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    openai = None
    OPENAI_AVAILABLE = False
    logger.warning("openai library not found. OpenAI models will be unavailable unless using direct HTTP call.")

# httpx is assumed to be available as per project structure, otherwise add try-except
import httpx

class EmbeddingGenerator:
    def __init__(self, model_name: str = None):
        """
        Initializes the EmbeddingGenerator.
        Model selection is controlled by RAG_EMBEDDING_MODEL environment variable.
        OPENAI_API_KEY environment variable is required for OpenAI models.

        Args:
            model_name (str, optional): Primarily for testing or direct instantiation.
                                      If None, RAG_EMBEDDING_MODEL env var is used.
        """
        self.model_name = model_name or os.environ.get('RAG_EMBEDDING_MODEL', 'sentence-transformers/all-MiniLM-L6-v2')
        self.api_key = os.environ.get('OPENAI_API_KEY')
        self.model = None
        self.model_type = None # 'sentence-transformers' or 'openai'
        self._embedding_dimension = None

        logger.info(f"Initializing EmbeddingGenerator with model identifier: {self.model_name}")

        if self.model_name.startswith('sentence-transformers/'):
            if SENTENCE_TRANSFORMERS_AVAILABLE:
                self.model_type = 'sentence-transformers'
                s_model_name = self.model_name.split('/')[-1]
                try:
                    self.model = SentenceTransformer(s_model_name)
                    logger.info(f"SentenceTransformer model '{s_model_name}' loaded successfully.")
                    if hasattr(self.model, 'get_sentence_embedding_dimension'):
                        self._embedding_dimension = self.model.get_sentence_embedding_dimension()
                    # Fallback for some models, or use known dimensions
                    elif "all-MiniLM-L6-v2" in s_model_name: self._embedding_dimension = 384
                    elif "all-mpnet-base-v2" in s_model_name: self._embedding_dimension = 768
                    else:
                        logger.warning(f"Could not automatically determine embedding dimension for ST model: {s_model_name}. You may need to set it manually or update logic.")
                    logger.info(f"SentenceTransformer model embedding dimension: {self._embedding_dimension}")
                except Exception as e:
                    logger.error(f"Failed to load SentenceTransformer model '{s_model_name}': {e}")
                    self.model = None # Ensure model is None if loading fails
            else:
                logger.error("RAG_EMBEDDING_MODEL is set to a sentence-transformers model, but the library is not available.")
        elif self.model_name.startswith('openai/'):
            self.model_type = 'openai'
            self.o_model_name = self.model_name.split('/')[-1] # Store the specific OpenAI model name
            if not self.api_key:
                logger.error("RAG_EMBEDDING_MODEL is set to an OpenAI model, but OPENAI_API_KEY is not set.")
            else:
                # Standard dimensions for OpenAI models
                if "text-embedding-ada-002" in self.o_model_name: self._embedding_dimension = 1536
                elif "text-embedding-3-small" in self.o_model_name: self._embedding_dimension = 1536
                elif "text-embedding-3-large" in self.o_model_name: self._embedding_dimension = 3072
                else:
                    logger.warning(f"Could not automatically determine embedding dimension for OpenAI model: {self.o_model_name}. Update `__init__` if this is a new model.")

                if OPENAI_AVAILABLE:
                    try:
                        self.model = openai.OpenAI(api_key=self.api_key) # Store the client
                        logger.info(f"OpenAI client configured for model '{self.o_model_name}'. Dimension: {self._embedding_dimension}")
                    except Exception as e:
                        logger.error(f"Failed to initialize OpenAI client: {e}")
                        self.model = None
                else: # OpenAI library not available, but API key is. httpx will be used.
                    logger.info(f"OpenAI library not found. Will use httpx for OpenAI embeddings for model '{self.o_model_name}'. Dimension: {self._embedding_dimension}")
                    # No specific model object to store here for httpx, it's used directly in the generation method.
        else:
            logger.error(f"Unsupported RAG_EMBEDDING_MODEL format: {self.model_name}. Must start with 'sentence-transformers/' or 'openai/'.")

    def get_embedding_dimension(self) -> Union[int, None]:
        """Returns the embedding dimension of the loaded model."""
        if self._embedding_dimension is None:
             logger.warning("Embedding dimension is not set. Model might not have loaded correctly or dimension couldn't be determined.")
        return self._embedding_dimension

    async def _generate_openai_embeddings_httpx(self, text_chunks: List[str]) -> Union[List[np.ndarray], None]:
        """Generates embeddings using OpenAI API via httpx (async)."""
        if not self.api_key or not hasattr(self, 'o_model_name'): # check o_model_name was set
            logger.error("OpenAI API key or model name not configured for httpx call.")
            return None

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        # OpenAI API currently processes up to 2048 input strings per request.
        # If text_chunks is larger, it needs to be batched.
        # For simplicity here, assuming text_chunks is within reasonable limits for a single call,
        # or add batching logic if necessary.
        all_embeddings = []
        batch_size = 2048 # OpenAI API limit

        for i in range(0, len(text_chunks), batch_size):
            batch = text_chunks[i:i+batch_size]
            json_data = {"input": batch, "model": self.o_model_name}

            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post("https://api.openai.com/v1/embeddings", headers=headers, json=json_data, timeout=60) # Increased timeout
                    response.raise_for_status()
                    data = response.json()
                    batch_embeddings = [np.array(item["embedding"]) for item in data["data"]]
                    all_embeddings.extend(batch_embeddings)
                    logger.info(f"Generated {len(batch_embeddings)} embeddings in batch {i//batch_size + 1} using OpenAI API (httpx).")
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error calling OpenAI API (httpx): {e.response.status_code} - {e.response.text}")
                return None # Fail fast on API error
            except Exception as e:
                logger.error(f"Error calling OpenAI API with httpx: {e}")
                return None # Fail fast

        return all_embeddings


    async def generate_embeddings(self, text_chunks: List[str]) -> Union[List[np.ndarray], None]:
        """
        Generates embeddings for a list of text chunks using the configured model.
        Args:
            text_chunks (List[str]): A list of text strings to embed.
        Returns:
            List[np.ndarray]: A list of embeddings (NumPy arrays), or None if issues occur.
        """
        if not self.model_type:
            logger.error("Embedding model type not determined. Cannot generate embeddings. Check initialization.")
            return None

        if not text_chunks or not isinstance(text_chunks, list):
            logger.warning("Input text_chunks is empty or not a list. Returning empty list.")
            return []

        if self.model_type == 'sentence-transformers':
            if not self.model: # self.model is the SentenceTransformer model instance
                logger.error("SentenceTransformer model is not loaded. Cannot generate embeddings.")
                return None
            try:
                embeddings = self.model.encode(text_chunks, convert_to_numpy=True)
                logger.info(f"Generated {len(embeddings)} embeddings using SentenceTransformers.")
                return [np.array(e) for e in embeddings] # Ensure they are np.array
            except Exception as e:
                logger.error(f"Error generating SentenceTransformer embeddings: {e}")
                return None

        elif self.model_type == 'openai':
            if not self.api_key or not hasattr(self, 'o_model_name'):
                logger.error("OpenAI API key or model name not configured. Cannot generate OpenAI embeddings.")
                return None

            if OPENAI_AVAILABLE and self.model: # self.model here is the openai.OpenAI client
                try:
                    # OpenAI API has limits on tokens per request and input array size.
                    # The python client handles batching for input array size, but not total tokens.
                    # Assuming text_chunks are reasonably sized.
                    all_embeddings = []
                    # The openai.embeddings.create input can be a list of strings.
                    # It's not explicitly stated if it handles internal batching for large lists against API limits (e.g. 2048 items).
                    # Let's assume it does, or we might need to batch manually if errors occur for large text_chunks.
                    # For safety, let's implement similar batching as for httpx, if text_chunks is very large.
                    # However, the `openai` library is supposed to handle this. Max items: 2048.

                    openai_batch_size = 2048
                    for i in range(0, len(text_chunks), openai_batch_size):
                        batch = text_chunks[i:i+openai_batch_size]
                        response = self.model.embeddings.create(input=batch, model=self.o_model_name)
                        batch_embeddings = [np.array(item.embedding) for item in response.data]
                        all_embeddings.extend(batch_embeddings)
                        logger.info(f"Generated {len(batch_embeddings)} embeddings in batch {i//openai_batch_size + 1} using OpenAI library.")
                    return all_embeddings
                except Exception as e:
                    logger.error(f"Error generating OpenAI embeddings using openai library: {e}.")
                    # As per prompt, if openai lib is present, we use it. If it fails, report error.
                    # No fallback to httpx if the library itself failed after being loaded.
                    return None

            elif not OPENAI_AVAILABLE: # OpenAI library not found, try httpx
                logger.info("OpenAI library not available, attempting to use httpx for embeddings.")
                return await self._generate_openai_embeddings_httpx(text_chunks)

            else: # API key might be missing, or client failed to init for other reasons
                 logger.error("OpenAI model not properly configured for generation (client not ready or API key missing).")
                 return None

        else:
            logger.error(f"Unknown model type: {self.model_type}")
            return None

    def chunk_document(self, document: str, chunk_size: int = 256, overlap: int = 32) -> List[str]:
        """
        Splits a document into overlapping chunks based on token count (approximated by words).
        Args:
            document (str): The document text to chunk.
            chunk_size (int): The target size of each chunk (in approximate tokens/words).
            overlap (int): The number of tokens/words to overlap between chunks.
        Returns:
            List[str]: A list of text chunks.
        """
        if not document or not isinstance(document, str):
            logger.warning("Input document is empty or not a string. Returning empty list.")
            return []

        """
        Splits a document into overlapping chunks based on token count (approximated by words).
        Args:
            document (str): The document text to chunk.
            chunk_size (int): The target size of each chunk (in approximate tokens/words).
            overlap (int): The number of tokens/words to overlap between chunks.
        Returns:
            List[str]: A list of text chunks.
        """
        if not document or not isinstance(document, str):
            logger.warning("Input document is empty or not a string. Returning empty list.")
            return []

        tokens = document.split() # Simple whitespace tokenization
        if not tokens:
            return []

        chunks = []
        idx = 0
        
        if chunk_size <= 0:
            logger.warning(f"Invalid chunk_size: {chunk_size}. Returning empty list.")
            return []
            
        effective_overlap = overlap
        if overlap >= chunk_size:
            logger.warning(f"Overlap {overlap} >= chunk_size {chunk_size}. Using chunk_size - 1 as overlap.")
            effective_overlap = max(0, chunk_size - 1)
            
        while idx < len(tokens):
            chunk_end_idx = min(idx + chunk_size, len(tokens))
            chunks.append(" ".join(tokens[idx:chunk_end_idx]))
            if chunk_end_idx == len(tokens):
                break
            step = chunk_size - effective_overlap
            if step <= 0:
                logger.warning(f"Non-positive step ({step}) detected due to overlap/chunk_size. Breaking.")
                break
            idx += step

        logger.info(f"Chunked document into {len(chunks)} chunks.")
        return chunks

# Example Usage (optional, for testing or demonstration within the file)
async def main_async(): # Renamed to avoid conflict if __name__ == '__main__' is used elsewhere
    logging.basicConfig(level=logging.INFO)

    # To test OpenAI, set RAG_EMBEDDING_MODEL="openai/text-embedding-ada-002"
    # and OPENAI_API_KEY="your_key" as environment variables.

    # Test with default (SentenceTransformer) or specific model
    # generator = EmbeddingGenerator(model_name='sentence-transformers/all-MiniLM-L6-v2')
    generator = EmbeddingGenerator() # Uses environment variables

    if generator.model_type: # Check if model type was determined
        logger.info(f"Using model: {generator.model_name}, Type: {generator.model_type}, Dimension: {generator.get_embedding_dimension()}")

        sample_texts = [
            "This is the first document for embedding.",
            "This document is the second document for testing purposes.",
            "And this is the third one, slightly different.",
            "Is this the first document again?"
        ]

        # generate_embeddings is now async
        embeddings = await generator.generate_embeddings(sample_texts)

        if embeddings is not None:
            for i, embedding in enumerate(embeddings):
                logger.info(f"Embedding {i+1} shape: {embedding.shape}")
                # logger.info(f"Embedding {i+1}: {embedding[:5]}...")
        else:
            logger.error("Failed to generate embeddings for sample texts.")

        long_document = " ".join(["word"] * 500) # A document of 500 words
        chunks = generator.chunk_document(long_document, chunk_size=100, overlap=20)
        logger.info(f"Long document chunked into {len(chunks)} pieces.")

        if chunks:
            logger.info(f"First chunk example: '{chunks[0][:100]}...'")
            chunk_embeddings = await generator.generate_embeddings(chunks)
            if chunk_embeddings is not None:
                 logger.info(f"Generated {len(chunk_embeddings)} embeddings for the document chunks.")
            else:
                logger.error("Failed to generate embeddings for document chunks.")
    else:
        logger.error("Could not run example usage because model type was not determined or model failed to load.")

if __name__ == '__main__':
    # To run this async main:
    # import asyncio
    # asyncio.run(main_async())
    pass # Keeping it non-blocking for automated environments by default.
