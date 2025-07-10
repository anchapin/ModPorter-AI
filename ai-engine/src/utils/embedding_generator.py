import logging
from typing import List, Union
import numpy as np # Add if numpy is used for embeddings

logger = logging.getLogger(__name__)

# Optional import for sentence-transformers
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SentenceTransformer = None
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logger.warning("sentence-transformers not available. EmbeddingGenerator will be disabled.")

class EmbeddingGenerator:
    def __init__(self, model_name: str = 'sentence-transformers/all-MiniLM-L6-v2'):
        """
        Initializes the EmbeddingGenerator and loads the specified sentence transformer model.
        Args:
            model_name (str): The name of the sentence transformer model to load.
        """
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            logger.error("sentence-transformers not available. Cannot initialize EmbeddingGenerator.")
            self.model = None
            return
            
        try:
            self.model = SentenceTransformer(model_name)
            logger.info(f"SentenceTransformer model '{model_name}' loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load SentenceTransformer model '{model_name}': {e}")
            # Consider re-raising the exception or handling it appropriately
            # For now, let's store None and log an error. The user of the class should check.
            self.model = None
            # raise e # Or re-raise to make it clear initialization failed

    def generate_embeddings(self, text_chunks: List[str]) -> Union[List[np.ndarray], None]:
        """
        Generates embeddings for a list of text chunks.
        Args:
            text_chunks (List[str]): A list of text strings to embed.
        Returns:
            List[np.ndarray]: A list of embeddings (NumPy arrays), or None if the model isn't loaded.
        """
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            logger.error("sentence-transformers not available. Cannot generate embeddings.")
            return None
            
        if not self.model:
            logger.error("Embedding model is not loaded. Cannot generate embeddings.")
            return None
        if not text_chunks or not isinstance(text_chunks, list):
            logger.warning("Input text_chunks is empty or not a list. Returning empty list.")
            return []

        try:
            embeddings = self.model.encode(text_chunks, convert_to_numpy=True)
            logger.info(f"Generated {len(embeddings)} embeddings.")
            return embeddings
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
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

        # Simple whitespace-based tokenization for approximation.
        # More sophisticated tokenization (e.g., from the model itself) could be used
        # for more accurate chunk sizing, but word splitting is a common heuristic.
        tokens = document.split()
        if not tokens:
            return []

        # Refined chunking logic:
        chunks = []
        idx = 0
        
        # Safety check for infinite loop conditions
        if chunk_size <= 0:
            logger.warning(f"Invalid chunk_size: {chunk_size}. Returning empty list.")
            return []
            
        if overlap >= chunk_size:
            logger.warning(f"Overlap {overlap} >= chunk_size {chunk_size}. Using chunk_size - 1 as overlap.")
            overlap = max(0, chunk_size - 1)
            
        while idx < len(tokens):
            # Define the end of the current chunk
            chunk_end_idx = min(idx + chunk_size, len(tokens))
            # Add the current chunk
            chunks.append(" ".join(tokens[idx:chunk_end_idx]))
            # If this chunk reaches the end of the document, break
            if chunk_end_idx == len(tokens):
                break
            # Move the starting point for the next chunk.
            # The step is chunk_size minus overlap to create overlapping windows.
            step = chunk_size - overlap
            if step <= 0:
                # This should not happen due to the safety check above, but just in case
                logger.warning(f"Non-positive step detected: {step}. Breaking to prevent infinite loop.")
                break
            idx += step

        logger.info(f"Chunked document into {len(chunks)} chunks.")
        return chunks

# Example Usage (optional, for testing or demonstration within the file)
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    generator = EmbeddingGenerator()

    if generator.model:
        sample_texts = [
            "This is the first document.",
            "This document is the second document.",
            "And this is the third one.",
            "Is this the first document?"
        ]
        embeddings = generator.generate_embeddings(sample_texts)
        if embeddings is not None:
            for i, embedding in enumerate(embeddings):
                logger.info(f"Embedding {i+1} shape: {embedding.shape}")
                # logger.info(f"Embedding {i+1}: {embedding[:5]}...") # Print first 5 elements

        long_document = " ".join(["word"] * 1000) # A long document of 1000 words
        chunks = generator.chunk_document(long_document, chunk_size=100, overlap=20)
        logger.info(f"Long document chunked into {len(chunks)} pieces.")
        if chunks:
            logger.info(f"First chunk example: '{chunks[0][:100]}...'")
            chunk_embeddings = generator.generate_embeddings(chunks)
            if chunk_embeddings is not None:
                 logger.info(f"Generated {len(chunk_embeddings)} embeddings for the chunks.")
    else:
        logger.error("Could not run example usage because model failed to load.")
