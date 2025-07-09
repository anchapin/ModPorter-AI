import abc
from typing import List
from .document import Document

class TextSplitter(abc.ABC):
    @abc.abstractmethod
    def split_text(self, document: Document) -> List[Document]:
        pass

class SemanticTextSplitter(TextSplitter):
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split_text(self, document: Document) -> List[Document]:
        # This is a placeholder implementation for semantic chunking.
        # A real implementation would use NLP libraries (e.g., spaCy or NLTK)
        # or other heuristic methods to split text into meaningful chunks.
        # For now, it splits by character count with overlap.

        chunks = []
        content = document.content
        metadata = document.metadata.copy() # Make a copy to avoid modifying original

        start_index = 0
        chunk_id = 0
        while start_index < len(content):
            end_index = min(start_index + self.chunk_size, len(content))
            chunk_content = content[start_index:end_index]

            chunk_metadata = metadata.copy()
            chunk_metadata["chunk_id"] = chunk_id
            chunk_metadata["original_document_source"] = metadata.get("source", "unknown")

            chunks.append(Document(content=chunk_content, metadata=chunk_metadata))

            chunk_id += 1
            if end_index == len(content):
                break
            start_index += self.chunk_size - self.chunk_overlap
            if start_index >= len(content): # Ensure we don't create an empty chunk if overlap is large
                break

        return chunks
