"""
Forge documentation source adapter.

Fetches documentation from the official Forge documentation site.
"""

import asyncio
import logging
from typing import Dict, Any, List
import aiohttp


from .base import BaseSourceAdapter, RawDocument, DocumentType


logger = logging.getLogger(__name__)


class ForgeDocsAdapter(BaseSourceAdapter):
    """
    Adapter for fetching Minecraft Forge documentation.

    Base URL: https://docs.minecraftforge.net
    """

    BASE_URL = "https://docs.minecraftforge.net"
    DEFAULT_TIMEOUT = 30  # seconds

    async def fetch(self, config: Dict[str, Any]) -> List[RawDocument]:
        """
        Fetch Forge documentation.

        Args:
            config: Configuration dict
                - version: Forge version (default: "1.20.1")
                - sections: List of documentation sections to fetch
                - max_pages: Maximum number of pages to fetch (default: 100)

        Returns:
            List of RawDocument objects

        Raises:
            Exception: If fetch fails (logged, not crashed)
        """
        version = config.get("version", "1.20.1")
        sections = config.get("sections", ["getting-started", "blocks", "items"])
        max_pages = config.get("max_pages", 100)

        documents = []

        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.DEFAULT_TIMEOUT)
            ) as session:
                for section in sections:
                    try:
                        # Construct URL for section
                        url = f"{self.BASE_URL}/en/latest/{section}/"

                        logger.info(f"Fetching Forge docs from: {url}")

                        async with session.get(url) as response:
                            if response.status != 200:
                                logger.warning(f"Failed to fetch {url}: status {response.status}")
                                continue

                            # Determine document type
                            content_type = response.headers.get("Content-Type", "")
                            doc_type = (
                                DocumentType.HTML
                                if "text/html" in content_type
                                else DocumentType.MARKDOWN
                            )

                            # Get content
                            content = await response.text()

                            # Extract metadata
                            metadata = {
                                "mod_loader": "forge",
                                "version": version,
                                "section": section,
                                "source": "forge_docs",
                            }

                            # Extract title from URL or content
                            title = section.replace("-", " ").replace("/", " ").title()

                            doc = RawDocument(
                                content=content,
                                source_url=url,
                                doc_type=doc_type,
                                metadata=metadata,
                                title=title,
                            )

                            documents.append(doc)

                            if len(documents) >= max_pages:
                                logger.warning(f"Reached max_pages limit ({max_pages})")
                                break

                    except Exception as e:
                        logger.error(f"Error fetching section {section}: {e}")
                        continue

        except Exception as e:
            logger.error(f"Failed to fetch Forge documentation: {e}")

        return documents

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate Forge documentation configuration.

        Args:
            config: Configuration to validate

        Returns:
            True if valid, False otherwise
        """
        # Version is optional (uses default)
        # Sections should be a list if provided
        sections = config.get("sections")
        if sections is not None and not isinstance(sections, list):
            return False

        # Max pages should be positive if provided
        max_pages = config.get("max_pages")
        if max_pages is not None and (not isinstance(max_pages, int) or max_pages <= 0):
            return False

        return True
