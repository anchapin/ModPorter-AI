import pytest
import os
from unittest.mock import mock_open, patch

# Adjust imports based on the actual location of your modules
from src.data_pipeline.document import Document
from src.data_pipeline.document_loader import MarkdownLoader, PdfLoader, DocumentLoader
from src.data_pipeline.text_splitter import SemanticTextSplitter, TextSplitter
from src.data_pipeline.pipeline import IngestionPipeline

# Create dummy files for testing loaders
DUMMY_MD_FILE_PATH = "dummy.md"
DUMMY_PDF_FILE_PATH = "dummy.pdf"

# Test Document class (basic instantiation)
def test_document_creation():
    doc = Document(content="Test content", metadata={"source": "test"})
    assert doc.content == "Test content"
    assert doc.metadata["source"] == "test"

# --- Test DocumentLoaders ---
class MockDocumentLoader(DocumentLoader):
    def load(self, file_path: str) -> list[Document]:
        return [Document(content=f"Content from {file_path}", metadata={"source": file_path})]

def test_markdown_loader_placeholder():
    loader = MarkdownLoader()
    # This test relies on the placeholder implementation detail.
    # It should be updated when actual file reading is implemented.
    docs = loader.load(DUMMY_MD_FILE_PATH)
    assert len(docs) == 1
    assert docs[0].content == f"Markdown content from {DUMMY_MD_FILE_PATH}"
    assert docs[0].metadata["source"] == DUMMY_MD_FILE_PATH
    assert docs[0].metadata["type"] == "markdown"

def test_pdf_loader_placeholder():
    loader = PdfLoader()
    # This test relies on the placeholder implementation detail.
    # It should be updated when actual file reading is implemented.
    docs = loader.load(DUMMY_PDF_FILE_PATH)
    assert len(docs) == 1
    assert docs[0].content == f"PDF content from {DUMMY_PDF_FILE_PATH}"
    assert docs[0].metadata["source"] == DUMMY_PDF_FILE_PATH
    assert docs[0].metadata["type"] == "pdf"

# --- Test TextSplitters ---
class MockTextSplitter(TextSplitter):
    def split_text(self, document: Document) -> list[Document]:
        # Simple split for testing, creates two chunks
        content1 = document.content[:len(document.content)//2]
        content2 = document.content[len(document.content)//2:]
        return [
            Document(content=content1, metadata=document.metadata.copy()),
            Document(content=content2, metadata=document.metadata.copy())
        ]

def test_semantic_text_splitter_placeholder():
    splitter = SemanticTextSplitter(chunk_size=10, chunk_overlap=2)
    doc_content = "This is a test document for splitting."
    doc = Document(content=doc_content, metadata={"source": "test_doc"})

    chunks = splitter.split_text(doc)

    assert len(chunks) > 0
    # Check if content is split (placeholder behavior)
    # Example: "This is a "
    assert chunks[0].content == doc_content[0:10]
    assert chunks[0].metadata["source"] == "test_doc"
    assert chunks[0].metadata["chunk_id"] == 0

    if len(chunks) > 1:
        # Example: "a test d" (starts at 10-2=8)
        assert chunks[1].content == doc_content[8:18]
        assert chunks[1].metadata["chunk_id"] == 1

def test_semantic_text_splitter_small_content():
    splitter = SemanticTextSplitter(chunk_size=100, chunk_overlap=20)
    doc_content = "Short."
    doc = Document(content=doc_content, metadata={"source": "short_doc"})
    chunks = splitter.split_text(doc)
    assert len(chunks) == 1
    assert chunks[0].content == "Short."
    assert chunks[0].metadata["chunk_id"] == 0

# --- Test IngestionPipeline ---
def test_ingestion_pipeline():
    # Use mock loader and splitter for pipeline test
    mock_loader = MockDocumentLoader()
    mock_splitter = MockTextSplitter()

    pipeline = IngestionPipeline(document_loader=mock_loader, text_splitter=mock_splitter)

    file_path = "test_file.txt"

    # Since MockDocumentLoader creates 1 doc, and MockTextSplitter splits it into 2 chunks
    processed_chunks = pipeline.process(file_path)

    assert len(processed_chunks) == 2
    assert processed_chunks[0].metadata["source"] == file_path
    assert processed_chunks[1].metadata["source"] == file_path
    # Check if content was split by mock_splitter logic
    expected_content_base = f"Content from {file_path}"
    assert processed_chunks[0].content == expected_content_base[:len(expected_content_base)//2]
    assert processed_chunks[1].content == expected_content_base[len(expected_content_base)//2:]

def test_ingestion_pipeline_batch():
    mock_loader = MockDocumentLoader()
    mock_splitter = MockTextSplitter()

    pipeline = IngestionPipeline(document_loader=mock_loader, text_splitter=mock_splitter)

    file_paths = ["file1.txt", "file2.txt"]

    # Each file produces 1 doc from loader, split into 2 chunks by splitter.
    # So, 2 files * 2 chunks/file = 4 chunks total.
    all_chunks = pipeline.process_batch(file_paths)

    assert len(all_chunks) == 4
    assert all_chunks[0].metadata["source"] == "file1.txt"
    assert all_chunks[1].metadata["source"] == "file1.txt"
    assert all_chunks[2].metadata["source"] == "file2.txt"
    assert all_chunks[3].metadata["source"] == "file2.txt"

# It's good practice to ensure dummy files used for tests are cleaned up if they were actually created.
# However, these tests currently use placeholder loaders that don't actually read from disk.
# If actual file I/O was added to loaders, setup/teardown for these files would be needed.
# For now, this is not strictly necessary.
