"""
Pattern Mapping Indexer - K³Trans Implementation

Indexes pattern mappings and conversion knowledge into the vector database
for retrieval during translation.

This module implements issue #992: Wire RAG Pipeline into Conversion Loop.
"""

import json
import logging
from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    from knowledge.patterns.mappings import PatternMappingRegistry
    from utils.vector_db_client import VectorDBClient

logger = logging.getLogger(__name__)


class PatternMappingIndexer:
    """
    Indexer for pattern mappings and conversion knowledge.

    Converts pattern mappings to indexable documents and stores them
    in the vector database for semantic retrieval.
    """

    def __init__(self, vector_db_client: Optional["VectorDBClient"] = None):
        """
        Initialize the pattern mapping indexer.

        Args:
            vector_db_client: Vector DB client for indexing
        """
        self.vector_db_client = vector_db_client

    def set_vector_db_client(self, client: "VectorDBClient") -> None:
        """Set the vector DB client."""
        self.vector_db_client = client

    async def index_pattern_mappings(
        self,
        pattern_registry: "PatternMappingRegistry",
        force_reindex: bool = False,
    ) -> Dict[str, Any]:
        """
        Index all pattern mappings from a registry.

        Args:
            pattern_registry: Registry containing pattern mappings
            force_reindex: If True, reindex even existing documents

        Returns:
            Dictionary with indexing results
        """
        if not self.vector_db_client:
            logger.warning("No vector DB client configured, skipping indexing")
            return {"success": False, "indexed": 0, "errors": ["No vector DB client"]}

        results = {
            "success": True,
            "indexed": 0,
            "errors": [],
        }

        try:
            documents = pattern_registry.to_indexable_documents()
            logger.info(f"Indexing {len(documents)} pattern mapping documents")

            for doc in documents:
                try:
                    success = await self.vector_db_client.index_document(
                        document_content=doc["content"],
                        document_source=doc["source"],
                    )
                    if success:
                        results["indexed"] += 1
                    else:
                        results["errors"].append(f"Failed to index: {doc['source']}")

                except Exception as e:
                    logger.error(f"Error indexing document {doc['source']}: {e}")
                    results["errors"].append(str(e))

            logger.info(f"Indexed {results['indexed']}/{len(documents)} pattern mappings")

        except Exception as e:
            logger.error(f"Error in index_pattern_mappings: {e}")
            results["success"] = False
            results["errors"].append(str(e))

        return results

    async def index_knowledge_base(
        self,
        knowledge_dir: str = "ai-engine/knowledge",
    ) -> Dict[str, Any]:
        """
        Index all knowledge base files.

        Args:
            knowledge_dir: Directory containing knowledge files

        Returns:
            Dictionary with indexing results
        """
        from pathlib import Path

        if not self.vector_db_client:
            return {"success": False, "indexed": 0, "errors": ["No vector DB client"]}

        results = {
            "success": True,
            "indexed": 0,
            "files_processed": 0,
            "errors": [],
        }

        knowledge_path = Path(knowledge_dir)
        if not knowledge_path.exists():
            results["success"] = False
            results["errors"].append(f"Knowledge directory not found: {knowledge_dir}")
            return results

        try:
            for file_path in knowledge_path.rglob("*.py"):
                if file_path.name.startswith("_") or file_path.name == "schema.py":
                    continue

                try:
                    content = file_path.read_text()
                    if len(content) > 100:
                        source = f"knowledge:{file_path.relative_to(knowledge_path)}"
                        success = await self.vector_db_client.index_document(
                            document_content=content[:5000],
                            document_source=source,
                        )
                        results["files_processed"] += 1
                        if success:
                            results["indexed"] += 1

                except Exception as e:
                    logger.warning(f"Could not index {file_path}: {e}")
                    results["errors"].append(f"{file_path}: {str(e)}")

        except Exception as e:
            logger.error(f"Error indexing knowledge base: {e}")
            results["success"] = False
            results["errors"].append(str(e))

        return results

    async def index_conversion_example(
        self,
        source_code: str,
        target_code: str,
        feature_type: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Index a successful conversion example.

        Args:
            source_code: Source Java code
            target_code: Converted Bedrock code
            feature_type: Type of feature (block, item, entity, etc.)
            metadata: Additional metadata about the conversion

        Returns:
            True if indexing succeeded
        """
        if not self.vector_db_client:
            return False

        try:
            content = json.dumps(
                {
                    "type": "conversion_example",
                    "feature_type": feature_type,
                    "source": source_code[:2000],
                    "target": target_code[:2000],
                    "metadata": metadata or {},
                }
            )

            source = f"conversion_example:{feature_type}"
            return await self.vector_db_client.index_document(content, source)

        except Exception as e:
            logger.error(f"Error indexing conversion example: {e}")
            return False


def create_pattern_indexer(
    vector_db_url: Optional[str] = None,
) -> PatternMappingIndexer:
    """
    Create a pattern indexer with configured vector DB client.

    Args:
        vector_db_url: Optional vector DB URL

    Returns:
        Configured PatternMappingIndexer instance
    """
    indexer = PatternMappingIndexer()

    try:
        from utils.vector_db_client import VectorDBClient

        if vector_db_url:
            client = VectorDBClient(base_url=vector_db_url)
        else:
            client = VectorDBClient()

        indexer.set_vector_db_client(client)
        logger.info("Pattern indexer initialized with vector DB client")

    except ImportError as e:
        logger.warning(f"Could not create vector DB client: {e}")
    except Exception as e:
        logger.warning(f"Could not initialize vector DB client: {e}")

    return indexer


async def index_all_knowledge(
    pattern_registry=None,
    vector_db_url: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Index all knowledge sources: patterns, bedrock docs, and examples.

    Args:
        pattern_registry: Optional pattern registry to index
        vector_db_url: Optional vector DB URL

    Returns:
        Combined indexing results
    """
    indexer = create_pattern_indexer(vector_db_url)

    results = {
        "pattern_mappings": {"indexed": 0},
        "knowledge_base": {"indexed": 0},
    }

    if pattern_registry:
        pattern_results = await indexer.index_pattern_mappings(pattern_registry)
        results["pattern_mappings"] = pattern_results

    kb_results = await indexer.index_knowledge_base()
    results["knowledge_base"] = kb_results

    return results
