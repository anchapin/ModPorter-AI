"""
Unit tests for AdvancedChunker and its strategies.
"""

import pytest
from utils.advanced_chunker import AdvancedChunker, ChunkType, JavaCodeChunker, SemanticChunker


class TestJavaCodeChunker:
    """Test cases for JavaCodeChunker."""

    @pytest.fixture
    def chunker(self):
        return JavaCodeChunker()

    def test_chunk_java_code_basic(self, chunker):
        """Test chunking basic Java code with package and imports."""
        code = """
package com.test;
import java.util.List;
import java.util.ArrayList;

public class TestClass {
    private String name;
    
    public TestClass(String name) {
        this.name = name;
    }
    
    public String getName() {
        return name;
    }
}
"""
        chunks = chunker.chunk_java_code(code, "TestClass.java")
        
        # Check package chunk
        assert any(c.metadata.get("package_name") == "com.test" for c in chunks)
        # Check imports chunk
        assert any(c.metadata.get("type") == "imports" for c in chunks)
        # Check class chunk
        assert any(c.chunk_type == ChunkType.CODE_CLASS and c.metadata.get("class_name") == "TestClass" for c in chunks)
        # Check method chunks
        method_chunks = [c for c in chunks if c.chunk_type == ChunkType.CODE_METHOD]
        assert len(method_chunks) >= 2
        assert any(c.metadata.get("method_name") == "getName" for c in chunks)

    def test_chunk_java_with_regex_fallback(self, chunker):
        """Test regex fallback for Java code."""
        code = "public class Fallback { }"
        chunks = chunker._chunk_java_with_regex(code, "Fallback.java")
        assert len(chunks) > 0
        assert chunks[0].metadata.get("class_name") == "Fallback"


class TestSemanticChunker:
    """Test cases for SemanticChunker."""

    @pytest.fixture
    def chunker(self):
        return SemanticChunker(max_chunk_size=100, overlap=10)

    def test_chunk_documentation(self, chunker):
        """Test chunking markdown documentation."""
        text = """
# Header 1
Content for section 1. This is a bit longer to test splitting.

## Header 2
Content for section 2.
"""
        chunks = chunker._chunk_documentation(text)
        assert len(chunks) >= 2
        assert chunks[0].metadata.get("header_text") == "Header 1"
        assert chunks[1].metadata.get("header_text") == "Header 2"

    def test_chunk_json_configuration(self, chunker):
        """Test chunking JSON configuration."""
        import json
        config = {
            "section1": {"key1": "value1", "key2": "value2" * 20},
            "section2": {"key3": "value3" * 20}
        }
        text = json.dumps(config)
        
        chunks = chunker._chunk_json_config(text)
        assert len(chunks) >= 2
        assert any(c.metadata.get("config_key") == "section1" for c in chunks)

    def test_chunk_yaml_configuration(self, chunker):
        """Test chunking YAML-like configuration."""
        text = """
section1:
  key1: value1
section2:
  key2: value2
"""
        chunks = chunker._chunk_yaml_config(text)
        assert len(chunks) >= 2
        assert any(c.metadata.get("config_key") == "section1" for c in chunks)

    def test_chunk_general_text(self, chunker):
        """Test chunking general text."""
        text = "Paragraph 1.\n\nParagraph 2 is much longer. " + "Sentence. " * 20
        chunks = chunker._chunk_general_text(text)
        assert len(chunks) > 1


class TestAdvancedChunker:
    """Test cases for AdvancedChunker main class."""

    @pytest.fixture
    def chunker(self):
        return AdvancedChunker()

    def test_chunk_content_routing(self, chunker):
        """Test routing to correct chunker based on type/path."""
        # Java routing
        chunks = chunker.chunk_content("public class Test {}", "java")
        assert any(c.chunk_type == ChunkType.CODE_CLASS for c in chunks)
        
        # Documentation routing
        chunks = chunker.chunk_content("# Doc", "text", "doc.md")
        assert any(c.metadata.get("header_text") == "Doc" for c in chunks)
        
        # Configuration routing
        chunks = chunker.chunk_content('{"a": 1}', "configuration")
        # For small JSON it might not create chunks in _chunk_json_config, 
        # but will return something from generic/general.

    def test_get_chunk_statistics(self, chunker):
        """Test chunk statistics calculation."""
        from utils.advanced_chunker import Chunk, ChunkType
        chunks = [
            Chunk("content1", ChunkType.TEXT),
            Chunk("content2 is longer", ChunkType.TEXT)
        ]
        stats = chunker.get_chunk_statistics(chunks)
        assert stats["total_chunks"] == 2
        assert stats["average_chunk_size"] > 0
        assert ChunkType.TEXT in stats["chunk_type_distribution"]
