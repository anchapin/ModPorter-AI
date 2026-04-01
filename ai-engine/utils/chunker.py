import logging
from typing import List

logger = logging.getLogger(__name__)


class Chunker:
    @staticmethod
    def chunk_document(document: str, chunk_size: int, overlap: int) -> List[str]:
        """
        Splits a document into smaller chunks with a specified overlap.

        Args:
            document: The text content of the document to chunk.
            chunk_size: The desired size of each chunk.
            overlap: The number of characters to overlap between consecutive chunks.

        Returns:
            A list of document chunks.
        """
        if not document or not isinstance(document, str):
            logger.warning("Document is empty or not a string. Returning empty list.")
            return []

        chunks = []
        start = 0
        increment = chunk_size - overlap
        if increment <= 0:
            logger.warning("chunk_size - overlap <= 0. Using chunk_size as increment to avoid infinite loop.")
            increment = chunk_size

        while start < len(document):
            end = start + chunk_size
            chunk = document[start:end]
            chunks.append(chunk)
            start += increment
        return chunks
