"""
Feature-based re-ranker using multiple relevance signals.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple, Callable
from datetime import datetime, timedelta, timezone

from schemas.multimodal_schema import SearchQuery, SearchResult

from .base import ReRankingFeature, ReRankingResult

logger = logging.getLogger(__name__)


class FeatureBasedReRanker:
    """
    Feature-based re-ranker that uses multiple relevance signals.

    This re-ranker analyzes various features of search results and documents
    to improve the ranking quality beyond simple similarity scores.
    """

    def __init__(self):
        self.feature_weights = self._initialize_feature_weights()
        self.feature_extractors = self._initialize_feature_extractors()

    def _initialize_feature_weights(self) -> Dict[str, float]:
        """Initialize weights for different ranking features."""
        return {
            "content_length_score": 0.1,
            "content_completeness": 0.15,
            "code_quality_score": 0.2,
            "documentation_quality": 0.1,
            "title_match_score": 0.25,
            "exact_phrase_match": 0.3,
            "semantic_coherence": 0.15,
            "domain_relevance": 0.2,
            "recency_score": 0.05,
            "popularity_score": 0.1,
            "authority_score": 0.1,
            "query_type_alignment": 0.2,
            "difficulty_match": 0.1,
            "completeness_match": 0.15,
        }

    def _initialize_feature_extractors(self) -> Dict[str, Callable]:
        """Initialize feature extraction functions."""
        return {
            "content_length_score": self._extract_content_length_score,
            "content_completeness": self._extract_content_completeness,
            "code_quality_score": self._extract_code_quality_score,
            "documentation_quality": self._extract_documentation_quality,
            "title_match_score": self._extract_title_match_score,
            "exact_phrase_match": self._extract_exact_phrase_match,
            "semantic_coherence": self._extract_semantic_coherence,
            "domain_relevance": self._extract_domain_relevance,
            "recency_score": self._extract_recency_score,
            "popularity_score": self._extract_popularity_score,
            "authority_score": self._extract_authority_score,
            "query_type_alignment": self._extract_query_type_alignment,
            "difficulty_match": self._extract_difficulty_match,
            "completeness_match": self._extract_completeness_match,
        }

    def rerank_results(
        self, query: SearchQuery, results: List[SearchResult], top_k: Optional[int] = None
    ) -> Tuple[List[SearchResult], List[ReRankingResult]]:
        """
        Re-rank search results using feature-based scoring.

        Args:
            query: Original search query
            results: Initial search results to re-rank
            top_k: Number of top results to focus re-ranking on

        Returns:
            Tuple of (reranked_results, reranking_explanations)
        """
        if not results:
            return results, []

        logger.info(f"Re-ranking {len(results)} results using feature-based approach")

        candidates = results[:top_k] if top_k else results
        remaining = results[top_k:] if top_k else []

        reranking_results = []

        for i, result in enumerate(candidates):
            features = self._extract_all_features(query, result)
            feature_score = sum(feature.value * feature.weight for feature in features)

            alpha = 0.7
            beta = 0.3
            new_score = alpha * result.final_score + beta * feature_score

            updated_result = SearchResult(
                document=result.document,
                similarity_score=result.similarity_score,
                keyword_score=result.keyword_score,
                final_score=new_score,
                rank=0,
                embedding_model_used=result.embedding_model_used,
                matched_content=result.matched_content,
                match_explanation=result.match_explanation,
            )

            candidates[i] = updated_result

            reranking_result = ReRankingResult(
                document=result.document,
                original_rank=result.rank,
                new_rank=0,
                original_score=result.final_score,
                reranked_score=new_score,
                final_score=new_score,
                features_used=features,
                relevance_features={},
                confidence=self._calculate_reranking_confidence(features),
                explanation=self._generate_feature_explanation(
                    features, result.final_score, new_score
                ),
            )
            reranking_results.append(reranking_result)

        candidates.sort(key=lambda x: x.final_score, reverse=True)

        for i, result in enumerate(candidates):
            result.rank = i + 1
            reranking_results[i].new_rank = i + 1

        final_results = candidates + remaining

        logger.info(
            f"Re-ranking completed. Score changes: {[r.reranked_score - r.original_score for r in reranking_results[:5]]}"
        )

        return final_results, reranking_results

    def _extract_all_features(
        self, query: SearchQuery, result: SearchResult
    ) -> List[ReRankingFeature]:
        """Extract all features for a search result."""
        features = []

        for feature_name, extractor in self.feature_extractors.items():
            try:
                value, explanation = extractor(query, result)
                weight = self.feature_weights.get(feature_name, 0.1)

                feature = ReRankingFeature(
                    name=feature_name, value=value, weight=weight, explanation=explanation
                )
                features.append(feature)

            except Exception as e:
                logger.warning(f"Failed to extract feature {feature_name}: {e}")
                continue

        return features

    def _extract_content_length_score(
        self, query: SearchQuery, result: SearchResult
    ) -> Tuple[float, str]:
        """Score based on content length appropriateness."""
        if not result.document.content_text:
            return 0.0, "No content available"

        content_length = len(result.document.content_text)
        query_length = len(query.query_text.split())

        if query_length <= 3:
            optimal_range = (100, 500)
        elif query_length <= 8:
            optimal_range = (300, 1000)
        else:
            optimal_range = (500, 2000)

        if optimal_range[0] <= content_length <= optimal_range[1]:
            score = 1.0
            explanation = f"Content length ({content_length}) is optimal"
        elif content_length < optimal_range[0]:
            score = 0.3 + 0.7 * (content_length / optimal_range[0])
            explanation = f"Content is shorter than optimal ({content_length} < {optimal_range[0]})"
        else:
            excess = content_length - optimal_range[1]
            score = 1.0 / (1.0 + 0.001 * excess)
            explanation = f"Content is longer than optimal ({content_length} > {optimal_range[1]})"

        return score, explanation

    def _extract_content_completeness(
        self, query: SearchQuery, result: SearchResult
    ) -> Tuple[float, str]:
        """Score based on content completeness."""
        document = result.document
        completeness_indicators = 0
        total_indicators = 5

        if document.content_text and len(document.content_text) > 50:
            completeness_indicators += 1

        if document.content_metadata and len(document.content_metadata) > 0:
            completeness_indicators += 1

        if document.tags and len(document.tags) > 0:
            completeness_indicators += 1

        if hasattr(document, "indexed_at") and document.indexed_at:
            completeness_indicators += 1

        if document.source_path and len(document.source_path) > 0:
            completeness_indicators += 1

        score = completeness_indicators / total_indicators
        explanation = (
            f"Completeness: {completeness_indicators}/{total_indicators} indicators present"
        )

        return score, explanation

    def _extract_code_quality_score(
        self, query: SearchQuery, result: SearchResult
    ) -> Tuple[float, str]:
        """Score code quality for code-related content."""
        if result.document.content_type != "code":
            return 0.5, "Not code content"

        if not result.document.content_text:
            return 0.0, "No code content available"

        code = result.document.content_text
        quality_score = 0.0
        indicators = []

        if "class " in code or "public class" in code:
            quality_score += 0.2
            indicators.append("has class definition")

        if "import " in code:
            quality_score += 0.1
            indicators.append("has imports")

        if "//" in code or "/*" in code:
            quality_score += 0.2
            indicators.append("has comments")

        if "public " in code or "private " in code:
            quality_score += 0.1
            indicators.append("uses access modifiers")

        if "Registry" in code or "GameRegistry" in code:
            quality_score += 0.2
            indicators.append("uses proper registration")

        if "@Override" in code or "@EventHandler" in code:
            quality_score += 0.1
            indicators.append("uses annotations")

        if len(code) < 100:
            quality_score *= 0.5
            indicators.append("short code snippet")

        explanation = (
            f"Code quality indicators: {', '.join(indicators) if indicators else 'none found'}"
        )
        return min(quality_score, 1.0), explanation

    def _extract_documentation_quality(
        self, query: SearchQuery, result: SearchResult
    ) -> Tuple[float, str]:
        """Score documentation quality."""
        if result.document.content_type != "documentation":
            return 0.5, "Not documentation content"

        if not result.document.content_text:
            return 0.0, "No documentation content"

        doc = result.document.content_text
        quality_indicators = []
        score = 0.0

        if "#" in doc:
            score += 0.3
            quality_indicators.append("has headers")

        if "```" in doc or "`" in doc:
            score += 0.2
            quality_indicators.append("has code examples")

        if len(doc.split("\n\n")) > 2:
            score += 0.2
            quality_indicators.append("well-structured")

        if any(word in doc.lower() for word in ["example", "usage", "how to"]):
            score += 0.2
            quality_indicators.append("has examples/usage")

        if len(doc) > 200:
            score += 0.1
            quality_indicators.append("substantial content")

        explanation = f"Documentation quality: {', '.join(quality_indicators) if quality_indicators else 'basic'}"
        return min(score, 1.0), explanation

    def _extract_title_match_score(
        self, query: SearchQuery, result: SearchResult
    ) -> Tuple[float, str]:
        """Score based on title/source path matching query."""
        source_path = result.document.source_path.lower() if result.document.source_path else ""
        query_terms = query.query_text.lower().split()

        if not source_path:
            return 0.0, "No source path available"

        filename = source_path.split("/")[-1] if "/" in source_path else source_path
        filename_without_ext = filename.split(".")[0] if "." in filename else filename

        matches = 0
        for term in query_terms:
            if term in filename_without_ext or any(
                term in part for part in filename_without_ext.split("_")
            ):
                matches += 1

        score = matches / len(query_terms) if query_terms else 0.0
        explanation = f"Title match: {matches}/{len(query_terms)} query terms in filename"

        return score, explanation

    def _extract_exact_phrase_match(
        self, query: SearchQuery, result: SearchResult
    ) -> Tuple[float, str]:
        """Score for exact phrase matches in content."""
        if not result.document.content_text:
            return 0.0, "No content to match"

        content_lower = result.document.content_text.lower()
        query_lower = query.query_text.lower()

        if query_lower in content_lower:
            return 1.0, f"Exact phrase match found: '{query.query_text}'"

        query_words = query_lower.split()
        if len(query_words) >= 3:
            for i in range(len(query_words) - 2):
                phrase = " ".join(query_words[i : i + 3])
                if phrase in content_lower:
                    return 0.7, f"Partial phrase match found: '{phrase}'"

        return 0.0, "No exact phrase matches"

    def _extract_semantic_coherence(
        self, query: SearchQuery, result: SearchResult
    ) -> Tuple[float, str]:
        """Score semantic coherence between query and result."""
        if not result.document.content_text:
            return 0.0, "No content for coherence analysis"

        query_words = set(query.query_text.lower().split())
        content_words = set(result.document.content_text.lower().split())

        intersection = query_words.intersection(content_words)
        union = query_words.union(content_words)

        jaccard_score = len(intersection) / len(union) if union else 0.0

        explanation = f"Semantic coherence (Jaccard): {jaccard_score:.3f}"
        return jaccard_score, explanation

    def _extract_domain_relevance(
        self, query: SearchQuery, result: SearchResult
    ) -> Tuple[float, str]:
        """Score relevance to Minecraft modding domain."""
        minecraft_keywords = {
            "minecraft",
            "block",
            "item",
            "entity",
            "mod",
            "forge",
            "fabric",
            "bedrock",
            "java",
            "recipe",
            "texture",
            "biome",
            "dimension",
        }

        content = (result.document.content_text or "").lower()
        query_text = query.query_text.lower()

        content_domain_words = sum(1 for word in minecraft_keywords if word in content)
        query_domain_words = sum(1 for word in minecraft_keywords if word in query_text)

        if query_domain_words == 0:
            return 0.5, "Non-domain specific query"

        content_words = len(content.split()) if content else 1
        domain_density = content_domain_words / content_words

        score = min(domain_density * 10, 1.0)
        explanation = (
            f"Domain relevance: {content_domain_words} domain words, density: {domain_density:.3f}"
        )

        return score, explanation

    def _extract_recency_score(self, query: SearchQuery, result: SearchResult) -> Tuple[float, str]:
        """Score based on document recency."""
        if not hasattr(result.document, "updated_at") or not result.document.updated_at:
            return 0.5, "No timestamp available"

        now = datetime.now(timezone.utc)
        doc_age = now - result.document.updated_at

        if doc_age < timedelta(days=7):
            score = 1.0
            explanation = "Very recent (< 1 week)"
        elif doc_age < timedelta(days=30):
            score = 0.8
            explanation = "Recent (< 1 month)"
        elif doc_age < timedelta(days=90):
            score = 0.6
            explanation = "Moderately recent (< 3 months)"
        elif doc_age < timedelta(days=365):
            score = 0.4
            explanation = "Older (< 1 year)"
        else:
            score = 0.2
            explanation = "Old (> 1 year)"

        return score, explanation

    def _extract_popularity_score(
        self, query: SearchQuery, result: SearchResult
    ) -> Tuple[float, str]:
        """Score based on content popularity (simplified)."""
        popularity_indicators = 0

        if result.document.content_metadata:
            popularity_indicators += len(result.document.content_metadata)

        if result.document.tags:
            popularity_indicators += len(result.document.tags)

        if result.document.content_text and len(result.document.content_text) > 1000:
            popularity_indicators += 2

        score = min(popularity_indicators / 10.0, 1.0)
        explanation = f"Popularity indicators: {popularity_indicators}"

        return score, explanation

    def _extract_authority_score(
        self, query: SearchQuery, result: SearchResult
    ) -> Tuple[float, str]:
        """Score based on content authority."""
        authority_score = 0.5
        indicators = []

        source_path = result.document.source_path.lower() if result.document.source_path else ""

        if "official" in source_path or "docs" in source_path:
            authority_score += 0.3
            indicators.append("official documentation")

        if "example" in source_path or "tutorial" in source_path:
            authority_score += 0.2
            indicators.append("educational content")

        if result.document.content_type == "code" and result.document.content_text:
            if "public class" in result.document.content_text:
                authority_score += 0.1
                indicators.append("complete class definition")

        explanation = f"Authority indicators: {', '.join(indicators) if indicators else 'baseline'}"
        return min(authority_score, 1.0), explanation

    def _extract_query_type_alignment(
        self, query: SearchQuery, result: SearchResult
    ) -> Tuple[float, str]:
        """Score alignment between query type and result type."""
        query_text = query.query_text.lower()

        if any(word in query_text for word in ["how", "create", "make", "build", "implement"]):
            query_type = "how_to"
        elif any(word in query_text for word in ["what", "explain", "definition", "meaning"]):
            query_type = "explanation"
        elif any(word in query_text for word in ["example", "sample", "demo"]):
            query_type = "example"
        elif any(word in query_text for word in ["error", "bug", "fix", "problem"]):
            query_type = "troubleshooting"
        else:
            query_type = "general"

        result_type = result.document.content_type
        content = result.document.content_text or ""

        alignment_score = 0.0

        if query_type == "how_to":
            if result_type == "documentation" or "tutorial" in content.lower():
                alignment_score = 1.0
            elif result_type == "code":
                alignment_score = 0.8
        elif query_type == "explanation":
            if result_type == "documentation":
                alignment_score = 1.0
            elif "comment" in content or "//" in content:
                alignment_score = 0.7
        elif query_type == "example":
            if result_type == "code":
                alignment_score = 1.0
            elif "example" in content.lower():
                alignment_score = 0.9
        elif query_type == "troubleshooting":
            if "error" in content.lower() or "exception" in content.lower():
                alignment_score = 1.0
            elif result_type == "documentation":
                alignment_score = 0.6
        else:
            alignment_score = 0.5

        explanation = f"Query type '{query_type}' alignment with '{result_type}'"
        return alignment_score, explanation

    def _extract_difficulty_match(
        self, query: SearchQuery, result: SearchResult
    ) -> Tuple[float, str]:
        """Score difficulty level matching."""
        query_complexity_indicators = len(
            [
                word
                for word in query.query_text.lower().split()
                if word in ["advanced", "complex", "detailed", "comprehensive", "optimize"]
            ]
        )

        content = result.document.content_text or ""
        content_complexity = 0

        if len(content) > 2000:
            content_complexity += 1
        if content.count("\n") > 50:
            content_complexity += 1
        if any(
            word in content.lower() for word in ["abstract", "interface", "extends", "implements"]
        ):
            content_complexity += 1

        if query_complexity_indicators == 0 and content_complexity <= 1:
            score = 1.0
            explanation = "Good difficulty match: simple"
        elif query_complexity_indicators > 0 and content_complexity > 1:
            score = 1.0
            explanation = "Good difficulty match: complex"
        else:
            score = 0.6
            explanation = f"Difficulty mismatch: query complexity {query_complexity_indicators}, content complexity {content_complexity}"

        return score, explanation

    def _extract_completeness_match(
        self, query: SearchQuery, result: SearchResult
    ) -> Tuple[float, str]:
        """Score completeness of answer for the query."""
        query_words = set(query.query_text.lower().split())
        content = result.document.content_text or ""

        if not content:
            return 0.0, "No content to assess completeness"

        content_words = set(content.lower().split())

        coverage = (
            len(query_words.intersection(content_words)) / len(query_words) if query_words else 0.0
        )

        length_bonus = min(len(content) / 1000, 0.3)

        completeness_score = min(coverage + length_bonus, 1.0)
        explanation = f"Query term coverage: {coverage:.2f}, length bonus: {length_bonus:.2f}"

        return completeness_score, explanation

    def _calculate_reranking_confidence(self, features: List[ReRankingFeature]) -> float:
        """Calculate confidence in the re-ranking decision."""
        feature_values = [f.value for f in features]

        if not feature_values:
            return 0.5

        avg_value = sum(feature_values) / len(feature_values)
        value_variance = sum((v - avg_value) ** 2 for v in feature_values) / len(feature_values)

        confidence = avg_value * (1.0 - min(value_variance, 0.5))

        return min(max(confidence, 0.0), 1.0)

    def _generate_feature_explanation(
        self, features: List[ReRankingFeature], original_score: float, new_score: float
    ) -> str:
        """Generate human-readable explanation for re-ranking."""
        score_change = new_score - original_score
        change_direction = "increased" if score_change > 0 else "decreased"

        top_features = sorted(features, key=lambda f: f.value * f.weight, reverse=True)[:3]

        feature_descriptions = []
        for feature in top_features:
            contribution = feature.value * feature.weight
            feature_descriptions.append(
                f"{feature.name}: {contribution:.3f} ({feature.explanation})"
            )

        explanation = (
            f"Score {change_direction} by {abs(score_change):.3f}. "
            f"Top factors: {'; '.join(feature_descriptions)}"
        )

        return explanation
