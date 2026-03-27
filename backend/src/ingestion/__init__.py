"""
Documentation ingestion pipeline for knowledge base expansion.

This module provides functionality to ingest documentation from external sources
(Forge, Fabric, Bedrock) into the RAG knowledge base.
"""

from .pipeline import IngestionPipeline

__all__ = ["IngestionPipeline"]
