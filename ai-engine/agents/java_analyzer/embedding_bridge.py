"""
Embedding generation bridge for mod analysis results
"""

import json

from utils.embedding_generator import LocalEmbeddingGenerator
from utils.logging_config import get_agent_logger

logger = get_agent_logger("java_analyzer.embedding_bridge")


class EmbeddingBridge:
    """Generates embeddings for mod analysis results to enable RAG retrieval"""

    def __init__(self, embedding_generator: LocalEmbeddingGenerator):
        self.embedding_generator = embedding_generator

    def generate_embeddings(self, result: dict) -> None:
        """Generate embeddings for the mod content to enable RAG retrieval."""
        try:
            if not self.embedding_generator.model:
                logger.warning("Embedding model not available, skipping embedding generation")
                result["embeddings_data"] = []
                return

            embedding_texts = []

            mod_info = result.get("mod_info", {})
            if mod_info.get("description"):
                embedding_texts.append(f"Mod Description: {mod_info['description']}")

            features = result.get("features", {})
            for feature_name, feature_data in features.items():
                if isinstance(feature_data, dict) and feature_data.get("description"):
                    embedding_texts.append(f"Feature {feature_name}: {feature_data['description']}")

            if result.get("structure"):
                structure_info = f"Mod Structure: {json.dumps(result['structure'])}"
                embedding_texts.append(structure_info)

            if embedding_texts:
                result["embeddings_data"] = [
                    {
                        "text": text,
                        "type": "mod_analysis",
                        "mod_name": mod_info.get("name", "unknown"),
                    }
                    for text in embedding_texts
                ]

        except Exception as e:
            logger.warning(f"Failed to generate embeddings: {e}")
            result["embeddings_data"] = []
