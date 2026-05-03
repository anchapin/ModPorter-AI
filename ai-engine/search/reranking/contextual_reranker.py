"""
Contextual re-ranker that considers user context and query history.
"""

import logging
from typing import Any, Dict, List

from schemas.multimodal_schema import SearchQuery, SearchResult

logger = logging.getLogger(__name__)


class ContextualReRanker:
    """
    Contextual re-ranker that considers user context and query history.

    This re-ranker adjusts rankings based on user context, previous queries,
    and session information to provide more personalized results.
    """

    def __init__(self):
        self.session_context = {}
        self.user_preferences = {}

    def update_session_context(self, query: SearchQuery, results: List[SearchResult]):
        """Update session context based on query and results."""
        session_id = getattr(query, "session_id", "default")

        if session_id not in self.session_context:
            from collections import defaultdict

            self.session_context[session_id] = {
                "queries": [],
                "viewed_results": [],
                "content_type_preferences": defaultdict(int),
                "topic_interests": defaultdict(int),
            }

        context = self.session_context[session_id]
        context["queries"].append(query.query_text)

        if query.content_types:
            for content_type in query.content_types:
                context["content_type_preferences"][content_type] += 1

        query_topics = self._extract_topics(query.query_text)
        for topic in query_topics:
            context["topic_interests"][topic] += 1

    def contextual_rerank(
        self, query: SearchQuery, results: List[SearchResult], session_id: str = "default"
    ) -> List[SearchResult]:
        """Re-rank results based on contextual information."""
        if session_id not in self.session_context:
            return results

        context = self.session_context[session_id]

        for result in results:
            contextual_boost = self._calculate_contextual_boost(result, context, query)
            result.final_score = result.final_score * (1.0 + contextual_boost)

        results.sort(key=lambda x: x.final_score, reverse=True)

        for i, result in enumerate(results):
            result.rank = i + 1

        return results

    def _extract_topics(self, query_text: str) -> List[str]:
        """Extract topics from query text."""
        minecraft_topics = {
            "blocks": ["block", "blocks", "cube", "tile"],
            "items": ["item", "items", "tool", "weapon", "armor"],
            "entities": ["entity", "entities", "mob", "creature"],
            "redstone": ["redstone", "circuit", "automation", "piston"],
            "crafting": ["craft", "recipe", "make", "create"],
            "building": ["build", "construction", "structure"],
            "modding": ["mod", "forge", "fabric", "addon"],
        }

        query_lower = query_text.lower()
        detected_topics = []

        for topic, keywords in minecraft_topics.items():
            if any(keyword in query_lower for keyword in keywords):
                detected_topics.append(topic)

        return detected_topics

    def _calculate_contextual_boost(
        self, result: SearchResult, context: Dict[str, Any], query: SearchQuery
    ) -> float:
        """Calculate contextual boost for a result."""
        boost = 0.0

        content_type_prefs = context.get("content_type_preferences", {})
        if result.document.content_type in content_type_prefs:
            preference_strength = content_type_prefs[result.document.content_type]
            boost += min(preference_strength * 0.05, 0.2)

        topic_interests = context.get("topic_interests", {})
        result_topics = self._extract_topics(result.document.content_text or "")

        for topic in result_topics:
            if topic in topic_interests:
                interest_strength = topic_interests[topic]
                boost += min(interest_strength * 0.03, 0.15)

        previous_queries = context.get("queries", [])
        for prev_query in previous_queries[-5:]:
            similarity = self._calculate_query_similarity(query.query_text, prev_query)
            if similarity > 0.7:
                boost += 0.1

        return min(boost, 0.5)

    def _calculate_query_similarity(self, query1: str, query2: str) -> float:
        """Calculate similarity between two queries."""
        words1 = set(query1.lower().split())
        words2 = set(query2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        return len(intersection) / len(union) if union else 0.0
