"""
Markdown document processor.

Processes markdown documents to extract content and metadata.
"""

import re
import logging
from typing import Dict, Any
from markdown import Markdown
from ..sources.base import RawDocument


logger = logging.getLogger(__name__)


class MarkdownProcessor:
    """
    Process markdown documents.

    Extracts:
    - HTML content (converted from markdown)
    - Title (from first heading)
    - Table of contents
    - Code blocks with language info
    - Word count
    """

    def __init__(self):
        """Initialize markdown processor with extensions."""
        self.md = Markdown(
            extensions=[
                "fenced_code",
                "tables",
                "toc",
                "meta",
                "nl2br",
                "sane_lists",
            ]
        )

    def process(self, doc: RawDocument) -> Dict[str, Any]:
        """
        Process a markdown document.

        Args:
            doc: RawDocument with markdown content

        Returns:
            Dict with:
                - content: HTML content converted from markdown
                - html_content: Raw HTML string
                - metadata: Extracted metadata (title, toc, code_blocks, word_count)
        """
        try:
            # Reset markdown instance
            self.md.reset()

            # Convert markdown to HTML
            html_content = self.md.convert(doc.content)

            # Extract metadata from markdown front matter
            md_meta = getattr(self.md, "Meta", {})

            # Extract title
            title = self._extract_title(doc.content, doc.title)

            # Extract table of contents
            toc = getattr(self.md, "toc", "")

            # Extract code blocks
            code_blocks = self._extract_code_blocks(doc.content)

            # Count words
            word_count = self._count_words(doc.content)

            # Build metadata dict
            metadata = {
                "title": title,
                "toc": toc,
                "code_blocks": code_blocks,
                "word_count": word_count,
                "has_code": len(code_blocks) > 0,
                "code_languages": list(set(cb["language"] for cb in code_blocks if cb["language"])),
            }

            # Merge with document's existing metadata
            metadata.update(doc.metadata)

            return {
                "content": html_content,
                "html_content": html_content,
                "metadata": metadata,
            }

        except Exception as e:
            logger.error(f"Error processing markdown document: {e}")
            # Return original content on error
            return {
                "content": doc.content,
                "html_content": doc.content,
                "metadata": doc.metadata,
            }

    def _extract_title(self, content: str, default: str = None) -> str:
        """
        Extract title from markdown content.

        Args:
            content: Markdown content
            default: Default title if no heading found

        Returns:
            Extracted title or default
        """
        # Look for first heading
        lines = content.split("\n")
        for line in lines:
            stripped = line.strip()
            match = re.match(r"^#{1,6}\s+(.+)$", stripped)
            if match:
                return match.group(1).strip()

        # Use default or first line
        return default or (lines[0][:100] if lines else "Untitled")

    def _extract_code_blocks(self, content: str) -> list:
        """
        Extract code blocks with language information.

        Args:
            content: Markdown content

        Returns:
            List of dicts with language and line_count
        """
        code_blocks = []

        # Match fenced code blocks: ```language ... ```
        pattern = r"```(\w+)?\n([\s\S]*?)```"
        matches = re.finditer(pattern, content)

        for match in matches:
            language = match.group(1) or "unknown"
            code = match.group(2)
            line_count = len(code.split("\n"))

            code_blocks.append(
                {
                    "language": language,
                    "line_count": line_count,
                    "preview": code[:200],  # First 200 chars
                }
            )

        return code_blocks

    def _count_words(self, content: str) -> int:
        """
        Count words in markdown content.

        Args:
            content: Markdown content

        Returns:
            Word count
        """
        # Remove code blocks first
        without_code = re.sub(r"```[\s\S]*?```", "", content)
        without_code = re.sub(r"`[^`]+`", "", without_code)

        # Count words (alphanumeric sequences)
        words = re.findall(r"\b\w+\b", without_code)
        return len(words)
