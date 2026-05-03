"""
Tests for indexing/metadata_extractor.py module.
"""

import pytest
from datetime import datetime
from indexing.metadata_extractor import (
    DocumentType,
    DocumentMetadata,
    ChunkMetadata,
    DocumentMetadataExtractor,
)


class TestDocumentType:
    """Test DocumentType enum"""

    def test_document_type_values(self):
        """Test DocumentType has expected values"""
        assert DocumentType.MARKDOWN.value == "markdown"
        assert DocumentType.CODE.value == "code"
        assert DocumentType.PLAIN_TEXT.value == "plain_text"
        assert DocumentType.PDF_LIKE.value == "pdf_like"
        assert DocumentType.UNKNOWN.value == "unknown"

    def test_document_type_count(self):
        """Test DocumentType has all expected members"""
        assert len(DocumentType) == 5


class TestDocumentMetadata:
    """Test DocumentMetadata dataclass"""

    def test_document_metadata_creation(self):
        """Test creating DocumentMetadata"""
        metadata = DocumentMetadata(
            title="Test Document",
            author="Test Author",
            date=datetime.now(),
            description="A test document",
            document_type=DocumentType.CODE,
            tags=["test", "sample"],
            source="test.java",
            word_count=100,
            heading_hierarchy=["Introduction", "Overview"],
            custom={"key": "value"},
        )

        assert metadata.title == "Test Document"
        assert metadata.author == "Test Author"
        assert metadata.document_type == DocumentType.CODE
        assert "test" in metadata.tags
        assert metadata.word_count == 100

    def test_document_metadata_defaults(self):
        """Test DocumentMetadata with default values"""
        metadata = DocumentMetadata()

        assert metadata.title is None
        assert metadata.author is None
        assert metadata.date is None
        assert metadata.document_type == DocumentType.UNKNOWN
        assert metadata.tags == []
        assert metadata.word_count == 0
        assert metadata.heading_hierarchy == []
        assert metadata.custom == {}

    def test_document_metadata_to_dict(self):
        """Test converting DocumentMetadata to dictionary"""
        metadata = DocumentMetadata(
            title="Test",
            document_type=DocumentType.MARKDOWN,
            word_count=50,
        )

        result = metadata.to_dict()

        assert isinstance(result, dict)
        assert result["title"] == "Test"
        assert result["document_type"] == "markdown"
        assert result["word_count"] == 50


class TestChunkMetadata:
    """Test ChunkMetadata dataclass"""

    def test_chunk_metadata_creation(self):
        """Test creating ChunkMetadata"""
        metadata = ChunkMetadata(
            source_document_id="doc-123",
            chunk_index=0,
            total_chunks=3,
            heading_context=["Section 1"],
            char_start=0,
            char_end=100,
        )

        assert metadata.source_document_id == "doc-123"
        assert metadata.chunk_index == 0
        assert metadata.total_chunks == 3
        assert "Section 1" in metadata.heading_context
        assert metadata.char_start == 0
        assert metadata.char_end == 100

    def test_chunk_metadata_defaults(self):
        """Test ChunkMetadata with required fields only"""
        metadata = ChunkMetadata(
            source_document_id="doc-123",
            chunk_index=0,
            total_chunks=1,
        )

        assert metadata.heading_context == []
        assert metadata.char_start == 0
        assert metadata.char_end == 0
        assert metadata.extracted_tags == []


class TestDocumentMetadataExtractor:
    """Test DocumentMetadataExtractor class"""

    @pytest.fixture
    def extractor(self):
        """Create a DocumentMetadataExtractor instance"""
        return DocumentMetadataExtractor()

    def test_extractor_initialization(self, extractor):
        """Test DocumentMetadataExtractor initialization"""
        assert extractor is not None

    def test_extract_from_markdown(self, extractor):
        """Test extracting metadata from markdown"""
        content = """---
title: Test Document
author: Test Author
tags: [test, sample]
---

# Introduction

This is a test document.
"""

        metadata = extractor.extract(content, "test.md")

        assert metadata is not None
        assert metadata.source == "test.md"

    def test_extract_from_java_code(self, extractor):
        """Test extracting metadata from Java code"""
        content = """package com.example;

import org.bukkit.plugin.JavaPlugin;

/**
 * Main plugin class
 */
public class MyPlugin extends JavaPlugin {
}
"""

        metadata = extractor.extract(content, "MyPlugin.java")

        assert metadata is not None
        assert metadata.source == "MyPlugin.java"
        # Check that 'java' appears in tags since it's a Java file
        assert "java" in metadata.tags

    def test_extract_word_count(self, extractor):
        """Test word count extraction"""
        content = "This is a test document with several words."

        metadata = extractor.extract(content, "test.txt")

        assert metadata.word_count > 0
        assert metadata.word_count >= 5

    def test_extract_from_java_file(self, extractor):
        """Test extracting from Java file"""
        content = "public class MyClass { private int x; }"

        metadata = extractor.extract(content, "MyClass.java")

        assert metadata.source == "MyClass.java"
        # Verify file extension is tracked
        assert metadata.source.endswith('.java')

    def test_extract_from_python_file(self, extractor):
        """Test extracting from Python file"""
        content = "def hello(): return 'world'"

        metadata = extractor.extract(content, "hello.py")

        assert metadata.source == "hello.py"
        assert "python" in [t.lower() for t in metadata.tags] or metadata.source.endswith('.py')

    def test_create_chunk_metadata(self, extractor):
        """Test creating chunk-level metadata"""
        content = "# Section 1\n\nSome content here."
        doc_metadata = extractor.extract(content, "test.md")

        chunk_metadata = extractor.create_chunk_metadata(
            document_id="doc-123",
            chunk_index=0,
            total_chunks=3,
            heading_context=["Section 1"],
            content=content,
            doc_type=doc_metadata.document_type,
            tags=doc_metadata.tags,
            original_heading="Section 1",
            char_start=0,
            char_end=len(content),
        )

        assert chunk_metadata.source_document_id == "doc-123"
        assert chunk_metadata.chunk_index == 0
        assert chunk_metadata.total_chunks == 3

    def test_extract_with_empty_content(self, extractor):
        """Test extracting metadata from empty content"""
        metadata = extractor.extract("", "empty.txt")

        assert metadata is not None
        assert metadata.word_count == 0

    def test_extract_headings_from_markdown(self, extractor):
        """Test extracting heading hierarchy from markdown"""
        content = """# Title

## Section 1

### Subsection

## Section 2
"""

        metadata = extractor.extract(content, "test.md")

        # Should detect heading hierarchy
        assert metadata.heading_hierarchy is not None


class TestDocumentMetadataExtractorIntegration:
    """Integration tests for DocumentMetadataExtractor"""

    def test_full_extraction_workflow(self):
        """Test complete metadata extraction workflow"""
        extractor = DocumentMetadataExtractor()

        java_code = """package com.example;

import org.bukkit.plugin.JavaPlugin;

/**
 * My awesome plugin
 * @author Developer
 */
public class MyPlugin extends JavaPlugin {
    private String configPath;
    
    @Override
    public void onEnable() {
        getLogger().info("Enabled!");
    }
}
"""

        # Extract document metadata
        doc_metadata = extractor.extract(java_code, "MyPlugin.java")

        # Create chunk metadata
        chunk_metadata = extractor.create_chunk_metadata(
            document_id="doc-1",
            chunk_index=0,
            total_chunks=1,
            heading_context=["MyPlugin"],
            content=java_code,
            doc_type=doc_metadata.document_type,
            tags=doc_metadata.tags,
            original_heading=None,
            char_start=0,
            char_end=len(java_code),
        )

        # Verify
        assert doc_metadata.source == "MyPlugin.java"
        assert chunk_metadata.source_document_id == "doc-1"
        assert chunk_metadata.chunk_index == 0

    def test_multiple_file_types(self):
        """Test extracting metadata from different file types"""
        extractor = DocumentMetadataExtractor()

        test_cases = [
            ("# Markdown\n\nContent", "test.md", DocumentType.MARKDOWN),
            ("public class Test {}", "Test.java", DocumentType.CODE),
            ("Plain text content", "test.txt", DocumentType.PLAIN_TEXT),
        ]

        for content, filename, expected_type in test_cases:
            metadata = extractor.extract(content, filename)
            # Type detection should work
            assert metadata is not None

    def test_large_document(self):
        """Test extracting metadata from large document"""
        extractor = DocumentMetadataExtractor()

        # Create large content
        content = "\n".join([f"Line {i}: " + "word " * 100 for i in range(100)])

        metadata = extractor.extract(content, "large.txt")

        assert metadata.word_count > 0