"""
Re-ranking engine for improving search result quality.

This module implements various re-ranking strategies to improve the final
ordering of search results based on additional relevance signals.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from collections import defaultdict

from schemas.multimodal_schema import SearchQuery, SearchResult

logger = logging.getLogger(__name__)


class ReRankingStrategy(str, Enum):
    """Re-ranking strategies available."""
    CROSS_ENCODER = "cross_encoder"
    FEATURE_BASED = "feature_based"
    NEURAL_RERANKER = "neural_reranker"
    ENSEMBLE = "ensemble"
    CONTEXTUAL = "contextual"


@dataclass
class ReRankingFeature:
    """Feature used for re-ranking with its weight and value."""
    name: str
    value: float
    weight: float
    explanation: str


@dataclass
class ReRankingResult:
    """Result of re-ranking with detailed explanation."""
    original_rank: int
    new_rank: int
    original_score: float
    reranked_score: float
    features_used: List[ReRankingFeature]
    confidence: float
    explanation: str


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
            # Content quality features
            'content_length_score': 0.1,
            'content_completeness': 0.15,
            'code_quality_score': 0.2,
            'documentation_quality': 0.1,
            
            # Relevance features
            'title_match_score': 0.25,
            'exact_phrase_match': 0.3,
            'semantic_coherence': 0.15,
            'domain_relevance': 0.2,
            
            # Context features
            'recency_score': 0.05,
            'popularity_score': 0.1,
            'authority_score': 0.1,
            
            # User intent features
            'query_type_alignment': 0.2,
            'difficulty_match': 0.1,
            'completeness_match': 0.15
        }
    
    def _initialize_feature_extractors(self) -> Dict[str, callable]:
        """Initialize feature extraction functions."""
        return {
            'content_length_score': self._extract_content_length_score,
            'content_completeness': self._extract_content_completeness,
            'code_quality_score': self._extract_code_quality_score,
            'documentation_quality': self._extract_documentation_quality,
            'title_match_score': self._extract_title_match_score,
            'exact_phrase_match': self._extract_exact_phrase_match,
            'semantic_coherence': self._extract_semantic_coherence,
            'domain_relevance': self._extract_domain_relevance,
            'recency_score': self._extract_recency_score,
            'popularity_score': self._extract_popularity_score,
            'authority_score': self._extract_authority_score,
            'query_type_alignment': self._extract_query_type_alignment,
            'difficulty_match': self._extract_difficulty_match,
            'completeness_match': self._extract_completeness_match
        }
    
    def rerank_results(
        self,
        query: SearchQuery,
        results: List[SearchResult],
        top_k: Optional[int] = None
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
        
        # Focus on top results for efficiency
        candidates = results[:top_k] if top_k else results
        remaining = results[top_k:] if top_k else []
        
        reranking_results = []
        
        # Extract features and calculate new scores for each candidate
        for i, result in enumerate(candidates):
            features = self._extract_all_features(query, result)
            
            # Calculate weighted feature score
            feature_score = sum(
                feature.value * feature.weight 
                for feature in features
            )
            
            # Combine with original score
            alpha = 0.7  # Weight for original score
            beta = 0.3   # Weight for feature score
            new_score = alpha * result.final_score + beta * feature_score
            
            # Create updated result
            updated_result = SearchResult(
                document=result.document,
                similarity_score=result.similarity_score,
                keyword_score=result.keyword_score,
                final_score=new_score,
                rank=0,  # Will be set after sorting
                embedding_model_used=result.embedding_model_used,
                matched_content=result.matched_content,
                match_explanation=result.match_explanation
            )
            
            candidates[i] = updated_result
            
            # Create re-ranking explanation
            reranking_result = ReRankingResult(
                original_rank=result.rank,
                new_rank=0,  # Will be set after sorting
                original_score=result.final_score,
                reranked_score=new_score,
                features_used=features,
                confidence=self._calculate_reranking_confidence(features),
                explanation=self._generate_feature_explanation(features, result.final_score, new_score)
            )
            reranking_results.append(reranking_result)
        
        # Sort by new scores
        candidates.sort(key=lambda x: x.final_score, reverse=True)
        
        # Update ranks
        for i, result in enumerate(candidates):
            result.rank = i + 1
            reranking_results[i].new_rank = i + 1
        
        # Combine with remaining results
        final_results = candidates + remaining
        
        logger.info(f"Re-ranking completed. Score changes: {[r.reranked_score - r.original_score for r in reranking_results[:5]]}")
        
        return final_results, reranking_results
    
    def _extract_all_features(self, query: SearchQuery, result: SearchResult) -> List[ReRankingFeature]:
        """Extract all features for a search result."""
        features = []
        
        for feature_name, extractor in self.feature_extractors.items():
            try:
                value, explanation = extractor(query, result)
                weight = self.feature_weights.get(feature_name, 0.1)
                
                feature = ReRankingFeature(
                    name=feature_name,
                    value=value,
                    weight=weight,
                    explanation=explanation
                )
                features.append(feature)
                
            except Exception as e:
                logger.warning(f"Failed to extract feature {feature_name}: {e}")
                continue
        
        return features
    
    def _extract_content_length_score(self, query: SearchQuery, result: SearchResult) -> Tuple[float, str]:
        """Score based on content length appropriateness."""
        if not result.document.content_text:
            return 0.0, "No content available"
        
        content_length = len(result.document.content_text)
        query_length = len(query.query_text.split())
        
        # Optimal length based on query complexity
        if query_length <= 3:
            optimal_range = (100, 500)  # Short queries prefer concise answers
        elif query_length <= 8:
            optimal_range = (300, 1000)  # Medium queries
        else:
            optimal_range = (500, 2000)  # Complex queries need detailed answers
        
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
    
    def _extract_content_completeness(self, query: SearchQuery, result: SearchResult) -> Tuple[float, str]:
        """Score based on content completeness."""
        document = result.document
        completeness_indicators = 0
        total_indicators = 5
        
        # Check for various completeness indicators
        if document.content_text and len(document.content_text) > 50:
            completeness_indicators += 1
        
        if document.content_metadata and len(document.content_metadata) > 0:
            completeness_indicators += 1
        
        if document.tags and len(document.tags) > 0:
            completeness_indicators += 1
        
        if hasattr(document, 'indexed_at') and document.indexed_at:
            completeness_indicators += 1
        
        if document.source_path and len(document.source_path) > 0:
            completeness_indicators += 1
        
        score = completeness_indicators / total_indicators
        explanation = f"Completeness: {completeness_indicators}/{total_indicators} indicators present"
        
        return score, explanation
    
    def _extract_code_quality_score(self, query: SearchQuery, result: SearchResult) -> Tuple[float, str]:
        """Score code quality for code-related content."""
        if result.document.content_type != "code":
            return 0.5, "Not code content"
        
        if not result.document.content_text:
            return 0.0, "No code content available"
        
        code = result.document.content_text
        quality_score = 0.0
        indicators = []
        
        # Check for good coding practices
        if 'class ' in code or 'public class' in code:
            quality_score += 0.2
            indicators.append("has class definition")
        
        if 'import ' in code:
            quality_score += 0.1
            indicators.append("has imports")
        
        if '//' in code or '/*' in code:
            quality_score += 0.2
            indicators.append("has comments")
        
        if 'public ' in code or 'private ' in code:
            quality_score += 0.1
            indicators.append("uses access modifiers")
        
        # Check for Minecraft-specific good practices
        if 'Registry' in code or 'GameRegistry' in code:
            quality_score += 0.2
            indicators.append("uses proper registration")
        
        if '@Override' in code or '@EventHandler' in code:
            quality_score += 0.1
            indicators.append("uses annotations")
        
        # Penalty for very short code snippets
        if len(code) < 100:
            quality_score *= 0.5
            indicators.append("short code snippet")
        
        explanation = f"Code quality indicators: {', '.join(indicators) if indicators else 'none found'}"
        return min(quality_score, 1.0), explanation
    
    def _extract_documentation_quality(self, query: SearchQuery, result: SearchResult) -> Tuple[float, str]:
        """Score documentation quality."""
        if result.document.content_type != "documentation":
            return 0.5, "Not documentation content"
        
        if not result.document.content_text:
            return 0.0, "No documentation content"
        
        doc = result.document.content_text
        quality_indicators = []
        score = 0.0
        
        # Check for structured documentation
        if '#' in doc:  # Markdown headers
            score += 0.3
            quality_indicators.append("has headers")
        
        if '```' in doc or '`' in doc:  # Code examples
            score += 0.2
            quality_indicators.append("has code examples")
        
        if len(doc.split('\n\n')) > 2:  # Multiple paragraphs
            score += 0.2
            quality_indicators.append("well-structured")
        
        if any(word in doc.lower() for word in ['example', 'usage', 'how to']):
            score += 0.2
            quality_indicators.append("has examples/usage")
        
        if len(doc) > 200:  # Substantial content
            score += 0.1
            quality_indicators.append("substantial content")
        
        explanation = f"Documentation quality: {', '.join(quality_indicators) if quality_indicators else 'basic'}"
        return min(score, 1.0), explanation
    
    def _extract_title_match_score(self, query: SearchQuery, result: SearchResult) -> Tuple[float, str]:
        """Score based on title/source path matching query."""
        source_path = result.document.source_path.lower() if result.document.source_path else ""
        query_terms = query.query_text.lower().split()
        
        if not source_path:
            return 0.0, "No source path available"
        
        # Extract filename from path
        filename = source_path.split('/')[-1] if '/' in source_path else source_path
        filename_without_ext = filename.split('.')[0] if '.' in filename else filename
        
        matches = 0
        for term in query_terms:
            if term in filename_without_ext or any(term in part for part in filename_without_ext.split('_')):
                matches += 1
        
        score = matches / len(query_terms) if query_terms else 0.0
        explanation = f"Title match: {matches}/{len(query_terms)} query terms in filename"
        
        return score, explanation
    
    def _extract_exact_phrase_match(self, query: SearchQuery, result: SearchResult) -> Tuple[float, str]:
        """Score for exact phrase matches in content."""
        if not result.document.content_text:
            return 0.0, "No content to match"
        
        content_lower = result.document.content_text.lower()
        query_lower = query.query_text.lower()
        
        # Check for exact query match
        if query_lower in content_lower:
            return 1.0, f"Exact phrase match found: '{query.query_text}'"
        
        # Check for partial phrase matches (3+ words)
        query_words = query_lower.split()
        if len(query_words) >= 3:
            for i in range(len(query_words) - 2):
                phrase = ' '.join(query_words[i:i+3])
                if phrase in content_lower:
                    return 0.7, f"Partial phrase match found: '{phrase}'"
        
        return 0.0, "No exact phrase matches"
    
    def _extract_semantic_coherence(self, query: SearchQuery, result: SearchResult) -> Tuple[float, str]:
        """Score semantic coherence between query and result."""
        # This is a simplified implementation
        # In a real system, this would use more sophisticated NLP techniques
        
        if not result.document.content_text:
            return 0.0, "No content for coherence analysis"
        
        query_words = set(query.query_text.lower().split())
        content_words = set(result.document.content_text.lower().split())
        
        # Simple Jaccard similarity
        intersection = query_words.intersection(content_words)
        union = query_words.union(content_words)
        
        jaccard_score = len(intersection) / len(union) if union else 0.0
        
        explanation = f"Semantic coherence (Jaccard): {jaccard_score:.3f}"
        return jaccard_score, explanation
    
    def _extract_domain_relevance(self, query: SearchQuery, result: SearchResult) -> Tuple[float, str]:
        """Score relevance to Minecraft modding domain."""
        minecraft_keywords = {
            'minecraft', 'block', 'item', 'entity', 'mod', 'forge', 'fabric',
            'bedrock', 'java', 'recipe', 'texture', 'biome', 'dimension'
        }
        
        content = (result.document.content_text or "").lower()
        query_text = query.query_text.lower()
        
        # Count domain keywords in content and query
        content_domain_words = sum(1 for word in minecraft_keywords if word in content)
        query_domain_words = sum(1 for word in minecraft_keywords if word in query_text)
        
        if query_domain_words == 0:
            # Non-domain query, neutral score
            return 0.5, "Non-domain specific query"
        
        # Score based on domain word density
        content_words = len(content.split()) if content else 1
        domain_density = content_domain_words / content_words
        
        score = min(domain_density * 10, 1.0)  # Scale up density
        explanation = f"Domain relevance: {content_domain_words} domain words, density: {domain_density:.3f}"
        
        return score, explanation
    
    def _extract_recency_score(self, query: SearchQuery, result: SearchResult) -> Tuple[float, str]:
        """Score based on document recency."""
        if not hasattr(result.document, 'updated_at') or not result.document.updated_at:
            return 0.5, "No timestamp available"
        
        from datetime import datetime, timedelta
        now = datetime.utcnow()
        doc_age = now - result.document.updated_at
        
        # Score decreases with age
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
    
    def _extract_popularity_score(self, query: SearchQuery, result: SearchResult) -> Tuple[float, str]:
        """Score based on content popularity (simplified)."""
        # This would typically use view counts, stars, downloads, etc.
        # For now, use a simple heuristic based on content completeness
        
        popularity_indicators = 0
        
        if result.document.content_metadata:
            popularity_indicators += len(result.document.content_metadata)
        
        if result.document.tags:
            popularity_indicators += len(result.document.tags)
        
        if result.document.content_text and len(result.document.content_text) > 1000:
            popularity_indicators += 2  # Substantial content suggests effort/popularity
        
        score = min(popularity_indicators / 10.0, 1.0)
        explanation = f"Popularity indicators: {popularity_indicators}"
        
        return score, explanation
    
    def _extract_authority_score(self, query: SearchQuery, result: SearchResult) -> Tuple[float, str]:
        """Score based on content authority."""
        # Simplified authority scoring
        authority_score = 0.5  # Neutral baseline
        indicators = []
        
        source_path = result.document.source_path.lower() if result.document.source_path else ""
        
        # Authority indicators
        if 'official' in source_path or 'docs' in source_path:
            authority_score += 0.3
            indicators.append("official documentation")
        
        if 'example' in source_path or 'tutorial' in source_path:
            authority_score += 0.2
            indicators.append("educational content")
        
        if result.document.content_type == "code" and result.document.content_text:
            if 'public class' in result.document.content_text:
                authority_score += 0.1
                indicators.append("complete class definition")
        
        explanation = f"Authority indicators: {', '.join(indicators) if indicators else 'baseline'}"
        return min(authority_score, 1.0), explanation
    
    def _extract_query_type_alignment(self, query: SearchQuery, result: SearchResult) -> Tuple[float, str]:
        """Score alignment between query type and result type."""
        query_text = query.query_text.lower()
        
        # Detect query intent
        if any(word in query_text for word in ['how', 'create', 'make', 'build', 'implement']):
            query_type = "how_to"
        elif any(word in query_text for word in ['what', 'explain', 'definition', 'meaning']):
            query_type = "explanation"
        elif any(word in query_text for word in ['example', 'sample', 'demo']):
            query_type = "example"
        elif any(word in query_text for word in ['error', 'bug', 'fix', 'problem']):
            query_type = "troubleshooting"
        else:
            query_type = "general"
        
        # Match with result type
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
            alignment_score = 0.5  # Neutral for general queries
        
        explanation = f"Query type '{query_type}' alignment with '{result_type}'"
        return alignment_score, explanation
    
    def _extract_difficulty_match(self, query: SearchQuery, result: SearchResult) -> Tuple[float, str]:
        """Score difficulty level matching."""
        # Simplified difficulty assessment
        query_complexity_indicators = len([
            word for word in query.query_text.lower().split()
            if word in ['advanced', 'complex', 'detailed', 'comprehensive', 'optimize']
        ])
        
        content = result.document.content_text or ""
        content_complexity = 0
        
        # Assess content complexity
        if len(content) > 2000:
            content_complexity += 1
        if content.count('\n') > 50:  # Many lines
            content_complexity += 1
        if any(word in content.lower() for word in ['abstract', 'interface', 'extends', 'implements']):
            content_complexity += 1
        
        # Match complexity levels
        if query_complexity_indicators == 0 and content_complexity <= 1:
            score = 1.0  # Simple query, simple content
            explanation = "Good difficulty match: simple"
        elif query_complexity_indicators > 0 and content_complexity > 1:
            score = 1.0  # Complex query, complex content  
            explanation = "Good difficulty match: complex"
        else:
            score = 0.6  # Mismatch, but not terrible
            explanation = f"Difficulty mismatch: query complexity {query_complexity_indicators}, content complexity {content_complexity}"
        
        return score, explanation
    
    def _extract_completeness_match(self, query: SearchQuery, result: SearchResult) -> Tuple[float, str]:
        """Score completeness of answer for the query."""
        query_words = set(query.query_text.lower().split())
        content = result.document.content_text or ""
        
        if not content:
            return 0.0, "No content to assess completeness"
        
        content_words = set(content.lower().split())
        
        # Calculate coverage of query terms
        coverage = len(query_words.intersection(content_words)) / len(query_words) if query_words else 0.0
        
        # Adjust for content length - longer content might be more complete
        length_bonus = min(len(content) / 1000, 0.3)  # Up to 0.3 bonus
        
        completeness_score = min(coverage + length_bonus, 1.0)
        explanation = f"Query term coverage: {coverage:.2f}, length bonus: {length_bonus:.2f}"
        
        return completeness_score, explanation
    
    def _calculate_reranking_confidence(self, features: List[ReRankingFeature]) -> float:
        """Calculate confidence in the re-ranking decision."""
        # Confidence based on feature diversity and strength
        feature_values = [f.value for f in features]
        
        if not feature_values:
            return 0.5
        
        # High confidence if features are strong and diverse
        avg_value = sum(feature_values) / len(feature_values)
        value_variance = sum((v - avg_value) ** 2 for v in feature_values) / len(feature_values)
        
        # High average value and low variance indicate strong, consistent signals
        confidence = avg_value * (1.0 - min(value_variance, 0.5))
        
        return min(max(confidence, 0.0), 1.0)
    
    def _generate_feature_explanation(
        self, 
        features: List[ReRankingFeature], 
        original_score: float, 
        new_score: float
    ) -> str:
        """Generate human-readable explanation for re-ranking."""
        score_change = new_score - original_score
        change_direction = "increased" if score_change > 0 else "decreased"
        
        # Find top contributing features
        top_features = sorted(features, key=lambda f: f.value * f.weight, reverse=True)[:3]
        
        feature_descriptions = []
        for feature in top_features:
            contribution = feature.value * feature.weight
            feature_descriptions.append(f"{feature.name}: {contribution:.3f} ({feature.explanation})")
        
        explanation = (
            f"Score {change_direction} by {abs(score_change):.3f}. "
            f"Top factors: {'; '.join(feature_descriptions)}"
        )
        
        return explanation


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
        # Track query patterns and result interactions
        session_id = getattr(query, 'session_id', 'default')
        
        if session_id not in self.session_context:
            self.session_context[session_id] = {
                'queries': [],
                'viewed_results': [],
                'content_type_preferences': defaultdict(int),
                'topic_interests': defaultdict(int)
            }
        
        context = self.session_context[session_id]
        context['queries'].append(query.query_text)
        
        # Track content type preferences
        if query.content_types:
            for content_type in query.content_types:
                context['content_type_preferences'][content_type] += 1
        
        # Extract topic interests from query
        query_topics = self._extract_topics(query.query_text)
        for topic in query_topics:
            context['topic_interests'][topic] += 1
    
    def contextual_rerank(
        self,
        query: SearchQuery,
        results: List[SearchResult],
        session_id: str = 'default'
    ) -> List[SearchResult]:
        """Re-rank results based on contextual information."""
        if session_id not in self.session_context:
            return results  # No context available
        
        context = self.session_context[session_id]
        
        # Apply contextual adjustments
        for result in results:
            contextual_boost = self._calculate_contextual_boost(result, context, query)
            result.final_score = result.final_score * (1.0 + contextual_boost)
        
        # Sort by adjusted scores
        results.sort(key=lambda x: x.final_score, reverse=True)
        
        # Update ranks
        for i, result in enumerate(results):
            result.rank = i + 1
        
        return results
    
    def _extract_topics(self, query_text: str) -> List[str]:
        """Extract topics from query text."""
        # Simplified topic extraction
        minecraft_topics = {
            'blocks': ['block', 'blocks', 'cube', 'tile'],
            'items': ['item', 'items', 'tool', 'weapon', 'armor'],
            'entities': ['entity', 'entities', 'mob', 'creature'],
            'redstone': ['redstone', 'circuit', 'automation', 'piston'],
            'crafting': ['craft', 'recipe', 'make', 'create'],
            'building': ['build', 'construction', 'structure'],
            'modding': ['mod', 'forge', 'fabric', 'addon']
        }
        
        query_lower = query_text.lower()
        detected_topics = []
        
        for topic, keywords in minecraft_topics.items():
            if any(keyword in query_lower for keyword in keywords):
                detected_topics.append(topic)
        
        return detected_topics
    
    def _calculate_contextual_boost(
        self,
        result: SearchResult,
        context: Dict[str, Any],
        query: SearchQuery
    ) -> float:
        """Calculate contextual boost for a result."""
        boost = 0.0
        
        # Content type preference boost
        content_type_prefs = context.get('content_type_preferences', {})
        if result.document.content_type in content_type_prefs:
            preference_strength = content_type_prefs[result.document.content_type]
            boost += min(preference_strength * 0.05, 0.2)  # Max 20% boost
        
        # Topic interest boost
        topic_interests = context.get('topic_interests', {})
        result_topics = self._extract_topics(result.document.content_text or "")
        
        for topic in result_topics:
            if topic in topic_interests:
                interest_strength = topic_interests[topic]
                boost += min(interest_strength * 0.03, 0.15)  # Max 15% boost per topic
        
        # Query similarity boost (if user has similar queries)
        previous_queries = context.get('queries', [])
        for prev_query in previous_queries[-5:]:  # Last 5 queries
            similarity = self._calculate_query_similarity(query.query_text, prev_query)
            if similarity > 0.7:
                boost += 0.1  # Boost for similar queries
        
        return min(boost, 0.5)  # Cap total boost at 50%
    
    def _calculate_query_similarity(self, query1: str, query2: str) -> float:
        """Calculate similarity between two queries."""
        words1 = set(query1.lower().split())
        words2 = set(query2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0


class EnsembleReRanker:
    """
    Ensemble re-ranker that combines multiple re-ranking strategies.
    
    This re-ranker uses multiple approaches and combines their outputs
    for more robust ranking decisions.
    """
    
    def __init__(self):
        self.feature_reranker = FeatureBasedReRanker()
        self.contextual_reranker = ContextualReRanker()
        self.strategy_weights = {
            'feature_based': 0.7,
            'contextual': 0.3
        }
    
    def ensemble_rerank(
        self,
        query: SearchQuery,
        results: List[SearchResult],
        session_id: str = 'default'
    ) -> Tuple[List[SearchResult], Dict[str, Any]]:
        """
        Re-rank using ensemble of strategies.
        
        Args:
            query: Search query
            results: Initial results
            session_id: Session identifier for contextual ranking
            
        Returns:
            Tuple of (reranked_results, explanation_metadata)
        """
        if not results:
            return results, {}
        
        logger.info(f"Ensemble re-ranking {len(results)} results")
        
        # Get rankings from different strategies
        feature_results, feature_explanations = self.feature_reranker.rerank_results(
            query, results.copy()
        )
        
        contextual_results = self.contextual_reranker.contextual_rerank(
            query, results.copy(), session_id
        )
        
        # Combine rankings using weighted average
        final_results = self._combine_rankings(
            [
                (feature_results, self.strategy_weights['feature_based']),
                (contextual_results, self.strategy_weights['contextual'])
            ]
        )
        
        # Update contextual information for future queries
        self.contextual_reranker.update_session_context(query, final_results)
        
        explanation_metadata = {
            'strategies_used': list(self.strategy_weights.keys()),
            'strategy_weights': self.strategy_weights,
            'feature_explanations': feature_explanations,
            'total_candidates': len(results),
            'reranked_candidates': len(final_results)
        }
        
        return final_results, explanation_metadata
    
    def _combine_rankings(self, strategy_results: List[Tuple[List[SearchResult], float]]) -> List[SearchResult]:
        """Combine rankings from multiple strategies."""
        if not strategy_results:
            return []
        
        # Create mapping from document ID to results from each strategy
        result_map = defaultdict(list)
        
        for results, weight in strategy_results:
            for result in results:
                result_map[result.document.id].append((result, weight))
        
        # Calculate combined scores
        combined_results = []
        
        for doc_id, result_weight_pairs in result_map.items():
            if not result_weight_pairs:
                continue
            
            # Use the first result as template
            base_result = result_weight_pairs[0][0]
            
            # Calculate weighted average score
            total_weighted_score = 0.0
            total_weight = 0.0
            
            for result, weight in result_weight_pairs:
                total_weighted_score += result.final_score * weight
                total_weight += weight
            
            combined_score = total_weighted_score / total_weight if total_weight > 0 else 0.0
            
            # Create combined result
            combined_result = SearchResult(
                document=base_result.document,
                similarity_score=base_result.similarity_score,
                keyword_score=base_result.keyword_score,
                final_score=combined_score,
                rank=0,  # Will be set after sorting
                embedding_model_used=base_result.embedding_model_used,
                matched_content=base_result.matched_content,
                match_explanation=f"Ensemble score: {combined_score:.3f}"
            )
            
            combined_results.append(combined_result)
        
        # Sort by combined score and update ranks
        combined_results.sort(key=lambda x: x.final_score, reverse=True)
        for i, result in enumerate(combined_results):
            result.rank = i + 1
        
        return combined_results