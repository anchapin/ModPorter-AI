"""
Main ingestion pipeline for knowledge base documentation.

Orchestrates fetching, processing, chunking, and indexing of documentation
from external sources (Forge, Fabric, Bedrock).
"""

import hashlib
import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from .sources.base import BaseSourceAdapter, RawDocument, DocumentType
from .processors.markdown import MarkdownProcessor
from .processors.html import HTMLProcessor
from .validators.quality import QualityValidator, ValidationResult

# Lazy import from ai-engine using importlib (doesn't pollute sys.path)
# This avoids the global sys.path.insert issue that causes import pollution
import importlib.util


def _get_ai_engine_module(module_path: str):
    """
    Lazily import a module from ai-engine without modifying sys.path.
    Uses importlib to import directly from the file path.
    """
    import sys
    from pathlib import Path

    ai_engine_path = Path(__file__).resolve().parent.parent.parent.parent / "ai-engine"
    module_file = ai_engine_path / module_path

    if not module_file.exists():
        raise ImportError(f"ai-engine module not found: {module_file}")

    spec = importlib.util.spec_from_file_location(module_path.replace("/", ".").replace(".py", ""), module_file)
    if spec and spec.loader:
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_path.replace("/", ".").replace(".py", "")] = module
        spec.loader.exec_module(module)
        return module
    raise ImportError(f"Failed to load ai-engine module: {module_path}")


# Import ai-engine modules lazily
_chunking_strategies = None
_metadata_extractor = None


def _get_chunking_strategies():
    global _chunking_strategies
    if _chunking_strategies is None:
        _chunking_strategies = _get_ai_engine_module("indexing/chunking_strategies.py")
    return _chunking_strategies


def _get_metadata_extractor():
    global _metadata_extractor
    if _metadata_extractor is None:
        _metadata_extractor = _get_ai_engine_module("indexing/metadata_extractor.py")
    return _metadata_extractor


# Now get the classes
ChunkingStrategyFactory = _get_chunking_strategies().ChunkingStrategyFactory
DocumentMetadataExtractor = _get_metadata_extractor().DocumentMetadataExtractor

# Import CRUD operations
from db import crud


logger = logging.getLogger(__name__)


class IngestionPipeline:
    """
    Main pipeline for ingesting documentation into the knowledge base.

    Flow:
    1. Fetch documents from source (Forge, Fabric, Bedrock)
    2. Process documents (markdown/HTML processing)
    3. Validate quality
    4. Chunk using strategy from Phase 15-01
    5. Extract metadata
    6. Generate embeddings
    7. Store in database with deduplication check
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize ingestion pipeline.

        Args:
            db: Async database session
        """
        self.db = db
        self.sources: Dict[str, BaseSourceAdapter] = {}
        self.processors: Dict[DocumentType, Any] = {}
        self.validator = QualityValidator()
        self.chunking_factory = ChunkingStrategyFactory()
        self.metadata_extractor = DocumentMetadataExtractor()

        # Load sources and processors
        self._load_sources()
        self._load_processors()

    def _load_sources(self):
        """Load available source adapters."""
        # Lazy load to avoid circular imports
        from .sources.forge_docs import ForgeDocsAdapter
        from .sources.fabric_docs import FabricDocsAdapter
        from .sources.bedrock_docs import BedrockDocsAdapter

        self.sources = {
            "forge_docs": ForgeDocsAdapter(),
            "fabric_docs": FabricDocsAdapter(),
            "bedrock_docs": BedrockDocsAdapter(),
        }

    def _load_processors(self):
        """Load document processors."""
        self.processors = {
            DocumentType.MARKDOWN: MarkdownProcessor(),
            DocumentType.HTML: HTMLProcessor(),
        }

    async def ingest_source(
        self, source_name: str, config: Dict[str, Any], chunking_strategy: str = "semantic"
    ) -> Dict[str, Any]:
        """
        Ingest documentation from a source.

        Args:
            source_name: Name of source ("forge_docs", "fabric_docs", "bedrock_docs")
            config: Source-specific configuration
            chunking_strategy: Chunking strategy to use ("semantic", "fixed", "recursive")

        Returns:
            Dict with results:
                - source: Source name
                - documents_processed: Number of documents processed
                - chunks_indexed: Number of chunks indexed
                - status: "success" or "error"
                - errors: List of errors (if any)
        """
        result = {
            "source": source_name,
            "documents_processed": 0,
            "chunks_indexed": 0,
            "status": "success",
            "errors": [],
        }

        try:
            # Validate source exists
            if source_name not in self.sources:
                raise ValueError(f"Unknown source: {source_name}")

            source = self.sources[source_name]

            # Validate configuration
            if not source.validate_config(config):
                raise ValueError(f"Invalid configuration for source: {source_name}")

            # Fetch documents
            logger.info(f"Fetching documents from {source_name}")
            raw_docs = await source.fetch(config)
            logger.info(f"Fetched {len(raw_docs)} documents from {source_name}")

            # Process each document
            all_chunks = []
            for doc in raw_docs:
                try:
                    # Process document (extract metadata, clean content)
                    processed = await self._process_document(doc)
                    if not processed:
                        continue

                    # Validate quality
                    validation = self.validator.validate(
                        processed["content"], processed["metadata"]
                    )
                    if not validation.is_valid:
                        logger.warning(f"Document failed validation: {validation.errors}")
                        result["errors"].extend(
                            [f"{doc.source_url}: {e}" for e in validation.errors]
                        )
                        continue

                    # Check for duplicates
                    content_hash = hashlib.md5(processed["content"].encode()).hexdigest()
                    existing = await crud.get_document_embedding_by_hash(self.db, content_hash)
                    if existing:
                        logger.info(f"Skipping duplicate document: {doc.source_url}")
                        continue

                    # Chunk document
                    chunks = self._chunk_document(
                        processed["content"], chunking_strategy, doc.title
                    )
                    logger.info(f"Created {len(chunks)} chunks for {doc.source_url}")

                    # Prepare chunks for database
                    for chunk in chunks:
                        # Extract metadata for chunk
                        chunk_metadata = self.metadata_extractor.create_chunk_metadata(
                            document_id="",  # Will be set by CRUD
                            chunk_index=chunk.index,
                            total_chunks=chunk.total_chunks,
                            heading_context=chunk.heading_context,
                            content=chunk.content,
                            doc_type=processed.get("doc_type", DocumentType.MARKDOWN),
                            tags=processed["metadata"].get("tags", []),
                            original_heading=chunk.original_heading,
                            char_start=chunk.char_start,
                            char_end=chunk.char_end,
                        )

                        # Generate embedding (using Phase 15-01 embedding API)
                        # For now, use a placeholder - will be generated by backend API
                        embedding = await self._generate_embedding(chunk.content)

                        all_chunks.append(
                            {
                                "content": chunk.content,
                                "embedding": embedding,
                                "content_hash": chunk.content_hash,
                                "metadata": chunk_metadata.to_dict(),
                            }
                        )

                    result["documents_processed"] += 1

                except Exception as e:
                    logger.error(f"Error processing document {doc.source_url}: {e}")
                    result["errors"].append(f"{doc.source_url}: {str(e)}")

            # Create document with chunks in database
            if all_chunks:
                document_source = f"{source_name}_{config.get('version', 'latest')}"
                parent_doc, created_chunks = await crud.create_document_with_chunks(
                    self.db,
                    chunks=all_chunks,
                    document_source=document_source,
                    title=config.get("title", source_name),
                )
                result["chunks_indexed"] = len(created_chunks)
                logger.info(f"Created {len(created_chunks)} chunks in database")

        except Exception as e:
            logger.error(f"Ingestion failed for {source_name}: {e}")
            result["status"] = "error"
            result["errors"].append(str(e))

        return result

    async def _process_document(self, doc: RawDocument) -> Optional[Dict[str, Any]]:
        """
        Process a raw document.

        Args:
            doc: RawDocument to process

        Returns:
            Processed document dict with content and metadata, or None if processing fails
        """
        # Get processor for document type
        processor = self.processors.get(doc.doc_type)
        if not processor:
            logger.warning(f"No processor for document type: {doc.doc_type}")
            return None

        # Process document
        processed = processor.process(doc)

        # Merge with existing metadata
        metadata = {**doc.metadata, **processed.get("metadata", {})}

        return {
            "content": processed["content"],
            "metadata": metadata,
            "doc_type": doc.doc_type,
        }

    def _chunk_document(self, content: str, strategy: str, title: Optional[str] = None):
        """
        Chunk document using specified strategy.

        Args:
            content: Document content
            strategy: Chunking strategy name
            title: Optional document title

        Returns:
            List of Chunk objects
        """
        chunker = self.chunking_factory.create(strategy)
        return chunker.chunk(content)

    async def _generate_embedding(self, content: str) -> List[float]:
        """
        Generate embedding for content.

        Args:
            content: Text content to embed

        Returns:
            Embedding vector (list of floats)

        Note:
            This is a placeholder. In production, this will call the backend
            embedding API or use a local model.
        """
        # NOTE: Embedding API integration not yet implemented.
        # Placeholder: return zero vector
        return [0.0] * 1536  # OpenAI embedding dimension
