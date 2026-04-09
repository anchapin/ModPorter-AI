"""
Bedrock API documentation source adapter.

Fetches Bedrock Script API reference documentation from Microsoft Learn.
"""

import asyncio
import logging
from typing import Dict, Any, List
import aiohttp


from .base import BaseSourceAdapter, RawDocument, DocumentType


logger = logging.getLogger(__name__)


class BedrockDocsAdapter(BaseSourceAdapter):
    """
    Adapter for fetching Minecraft Bedrock Script API documentation.

    Base URL: https://learn.microsoft.com/en-us/minecraft/creator/
    """

    BASE_URL = "https://learn.microsoft.com/en-us/minecraft/creator"
    API_REFERENCE_URL = f"{BASE_URL}/script/scriptapi/"
    DEFAULT_TIMEOUT = 30  # seconds

    async def fetch(self, config: Dict[str, Any]) -> List[RawDocument]:
        """
        Fetch Bedrock Script API documentation.

        Args:
            config: Configuration dict
                - namespaces: List of API namespaces to fetch (default: ["minecraft"])
                - game_version: Game version (default: "1.21.0")
                - max_pages: Maximum number of pages to fetch (default: 100)

        Returns:
            List of RawDocument objects

        Raises:
            Exception: If fetch fails (logged, not crashed)
        """
        namespaces = config.get("namespaces", ["minecraft", "mojang-minecraft", "mojang-gametest"])
        game_version = config.get("game_version", "1.21.0")
        max_pages = config.get("max_pages", 100)

        documents = []

        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.DEFAULT_TIMEOUT)
            ) as session:
                for namespace in namespaces:
                    try:
                        # Construct URL for namespace
                        url = f"{self.API_REFERENCE_URL}{namespace}/"

                        logger.info(f"Fetching Bedrock API docs from: {url}")

                        async with session.get(url) as response:
                            if response.status != 200:
                                logger.warning(f"Failed to fetch {url}: status {response.status}")
                                continue

                            # Bedrock docs are HTML
                            doc_type = DocumentType.HTML

                            # Get content
                            content = await response.text()

                            # Extract metadata
                            metadata = {
                                "api_type": "script_api",
                                "namespace": namespace,
                                "game_version": game_version,
                                "source": "bedrock_docs",
                            }

                            # Extract title from namespace
                            title = namespace.replace("-", " ").title()

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
                        logger.error(f"Error fetching namespace {namespace}: {e}")
                        continue

        except Exception as e:
            logger.error(f"Failed to fetch Bedrock documentation: {e}")

        return documents

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate Bedrock documentation configuration.

        Args:
            config: Configuration to validate

        Returns:
            True if valid, False otherwise
        """
        # Namespaces should be a list if provided
        namespaces = config.get("namespaces")
        if namespaces is not None and not isinstance(namespaces, list):
            return False

        # Game version should be a string if provided
        game_version = config.get("game_version")
        if game_version is not None and not isinstance(game_version, str):
            return False

        # Max pages should be positive if provided
        max_pages = config.get("max_pages")
        if max_pages is not None and (not isinstance(max_pages, int) or max_pages <= 0):
            return False

        return True
