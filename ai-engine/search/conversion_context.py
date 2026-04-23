"""
Conversion Context Aggregator - K³Trans Implementation

Bridges the RAG pipeline with the conversion process to provide
context-augmented translation using triple knowledge retrieval:
1. Target-language code samples (Bedrock examples)
2. Dependency usage examples (Bedrock API usage)
3. Prior successful translations (historical conversions)

This module implements the K³Trans approach from issue #992.
"""

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from knowledge.patterns.mappings import PatternMappingRegistry
    from search.rag_pipeline import RAGPipeline

logger = logging.getLogger(__name__)


@dataclass
class ConversionContext:
    """Context retrieved for a conversion task."""

    query: str
    pattern_mappings: List["PatternMapping"] = field(default_factory=list)
    bedrock_examples: List[Dict[str, Any]] = field(default_factory=list)
    prior_translations: List[Dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "pattern_mappings": [
                m.to_dict() if hasattr(m, "to_dict") else str(m) for m in self.pattern_mappings
            ],
            "bedrock_examples": self.bedrock_examples,
            "prior_translations": self.prior_translations,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }

    def format_for_llm(self) -> str:
        """Format context as a string for LLM consumption."""
        lines = ["=== CONVERSION CONTEXT ==="]

        if self.pattern_mappings:
            lines.append("\n## Pattern Mappings:")
            for mapping in self.pattern_mappings:
                if hasattr(mapping, "to_dict"):
                    lines.append(
                        f"- {mapping.java_pattern_id} → {mapping.bedrock_pattern_id} "
                        f"(confidence: {mapping.confidence})"
                    )
                    if mapping.notes:
                        lines.append(f"  Notes: {mapping.notes}")

        if self.bedrock_examples:
            lines.append("\n## Bedrock Code Examples:")
            for i, example in enumerate(self.bedrock_examples[:3], 1):
                lines.append(f"\nExample {i}:")
                if "code" in example:
                    lines.append(f"```javascript\n{example['code']}\n```")
                if "description" in example:
                    lines.append(f"Description: {example['description']}")

        if self.prior_translations:
            lines.append("\n## Prior Successful Translations:")
            for i, translation in enumerate(self.prior_translations[:2], 1):
                lines.append(f"\nTranslation {i}:")
                if "source" in translation:
                    lines.append(f"Source: {translation['source'][:100]}...")
                if "target" in translation:
                    lines.append(f"Target: {translation['target'][:100]}...")

        lines.append("\n=======================")
        return "\n".join(lines)


class ConversionContextAggregator:
    """
    Aggregates context from multiple knowledge sources for conversion augmentation.

    The K³Trans approach retrieves:
    1. Pattern mappings with confidence scores
    2. Bedrock code samples and API examples
    3. Prior successful translations

    This context is then fed to the LLM during translation for improved accuracy.
    """

    def __init__(
        self,
        rag_pipeline: Optional["RAGPipeline"] = None,
        pattern_registry: Optional["PatternMappingRegistry"] = None,
    ):
        """
        Initialize the context aggregator.

        Args:
            rag_pipeline: RAG pipeline for semantic search
            pattern_registry: Registry of Java→Bedrock pattern mappings
        """
        self.rag_pipeline = rag_pipeline
        self.pattern_registry = pattern_registry
        self._search_engine = None

    def set_rag_pipeline(self, rag_pipeline: "RAGPipeline"):
        """Set the RAG pipeline for semantic search."""
        self.rag_pipeline = rag_pipeline

    def set_pattern_registry(self, pattern_registry: "PatternMappingRegistry"):
        """Set the pattern registry for mapping lookups."""
        self.pattern_registry = pattern_registry

    def set_search_engine(self, search_engine):
        """Set the search engine used by the RAG pipeline."""
        self._search_engine = search_engine
        if self.rag_pipeline:
            self.rag_pipeline.set_search_engine(search_engine)

    async def get_conversion_context(
        self,
        java_feature: str,
        feature_type: str,
        top_k: int = 5,
    ) -> ConversionContext:
        """
        Get conversion context for a Java feature.

        Args:
            java_feature: Description of the Java feature to convert
            feature_type: Type of feature (block, item, entity, etc.)
            top_k: Number of context items to retrieve

        Returns:
            ConversionContext with aggregated knowledge
        """
        context = ConversionContext(query=java_feature)

        query_text = self._build_query(java_feature, feature_type)

        pattern_mappings = await self._get_pattern_mappings(query_text, feature_type)
        context.pattern_mappings = pattern_mappings

        bedrock_examples = await self._get_bedrock_examples(query_text, top_k)
        context.bedrock_examples = bedrock_examples

        prior_translations = await self._get_prior_translations(query_text, top_k)
        context.prior_translations = prior_translations

        context.confidence = self._calculate_confidence(
            pattern_mappings, bedrock_examples, prior_translations
        )

        logger.info(
            f"Retrieved context for '{java_feature}' (type={feature_type}): "
            f"{len(pattern_mappings)} patterns, {len(bedrock_examples)} examples, "
            f"{len(prior_translations)} prior translations, confidence={context.confidence:.2f}"
        )

        return context

    def _build_query(self, java_feature: str, feature_type: str) -> str:
        """Build a search query from feature information."""
        parts = [java_feature, f"Java {feature_type}", "to Bedrock conversion", "Minecraft"]
        return " ".join(parts)

    async def _get_pattern_mappings(self, query: str, feature_type: str) -> List["PatternMapping"]:
        """Get relevant pattern mappings from registry."""
        if not self.pattern_registry:
            return []

        try:
            mappings = self.pattern_registry.get_all_mappings()

            feature_type_patterns = {
                "block": [
                    "java_simple_block",
                    "java_block_properties",
                    "java_rotatable_block",
                    "java_tile_entity",
                ],
                "item": [
                    "java_simple_item",
                    "java_item_properties",
                    "java_food_item",
                    "java_ranged_weapon",
                ],
                "entity": ["java_simple_entity", "java_entity_attributes"],
                "recipe": ["java_shaped_recipe", "java_shapeless_recipe", "java_smelting_recipe"],
                "event": ["java_player_interact", "java_block_break", "java_entity_join"],
                "capability": ["java_item_handler", "java_fluid_handler"],
            }

            relevant_patterns = feature_type_patterns.get(feature_type.lower(), [])

            if relevant_patterns:
                mappings = [m for m in mappings if m.java_pattern_id in relevant_patterns]

            mappings.sort(key=lambda m: m.confidence, reverse=True)
            return mappings[:5]

        except Exception as e:
            logger.error(f"Error getting pattern mappings: {e}")
            return []

    async def _get_bedrock_examples(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """Get Bedrock code examples from RAG pipeline."""
        if not self.rag_pipeline:
            return []

        try:
            results = self.rag_pipeline.search(query, top_k=top_k)

            examples = []
            for result in results.results[:top_k]:
                if hasattr(result, "document") and hasattr(result.document, "content"):
                    examples.append(
                        {
                            "code": result.document.content[:500],
                            "source": getattr(result.document, "source", "unknown"),
                            "score": getattr(result, "final_score", 0.0),
                        }
                    )

            return examples

        except Exception as e:
            logger.error(f"Error getting Bedrock examples: {e}")
            return []

    async def _get_prior_translations(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """Get prior successful translations from RAG pipeline."""
        if not self.rag_pipeline:
            return []

        try:
            translation_query = f"{query} successful translation example"
            results = self.rag_pipeline.search(translation_query, top_k=top_k)

            translations = []
            for result in results.results[:top_k]:
                if hasattr(result, "document"):
                    content = getattr(result.document, "content", "")
                    if content and len(content) > 50:
                        translations.append(
                            {
                                "source": content[:200],
                                "target": getattr(result.document, "metadata", {}).get(
                                    "target", ""
                                ),
                                "score": getattr(result, "final_score", 0.0),
                            }
                        )

            return translations

        except Exception as e:
            logger.error(f"Error getting prior translations: {e}")
            return []

    def _calculate_confidence(
        self,
        pattern_mappings: List,
        bedrock_examples: List[Dict],
        prior_translations: List[Dict],
    ) -> float:
        """Calculate overall confidence based on available context."""
        confidence = 0.0

        if pattern_mappings:
            avg_confidence = sum(m.confidence for m in pattern_mappings) / len(pattern_mappings)
            confidence += avg_confidence * 0.4

        if bedrock_examples:
            avg_score = sum(e.get("score", 0.5) for e in bedrock_examples) / len(bedrock_examples)
            confidence += avg_score * 0.3

        if prior_translations:
            avg_score = sum(t.get("score", 0.5) for t in prior_translations) / len(
                prior_translations
            )
            confidence += avg_score * 0.3

        return min(confidence, 1.0)

    def format_context_prompt(self, context: ConversionContext) -> str:
        """
        Format conversion context as a prompt addition for the LLM.

        Args:
            context: The conversion context to format

        Returns:
            Formatted string to add to LLM prompt
        """
        if context.confidence < 0.1:
            return ""

        parts = []

        if context.pattern_mappings:
            parts.append("\n## Relevant Java→Bedrock Pattern Mappings:\n")
            for mapping in context.pattern_mappings:
                if hasattr(mapping, "java_pattern_id"):
                    parts.append(
                        f"- **{mapping.java_pattern_id}** → {mapping.bedrock_pattern_id} "
                        f"(confidence: {mapping.confidence:.0%})\n"
                    )
                    if mapping.notes:
                        parts.append(f"  {mapping.notes}\n")

        if context.bedrock_examples:
            parts.append("\n## Bedrock Code Reference:\n")
            for i, example in enumerate(context.bedrock_examples[:2], 1):
                parts.append(f"\nExample {i}:\n")
                if "code" in example:
                    code = example["code"]
                    if len(code) > 300:
                        code = code[:300] + "..."
                    parts.append(f"```javascript\n{code}\n```\n")

        if context.prior_translations:
            parts.append("\n## Prior Translation Reference:\n")
            for translation in context.prior_translations[:1]:
                if "source" in translation:
                    parts.append(f"Java: {translation['source'][:150]}...\n")
                if "target" in translation:
                    parts.append(f"Bedrock: {translation['target'][:150]}...\n")

        if parts:
            parts.insert(
                0,
                "\n\n=== CONVERSION CONTEXT (confidence: {:.0%}) ===\n".format(context.confidence),
            )
            parts.append("\n" + "=" * 50 + "\n")

        return "".join(parts)
