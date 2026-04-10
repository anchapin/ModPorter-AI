"""
HTML document processor.

Processes HTML documents to extract clean content and metadata.
"""

import re
import logging
from typing import Dict, Any, List
from bs4 import BeautifulSoup
from ..sources.base import RawDocument


logger = logging.getLogger(__name__)


class HTMLProcessor:
    """
    Process HTML documents.

    Extracts:
    - Main content (removes nav, footer, sidebar)
    - Title (from <title> or <h1>)
    - Code blocks (<pre><code>)
    - Links and headings
    - Clean text content
    """

    def __init__(self):
        """Initialize HTML processor."""
        # Tags to remove (navigation, sidebars, footers)
        self.remove_tags = [
            "nav",
            "navigation",
            "header",
            "footer",
            "aside",
            "sidebar",
            "script",
            "style",
            "noscript",
            "iframe",
        ]

        # Classes/IDs to remove
        self.remove_classes = [
            "navigation",
            "navbar",
            "sidebar",
            "footer",
            "menu",
            "breadcrumb",
        ]

    def process(self, doc: RawDocument) -> Dict[str, Any]:
        """
        Process an HTML document.

        Args:
            doc: RawDocument with HTML content

        Returns:
            Dict with:
                - content: Clean text content
                - html_content: Processed HTML
                - metadata: Extracted metadata (title, code_blocks, links, headings)
        """
        try:
            # Parse HTML
            soup = BeautifulSoup(doc.content, "html.parser")

            # Remove unwanted elements
            self._remove_unwanted(soup)

            # Extract title
            title = self._extract_title(soup, doc.title)

            # Extract main content
            main_content = self._extract_main_content(soup)

            # Extract code blocks
            code_blocks = self._extract_code_blocks(soup)

            # Extract links
            links = self._extract_links(soup)

            # Extract headings
            headings = self._extract_headings(soup)

            # Get clean text
            clean_text = main_content.get_text(separator="\n", strip=True)

            # Count words
            word_count = len(clean_text.split())

            # Build metadata
            metadata = {
                "title": title,
                "code_blocks": code_blocks,
                "links_count": len(links),
                "headings": headings,
                "word_count": word_count,
                "has_code": len(code_blocks) > 0,
            }

            # Merge with document's existing metadata
            metadata.update(doc.metadata)

            return {
                "content": clean_text,
                "html_content": str(main_content),
                "metadata": metadata,
            }

        except Exception as e:
            logger.error(f"Error processing HTML document: {e}")
            # Return original content on error
            return {
                "content": doc.content,
                "html_content": doc.content,
                "metadata": doc.metadata,
            }

    def _remove_unwanted(self, soup: BeautifulSoup):
        """Remove unwanted elements from HTML."""
        # Remove by tag name
        for tag in self.remove_tags:
            for element in soup.find_all(tag):
                element.decompose()

        # Remove by class/ID
        for class_name in self.remove_classes:
            for element in soup.find_all(class_=class_name):
                element.decompose()
            for element in soup.find_all(id=class_name):
                element.decompose()

    def _extract_main_content(self, soup: BeautifulSoup) -> BeautifulSoup:
        """
        Extract main content from HTML.

        Looks for <main>, <article>, or falls back to <body>.
        """
        # Try to find main content
        main = soup.find("main")
        if main:
            return main

        article = soup.find("article")
        if article:
            return article

        # Fall back to body but remove scripts/styles
        body = soup.find("body")
        if body:
            return body

        return soup

    def _extract_title(self, soup: BeautifulSoup, default: str = None) -> str:
        """
        Extract title from HTML.

        Args:
            soup: BeautifulSoup object
            default: Default title

        Returns:
            Extracted title
        """
        # Try <title> tag
        title_tag = soup.find("title")
        if title_tag and title_tag.string:
            return title_tag.string.strip()

        # Try <h1> tag
        h1_tag = soup.find("h1")
        if h1_tag and h1_tag.string:
            return h1_tag.string.strip()

        # Use default
        return default or "Untitled"

    def _extract_code_blocks(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """
        Extract code blocks from HTML.

        Returns:
            List of dicts with language and preview
        """
        code_blocks = []

        # Find all <pre><code> blocks
        for pre in soup.find_all("pre"):
            code = pre.find("code")
            if not code:
                continue

            # Get code text
            code_text = code.get_text()

            # Try to get language from class
            language = "unknown"
            if code.get("class"):
                classes = code["class"]
                for cls in classes:
                    if "language-" in cls:
                        language = cls.replace("language-", "")
                        break

            code_blocks.append(
                {
                    "language": language,
                    "line_count": len(code_text.split("\n")),
                    "preview": code_text[:200],
                }
            )

        return code_blocks

    def _extract_links(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """
        Extract links from HTML.

        Returns:
            List of dicts with href and text
        """
        links = []

        for a in soup.find_all("a", href=True):
            href = a["href"]
            text = a.get_text().strip()[:100]  # Limit text length
            if href and text:
                links.append(
                    {
                        "href": href,
                        "text": text,
                    }
                )

        return links

    def _extract_headings(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """
        Extract headings from HTML.

        Returns:
            List of dicts with level and text
        """
        headings = []

        for level in range(1, 7):
            for heading in soup.find_all(f"h{level}"):
                text = heading.get_text().strip()
                if text:
                    headings.append(
                        {
                            "level": level,
                            "text": text,
                        }
                    )

        return headings
