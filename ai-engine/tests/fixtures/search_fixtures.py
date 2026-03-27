"""
Shared test fixtures for search integration tests.

Provides mock documents, queries, and embeddings for testing
hybrid search, re-ranking, and query expansion.
"""

import pytest
from typing import Dict, List
import sys
from pathlib import Path

# Add ai-engine to path
ai_engine_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ai_engine_root))

from schemas.multimodal_schema import (
    MultiModalDocument,
    ContentType,
)


@pytest.fixture
def mock_documents() -> Dict[str, MultiModalDocument]:
    """
    Create mock documents for testing.

    Returns dictionary of document_id -> MultiModalDocument
    """
    documents = {
        "doc1": MultiModalDocument(
            id="doc1",
            content="How to create a custom block in Minecraft Forge. Blocks are fundamental building units in Minecraft.",
            content_type=ContentType.TEXT,
            metadata={
                "title": "Creating Custom Blocks",
                "type": "tutorial",
                "tags": ["blocks", "forge", "tutorial"],
                "mod_loader": "forge",
                "minecraft_version": "1.20",
            },
        ),
        "doc2": MultiModalDocument(
            id="doc2",
            content="Creating custom items in Minecraft Fabric involves extending the Item class and registering with Registry.register().",
            content_type=ContentType.TEXT,
            metadata={
                "title": "Creating Custom Items",
                "type": "tutorial",
                "tags": ["items", "fabric", "registry"],
                "mod_loader": "fabric",
                "minecraft_version": "1.20",
            },
        ),
        "doc3": MultiModalDocument(
            id="doc3",
            content="Bedrock Edition uses JSON files for behavior packs and JavaScript for Script API. Blocks are defined in behavior_packs/blocks/",
            content_type=ContentType.TEXT,
            metadata={
                "title": "Bedrock Block System",
                "type": "reference",
                "tags": ["bedrock", "blocks", "json", "javascript"],
                "platform": "bedrock",
                "minecraft_version": "1.20",
            },
        ),
        "doc4": MultiModalDocument(
            id="doc4",
            content="Java Edition modding requires ForgeGradle for build automation. Gradle handles dependency management and obfuscation.",
            content_type=ContentType.TEXT,
            metadata={
                "title": "ForgeGradle Setup",
                "type": "tutorial",
                "tags": ["gradle", "forge", "build", "dependencies"],
                "mod_loader": "forge",
                "minecraft_version": "1.19",
            },
        ),
        "doc5": MultiModalDocument(
            id="doc5",
            content="Minecraft entities extend the Entity class. Custom entities require attributes, AI goals, and spawn rules.",
            content_type=ContentType.TEXT,
            metadata={
                "title": "Creating Custom Entities",
                "type": "tutorial",
                "tags": ["entities", "ai", "spawn", "attributes"],
                "mod_loader": "forge",
                "minecraft_version": "1.20",
            },
        ),
        "doc6": MultiModalDocument(
            id="doc6",
            content="Recipe system in Minecraft uses JSON files. Crafting recipes define ingredients, pattern, and result item.",
            content_type=ContentType.TEXT,
            metadata={
                "title": "Recipe System",
                "type": "reference",
                "tags": ["recipes", "crafting", "json"],
                "platform": "bedrock",
                "minecraft_version": "1.20",
            },
        ),
        "doc7": MultiModalDocument(
            id="doc7",
            content="NeoForge is the continuation of Forge after 1.20. It maintains API compatibility with Forge mods.",
            content_type=ContentType.TEXT,
            metadata={
                "title": "NeoForge Overview",
                "type": "reference",
                "tags": ["neoforge", "forge", "migration"],
                "mod_loader": "neoforge",
                "minecraft_version": "1.20",
            },
        ),
        "doc8": MultiModalDocument(
            id="doc8",
            content="Texture mapping in Bedrock uses resource packs. Textures are PNG files in textures/blocks/ directory.",
            content_type=ContentType.TEXT,
            metadata={
                "title": "Texture Mapping",
                "type": "tutorial",
                "tags": ["textures", "resources", "png", "bedrock"],
                "platform": "bedrock",
                "minecraft_version": "1.20",
            },
        ),
        "doc9": MultiModalDocument(
            id="doc9",
            content="Event handling in Forge uses the @SubscribeEvent annotation. Events fire on specific game actions.",
            content_type=ContentType.TEXT,
            metadata={
                "title": "Event System",
                "type": "tutorial",
                "tags": ["events", "annotations", "forge"],
                "mod_loader": "forge",
                "minecraft_version": "1.20",
            },
        ),
        "doc10": MultiModalDocument(
            id="doc10",
            content="Script API in Bedrock allows JavaScript code to run in-game. Use @minecraft/server module for server-side scripts.",
            content_type=ContentType.TEXT,
            metadata={
                "title": "Script API Introduction",
                "type": "tutorial",
                "tags": ["javascript", "scripting", "bedrock", "api"],
                "platform": "bedrock",
                "minecraft_version": "1.20",
            },
        ),
    }
    return documents


@pytest.fixture
def mock_embeddings() -> Dict[str, List[float]]:
    """
    Create mock embeddings for testing.

    Returns dictionary of document_id -> embedding vector (384-dim)
    """
    import random
    random.seed(42)  # Reproducible embeddings

    embeddings = {}
    for doc_id in [f"doc{i}" for i in range(1, 11)]:
        # Generate mock 384-dim embedding (all-MiniLM-L6-v2 dimension)
        embedding = [random.uniform(-1, 1) for _ in range(384)]
        # Normalize to unit length
        norm = sum(x**2 for x in embedding) ** 0.5
        embedding = [x / norm for x in embedding]
        embeddings[doc_id] = embedding

    return embeddings


@pytest.fixture
def test_queries() -> Dict[str, Dict[str, any]]:
    """
    Create test queries with expected results.

    Returns dictionary of query_name -> {query, expected_docs, expansion_terms}
    """
    return {
        "block_creation": {
            "query": "How to create a custom block",
            "expected_docs": ["doc1"],  # Should match doc1 (Creating Custom Blocks)
            "expansion_terms": ["blocks", "cube", "tile"],  # Domain-specific expansions
        },
        "item_fabric": {
            "query": "custom items in Fabric",
            "expected_docs": ["doc2"],  # Should match doc2 (Creating Custom Items)
            "expansion_terms": ["item", "objects"],
        },
        "bedrock_json": {
            "query": "Bedrock JSON behavior packs",
            "expected_docs": ["doc3"],  # Should match doc3 (Bedrock Block System)
            "expansion_terms": ["json", "behavior_pack"],
        },
        "entity_ai": {
            "query": "custom entity with AI goals",
            "expected_docs": ["doc5"],  # Should match doc5 (Creating Custom Entities)
            "expansion_terms": ["entities", "goals", "behaviors"],
        },
        "recipe_crafting": {
            "query": "crafting recipes",
            "expected_docs": ["doc6"],  # Should match doc6 (Recipe System)
            "expansion_terms": ["recipe", "craft", "smelting"],
        },
        "texture_resources": {
            "query": "texture mapping",
            "expected_docs": ["doc8"],  # Should match doc8 (Texture Mapping)
            "expansion_terms": ["textures", "resources", "images"],
        },
        "javascript_scripting": {
            "query": "JavaScript scripting",
            "expected_docs": ["doc10"],  # Should match doc10 (Script API Introduction)
            "expansion_terms": ["javascript", "scripting", "script"],
        },
    }


@pytest.fixture
def mock_query_embedding() -> List[float]:
    """
    Create mock query embedding (384-dim).
    """
    import random
    random.seed(123)
    embedding = [random.uniform(-1, 1) for _ in range(384)]
    # Normalize to unit length
    norm = sum(x**2 for x in embedding) ** 0.5
    embedding = [x / norm for x in embedding]
    return embedding
