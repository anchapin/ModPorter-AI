"""
Query expansion system for improving search recall and precision.

This module implements various query expansion techniques to enhance search
queries with additional context and related terms before processing.
"""

import logging
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass
from enum import Enum
import re
from collections import defaultdict, Counter

from schemas.multimodal_schema import SearchQuery

logger = logging.getLogger(__name__)


class ExpansionStrategy(str, Enum):
    """Query expansion strategies available."""
    SYNONYM_EXPANSION = "synonym_expansion"
    CONTEXTUAL_EXPANSION = "contextual_expansion"
    DOMAIN_EXPANSION = "domain_expansion"
    SEMANTIC_EXPANSION = "semantic_expansion"
    HISTORICAL_EXPANSION = "historical_expansion"


@dataclass
class ExpansionTerm:
    """Term added during query expansion with metadata."""
    term: str
    expansion_type: ExpansionStrategy
    confidence: float
    source: str
    weight: float = 1.0


@dataclass
class ExpandedQuery:
    """Query after expansion with metadata."""
    original_query: str
    expanded_query: str
    expansion_terms: List[ExpansionTerm]
    expansion_confidence: float
    expansion_metadata: Dict[str, Any]


class MinecraftDomainExpander:
    """
    Domain-specific query expander for Minecraft modding.
    
    This expander understands Minecraft-specific terminology and concepts
    to add relevant domain terms to queries.
    """
    
    def __init__(self):
        self.domain_knowledge = self._load_domain_knowledge()
        self.concept_hierarchy = self._build_concept_hierarchy()
        self.version_mappings = self._load_version_mappings()
    
    def _load_domain_knowledge(self) -> Dict[str, Dict[str, Any]]:
        """Load Minecraft domain knowledge base."""
        return {
            'blocks': {
                'synonyms': ['block', 'blocks', 'tile', 'cube'],
                'related': ['material', 'hardness', 'tool', 'drop', 'state'],
                'concepts': ['placement', 'breaking', 'interaction', 'properties'],
                'examples': ['stone', 'wood', 'dirt', 'iron_ore', 'diamond_block']
            },
            'items': {
                'synonyms': ['item', 'items', 'object', 'thing'],
                'related': ['inventory', 'stack', 'durability', 'enchantment'],
                'concepts': ['crafting', 'usage', 'obtaining', 'properties'],
                'examples': ['sword', 'pickaxe', 'food', 'potion', 'book']
            },
            'entities': {
                'synonyms': ['entity', 'entities', 'mob', 'mobs', 'creature'],
                'related': ['ai', 'behavior', 'spawn', 'health', 'drops'],
                'concepts': ['movement', 'combat', 'interaction', 'breeding'],
                'examples': ['zombie', 'villager', 'cow', 'dragon', 'player']
            },
            'recipes': {
                'synonyms': ['recipe', 'recipes', 'crafting', 'craft'],
                'related': ['ingredients', 'pattern', 'result', 'shapeless'],
                'concepts': ['crafting_table', 'furnace', 'brewing', 'smithing'],
                'examples': ['shaped_recipe', 'smelting_recipe', 'brewing_recipe']
            },
            'world_generation': {
                'synonyms': ['worldgen', 'generation', 'terrain'],
                'related': ['biome', 'structure', 'ore', 'feature'],
                'concepts': ['noise', 'placement', 'decoration', 'population'],
                'examples': ['village', 'dungeon', 'ore_vein', 'tree', 'lake']
            },
            'redstone': {
                'synonyms': ['redstone', 'circuit', 'wiring', 'automation'],
                'related': ['power', 'signal', 'component', 'logic'],
                'concepts': ['activation', 'transmission', 'gates', 'timing'],
                'examples': ['repeater', 'comparator', 'piston', 'dispenser']
            },
            'modding': {
                'synonyms': ['mod', 'mods', 'modification', 'addon'],
                'related': ['forge', 'fabric', 'api', 'library', 'framework'],
                'concepts': ['loading', 'compatibility', 'dependencies', 'events'],
                'examples': ['mod_loader', 'mixins', 'asm', 'coremod']
            }
        }
    
    def _build_concept_hierarchy(self) -> Dict[str, List[str]]:
        """Build hierarchical relationships between concepts."""
        return {
            'gameplay': ['blocks', 'items', 'entities', 'recipes', 'combat'],
            'technical': ['modding', 'redstone', 'world_generation', 'performance'],
            'content': ['blocks', 'items', 'entities', 'structures', 'biomes'],
            'systems': ['crafting', 'enchanting', 'brewing', 'trading', 'experience']
        }
    
    def _load_version_mappings(self) -> Dict[str, List[str]]:
        """Load version-specific terminology mappings."""
        return {
            '1.19': ['caves_and_cliffs', 'deep_dark', 'warden', 'sculk'],
            '1.20': ['trails_and_tales', 'archaeology', 'sniffer', 'cherry'],
            'bedrock': ['behavior_packs', 'resource_packs', 'mcaddon', 'script_api'],
            'forge': ['mod_bus', 'event_handler', 'capability', 'registry'],
            'fabric': ['mixin', 'fabric_api', 'mod_initializer', 'entry_point']
        }
    
    def expand_domain_terms(self, query: str, context: Dict[str, Any] = None) -> List[ExpansionTerm]:
        """
        Expand query with domain-specific terms.
        
        Args:
            query: Original query text
            context: Additional context information
            
        Returns:
            List of expansion terms with metadata
        """
        expansion_terms = []
        query_lower = query.lower()
        context = context or {}
        
        # Detect domain concepts in query
        detected_concepts = []
        for concept, data in self.domain_knowledge.items():
            if any(synonym in query_lower for synonym in data['synonyms']):
                detected_concepts.append(concept)
        
        # Add related terms for detected concepts
        for concept in detected_concepts:
            concept_data = self.domain_knowledge[concept]
            
            # Add related terms
            for related_term in concept_data['related']:
                if related_term.lower() not in query_lower:
                    expansion_terms.append(ExpansionTerm(
                        term=related_term,
                        expansion_type=ExpansionStrategy.DOMAIN_EXPANSION,
                        confidence=0.8,
                        source=f"domain_concept:{concept}",
                        weight=0.7
                    ))
            
            # Add concept terms
            for concept_term in concept_data['concepts']:
                if concept_term.lower() not in query_lower:
                    expansion_terms.append(ExpansionTerm(
                        term=concept_term,
                        expansion_type=ExpansionStrategy.DOMAIN_EXPANSION,
                        confidence=0.7,
                        source=f"domain_concept:{concept}",
                        weight=0.6
                    ))
        
        # Add version-specific terms if context available
        target_version = context.get('minecraft_version') or context.get('mod_loader')
        if target_version and target_version in self.version_mappings:
            for version_term in self.version_mappings[target_version]:
                if version_term.lower() not in query_lower:
                    expansion_terms.append(ExpansionTerm(
                        term=version_term,
                        expansion_type=ExpansionStrategy.DOMAIN_EXPANSION,
                        confidence=0.9,
                        source=f"version:{target_version}",
                        weight=0.8
                    ))
        
        # Add hierarchical terms
        for parent_concept, child_concepts in self.concept_hierarchy.items():
            if any(child in detected_concepts for child in child_concepts):
                if parent_concept.lower() not in query_lower:
                    expansion_terms.append(ExpansionTerm(
                        term=parent_concept,
                        expansion_type=ExpansionStrategy.DOMAIN_EXPANSION,
                        confidence=0.6,
                        source="concept_hierarchy",
                        weight=0.5
                    ))
        
        logger.info(f"Domain expansion added {len(expansion_terms)} terms for concepts: {detected_concepts}")
        return expansion_terms


class SynonymExpander:
    """
    Synonym-based query expander.
    
    This expander adds synonyms and alternative terms to improve
    query coverage and recall.
    """
    
    def __init__(self):
        self.synonym_database = self._load_synonyms()
        self.programming_terms = self._load_programming_synonyms()
        self.common_expansions = self._load_common_expansions()
    
    def _load_synonyms(self) -> Dict[str, List[str]]:
        """Load general synonym database."""
        return {
            'create': ['make', 'build', 'generate', 'construct', 'develop'],
            'implement': ['create', 'build', 'develop', 'code', 'write'],
            'fix': ['repair', 'solve', 'correct', 'debug', 'resolve'],
            'error': ['bug', 'issue', 'problem', 'exception', 'failure'],
            'guide': ['tutorial', 'howto', 'instructions', 'walkthrough'],
            'example': ['sample', 'demo', 'illustration', 'case', 'instance'],
            'simple': ['basic', 'easy', 'elementary', 'straightforward'],
            'advanced': ['complex', 'sophisticated', 'detailed', 'comprehensive'],
            'quick': ['fast', 'rapid', 'swift', 'speedy', 'brief'],
            'complete': ['full', 'comprehensive', 'thorough', 'entire'],
            'custom': ['personalized', 'tailored', 'bespoke', 'specialized'],
            'optimize': ['improve', 'enhance', 'streamline', 'efficient']
        }
    
    def _load_programming_synonyms(self) -> Dict[str, List[str]]:
        """Load programming-specific synonyms."""
        return {
            'function': ['method', 'procedure', 'routine', 'subroutine'],
            'variable': ['var', 'field', 'property', 'attribute'],
            'class': ['object', 'type', 'entity', 'model'],
            'interface': ['contract', 'protocol', 'api', 'specification'],
            'library': ['framework', 'package', 'module', 'dependency'],
            'import': ['include', 'require', 'load', 'reference'],
            'export': ['expose', 'provide', 'publish', 'output'],
            'initialize': ['init', 'setup', 'create', 'instantiate'],
            'parameter': ['argument', 'input', 'param', 'value'],
            'return': ['output', 'result', 'response', 'yield']
        }
    
    def _load_common_expansions(self) -> Dict[str, List[str]]:
        """Load common query expansion patterns."""
        return {
            'how_to_patterns': {
                'triggers': ['how', 'howto', 'how to'],
                'expansions': ['tutorial', 'guide', 'instructions', 'steps', 'walkthrough']
            },
            'what_is_patterns': {
                'triggers': ['what is', 'what are', 'define', 'definition'],
                'expansions': ['explanation', 'meaning', 'concept', 'overview', 'introduction']
            },
            'example_patterns': {
                'triggers': ['example', 'examples', 'sample'],
                'expansions': ['demo', 'illustration', 'case study', 'use case', 'instance']
            },
            'troubleshooting_patterns': {
                'triggers': ['error', 'problem', 'issue', 'bug', 'not working'],
                'expansions': ['fix', 'solve', 'debug', 'troubleshoot', 'resolution']
            }
        }
    
    def expand_synonyms(self, query: str) -> List[ExpansionTerm]:
        """
        Expand query with synonyms.
        
        Args:
            query: Original query text
            
        Returns:
            List of synonym expansion terms
        """
        expansion_terms = []
        query_words = query.lower().split()
        
        # Expand individual words
        for word in query_words:
            # Check general synonyms
            if word in self.synonym_database:
                for synonym in self.synonym_database[word]:
                    if synonym not in query.lower():
                        expansion_terms.append(ExpansionTerm(
                            term=synonym,
                            expansion_type=ExpansionStrategy.SYNONYM_EXPANSION,
                            confidence=0.8,
                            source=f"synonym:{word}",
                            weight=0.7
                        ))
            
            # Check programming synonyms
            if word in self.programming_terms:
                for synonym in self.programming_terms[word]:
                    if synonym not in query.lower():
                        expansion_terms.append(ExpansionTerm(
                            term=synonym,
                            expansion_type=ExpansionStrategy.SYNONYM_EXPANSION,
                            confidence=0.9,
                            source=f"programming_synonym:{word}",
                            weight=0.8
                        ))
        
        # Expand common patterns
        query_lower = query.lower()
        for pattern_name, pattern_data in self.common_expansions.items():
            if any(trigger in query_lower for trigger in pattern_data['triggers']):
                for expansion in pattern_data['expansions']:
                    if expansion not in query_lower:
                        expansion_terms.append(ExpansionTerm(
                            term=expansion,
                            expansion_type=ExpansionStrategy.SYNONYM_EXPANSION,
                            confidence=0.7,
                            source=f"pattern:{pattern_name}",
                            weight=0.6
                        ))
        
        logger.info(f"Synonym expansion added {len(expansion_terms)} terms")
        return expansion_terms


class ContextualExpander:
    """
    Contextual query expander that uses session and user context.
    
    This expander adds terms based on previous queries, user preferences,
    and session context to personalize search results.
    """
    
    def __init__(self):
        self.session_context = {}
        self.user_profiles = {}
        self.query_history = defaultdict(list)
    
    def update_context(self, query: SearchQuery, session_id: str = 'default'):
        """Update contextual information."""
        if session_id not in self.session_context:
            self.session_context[session_id] = {
                'recent_queries': [],
                'topics': Counter(),
                'content_types': Counter(),
                'complexity_level': 'medium'
            }
        
        context = self.session_context[session_id]
        
        # Add to recent queries
        context['recent_queries'].append(query.query_text)
        context['recent_queries'] = context['recent_queries'][-10:]  # Keep last 10
        
        # Update topic interests
        topics = self._extract_topics(query.query_text)
        for topic in topics:
            context['topics'][topic] += 1
        
        # Update content type preferences
        if query.content_types:
            for content_type in query.content_types:
                context['content_types'][content_type] += 1
        
        # Update complexity level based on query
        complexity = self._assess_query_complexity(query.query_text)
        if complexity != context['complexity_level']:
            context['complexity_level'] = complexity
    
    def expand_contextually(
        self, 
        query: str, 
        session_id: str = 'default',
        user_id: str = None
    ) -> List[ExpansionTerm]:
        """
        Expand query based on contextual information.
        
        Args:
            query: Original query text
            session_id: Session identifier
            user_id: User identifier (optional)
            
        Returns:
            List of contextual expansion terms
        """
        expansion_terms = []
        
        # Get session context
        context = self.session_context.get(session_id, {})
        
        # Add terms from recent topics
        topic_interests = context.get('topics', Counter())
        for topic, frequency in topic_interests.most_common(5):
            if topic.lower() not in query.lower() and frequency > 1:
                confidence = min(0.5 + (frequency * 0.1), 0.9)
                expansion_terms.append(ExpansionTerm(
                    term=topic,
                    expansion_type=ExpansionStrategy.CONTEXTUAL_EXPANSION,
                    confidence=confidence,
                    source=f"session_topic:frequency_{frequency}",
                    weight=0.5
                ))
        
        # Add terms from similar previous queries
        recent_queries = context.get('recent_queries', [])
        for prev_query in recent_queries[-5:]:
            similarity = self._calculate_query_similarity(query, prev_query)
            if similarity > 0.6:
                prev_terms = set(prev_query.lower().split()) - set(query.lower().split())
                for term in list(prev_terms)[:3]:  # Add up to 3 terms
                    expansion_terms.append(ExpansionTerm(
                        term=term,
                        expansion_type=ExpansionStrategy.CONTEXTUAL_EXPANSION,
                        confidence=similarity,
                        source=f"similar_query:similarity_{similarity:.2f}",
                        weight=0.4
                    ))
        
        # Add complexity-appropriate terms
        complexity_level = context.get('complexity_level', 'medium')
        complexity_terms = self._get_complexity_terms(complexity_level)
        for term in complexity_terms:
            if term.lower() not in query.lower():
                expansion_terms.append(ExpansionTerm(
                    term=term,
                    expansion_type=ExpansionStrategy.CONTEXTUAL_EXPANSION,
                    confidence=0.6,
                    source=f"complexity_level:{complexity_level}",
                    weight=0.3
                ))
        
        # Add user profile terms if available
        if user_id and user_id in self.user_profiles:
            profile_terms = self._get_user_profile_terms(user_id, query)
            expansion_terms.extend(profile_terms)
        
        logger.info(f"Contextual expansion added {len(expansion_terms)} terms for session {session_id}")
        return expansion_terms
    
    def _extract_topics(self, query: str) -> List[str]:
        """Extract topics from query text."""
        # Simplified topic extraction
        minecraft_topics = {
            'blocks', 'items', 'entities', 'recipes', 'crafting', 'redstone',
            'modding', 'forge', 'fabric', 'java', 'bedrock', 'biomes',
            'structures', 'world_generation', 'automation', 'building'
        }
        
        query_lower = query.lower()
        detected_topics = []
        
        for topic in minecraft_topics:
            if topic in query_lower:
                detected_topics.append(topic)
        
        return detected_topics
    
    def _assess_query_complexity(self, query: str) -> str:
        """Assess the complexity level of a query."""
        complexity_indicators = {
            'simple': ['how', 'what', 'simple', 'basic', 'easy'],
            'advanced': ['advanced', 'complex', 'detailed', 'comprehensive', 'optimize'],
            'technical': ['implement', 'algorithm', 'performance', 'architecture', 'design']
        }
        
        query_lower = query.lower()
        
        for level, indicators in complexity_indicators.items():
            if any(indicator in query_lower for indicator in indicators):
                return level
        
        # Default to medium if no specific indicators
        return 'medium'
    
    def _get_complexity_terms(self, complexity_level: str) -> List[str]:
        """Get terms appropriate for the complexity level."""
        complexity_terms = {
            'simple': ['basic', 'easy', 'beginner', 'introduction', 'getting started'],
            'medium': ['tutorial', 'guide', 'example', 'walkthrough'],
            'advanced': ['advanced', 'detailed', 'comprehensive', 'optimization', 'best practices'],
            'technical': ['implementation', 'architecture', 'design patterns', 'performance', 'scalability']
        }
        
        return complexity_terms.get(complexity_level, [])
    
    def _calculate_query_similarity(self, query1: str, query2: str) -> float:
        """Calculate similarity between two queries."""
        words1 = set(query1.lower().split())
        words2 = set(query2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0
    
    def _get_user_profile_terms(self, user_id: str, query: str) -> List[ExpansionTerm]:
        """Get expansion terms from user profile."""
        profile = self.user_profiles.get(user_id, {})
        expansion_terms = []
        
        # Add terms from user's favorite topics
        favorite_topics = profile.get('favorite_topics', [])
        for topic in favorite_topics:
            if topic.lower() not in query.lower():
                expansion_terms.append(ExpansionTerm(
                    term=topic,
                    expansion_type=ExpansionStrategy.CONTEXTUAL_EXPANSION,
                    confidence=0.7,
                    source=f"user_profile:favorite_topic",
                    weight=0.6
                ))
        
        return expansion_terms


class QueryExpansionEngine:
    """
    Main query expansion engine that coordinates different expansion strategies.
    
    This engine combines multiple expansion approaches to create enhanced
    queries that improve search recall and precision.
    """
    
    def __init__(self):
        self.domain_expander = MinecraftDomainExpander()
        self.synonym_expander = SynonymExpander()
        self.contextual_expander = ContextualExpander()
        
        self.expansion_strategies = {
            ExpansionStrategy.DOMAIN_EXPANSION: self.domain_expander.expand_domain_terms,
            ExpansionStrategy.SYNONYM_EXPANSION: self.synonym_expander.expand_synonyms,
            ExpansionStrategy.CONTEXTUAL_EXPANSION: self.contextual_expander.expand_contextually
        }
    
    def expand_query(
        self,
        query: SearchQuery,
        strategies: List[ExpansionStrategy] = None,
        max_expansion_terms: int = 10,
        session_context: Dict[str, Any] = None
    ) -> ExpandedQuery:
        """
        Expand a search query using specified strategies.
        
        Args:
            query: Original search query
            strategies: List of expansion strategies to use
            max_expansion_terms: Maximum number of terms to add
            session_context: Session context for contextual expansion
            
        Returns:
            Expanded query with metadata
        """
        if strategies is None:
            strategies = [
                ExpansionStrategy.DOMAIN_EXPANSION,
                ExpansionStrategy.SYNONYM_EXPANSION,
                ExpansionStrategy.CONTEXTUAL_EXPANSION
            ]
        
        logger.info(f"Expanding query '{query.query_text}' using strategies: {strategies}")
        
        all_expansion_terms = []
        expansion_metadata = {
            'original_length': len(query.query_text.split()),
            'strategies_used': strategies,
            'strategy_results': {}
        }
        
        # Apply each expansion strategy
        for strategy in strategies:
            try:
                if strategy == ExpansionStrategy.DOMAIN_EXPANSION:
                    context = session_context or {}
                    terms = self.domain_expander.expand_domain_terms(query.query_text, context)
                elif strategy == ExpansionStrategy.SYNONYM_EXPANSION:
                    terms = self.synonym_expander.expand_synonyms(query.query_text)
                elif strategy == ExpansionStrategy.CONTEXTUAL_EXPANSION:
                    session_id = session_context.get('session_id', 'default') if session_context else 'default'
                    user_id = session_context.get('user_id') if session_context else None
                    terms = self.contextual_expander.expand_contextually(
                        query.query_text, session_id, user_id
                    )
                else:
                    terms = []
                
                all_expansion_terms.extend(terms)
                expansion_metadata['strategy_results'][strategy] = {
                    'terms_added': len(terms),
                    'avg_confidence': sum(t.confidence for t in terms) / len(terms) if terms else 0.0
                }
                
            except Exception as e:
                logger.warning(f"Error in expansion strategy {strategy}: {e}")
                expansion_metadata['strategy_results'][strategy] = {
                    'terms_added': 0,
                    'error': str(e)
                }
        
        # Remove duplicates and sort by confidence * weight
        unique_terms = {}
        for term in all_expansion_terms:
            term_key = term.term.lower()
            if term_key not in unique_terms or (term.confidence * term.weight) > (unique_terms[term_key].confidence * unique_terms[term_key].weight):
                unique_terms[term_key] = term
        
        # Sort and limit expansion terms
        sorted_terms = sorted(
            unique_terms.values(),
            key=lambda t: t.confidence * t.weight,
            reverse=True
        )
        final_expansion_terms = sorted_terms[:max_expansion_terms]
        
        # Build expanded query
        expansion_text_parts = [term.term for term in final_expansion_terms]
        expanded_query_text = query.query_text
        
        if expansion_text_parts:
            expanded_query_text += " " + " ".join(expansion_text_parts)
        
        # Calculate overall expansion confidence
        expansion_confidence = (
            sum(term.confidence * term.weight for term in final_expansion_terms) /
            sum(term.weight for term in final_expansion_terms)
        ) if final_expansion_terms else 0.0
        
        # Update metadata
        expansion_metadata.update({
            'total_candidate_terms': len(all_expansion_terms),
            'unique_candidate_terms': len(unique_terms),
            'final_expansion_terms': len(final_expansion_terms),
            'expanded_length': len(expanded_query_text.split()),
            'expansion_ratio': len(expanded_query_text.split()) / len(query.query_text.split()),
            'avg_term_confidence': expansion_confidence
        })
        
        # Update contextual information for future queries
        if session_context:
            session_id = session_context.get('session_id', 'default')
            self.contextual_expander.update_context(query, session_id)
        
        expanded_query = ExpandedQuery(
            original_query=query.query_text,
            expanded_query=expanded_query_text,
            expansion_terms=final_expansion_terms,
            expansion_confidence=expansion_confidence,
            expansion_metadata=expansion_metadata
        )
        
        logger.info(f"Query expansion completed: {len(query.query_text.split())} -> {len(expanded_query_text.split())} terms")
        
        return expanded_query
    
    def get_expansion_explanation(self, expanded_query: ExpandedQuery) -> str:
        """Generate human-readable explanation of query expansion."""
        metadata = expanded_query.expansion_metadata
        
        explanation_parts = [
            f"Original query: '{expanded_query.original_query}'",
            f"Expanded to {metadata['expanded_length']} terms ({metadata['expansion_ratio']:.1f}x longer)"
        ]
        
        # Add strategy results
        for strategy, results in metadata['strategy_results'].items():
            if 'error' not in results:
                explanation_parts.append(
                    f"{strategy}: added {results['terms_added']} terms "
                    f"(avg confidence: {results['avg_confidence']:.2f})"
                )
        
        # Add top expansion terms
        if expanded_query.expansion_terms:
            top_terms = expanded_query.expansion_terms[:5]
            term_descriptions = [
                f"{term.term} ({term.expansion_type}, {term.confidence:.2f})"
                for term in top_terms
            ]
            explanation_parts.append(f"Top expansion terms: {', '.join(term_descriptions)}")
        
        return "; ".join(explanation_parts)
    
    def analyze_expansion_effectiveness(
        self,
        expanded_query: ExpandedQuery,
        search_results_count: int,
        user_satisfaction: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Analyze the effectiveness of query expansion.
        
        Args:
            expanded_query: The expanded query
            search_results_count: Number of results returned
            user_satisfaction: Optional user satisfaction score (0-1)
            
        Returns:
            Analysis results
        """
        metadata = expanded_query.expansion_metadata
        
        analysis = {
            'expansion_effectiveness': {
                'results_increase': search_results_count > 0,
                'expansion_confidence': expanded_query.expansion_confidence,
                'term_diversity': len(set(term.expansion_type for term in expanded_query.expansion_terms)),
                'strategy_balance': self._calculate_strategy_balance(expanded_query.expansion_terms)
            },
            'recommendations': []
        }
        
        # Add recommendations based on analysis
        if expanded_query.expansion_confidence < 0.5:
            analysis['recommendations'].append("Consider using more conservative expansion strategies")
        
        if metadata['expansion_ratio'] > 3.0:
            analysis['recommendations'].append("Query expansion may be too aggressive")
        
        if search_results_count == 0:
            analysis['recommendations'].append("Try alternative expansion strategies or reduce expansion scope")
        
        if user_satisfaction is not None:
            analysis['user_satisfaction'] = user_satisfaction
            if user_satisfaction < 0.6:
                analysis['recommendations'].append("User satisfaction low - review expansion strategy effectiveness")
        
        return analysis
    
    def _calculate_strategy_balance(self, expansion_terms: List[ExpansionTerm]) -> Dict[str, float]:
        """Calculate balance between different expansion strategies."""
        if not expansion_terms:
            return {}
        
        strategy_counts = Counter(term.expansion_type for term in expansion_terms)
        total_terms = len(expansion_terms)
        
        return {
            strategy: count / total_terms
            for strategy, count in strategy_counts.items()
        }