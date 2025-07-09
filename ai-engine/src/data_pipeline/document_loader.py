import abc
from typing import List
from .document import Document

class DocumentLoader(abc.ABC):
    @abc.abstractmethod
    def load(self, file_path: str) -> List[Document]:
        pass

class MarkdownLoader(DocumentLoader):
    def load(self, file_path: str) -> List[Document]:
        # This is a placeholder implementation.
        # Actual implementation will read markdown file content.
        # For now, it returns a Document with the file path as content
        # and relevant metadata.
        return [Document(content=f"Markdown content from {file_path}", metadata={"source": file_path, "type": "markdown"})]

class PdfLoader(DocumentLoader):
    def load(self, file_path: str) -> List[Document]:
        # This is a placeholder implementation.
        # Actual implementation will use a PDF parsing library (e.g., PyPDF2 or pdfminer.six)
        # For now, it returns a Document with the file path as content
        # and relevant metadata.
        # Ensure to handle potential FileNotFoundError if the pdf library is not installed
        # or if the file doesn't exist, though the file existence check should ideally be
        # done before calling this loader.
        return [Document(content=f"PDF content from {file_path}", metadata={"source": file_path, "type": "pdf"})]
