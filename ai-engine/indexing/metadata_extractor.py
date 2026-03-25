"""
Metadata extraction for document indexing.

Provides extraction of:
- Document-level metadata (title, author, date, type, tags)
- Chunk-level metadata (heading context, position, references)
"""

import re
import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum


class DocumentType(Enum):
    """Document type classification."""
    MARKDOWN = "markdown"
    CODE = "code"
    PLAIN_TEXT = "plain_text"
    PDF_LIKE = "pdf_like"
    UNKNOWN = "unknown"


@dataclass
class DocumentMetadata:
    """Metadata for a complete document."""
    title: Optional[str] = None
    author: Optional[str] = None
    date: Optional[datetime] = None
    description: Optional[str] = None
    document_type: DocumentType = DocumentType.UNKNOWN
    tags: List[str] = field(default_factory=list)
    source: Optional[str] = None
    word_count: int = 0
    heading_hierarchy: List[str] = field(default_factory=list)
    custom: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "title": self.title,
            "author": self.author,
            "date": self.date.isoformat() if self.date else None,
            "description": self.description,
            "document_type": self.document_type.value,
            "tags": self.tags,
            "source": self.source,
            "word_count": self.word_count,
            "heading_hierarchy": self.heading_hierarchy,
            "custom": self.custom,
        }


@dataclass
class ChunkMetadata:
    """Metadata for a single chunk."""
    source_document_id: str
    chunk_index: int
    total_chunks: int
    heading_context: List[str] = field(default_factory=list)
    document_type: str = "unknown"
    extracted_tags: List[str] = field(default_factory=list)
    original_heading: Optional[str] = None
    char_start: int = 0
    char_end: int = 0
    content_hash: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "source_document_id": self.source_document_id,
            "chunk_index": self.chunk_index,
            "total_chunks": self.total_chunks,
            "heading_context": self.heading_context,
            "document_type": self.document_type,
            "extracted_tags": self.extracted_tags,
            "original_heading": self.original_heading,
            "char_start": self.char_start,
            "char_end": self.char_end,
            "content_hash": self.content_hash,
        }


class DocumentMetadataExtractor:
    """
    Extract metadata from documents.
    
    Analyzes document content to extract:
    - Title (from first heading or first line)
    - Author (from metadata or heuristics)
    - Date (from metadata or content)
    - Document type (markdown, code, plain text)
    - Tags (from content analysis)
    - Heading hierarchy
    """
    
    # Common author patterns in comments
    AUTHOR_PATTERNS = [
        r'@author\s+(.+)',
        r'Author:\s+(.+)',
        r'Written by\s+(.+)',
    ]
    
    # Date patterns
    DATE_PATTERNS = [
        r'(\d{4}-\d{2}-\d{2})',  # ISO date
        r'(\d{2}/\d{2}/\d{4})',  # US date
        r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})',  # ISO datetime
    ]
    
    # Code block patterns
    CODE_BLOCK_PATTERN = r'```(\w+)?'
    CODE_INDENT_PATTERN = r'^\s{4,}'
    
    # Heading pattern
    HEADING_PATTERN = r'^(#{1,6})\s+(.+)$'
    
    def extract(self, content: str, source: Optional[str] = None, 
                existing_metadata: Optional[Dict] = None) -> DocumentMetadata:
        """
        Extract metadata from document content.
        
        Args:
            content: Document content
            source: Optional source identifier
            existing_metadata: Optional pre-existing metadata to merge
            
        Returns:
            DocumentMetadata object
        """
        metadata = DocumentMetadata(source=source)
        
        # Detect document type
        metadata.document_type = self._detect_document_type(content)
        
        # Extract title
        metadata.title = self._extract_title(content)
        
        # Extract author
        metadata.author = self._extract_author(content)
        
        # Extract date
        metadata.date = self._extract_date(content)
        
        # Extract description
        metadata.description = self._extract_description(content)
        
        # Count words
        metadata.word_count = self._count_words(content)
        
        # Extract heading hierarchy
        metadata.heading_hierarchy = self._extract_headings(content)
        
        # Generate tags from content
        metadata.tags = self._generate_tags(content, metadata.document_type)
        
        # Merge with existing metadata
        if existing_metadata:
            metadata.custom.update(existing_metadata)
        
        return metadata
    
    def _detect_document_type(self, content: str) -> DocumentType:
        """Detect the document type from content."""
        # Check for markdown headings
        if re.search(self.HEADING_PATTERN, content, re.MULTILINE):
            return DocumentType.MARKDOWN
        
        # Check for code blocks
        if re.search(self.CODE_BLOCK_PATTERN, content):
            return DocumentType.CODE
        
        # Check for code indentation
        lines = content.split('\n')
        code_lines = sum(1 for line in lines if re.match(self.CODE_INDENT_PATTERN, line))
        if code_lines > len(lines) * 0.3:  # 30% or more indented
            return DocumentType.CODE
        
        # Check for PDF-like structure (multiple newlines, columns indicators)
        if '\n\n\n' in content and len(content) > 1000:
            return DocumentType.PDF_LIKE
        
        return DocumentType.PLAIN_TEXT
    
    def _extract_title(self, content: str) -> Optional[str]:
        """Extract title from content."""
        lines = content.split('\n')
        
        # Try first heading
        for line in lines:
            match = re.match(self.HEADING_PATTERN, line.strip())
            if match:
                return match.group(2).strip()
        
        # Try first non-empty line as title
        for line in lines:
            stripped = line.strip()
            if stripped and len(stripped) > 3:
                # Skip comment lines
                if not stripped.startswith('//') and not stripped.startswith('#'):
                    return stripped[:100]  # Limit title length
        
        return None
    
    def _extract_author(self, content: str) -> Optional[str]:
        """Extract author from content."""
        # Check metadata/comment block at start
        comment_block = content[:500]
        
        for pattern in self.AUTHOR_PATTERNS:
            match = re.search(pattern, comment_block, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _extract_date(self, content: str) -> Optional[datetime]:
        """Extract date from content."""
        # Check first 500 chars for date
        header = content[:500]
        
        for pattern in self.DATE_PATTERNS:
            match = re.search(pattern, header)
            if match:
                try:
                    date_str = match.group(1)
                    # Try parsing ISO format
                    try:
                        return datetime.fromisoformat(date_str)
                    except ValueError:
                        pass
                except Exception:
                    continue
        
        return None
    
    def _extract_description(self, content: str) -> Optional[str]:
        """Extract description from content."""
        lines = content.split('\n')
        
        # Look for description after title (first heading)
        found_title = False
        description_parts = []
        
        for line in lines:
            stripped = line.strip()
            
            if not found_title:
                if re.match(self.HEADING_PATTERN, stripped):
                    found_title = True
                continue
            
            # Stop at next heading or after 3 lines
            if re.match(self.HEADING_PATTERN, stripped):
                break
            
            if stripped and not stripped.startswith('#'):
                description_parts.append(stripped)
                if len(description_parts) >= 3:
                    break
        
        if description_parts:
            return ' '.join(description_parts)[:500]
        
        return None
    
    def _count_words(self, content: str) -> int:
        """Count words in content."""
        # Simple word count
        words = re.findall(r'\b\w+\b', content)
        return len(words)
    
    def _extract_headings(self, content: str) -> List[str]:
        """Extract all headings in order."""
        headings = []
        
        for line in content.split('\n'):
            match = re.match(self.HEADING_PATTERN, line.strip())
            if match:
                level = len(match.group(1))
                text = match.group(2).strip()
                headings.append(f"{'#' * level} {text}")
        
        return headings
    
    def _generate_tags(self, content: str, doc_type: DocumentType) -> List[str]:
        """Generate tags from content analysis."""
        tags = []
        
        # Add document type as tag
        tags.append(doc_type.value)
        
        # Extract programming languages from code blocks
        code_langs = re.findall(r'```(\w+)', content)
        tags.extend([lang.lower() for lang in set(code_langs)])
        
        # Common tech keywords
        tech_keywords = [
            'python', 'javascript', 'typescript', 'java', 'rust', 'go',
            'api', 'database', 'sql', 'nosql', 'rest', 'graphql',
            'async', 'parallel', 'testing', 'deployment', 'docker',
        ]
        
        content_lower = content.lower()
        for keyword in tech_keywords:
            if keyword in content_lower:
                tags.append(keyword)
        
        return list(set(tags))[:10]  # Limit to 10 tags
    
    def create_chunk_metadata(self, document_id: str, chunk_index: int,
                              total_chunks: int, heading_context: List[str],
                              content: str, doc_type: DocumentType,
                              tags: List[str], original_heading: Optional[str],
                              char_start: int, char_end: int) -> ChunkMetadata:
        """
        Create metadata for a chunk.
        
        Args:
            document_id: Parent document ID
            chunk_index: Index of this chunk
            total_chunks: Total number of chunks
            heading_context: Parent headings
            chunk_content: Content of this chunk
            doc_type: Document type
            tags: Extracted tags
            original_heading: Heading this chunk is under
            char_start: Character start position
            char_end: Character end position
            
        Returns:
            ChunkMetadata object
        """
        content_hash = hashlib.md5(content.encode()).hexdigest()
        
        return ChunkMetadata(
            source_document_id=document_id,
            chunk_index=chunk_index,
            total_chunks=total_chunks,
            heading_context=heading_context,
            document_type=doc_type.value,
            extracted_tags=tags[:5],  # Limit chunk tags
            original_heading=original_heading,
            char_start=char_start,
            char_end=char_end,
            content_hash=content_hash,
        )
