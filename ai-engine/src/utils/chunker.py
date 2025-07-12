import logging

logger = logging.getLogger(__name__)

class Chunker:
    @staticmethod
    def chunk_document(document: str, chunk_size: int = 256, overlap: int = 32):
        if not document or not isinstance(document, str):
            logger.warning("Input document is empty or not a string. Returning empty list.")
            return []
        tokens = document.split()
        if not tokens:
            return []
        chunks = []
        idx = 0
        effective_overlap = overlap
        if chunk_size <= 0:
            logger.warning(f"Invalid chunk_size: {chunk_size}. Returning empty list.")
            return []
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
