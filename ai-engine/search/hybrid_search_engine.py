"""
Hybrid search engine combining vector similarity and keyword-based search.

This module implements advanced search capabilities that combine the semantic
understanding of vector embeddings with the precision of keyword matching.
"""

import re
import logging
from typing import List, Dict, Any, Tuple, Set, Optional
from dataclasses import dataclass
from enum import Enum
import numpy as np
from collections import Counter, defaultdict
import math

# Initialize logger first
logger = logging.getLogger(__name__)

# BM25 import with fallback
try:
    from rank_bm25 import BM25Okapi
    BM25_AVAILABLE = True
except ImportError:
    BM25_AVAILABLE = False
    logger.warning("rank_bm25 not installed. BM25 search will not be available.")

from schemas.multimodal_schema import SearchQuery, SearchResult, MultiModalDocument


class SearchMode(str, Enum):
    """Search modes for the hybrid search engine."""

    VECTOR_ONLY = "vector_only"
    KEYWORD_ONLY = "keyword_only"
    HYBRID = "hybrid"
    ADAPTIVE = "adaptive"


class RankingStrategy(str, Enum):
    """Ranking strategies for combining scores."""

    WEIGHTED_SUM = "weighted_sum"
    RECIPROCAL_RANK_FUSION = "reciprocal_rank_fusion"
    BAYESIAN_COMBINATION = "bayesian_combination"
    LEARNED_COMBINATION = "learned_combination"


@dataclass
class SearchCandidate:
    """Candidate document with multiple relevance scores."""

    document: MultiModalDocument
    vector_score: float = 0.0
    keyword_score: float = 0.0
    semantic_score: float = 0.0
    context_score: float = 0.0
    final_score: float = 0.0
    explanation: List[str] = None

    def __post_init__(self):
        if self.explanation is None:
            self.explanation = []


class KeywordSearchEngine:
    """
    Advanced keyword search engine with fuzzy matching and stemming.

    This engine provides sophisticated text matching capabilities including
    fuzzy matching, stemming, and domain-specific term recognition.
    """

    def __init__(self):
        self.stop_words = self._load_stop_words()
        self.minecraft_terms = self._load_minecraft_terms()
        self.programming_terms = self._load_programming_terms()

    def _load_stop_words(self) -> Set[str]:
        """Load common stop words to filter out."""
        return {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "being",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
            "may",
            "might",
            "must",
            "can",
            "this",
            "that",
            "these",
            "those",
        }

    def _load_minecraft_terms(self) -> Dict[str, List[str]]:
        """Load Minecraft-specific terms and their synonyms."""
        return {
            "block": ["blocks", "cube", "tile"],
            "item": ["items", "object", "tool", "weapon"],
            "entity": ["entities", "mob", "mobs", "creature", "npc"],
            "recipe": ["recipes", "crafting", "craft", "make", "create"],
            "texture": ["textures", "skin", "sprite", "image", "visual"],
            "biome": ["biomes", "environment", "terrain", "landscape"],
            "dimension": ["dimensions", "world", "realm", "plane"],
            "redstone": ["circuit", "wiring", "automation", "logic"],
            "forge": ["mod", "modification", "modding", "addon"],
            "bedrock": ["pocket", "mobile", "cross-platform"],
        }

    def _load_programming_terms(self) -> Dict[str, List[str]]:
        """Load programming-specific terms and their synonyms."""
        return {
            "class": ["classes", "object", "type", "definition"],
            "method": ["methods", "function", "procedure", "routine"],
            "variable": ["variables", "var", "field", "property"],
            "import": ["imports", "include", "require", "dependency"],
            "interface": ["interfaces", "contract", "protocol"],
            "abstract": ["abstraction", "base", "template"],
            "static": ["shared", "class-level"],
            "public": ["accessible", "exposed", "visible"],
            "private": ["hidden", "internal", "encapsulated"],
            "constructor": ["init", "initialize", "create", "instantiate"],
        }

    def extract_keywords(self, text: str, include_synonyms: bool = True) -> List[str]:
        """
        Extract and normalize keywords from text.

        Args:
            text: Input text to extract keywords from
            include_synonyms: Whether to include domain-specific synonyms

        Returns:
            List of normalized keywords
        """
        # Convert to lowercase and split into words
        words = re.findall(r"\b\w+\b", text.lower())

        # Filter stop words
        keywords = [word for word in words if word not in self.stop_words and len(word) > 2]

        # Add domain-specific synonyms
        if include_synonyms:
            expanded_keywords = []
            for keyword in keywords:
                expanded_keywords.append(keyword)

                # Add Minecraft synonyms
                for term, synonyms in self.minecraft_terms.items():
                    if keyword == term or keyword in synonyms:
                        expanded_keywords.extend([term] + synonyms)

                # Add programming synonyms
                for term, synonyms in self.programming_terms.items():
                    if keyword == term or keyword in synonyms:
                        expanded_keywords.extend([term] + synonyms)

            keywords = list(set(expanded_keywords))  # Remove duplicates

        return keywords

    def calculate_keyword_similarity(
        self, query_keywords: List[str], document_text: str
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Calculate keyword-based similarity score.

        Args:
            query_keywords: Keywords extracted from the query
            document_text: Text content of the document

        Returns:
            Tuple of (similarity_score, explanation_metadata)
        """
        if not query_keywords or not document_text:
            return 0.0, {}

        doc_keywords = self.extract_keywords(document_text, include_synonyms=False)
        doc_keyword_counts = Counter(doc_keywords)

        # Calculate term frequency-inverse document frequency (TF-IDF) style scoring
        matched_terms = []
        total_score = 0.0

        for query_keyword in query_keywords:
            # Exact match
            if query_keyword in doc_keyword_counts:
                tf = doc_keyword_counts[query_keyword]
                # Simple TF score (could be enhanced with IDF)
                term_score = 1.0 + math.log(tf)
                total_score += term_score
                matched_terms.append(
                    {
                        "term": query_keyword,
                        "frequency": tf,
                        "score": term_score,
                        "match_type": "exact",
                    }
                )
            else:
                # Fuzzy match
                fuzzy_matches = self._find_fuzzy_matches(query_keyword, doc_keywords)
                for match, similarity in fuzzy_matches:
                    if similarity > 0.8:  # High similarity threshold
                        tf = doc_keyword_counts[match]
                        term_score = similarity * (1.0 + math.log(tf))
                        total_score += term_score
                        matched_terms.append(
                            {
                                "term": query_keyword,
                                "matched_term": match,
                                "frequency": tf,
                                "score": term_score,
                                "similarity": similarity,
                                "match_type": "fuzzy",
                            }
                        )

        # Normalize score by query length
        normalized_score = total_score / len(query_keywords) if query_keywords else 0.0

        # Apply length penalty for very short or very long documents
        doc_length_penalty = self._calculate_length_penalty(len(doc_keywords))
        final_score = normalized_score * doc_length_penalty

        explanation = {
            "matched_terms": matched_terms,
            "query_keyword_count": len(query_keywords),
            "doc_keyword_count": len(doc_keywords),
            "total_matches": len(matched_terms),
            "raw_score": total_score,
            "normalized_score": normalized_score,
            "length_penalty": doc_length_penalty,
            "final_score": final_score,
        }

        return min(final_score, 1.0), explanation

    def _find_fuzzy_matches(
        self, query_term: str, doc_keywords: List[str], max_matches: int = 3
    ) -> List[Tuple[str, float]]:
        """Find fuzzy matches for a query term in document keywords."""
        matches = []

        for doc_keyword in doc_keywords:
            similarity = self._calculate_edit_distance_similarity(query_term, doc_keyword)
            if similarity > 0.6:  # Minimum similarity threshold
                matches.append((doc_keyword, similarity))

        # Sort by similarity and return top matches
        matches.sort(key=lambda x: x[1], reverse=True)
        return matches[:max_matches]

    def _calculate_edit_distance_similarity(self, str1: str, str2: str) -> float:
        """Calculate similarity based on edit distance."""
        if str1 == str2:
            return 1.0

        # Simple Levenshtein distance implementation
        len1, len2 = len(str1), len(str2)
        if len1 == 0:
            return 0.0 if len2 > 0 else 1.0
        if len2 == 0:
            return 0.0

        # Create distance matrix
        matrix = [[0] * (len2 + 1) for _ in range(len1 + 1)]

        # Initialize first row and column
        for i in range(len1 + 1):
            matrix[i][0] = i
        for j in range(len2 + 1):
            matrix[0][j] = j

        # Fill the matrix
        for i in range(1, len1 + 1):
            for j in range(1, len2 + 1):
                cost = 0 if str1[i - 1] == str2[j - 1] else 1
                matrix[i][j] = min(
                    matrix[i - 1][j] + 1,  # deletion
                    matrix[i][j - 1] + 1,  # insertion
                    matrix[i - 1][j - 1] + cost,  # substitution
                )

        # Calculate similarity as (1 - normalized_distance)
        max_len = max(len1, len2)
        distance = matrix[len1][len2]
        similarity = 1.0 - (distance / max_len)

        return max(similarity, 0.0)

    def _calculate_length_penalty(self, doc_length: int) -> float:
        """Calculate length penalty to favor documents of appropriate length."""
        # Optimal length range (in terms of keyword count)
        optimal_min, optimal_max = 10, 100

        if optimal_min <= doc_length <= optimal_max:
            return 1.0
        elif doc_length < optimal_min:
            # Penalty for very short documents
            return 0.5 + 0.5 * (doc_length / optimal_min)
        else:
            # Penalty for very long documents
            excess = doc_length - optimal_max
            penalty = 1.0 / (1.0 + 0.01 * excess)
            return max(penalty, 0.3)  # Minimum penalty

    # BM25-specific attributes
    _bm25_index: Optional[Any] = None
    _bm25_documents: List[str] = []

    def build_bm25_index(self, documents: Dict[str, MultiModalDocument]) -> bool:
        """
        Build a BM25 index from documents for keyword search.

        Args:
            documents: Dictionary of document_id to MultiModalDocument

        Returns:
            True if index was built successfully, False otherwise
        """
        if not BM25_AVAILABLE:
            logger.warning("BM25 not available - rank_bm25 not installed")
            return False

        try:
            # Prepare documents for BM25 (tokenized)
            self._bm25_documents = []
            doc_ids = []

            for doc_id, doc in documents.items():
                if doc.content_text:
                    # Tokenize: lowercase and split on whitespace/punctuation
                    tokens = re.findall(r'\b\w+\b', doc.content_text.lower())
                    # Filter out stop words
                    tokens = [t for t in tokens if t not in self.stop_words and len(t) > 1]
                    self._bm25_documents.append(tokens)
                    doc_ids.append(doc_id)

            if not self._bm25_documents:
                logger.warning("No documents with content to index for BM25")
                return False

            # Build BM25 index
            self._bm25_index = BM25Okapi(self._bm25_documents)
            logger.info(f"Built BM25 index with {len(self._bm25_documents)} documents")
            return True

        except Exception as e:
            logger.error(f"Failed to build BM25 index: {e}")
            return False

    def search_bm25(
        self,
        query: str,
        documents: Dict[str, MultiModalDocument],
        top_k: int = 10,
    ) -> List[Tuple[str, float]]:
        """
        Search documents using BM25 algorithm.

        Args:
            query: Search query text
            documents: Dictionary of document_id to MultiModalDocument
            top_k: Number of top results to return

        Returns:
            List of (document_id, bm25_score) tuples
        """
        if not BM25_AVAILABLE or self._bm25_index is None:
            # Fall back to simple keyword search
            query_keywords = self.extract_keywords(query)
            results = []
            for doc_id, doc in documents.items():
                if doc.content_text:
                    score, _ = self.calculate_keyword_similarity(query_keywords, doc.content_text)
                    results.append((doc_id, score))
            results.sort(key=lambda x: x[1], reverse=True)
            return results[:top_k]

        try:
            # Tokenize query
            query_tokens = re.findall(r'\b\w+\b', query.lower())
            query_tokens = [t for t in query_tokens if t not in self.stop_words and len(t) > 1]

            if not query_tokens:
                return []

            # Get BM25 scores
            scores = self._bm25_index.get_scores(query_tokens)

            # Map scores back to document IDs
            doc_ids = list(documents.keys())
            results = []
            for i, score in enumerate(scores):
                if i < len(doc_ids):
                    results.append((doc_ids[i], score))

            # Normalize scores to 0-1 range
            if results:
                max_score = max(s for _, s in results)
                if max_score > 0:
                    results = [(doc_id, score / max_score) for doc_id, score in results]

            # Sort by score and return top_k
            results.sort(key=lambda x: x[1], reverse=True)
            return results[:top_k]

        except Exception as e:
            logger.error(f"BM25 search failed: {e}")
            # Fall back to simple keyword search
            query_keywords = self.extract_keywords(query)
            results = []
            for doc_id, doc in documents.items():
                if doc.content_text:
                    score, _ = self.calculate_keyword_similarity(query_keywords, doc.content_text)
                    results.append((doc_id, score))
            results.sort(key=lambda x: x[1], reverse=True)
            return results[:top_k]


class HybridSearchEngine:
    """
    Main hybrid search engine that combines vector and keyword search.

    This engine provides sophisticated search capabilities by combining
    semantic vector similarity with keyword-based relevance scoring.
    """

    def __init__(self):
        self.keyword_engine = KeywordSearchEngine()
        self.ranking_strategies = {
            RankingStrategy.WEIGHTED_SUM: self._weighted_sum_ranking,
            RankingStrategy.RECIPROCAL_RANK_FUSION: self._reciprocal_rank_fusion,
            RankingStrategy.BAYESIAN_COMBINATION: self._bayesian_combination,
        }
        self._bm25_built = False

    def build_index(self, documents: Dict[str, MultiModalDocument]) -> bool:
        """
        Build search indexes for the documents.

        Args:
            documents: Dictionary of document_id to MultiModalDocument

        Returns:
            True if index was built successfully
        """
        # Build BM25 index for keyword search
        if BM25_AVAILABLE:
            self._bm25_built = self.keyword_engine.build_bm25_index(documents)
            if self._bm25_built:
                logger.info("BM25 index built successfully")
            else:
                logger.warning("Failed to build BM25 index, will use basic keyword search")
        else:
            logger.info("BM25 not available, using basic keyword search")
            self._bm25_built = False

        return True

    async def search(
        self,
        query: SearchQuery,
        documents: Dict[str, MultiModalDocument],
        embeddings: Dict[str, List],  # Document embeddings
        query_embedding: List[float],
        search_mode: SearchMode = SearchMode.HYBRID,
        ranking_strategy: RankingStrategy = RankingStrategy.WEIGHTED_SUM,
    ) -> List[SearchResult]:
        """
        Perform hybrid search across documents.

        Args:
            query: Search query with parameters
            documents: Available documents to search
            embeddings: Document embeddings
            query_embedding: Query embedding vector
            search_mode: Search mode to use
            ranking_strategy: Ranking strategy for combining scores

        Returns:
            Ranked list of search results
        """
        logger.info(f"Performing {search_mode} search for: {query.query_text}")

        # Auto-build BM25 index if needed and keyword search is requested
        if search_mode in [SearchMode.KEYWORD_ONLY, SearchMode.HYBRID, SearchMode.ADAPTIVE]:
            if not self._bm25_built and BM25_AVAILABLE:
                logger.info("Building BM25 index on first search...")
                self.build_index(documents)

        candidates = []
        query_keywords = self.keyword_engine.extract_keywords(query.query_text)

        for doc_id, document in documents.items():
            # Apply filters
            if not self._passes_filters(document, query):
                continue

            candidate = SearchCandidate(document=document)

            # Calculate vector similarity if embeddings available
            if search_mode in [SearchMode.VECTOR_ONLY, SearchMode.HYBRID, SearchMode.ADAPTIVE]:
                doc_embeddings = embeddings.get(doc_id, [])
                if doc_embeddings and query_embedding:
                    candidate.vector_score = self._calculate_vector_similarity(
                        query_embedding, doc_embeddings
                    )
                    candidate.explanation.append(f"Vector similarity: {candidate.vector_score:.3f}")

            # Calculate keyword similarity (use BM25 if available, otherwise use basic keyword matching)
            if search_mode in [SearchMode.KEYWORD_ONLY, SearchMode.HYBRID, SearchMode.ADAPTIVE]:
                if document.content_text:
                    # Try BM25 first if index is built
                    if self.keyword_engine._bm25_index is not None and BM25_AVAILABLE:
                        bm25_results = self.keyword_engine.search_bm25(
                            query.query_text, documents, top_k=len(documents)
                        )
                        # Get score for this document
                        doc_bm25_score = 0.0
                        for result_doc_id, score in bm25_results:
                            if result_doc_id == doc_id:
                                doc_bm25_score = score
                                break
                        candidate.keyword_score = doc_bm25_score
                        candidate.explanation.append(f"BM25 score: {doc_bm25_score:.3f}")
                    else:
                        # Fall back to basic keyword similarity
                        keyword_score, keyword_explanation = (
                            self.keyword_engine.calculate_keyword_similarity(
                                query_keywords, document.content_text
                            )
                        )
                        candidate.keyword_score = keyword_score
                        candidate.explanation.append(f"Keyword similarity: {keyword_score:.3f}")
                        candidate.explanation.append(
                            f"Matched terms: {len(keyword_explanation.get('matched_terms', []))}"
                        )

            # Calculate context-aware score
            candidate.context_score = self._calculate_context_score(document, query)
            if candidate.context_score > 0:
                candidate.explanation.append(f"Context bonus: {candidate.context_score:.3f}")

            candidates.append(candidate)

        # Rank candidates using the specified strategy
        ranked_candidates = self.ranking_strategies[ranking_strategy](
            candidates, query, search_mode
        )

        # Convert to search results
        results = []
        for i, candidate in enumerate(ranked_candidates[: query.top_k]):
            result = SearchResult(
                document=candidate.document,
                similarity_score=candidate.vector_score,
                keyword_score=candidate.keyword_score,
                final_score=candidate.final_score,
                rank=i + 1,
                embedding_model_used="sentence-transformers/all-MiniLM-L6-v2",
                matched_content=candidate.document.content_text[:200]
                if candidate.document.content_text
                else None,
                match_explanation="; ".join(candidate.explanation),
            )
            results.append(result)

        logger.info(f"Returning {len(results)} results")
        return results

    def _passes_filters(self, document: MultiModalDocument, query: SearchQuery) -> bool:
        """Check if document passes the query filters."""
        # Content type filter
        if query.content_types and document.content_type not in query.content_types:
            return False

        # Tags filter
        if query.tags and not any(tag in document.tags for tag in query.tags):
            return False

        # Project context filter
        if query.project_context and document.project_context != query.project_context:
            return False

        # Date range filter (if implemented)
        if query.date_range:
            # Implementation would go here
            pass

        return True

    def _calculate_vector_similarity(
        self, query_embedding: List[float], doc_embeddings: List
    ) -> float:
        """Calculate the best vector similarity score for a document."""
        if not doc_embeddings:
            return 0.0

        max_similarity = 0.0
        query_vector = np.array(query_embedding)

        # Handle case where doc_embeddings is a simple list of floats (not objects)
        # Check if first element is a number (not an object with .embedding attribute)
        if doc_embeddings and not hasattr(doc_embeddings[0], 'embedding') and not hasattr(doc_embeddings[0], 'embedding_vector'):
            # Treat entire list as a single embedding vector
            doc_vector = np.array(doc_embeddings)
            if doc_vector.size > 0 and query_vector.shape[0] == doc_vector.shape[0]:
                dot_product = np.dot(query_vector, doc_vector)
                norm_query = np.linalg.norm(query_vector)
                norm_doc = np.linalg.norm(doc_vector)
                if norm_query > 0 and norm_doc > 0:
                    return dot_product / (norm_query * norm_doc)
            return 0.0

        for embedding_data in doc_embeddings:
            if hasattr(embedding_data, "embedding"):
                doc_vector = np.array(embedding_data.embedding)
            elif hasattr(embedding_data, "embedding_vector"):
                doc_vector = np.array(embedding_data.embedding_vector)
            else:
                doc_vector = np.array(embedding_data)

            # Ensure vectors have the same dimension
            if doc_vector.size == 0 or query_vector.shape[0] != doc_vector.shape[0]:
                continue

            # Calculate cosine similarity
            dot_product = np.dot(query_vector, doc_vector)
            norm_query = np.linalg.norm(query_vector)
            norm_doc = np.linalg.norm(doc_vector)

            if norm_query > 0 and norm_doc > 0:
                similarity = dot_product / (norm_query * norm_doc)
                max_similarity = max(max_similarity, similarity)

        return max_similarity

    def _calculate_context_score(self, document: MultiModalDocument, query: SearchQuery) -> float:
        """Calculate context-aware relevance score."""
        context_score = 0.0

        # Boost score for documents with relevant metadata
        if document.content_metadata:
            metadata = document.content_metadata

            # Check for query context in metadata
            if query.query_context:
                query_context_lower = query.query_context.lower()
                for key, value in metadata.items():
                    if isinstance(value, str) and query_context_lower in value.lower():
                        context_score += 0.1

            # Domain-specific boosts
            if "minecraft_version" in metadata or "mod_loader" in metadata:
                context_score += 0.05  # Minecraft-specific content

            if "class_name" in metadata or "method_name" in metadata:
                context_score += 0.05  # Code-specific content

        # Boost for recent documents (if timestamp available)
        if hasattr(document, "updated_at") and document.updated_at:
            # Recent documents get a small boost
            from datetime import datetime, timedelta

            if document.updated_at > datetime.utcnow() - timedelta(days=30):
                context_score += 0.02

        return min(context_score, 0.3)  # Cap context score

    def _weighted_sum_ranking(
        self, candidates: List[SearchCandidate], query: SearchQuery, search_mode: SearchMode
    ) -> List[SearchCandidate]:
        """Rank candidates using weighted sum of scores."""
        # Default weights
        vector_weight = 0.7
        keyword_weight = 0.3
        context_weight = 0.1

        # Adjust weights based on search mode
        if search_mode == SearchMode.VECTOR_ONLY:
            vector_weight, keyword_weight = 1.0, 0.0
        elif search_mode == SearchMode.KEYWORD_ONLY:
            vector_weight, keyword_weight = 0.0, 1.0
        elif search_mode == SearchMode.ADAPTIVE:
            # Adapt weights based on query characteristics
            query_length = len(query.query_text.split())
            if query_length <= 3:
                # Short queries benefit from keyword matching
                vector_weight, keyword_weight = 0.5, 0.5
            else:
                # Longer queries benefit from semantic understanding
                vector_weight, keyword_weight = 0.8, 0.2

        # Calculate final scores
        for candidate in candidates:
            candidate.final_score = (
                vector_weight * candidate.vector_score
                + keyword_weight * candidate.keyword_score
                + context_weight * candidate.context_score
            )

            candidate.explanation.append(
                f"Final: {candidate.final_score:.3f} = "
                f"{vector_weight}*{candidate.vector_score:.3f} + "
                f"{keyword_weight}*{candidate.keyword_score:.3f} + "
                f"{context_weight}*{candidate.context_score:.3f}"
            )

        # Sort by final score
        candidates.sort(key=lambda x: x.final_score, reverse=True)
        return candidates

    def _reciprocal_rank_fusion(
        self, candidates: List[SearchCandidate], query: SearchQuery, search_mode: SearchMode
    ) -> List[SearchCandidate]:
        """Rank candidates using Reciprocal Rank Fusion."""
        # Create separate rankings for each score type
        vector_ranking = sorted(candidates, key=lambda x: x.vector_score, reverse=True)
        keyword_ranking = sorted(candidates, key=lambda x: x.keyword_score, reverse=True)
        context_ranking = sorted(candidates, key=lambda x: x.context_score, reverse=True)

        # Calculate RRF scores
        k = 60  # RRF parameter
        candidate_scores = defaultdict(float)

        for i, candidate in enumerate(vector_ranking):
            candidate_scores[candidate.document.id] += 1.0 / (k + i + 1)

        for i, candidate in enumerate(keyword_ranking):
            candidate_scores[candidate.document.id] += 1.0 / (k + i + 1)

        for i, candidate in enumerate(context_ranking):
            candidate_scores[candidate.document.id] += 0.5 / (k + i + 1)  # Lower weight for context

        # Assign final scores
        for candidate in candidates:
            candidate.final_score = candidate_scores[candidate.document.id]
            candidate.explanation.append(f"RRF score: {candidate.final_score:.3f}")

        # Sort by RRF score
        candidates.sort(key=lambda x: x.final_score, reverse=True)
        return candidates

    def _bayesian_combination(
        self, candidates: List[SearchCandidate], query: SearchQuery, search_mode: SearchMode
    ) -> List[SearchCandidate]:
        """Rank candidates using Bayesian score combination."""
        # Simple Bayesian-inspired combination
        # P(relevant | scores) ∝ P(scores | relevant) * P(relevant)

        prior_relevance = 0.1  # Prior probability of relevance

        for candidate in candidates:
            # Likelihood of observing these scores given relevance
            vector_likelihood = candidate.vector_score
            keyword_likelihood = candidate.keyword_score
            context_likelihood = candidate.context_score if candidate.context_score > 0 else 0.1

            # Combined likelihood (assuming independence)
            combined_likelihood = vector_likelihood * keyword_likelihood * context_likelihood

            # Posterior probability (unnormalized)
            candidate.final_score = combined_likelihood * prior_relevance
            candidate.explanation.append(f"Bayesian score: {candidate.final_score:.3f}")

        # Sort by posterior probability
        candidates.sort(key=lambda x: x.final_score, reverse=True)
        return candidates


class UnifiedSearchEngine:
    """
    Unified search engine that combines hybrid search with query expansion and reranking.

    This engine provides a complete RAG search pipeline:
    1. Query expansion for better recall
    2. Hybrid search combining vector and keyword search
    3. Cross-encoder reranking for improved precision

    Attributes:
        hybrid_engine: The underlying hybrid search engine
        reranker: Optional reranker for post-processing results
        query_expander: Optional query expander for improving recall
    """

    def __init__(
        self,
        vector_store: Any = None,
        document_index: Any = None,
        reranker: Any = None,
        query_expander: Any = None,
        embedding_model: str = "all-MiniLM-L6-v2",
        search_mode: SearchMode = SearchMode.HYBRID,
        keyword_weight: float = 0.3,
        vector_weight: float = 0.5,
        rerank_top_k: int = 50,
        enable_query_expansion: bool = True,
        enable_reranking: bool = True,
    ):
        """
        Initialize the unified search engine.

        Args:
            vector_store: Vector store for semantic search
            document_index: Document index for keyword search
            reranker: Reranker instance for post-processing results
            query_expander: Query expander for improving recall
            embedding_model: Name of the embedding model to use
            search_mode: Search mode to use (HYBRID, KEYWORD_ONLY, VECTOR_ONLY)
            keyword_weight: Weight for keyword search scores (0-1)
            vector_weight: Weight for vector search scores (0-1)
            rerank_top_k: Number of top results to rerank
            enable_query_expansion: Whether to enable query expansion
            enable_reranking: Whether to enable reranking
        """
        self.hybrid_engine = HybridSearchEngine(
            vector_store=vector_store,
            document_index=document_index,
            embedding_model=embedding_model,
            search_mode=search_mode,
            keyword_weight=keyword_weight,
            vector_weight=vector_weight,
        )

        self.reranker = reranker
        self.query_expander = query_expander
        self.rerank_top_k = rerank_top_k
        self.enable_query_expansion = enable_query_expansion
        self.enable_reranking = enable_reranking

        logger.info(
            f"UnifiedSearchEngine initialized with mode={search_mode}, "
            f"reranking={enable_reranking}, query_expansion={enable_query_expansion}"
        )

    def search(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        top_k: int = 10,
        expand_queries: bool = None,
        rerank_results: bool = None,
        search_mode: SearchMode = None,
    ) -> List[SearchCandidate]:
        """
        Perform unified search with optional query expansion and reranking.

        Args:
            query: The search query string
            filters: Optional filters to apply to search results
            top_k: Number of results to return
            expand_queries: Override for query expansion (default: use instance setting)
            rerank_results: Override for reranking (default: use instance setting)
            search_mode: Override for search mode (default: use instance setting)

        Returns:
            List of search candidates sorted by relevance
        """
        # Determine settings to use
        do_expand = expand_queries if expand_queries is not None else self.enable_query_expansion
        do_rerank = rerank_results if rerank_results is not None else self.enable_reranking
        mode = search_mode if search_mode else self.hybrid_engine.search_mode

        # Step 1: Query expansion
        expanded_queries = [query]
        if do_expand and self.query_expander:
            try:
                expanded = self.query_expander.expand(query)
                expanded_queries = [eq.text for eq in expanded.expanded_terms]
                logger.info(f"Query expanded to: {expanded_queries}")
            except Exception as e:
                logger.warning(f"Query expansion failed: {e}, using original query")
                expanded_queries = [query]

        # Step 2: Hybrid search with expanded queries
        all_candidates = []
        for eq in expanded_queries:
            search_query = SearchQuery(text=eq, filters=filters or {}, mode=mode, top_k=top_k)
            candidates = self.hybrid_engine.search(search_query)
            all_candidates.extend(candidates)

        # Deduplicate and combine candidates from expanded queries
        candidates_dict = {}
        for candidate in all_candidates:
            doc_id = candidate.document.id
            if doc_id not in candidates_dict:
                candidates_dict[doc_id] = candidate
            else:
                # Combine scores
                existing = candidates_dict[doc_id]
                existing.final_score = max(existing.final_score, candidate.final_score)
                existing.explanation.append(f"Combined from: {eq}")

        candidates = list(candidates_dict.values())
        candidates.sort(key=lambda x: x.final_score, reverse=True)

        # Keep only top_k for reranking efficiency
        candidates = candidates[: self.rerank_top_k]

        # Step 3: Reranking
        if do_rerank and self.reranker:
            try:
                # Convert candidates to SearchResult for reranker
                search_results = [
                    SearchResult(
                        document=candidate.document,
                        similarity_score=candidate.vector_score,
                        keyword_score=candidate.keyword_score,
                        final_score=candidate.final_score,
                        rank=i + 1,
                        matched_content=candidate.matched_content,
                        match_explanation="; ".join(candidate.explanation),
                    )
                    for i, candidate in enumerate(candidates)
                ]

                # Perform reranking
                reranked = self.reranker.rerank(query, search_results)

                # Convert back to candidates
                for i, result in enumerate(reranked):
                    if i < len(candidates):
                        candidates[i].final_score = result.final_score
                        candidates[i].rank = result.rank
                        candidates[i].explanation.append(
                            f"Reranked score: {result.final_score:.3f}"
                        )

                # Re-sort by reranked scores
                candidates.sort(key=lambda x: x.final_score, reverse=True)
                logger.info(
                    f"Results reranked, top score: {candidates[0].final_score if candidates else 0}"
                )

            except Exception as e:
                logger.warning(f"Reranking failed: {e}, using original rankings")

        # Return top_k final results
        return candidates[:top_k]

    def set_reranker(self, reranker: Any) -> None:
        """Set or update the reranker."""
        self.reranker = reranker
        logger.info("Reranker updated")

    def set_query_expander(self, query_expander: Any) -> None:
        """Set or update the query expander."""
        self.query_expander = query_expander
        logger.info("Query expander updated")

    def enable_features(self, query_expansion: bool = None, reranking: bool = None) -> None:
        """Enable or disable features dynamically."""
        if query_expansion is not None:
            self.enable_query_expansion = query_expansion
            logger.info(f"Query expansion {'enabled' if query_expansion else 'disabled'}")

        if reranking is not None:
            self.enable_reranking = reranking
            logger.info(f"Reranking {'enabled' if reranking else 'disabled'}")
