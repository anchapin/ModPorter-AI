"""
Unit tests for ingestion source base module.
"""

import pytest
from src.ingestion.sources.base import (
    DocumentType,
    RawDocument,
    BaseSourceAdapter,
)


class TestDocumentType:
    """Test cases for DocumentType enum."""

    def test_all_document_types(self):
        """Test all document types are defined."""
        assert DocumentType.MARKDOWN.value == "markdown"
        assert DocumentType.HTML.value == "html"
        assert DocumentType.PDF.value == "pdf"
        assert DocumentType.CODE.value == "code"


class TestRawDocument:
    """Test cases for RawDocument dataclass."""

    def test_creation_with_required_fields(self):
        """Test creating raw document with required fields."""
        doc = RawDocument(
            content="# Test Content",
            source_url="https://example.com/test",
            doc_type=DocumentType.MARKDOWN,
            metadata={},
        )

        assert doc.content == "# Test Content"
        assert doc.source_url == "https://example.com/test"
        assert doc.doc_type == DocumentType.MARKDOWN
        assert doc.metadata == {}

    def test_creation_with_all_fields(self):
        """Test creating raw document with all fields."""
        doc = RawDocument(
            content="# Test Content",
            source_url="https://example.com/test",
            doc_type=DocumentType.MARKDOWN,
            metadata={"author": "test"},
            title="Test Title",
        )

        assert doc.title == "Test Title"
        assert doc.metadata["author"] == "test"

    def test_default_metadata_none(self):
        """Test metadata defaults to empty dict when None."""
        doc = RawDocument(
            content="content",
            source_url="https://example.com",
            doc_type=DocumentType.HTML,
            metadata=None,
        )

        assert doc.metadata == {}

    def test_post_init_sets_metadata_dict(self):
        """Test __post_init__ ensures metadata is a dict."""
        doc = RawDocument(
            content="content",
            source_url="https://example.com",
            doc_type=DocumentType.HTML,
            metadata={"key": "value"},
        )

        assert isinstance(doc.metadata, dict)
        assert doc.metadata["key"] == "value"


class TestBaseSourceAdapter:
    """Test cases for BaseSourceAdapter abstract class."""

    def test_is_abstract(self):
        """Test that BaseSourceAdapter cannot be instantiated."""
        with pytest.raises(TypeError):
            BaseSourceAdapter()

    def test_subclass_must_implement_methods(self):
        """Test that subclass must implement abstract methods."""

        class IncompleteAdapter(BaseSourceAdapter):
            pass

        with pytest.raises(TypeError):
            IncompleteAdapter()

    def test_subclass_can_implement_methods(self):
        """Test that proper subclass can be instantiated."""

        class CompleteAdapter(BaseSourceAdapter):
            async def fetch(self, config):
                return []

            def validate_config(self, config):
                return True

        adapter = CompleteAdapter()

        # These should not raise
        import asyncio

        result = asyncio.run(adapter.fetch({}))
        assert result == []

        assert adapter.validate_config({}) is True
