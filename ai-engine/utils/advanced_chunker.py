"""
Advanced chunking system for multi-modal content.

This module provides enhanced chunking strategies for different content types
including code-aware chunking, semantic chunking, and multi-modal content processing.
"""

import ast
import re
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
import hashlib

logger = logging.getLogger(__name__)


class ChunkType(str, Enum):
    """Types of chunks supported by the advanced chunking system."""
    TEXT = "text"
    CODE_CLASS = "code_class"
    CODE_METHOD = "code_method"
    CODE_BLOCK = "code_block"
    DOCUMENTATION = "documentation"
    CONFIGURATION = "configuration"
    COMMENT = "comment"


@dataclass
class Chunk:
    """Represents a chunk of content with metadata."""
    content: str
    chunk_type: ChunkType
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    metadata: Dict[str, Any] = None
    parent_chunk: Optional[str] = None
    chunk_id: Optional[str] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.chunk_id is None:
            self.chunk_id = hashlib.md5(self.content.encode()).hexdigest()[:12]


class JavaCodeChunker:
    """
    Advanced Java code chunker that understands language structure.
    
    This chunker creates semantically meaningful chunks based on Java
    language constructs rather than arbitrary text boundaries.
    """
    
    def __init__(self):
        self.class_pattern = re.compile(r'^\s*(?:public|private|protected)?\s*(?:static|final)?\s*class\s+(\w+)', re.MULTILINE)
        self.method_pattern = re.compile(r'^\s*(?:public|private|protected)?\s*(?:static|final)?\s*(?:\w+\s+)*(\w+)\s*\([^)]*\)\s*\{', re.MULTILINE)
        self.field_pattern = re.compile(r'^\s*(?:public|private|protected)?\s*(?:static|final)?\s*\w+\s+(\w+)\s*[=;]', re.MULTILINE)
        self.import_pattern = re.compile(r'^import\s+([^;]+);', re.MULTILINE)
        self.package_pattern = re.compile(r'^package\s+([^;]+);', re.MULTILINE)
        self.annotation_pattern = re.compile(r'^\s*@(\w+)', re.MULTILINE)
    
    def chunk_java_code(self, code: str, file_path: str = "") -> List[Chunk]:
        """
        Chunk Java code into semantically meaningful pieces.
        
        Args:
            code: The Java source code to chunk
            file_path: Path to the source file (for metadata)
            
        Returns:
            List of chunks representing different parts of the code
        """
        chunks = []
        code.split('\n')
        
        # Extract package and imports
        package_match = self.package_pattern.search(code)
        if package_match:
            package_name = package_match.group(1)
            chunks.append(Chunk(
                content=package_match.group(0),
                chunk_type=ChunkType.CODE_BLOCK,
                start_line=1,
                end_line=1,
                metadata={
                    'type': 'package_declaration',
                    'package_name': package_name,
                    'file_path': file_path
                }
            ))
        
        # Extract imports
        import_matches = list(self.import_pattern.finditer(code))
        if import_matches:
            import_lines = [match.group(0) for match in import_matches]
            chunks.append(Chunk(
                content='\n'.join(import_lines),
                chunk_type=ChunkType.CODE_BLOCK,
                metadata={
                    'type': 'imports',
                    'import_count': len(import_lines),
                    'file_path': file_path
                }
            ))
        
        # Find class boundaries
        try:
            ast.parse(code)  # This won't work for Java, but shows the concept
        except:
            # Fallback to regex-based chunking for Java
            chunks.extend(self._chunk_java_with_regex(code, file_path))
        
        return chunks
    
    def _chunk_java_with_regex(self, code: str, file_path: str) -> List[Chunk]:
        """Fallback regex-based chunking for Java code."""
        chunks = []
        code.split('\n')
        
        # Find classes
        for class_match in self.class_pattern.finditer(code):
            class_name = class_match.group(1)
            class_start = code[:class_match.start()].count('\n') + 1
            
            # Find the class body
            class_content = self._extract_class_body(code, class_match.start())
            if class_content:
                chunks.append(Chunk(
                    content=class_content,
                    chunk_type=ChunkType.CODE_CLASS,
                    start_line=class_start,
                    metadata={
                        'class_name': class_name,
                        'file_path': file_path,
                        'type': 'class_definition'
                    }
                ))
                
                # Extract methods from the class
                method_chunks = self._extract_methods_from_class(class_content, class_name, class_start)
                chunks.extend(method_chunks)
        
        return chunks
    
    def _extract_class_body(self, code: str, start_pos: int) -> Optional[str]:
        """Extract the complete class body including nested braces."""
        brace_count = 0
        in_class = False
        
        for i, char in enumerate(code[start_pos:], start_pos):
            if char == '{':
                if not in_class:
                    in_class = True
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0 and in_class:
                    return code[start_pos:i+1]
        
        return None
    
    def _extract_methods_from_class(self, class_content: str, class_name: str, class_start_line: int) -> List[Chunk]:
        """Extract method definitions from a class."""
        method_chunks = []
        
        for method_match in self.method_pattern.finditer(class_content):
            method_name = method_match.group(1)
            method_start = class_start_line + class_content[:method_match.start()].count('\n')
            
            # Extract method body
            method_body = self._extract_method_body(class_content, method_match.start())
            if method_body:
                method_chunks.append(Chunk(
                    content=method_body,
                    chunk_type=ChunkType.CODE_METHOD,
                    start_line=method_start,
                    metadata={
                        'method_name': method_name,
                        'class_name': class_name,
                        'type': 'method_definition'
                    },
                    parent_chunk=class_name
                ))
        
        return method_chunks
    
    def _extract_method_body(self, content: str, start_pos: int) -> Optional[str]:
        """Extract the complete method body."""
        brace_count = 0
        in_method = False
        
        for i, char in enumerate(content[start_pos:], start_pos):
            if char == '{':
                if not in_method:
                    in_method = True
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0 and in_method:
                    return content[start_pos:i+1]
        
        return None


class SemanticChunker:
    """
    Semantic chunker that creates chunks based on content meaning.
    
    This chunker attempts to keep semantically related content together
    and split at natural boundaries.
    """
    
    def __init__(self, max_chunk_size: int = 512, overlap: int = 50):
        self.max_chunk_size = max_chunk_size
        self.overlap = overlap
        self.sentence_endings = {'.', '!', '?', '\n\n'}
        self.paragraph_markers = {'\n\n', '\n\n\n'}
    
    def chunk_text(self, text: str, document_type: str = "general") -> List[Chunk]:
        """
        Create semantic chunks from text content.
        
        Args:
            text: The text to chunk
            document_type: Type of document (affects chunking strategy)
            
        Returns:
            List of semantic chunks
        """
        if document_type == "documentation":
            return self._chunk_documentation(text)
        elif document_type == "configuration":
            return self._chunk_configuration(text)
        else:
            return self._chunk_general_text(text)
    
    def _chunk_documentation(self, text: str) -> List[Chunk]:
        """Chunk documentation with awareness of structure."""
        chunks = []
        
        # Split by headers first
        header_pattern = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)
        sections = []
        last_end = 0
        
        for match in header_pattern.finditer(text):
            if last_end < match.start():
                content = text[last_end:match.start()].strip()
                if content:
                    sections.append(('content', content))
            
            header_level = len(match.group(1))
            header_text = match.group(2)
            sections.append(('header', match.group(0), header_level, header_text))
            last_end = match.end()
        
        # Add remaining content
        if last_end < len(text):
            content = text[last_end:].strip()
            if content:
                sections.append(('content', content))
        
        # Create chunks from sections
        current_chunk = ""
        current_metadata = {}
        
        for section in sections:
            if section[0] == 'header':
                # Start new chunk with header
                if current_chunk:
                    chunks.append(Chunk(
                        content=current_chunk.strip(),
                        chunk_type=ChunkType.DOCUMENTATION,
                        metadata=current_metadata.copy()
                    ))
                
                current_chunk = section[1] + '\n\n'
                current_metadata = {
                    'header_level': section[2],
                    'header_text': section[3],
                    'type': 'documentation_section'
                }
            else:
                # Add content to current chunk
                if len(current_chunk) + len(section[1]) > self.max_chunk_size:
                    # Split the content
                    remaining_space = self.max_chunk_size - len(current_chunk)
                    if remaining_space > 100:  # Add some content if there's space
                        split_point = self._find_split_point(section[1], remaining_space)
                        current_chunk += section[1][:split_point]
                        
                        chunks.append(Chunk(
                            content=current_chunk.strip(),
                            chunk_type=ChunkType.DOCUMENTATION,
                            metadata=current_metadata.copy()
                        ))
                        
                        # Start new chunk with remaining content
                        current_chunk = section[1][split_point - self.overlap:]
                    else:
                        # Finish current chunk and start new one
                        chunks.append(Chunk(
                            content=current_chunk.strip(),
                            chunk_type=ChunkType.DOCUMENTATION,
                            metadata=current_metadata.copy()
                        ))
                        current_chunk = section[1]
                else:
                    current_chunk += section[1] + '\n\n'
        
        # Add final chunk
        if current_chunk.strip():
            chunks.append(Chunk(
                content=current_chunk.strip(),
                chunk_type=ChunkType.DOCUMENTATION,
                metadata=current_metadata
            ))
        
        return chunks
    
    def _chunk_configuration(self, text: str) -> List[Chunk]:
        """Chunk configuration files (JSON, YAML, etc.)."""
        chunks = []
        
        # Try to detect configuration format
        text_stripped = text.strip()
        
        if text_stripped.startswith('{') and text_stripped.endswith('}'):
            # JSON configuration
            chunks.extend(self._chunk_json_config(text))
        elif re.match(r'^\w+:', text_stripped, re.MULTILINE):
            # YAML-like configuration
            chunks.extend(self._chunk_yaml_config(text))
        else:
            # Generic configuration
            chunks.extend(self._chunk_generic_config(text))
        
        return chunks
    
    def _chunk_json_config(self, text: str) -> List[Chunk]:
        """Chunk JSON configuration."""
        import json
        
        try:
            config = json.loads(text)
            chunks = []
            
            # Create chunks for major sections
            for key, value in config.items():
                if isinstance(value, dict) and len(str(value)) > 100:
                    chunk_content = f'"{key}": {json.dumps(value, indent=2)}'
                    chunks.append(Chunk(
                        content=chunk_content,
                        chunk_type=ChunkType.CONFIGURATION,
                        metadata={
                            'config_key': key,
                            'config_type': 'json_section',
                            'value_type': type(value).__name__
                        }
                    ))
            
            return chunks
        except json.JSONDecodeError:
            # Fallback to generic chunking
            return self._chunk_generic_config(text)
    
    def _chunk_yaml_config(self, text: str) -> List[Chunk]:
        """Chunk YAML-like configuration."""
        chunks = []
        lines = text.split('\n')
        current_section = []
        current_key = None
        
        for line in lines:
            if re.match(r'^\w+:', line):
                # New top-level key
                if current_section:
                    chunks.append(Chunk(
                        content='\n'.join(current_section),
                        chunk_type=ChunkType.CONFIGURATION,
                        metadata={
                            'config_key': current_key,
                            'config_type': 'yaml_section'
                        }
                    ))
                
                current_key = line.split(':')[0]
                current_section = [line]
            else:
                current_section.append(line)
        
        # Add final section
        if current_section:
            chunks.append(Chunk(
                content='\n'.join(current_section),
                chunk_type=ChunkType.CONFIGURATION,
                metadata={
                    'config_key': current_key,
                    'config_type': 'yaml_section'
                }
            ))
        
        return chunks
    
    def _chunk_generic_config(self, text: str) -> List[Chunk]:
        """Generic configuration chunking."""
        # Simple line-based chunking for unknown formats
        lines = text.split('\n')
        chunks = []
        current_chunk_lines = []
        
        for line in lines:
            current_chunk_lines.append(line)
            
            if len('\n'.join(current_chunk_lines)) > self.max_chunk_size:
                chunks.append(Chunk(
                    content='\n'.join(current_chunk_lines[:-1]),
                    chunk_type=ChunkType.CONFIGURATION,
                    metadata={'config_type': 'generic'}
                ))
                current_chunk_lines = current_chunk_lines[-self.overlap//10:]  # Keep some overlap
        
        if current_chunk_lines:
            chunks.append(Chunk(
                content='\n'.join(current_chunk_lines),
                chunk_type=ChunkType.CONFIGURATION,
                metadata={'config_type': 'generic'}
            ))
        
        return chunks
    
    def _chunk_general_text(self, text: str) -> List[Chunk]:
        """Chunk general text content."""
        chunks = []
        
        # Split by paragraphs first
        paragraphs = re.split(r'\n\s*\n', text)
        current_chunk = ""
        
        for paragraph in paragraphs:
            if len(current_chunk) + len(paragraph) > self.max_chunk_size:
                if current_chunk:
                    chunks.append(Chunk(
                        content=current_chunk.strip(),
                        chunk_type=ChunkType.TEXT,
                        metadata={'type': 'general_text'}
                    )) 
                
                # If paragraph is too long, split it
                if len(paragraph) > self.max_chunk_size:
                    sub_chunks = self._split_long_paragraph(paragraph)
                    chunks.extend(sub_chunks)
                    current_chunk = ""
                else:
                    current_chunk = paragraph
            else:
                if current_chunk:
                    current_chunk += '\n\n' + paragraph
                else:
                    current_chunk = paragraph
        
        if current_chunk.strip():
            chunks.append(Chunk(
                content=current_chunk.strip(),
                chunk_type=ChunkType.TEXT,
                metadata={'type': 'general_text'}
            ))
        
        return chunks
    
    def _split_long_paragraph(self, paragraph: str) -> List[Chunk]:
        """Split a paragraph that's too long."""
        chunks = []
        sentences = re.split(r'[.!?]+\s+', paragraph)
        current_chunk = ""
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) > self.max_chunk_size:
                if current_chunk:
                    chunks.append(Chunk(
                        content=current_chunk.strip(),
                        chunk_type=ChunkType.TEXT,
                        metadata={'type': 'text_fragment'}
                    ))
                current_chunk = sentence
            else:
                if current_chunk:
                    current_chunk += '. ' + sentence
                else:
                    current_chunk = sentence
        
        if current_chunk.strip():
            chunks.append(Chunk(
                content=current_chunk.strip(),
                chunk_type=ChunkType.TEXT,
                metadata={'type': 'text_fragment'}
            ))
        
        return chunks
    
    def _find_split_point(self, text: str, max_length: int) -> int:
        """Find the best point to split text."""
        if len(text) <= max_length:
            return len(text)
        
        # Look for sentence boundaries
        for i in range(max_length, max(0, max_length - 100), -1):
            if text[i] in self.sentence_endings:
                return i + 1
        
        # Look for word boundaries
        for i in range(max_length, max(0, max_length - 50), -1):
            if text[i].isspace():
                return i
        
        # Fallback to max length
        return max_length


class AdvancedChunker:
    """
    Main chunking class that coordinates different chunking strategies.
    
    This class automatically selects the appropriate chunking strategy
    based on content type and format.
    """
    
    def __init__(self, max_chunk_size: int = 512, overlap: int = 50):
        self.java_chunker = JavaCodeChunker()
        self.semantic_chunker = SemanticChunker(max_chunk_size, overlap)
        self.max_chunk_size = max_chunk_size
        self.overlap = overlap
    
    def chunk_content(self, content: str, content_type: str, file_path: str = "", **kwargs) -> List[Chunk]:
        """
        Chunk content using the appropriate strategy.
        
        Args:
            content: The content to chunk
            content_type: Type of content (code, text, documentation, etc.)
            file_path: Path to the source file
            **kwargs: Additional parameters for specific chunkers
            
        Returns:
            List of chunks
        """
        logger.info(f"Chunking content of type '{content_type}' from '{file_path}'")
        
        if content_type == "java" or (file_path and file_path.endswith('.java')):
            return self.java_chunker.chunk_java_code(content, file_path)
        elif content_type == "documentation" or file_path.endswith(('.md', '.rst', '.txt')):
            return self.semantic_chunker.chunk_text(content, "documentation")
        elif content_type == "configuration" or file_path.endswith(('.json', '.yaml', '.yml', '.toml', '.ini')):
            return self.semantic_chunker.chunk_text(content, "configuration")
        else:
            return self.semantic_chunker.chunk_text(content, "general")
    
    def get_chunk_statistics(self, chunks: List[Chunk]) -> Dict[str, Any]:
        """Get statistics about the chunks."""
        if not chunks:
            return {}
        
        chunk_sizes = [len(chunk.content) for chunk in chunks]
        chunk_types = [chunk.chunk_type for chunk in chunks]
        
        from collections import Counter
        type_counts = Counter(chunk_types)
        
        return {
            'total_chunks': len(chunks),
            'total_characters': sum(chunk_sizes),
            'average_chunk_size': sum(chunk_sizes) / len(chunks),
            'min_chunk_size': min(chunk_sizes),
            'max_chunk_size': max(chunk_sizes),
            'chunk_type_distribution': dict(type_counts),
            'chunks_with_metadata': sum(1 for chunk in chunks if chunk.metadata)
        }