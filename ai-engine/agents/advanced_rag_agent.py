"""
Advanced RAG Agent that integrates multi-modal search capabilities.

This agent provides sophisticated retrieval-augmented generation with support
for multi-modal content, hybrid search, query expansion, and result re-ranking.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Union, Tuple
from dataclasses import dataclass
from datetime import datetime
import json

# Import advanced RAG components
from search.hybrid_search_engine import HybridSearchEngine, SearchMode, RankingStrategy
from search.reranking_engine import FeatureBasedReRanker, ContextualReRanker, EnsembleReRanker
from search.query_expansion import QueryExpansionEngine, ExpansionStrategy
from utils.multimodal_embedding_generator import MultiModalEmbeddingGenerator, EmbeddingStrategy
from utils.advanced_chunker import AdvancedChunker
from schemas.multimodal_schema import (
    SearchQuery, SearchResult, MultiModalDocument, 
    ContentType, EmbeddingModel, HybridSearchConfig
)

# Import existing components
from utils.vector_db_client import VectorDBClient
from models.document import Document

logger = logging.getLogger(__name__)


@dataclass
class RAGResponse:
    """Response from the Advanced RAG Agent."""
    answer: str
    sources: List[SearchResult]
    confidence: float
    processing_time_ms: float
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'answer': self.answer,
            'sources': [
                {
                    'document_id': source.document.id,
                    'title': source.document.source_path,
                    'content_preview': source.matched_content,
                    'relevance_score': source.final_score,
                    'rank': source.rank
                }
                for source in self.sources
            ],
            'confidence': self.confidence,
            'processing_time_ms': self.processing_time_ms,
            'metadata': self.metadata
        }


class AdvancedRAGAgent:
    """
    Advanced RAG agent with multi-modal search and intelligent retrieval.
    
    This agent combines multiple advanced techniques to provide high-quality
    retrieval-augmented generation for Minecraft modding queries.
    """
    
    def __init__(
        self,
        vector_db_client: Optional[VectorDBClient] = None,
        enable_query_expansion: bool = True,
        enable_reranking: bool = True,
        enable_multimodal: bool = True
    ):
        """
        Initialize the Advanced RAG Agent.
        
        Args:
            vector_db_client: Vector database client
            enable_query_expansion: Whether to enable query expansion
            enable_reranking: Whether to enable result re-ranking
            enable_multimodal: Whether to enable multi-modal capabilities
        """
        # Core components
        self.vector_db = vector_db_client or VectorDBClient()
        self.hybrid_search = HybridSearchEngine()
        self.embedding_generator = MultiModalEmbeddingGenerator()
        self.chunker = AdvancedChunker()
        
        # Optional components
        self.query_expander = QueryExpansionEngine() if enable_query_expansion else None
        self.reranker = EnsembleReRanker() if enable_reranking else None
        
        # Configuration
        self.enable_multimodal = enable_multimodal
        self.config = {
            'max_sources': 10,
            'min_relevance_threshold': 0.3,
            'answer_max_length': 2000,
            'context_window_size': 4000,
            'confidence_threshold': 0.6
        }
        
        # Internal state
        self.document_cache = {}
        self.embedding_cache = {}
        self.session_contexts = {}
        
        logger.info("Advanced RAG Agent initialized")
    
    async def query(
        self,
        query_text: str,
        content_types: Optional[List[ContentType]] = None,
        project_context: Optional[str] = None,
        session_id: str = 'default',
        **kwargs
    ) -> RAGResponse:
        """
        Process a query and generate an answer with sources.
        
        Args:
            query_text: The user's query
            content_types: Preferred content types to search
            project_context: Project context for filtering
            session_id: Session identifier for context
            **kwargs: Additional parameters
            
        Returns:
            RAG response with answer and sources
        """
        start_time = datetime.utcnow()
        
        try:
            logger.info(f"Processing RAG query: '{query_text[:100]}...'")
            
            # Create search query object
            search_query = SearchQuery(
                query_text=query_text,
                content_types=content_types,
                project_context=project_context,
                top_k=self.config['max_sources'],
                similarity_threshold=self.config['min_relevance_threshold'],
                use_hybrid_search=True,
                enable_reranking=bool(self.reranker),
                expand_query=bool(self.query_expander)
            )
            
            # Step 1: Query expansion (if enabled)
            expanded_query = None
            if self.query_expander:
                session_context = self.session_contexts.get(session_id, {})
                session_context.update({
                    'session_id': session_id,
                    'project_context': project_context
                })
                
                expanded_query = self.query_expander.expand_query(
                    search_query,
                    strategies=[
                        ExpansionStrategy.DOMAIN_EXPANSION,
                        ExpansionStrategy.SYNONYM_EXPANSION,
                        ExpansionStrategy.CONTEXTUAL_EXPANSION
                    ],
                    session_context=session_context
                )
                
                # Update query text with expansion
                search_query.query_text = expanded_query.expanded_query
            
            # Step 2: Retrieve relevant documents
            search_results = await self._retrieve_documents(search_query)
            
            # Step 3: Re-rank results (if enabled)
            reranking_metadata = {}
            if self.reranker and search_results:
                search_results, reranking_metadata = self.reranker.ensemble_rerank(
                    search_query, search_results, session_id
                )
            
            # Step 4: Generate answer from retrieved context
            answer, confidence, generation_metadata = await self._generate_answer(
                query_text, search_results
            )
            
            # Calculate processing time
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            # Compile metadata
            response_metadata = {
                'query_expansion': {
                    'enabled': bool(self.query_expander),
                    'original_query': query_text,
                    'expanded_query': expanded_query.expanded_query if expanded_query else query_text,
                    'expansion_terms_count': len(expanded_query.expansion_terms) if expanded_query else 0,
                    'expansion_confidence': expanded_query.expansion_confidence if expanded_query else 0.0
                },
                'retrieval': {
                    'total_results': len(search_results),
                    'search_mode': 'hybrid',
                    'content_types_searched': content_types or ['all']
                },
                'reranking': {
                    'enabled': bool(self.reranker),
                    **reranking_metadata
                },
                'generation': generation_metadata,
                'session_id': session_id,
                'timestamp': start_time.isoformat()
            }
            
            # Create response
            response = RAGResponse(
                answer=answer,
                sources=search_results[:5],  # Top 5 sources
                confidence=confidence,
                processing_time_ms=processing_time,
                metadata=response_metadata
            )
            
            # Update session context
            self._update_session_context(session_id, search_query, response)
            
            logger.info(f"RAG query completed in {processing_time:.1f}ms with confidence {confidence:.2f}")
            return response
            
        except Exception as e:
            logger.error(f"Error processing RAG query: {e}")
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            # Return error response
            return RAGResponse(
                answer=f"I apologize, but I encountered an error while processing your query: {str(e)}",
                sources=[],
                confidence=0.0,
                processing_time_ms=processing_time,
                metadata={'error': str(e), 'timestamp': start_time.isoformat()}
            )
    
    async def _retrieve_documents(self, query: SearchQuery) -> List[SearchResult]:
        """Retrieve relevant documents using hybrid search."""
        try:
            # Generate query embedding
            query_embedding_result = await self.embedding_generator.generate_embedding(
                query.query_text, EmbeddingStrategy.HYBRID
            )
            
            if not query_embedding_result:
                logger.warning("Failed to generate query embedding, using keyword-only search")
                query_embedding = []
            else:
                query_embedding = query_embedding_result.embedding.tolist()
            
            # Get available documents (in a real implementation, this would query the database)
            documents = await self._get_available_documents(query)
            
            # Get document embeddings
            embeddings = await self._get_document_embeddings(documents)
            
            # Perform hybrid search
            search_results = await self.hybrid_search.search(
                query=query,
                documents=documents,
                embeddings=embeddings,
                query_embedding=query_embedding,
                search_mode=SearchMode.HYBRID,
                ranking_strategy=RankingStrategy.WEIGHTED_SUM
            )
            
            logger.info(f"Retrieved {len(search_results)} documents from hybrid search")
            return search_results
            
        except Exception as e:
            logger.error(f"Error in document retrieval: {e}")
            return []
    
    async def _get_available_documents(self, query: SearchQuery) -> Dict[str, MultiModalDocument]:
        """Get available documents for search (placeholder implementation)."""
        # In a real implementation, this would query the vector database
        # For now, return cached documents or create mock documents
        
        if not self.document_cache:
            # Create some mock documents for demonstration
            self.document_cache = {
                'java_blocks': MultiModalDocument(
                    id='java_blocks',
                    content_hash='mock_hash_1',
                    source_path='docs/java/blocks.md',
                    content_type=ContentType.DOCUMENTATION,
                    content_text='''
                    # Java Blocks in Minecraft Modding
                    
                    Blocks are the fundamental building components of Minecraft worlds. 
                    In Java Edition modding, blocks are defined as classes that extend 
                    the Block base class.
                    
                    ## Creating a Basic Block
                    
                    To create a basic block, you need to:
                    1. Create a class that extends Block
                    2. Define the block properties (material, hardness, etc.)
                    3. Register the block with the game registry
                    
                    Example:
                    ```java
                    public class CopperBlock extends Block {
                        public CopperBlock() {
                            super(Block.Properties.of(Material.METAL)
                                .strength(3.0F, 6.0F)
                                .sound(SoundType.METAL));
                        }
                    }
                    ```
                    ''',
                    tags=['java', 'blocks', 'modding', 'tutorial'],
                    project_context='minecraft_mod'
                ),
                'bedrock_blocks': MultiModalDocument(
                    id='bedrock_blocks',
                    content_hash='mock_hash_2',
                    source_path='docs/bedrock/blocks.md',
                    content_type=ContentType.DOCUMENTATION,
                    content_text='''
                    # Bedrock Blocks Documentation
                    
                    In Minecraft Bedrock Edition, blocks are defined using JSON
                    files in behavior and resource packs.
                    
                    ## Block Behavior Definition
                    
                    Blocks in Bedrock are defined with behavior files that specify:
                    - Block properties
                    - Component behaviors
                    - Event responses
                    
                    Example behavior file:
                    ```json
                    {
                        "format_version": "1.20.10",
                        "minecraft:block": {
                            "description": {
                                "identifier": "custom:copper_block"
                            },
                            "components": {
                                "minecraft:material_instances": {
                                    "*": {
                                        "texture": "copper_block",
                                        "render_method": "opaque"
                                    }
                                },
                                "minecraft:destroy_time": 3.0,
                                "minecraft:explosion_resistance": 6.0
                            }
                        }
                    }
                    ```
                    ''',
                    tags=['bedrock', 'blocks', 'json', 'behavior'],
                    project_context='minecraft_mod'
                ),
                'recipe_system': MultiModalDocument(
                    id='recipe_system',
                    content_hash='mock_hash_3',
                    source_path='docs/recipes/crafting.md',
                    content_type=ContentType.DOCUMENTATION,
                    content_text='''
                    # Recipe System in Minecraft
                    
                    Recipes define how players can craft items and blocks.
                    Both Java and Bedrock editions support recipe systems.
                    
                    ## Java Recipe Format
                    
                    Java recipes are defined in JSON format:
                    ```json
                    {
                        "type": "minecraft:crafting_shaped",
                        "pattern": [
                            "CCC",
                            "CCC",
                            "CCC"
                        ],
                        "key": {
                            "C": {
                                "item": "minecraft:copper_ingot"
                            }
                        },
                        "result": {
                            "item": "minecraft:copper_block"
                        }
                    }
                    ```
                    
                    ## Bedrock Recipe Format
                    
                    Bedrock uses a similar but slightly different format.
                    ''',
                    tags=['recipes', 'crafting', 'java', 'bedrock'],
                    project_context='minecraft_mod'
                )
            }
        
        # Filter documents based on query criteria
        filtered_documents = {}
        for doc_id, document in self.document_cache.items():
            # Apply content type filter
            if query.content_types and document.content_type not in query.content_types:
                continue
            
            # Apply project context filter
            if query.project_context and document.project_context != query.project_context:
                continue
            
            # Apply tag filter
            if query.tags and not any(tag in document.tags for tag in query.tags):
                continue
            
            filtered_documents[doc_id] = document
        
        return filtered_documents
    
    async def _get_document_embeddings(self, documents: Dict[str, MultiModalDocument]) -> Dict[str, List]:
        """Get embeddings for documents."""
        embeddings = {}
        
        for doc_id, document in documents.items():
            if doc_id in self.embedding_cache:
                embeddings[doc_id] = self.embedding_cache[doc_id]
                continue
            
            # Generate embedding for the document
            if document.content_text:
                embedding_result = await self.embedding_generator.generate_embedding(
                    document.content_text, EmbeddingStrategy.HYBRID
                )
                
                if embedding_result:
                    # Store embedding in cache
                    self.embedding_cache[doc_id] = [embedding_result]
                    embeddings[doc_id] = [embedding_result]
        
        return embeddings
    
    async def _generate_answer(
        self, 
        query: str, 
        sources: List[SearchResult]
    ) -> Tuple[str, float, Dict[str, Any]]:
        """
        Generate an answer based on retrieved sources.
        
        Args:
            query: Original user query
            sources: Retrieved and ranked sources
            
        Returns:
            Tuple of (answer, confidence, metadata)
        """
        if not sources:
            return (
                "I couldn't find relevant information to answer your question. "
                "Please try rephrasing your query or being more specific.",
                0.1,
                {'source_count': 0, 'generation_method': 'fallback'}
            )
        
        # Combine source content for context
        context_parts = []
        source_info = []
        
        for i, source in enumerate(sources[:5]):  # Use top 5 sources
            if source.document.content_text:
                # Truncate content to fit context window
                content = source.document.content_text[:800]  # Limit per source
                context_parts.append(f"Source {i+1} ({source.document.source_path}):\n{content}")
                source_info.append({
                    'rank': source.rank,
                    'relevance': source.final_score,
                    'content_type': source.document.content_type,
                    'source_path': source.document.source_path
                })
        
        combined_context = "\n\n".join(context_parts)
        
        # Simple answer generation (in a real implementation, this would use an LLM)
        answer = self._generate_simple_answer(query, combined_context, sources)
        
        # Calculate confidence based on source quality and relevance
        avg_relevance = sum(s.final_score for s in sources[:3]) / min(3, len(sources))
        source_diversity = len(set(s.document.content_type for s in sources[:3]))
        confidence = min(avg_relevance * (1 + source_diversity * 0.1), 1.0)
        
        metadata = {
            'source_count': len(sources),
            'sources_used': source_info,
            'context_length': len(combined_context),
            'avg_source_relevance': avg_relevance,
            'source_diversity': source_diversity,
            'generation_method': 'context_synthesis'
        }
        
        return answer, confidence, metadata
    
    def _generate_simple_answer(
        self, 
        query: str, 
        context: str, 
        sources: List[SearchResult]
    ) -> str:
        """
        Generate a simple answer based on context (placeholder implementation).
        
        In a real implementation, this would use a language model to generate
        a proper answer. For now, we'll create a structured response.
        """
        query_lower = query.lower()
        
        # Determine query type and generate appropriate response
        if any(word in query_lower for word in ['how', 'create', 'make', 'build']):
            return self._generate_how_to_answer(query, context, sources)
        elif any(word in query_lower for word in ['what', 'explain', 'definition']):
            return self._generate_explanation_answer(query, context, sources)
        elif any(word in query_lower for word in ['example', 'sample', 'demo']):
            return self._generate_example_answer(query, context, sources)
        else:
            return self._generate_general_answer(query, context, sources)
    
    def _generate_how_to_answer(self, query: str, context: str, sources: List[SearchResult]) -> str:
        """Generate a how-to style answer."""
        steps = []
        
        # Extract step-like content from sources
        for source in sources[:3]:
            if source.document.content_text:
                content = source.document.content_text
                # Look for numbered lists or bullet points
                lines = content.split('\n')
                for line in lines:
                    line = line.strip()
                    if (line.startswith(('1.', '2.', '3.', '-', '*')) or 
                        'step' in line.lower() or 
                        any(word in line.lower() for word in ['create', 'define', 'register', 'add'])):
                        if len(line) > 20 and len(line) < 200:  # Reasonable step length
                            steps.append(line)
        
        if steps:
            answer = f"Based on the available documentation, here's how to {query.lower()}:\n\n"
            for i, step in enumerate(steps[:5], 1):
                answer += f"{i}. {step.lstrip('123456789.-* ')}\n"
            answer += f"\nThis information is based on {len(sources)} relevant sources."
        else:
            answer = self._generate_general_answer(query, context, sources)
        
        return answer
    
    def _generate_explanation_answer(self, query: str, context: str, sources: List[SearchResult]) -> str:
        """Generate an explanatory answer."""
        # Find the most relevant source for explanation
        best_source = sources[0] if sources else None
        
        if best_source and best_source.document.content_text:
            content = best_source.document.content_text
            
            # Extract the first substantial paragraph
            paragraphs = [p.strip() for p in content.split('\n\n') if len(p.strip()) > 50]
            
            if paragraphs:
                main_explanation = paragraphs[0]
                
                answer = f"{main_explanation}\n\n"
                
                # Add additional details from other sources
                if len(sources) > 1:
                    answer += "Additional details:\n"
                    for source in sources[1:3]:
                        if source.document.content_text:
                            # Extract key sentences
                            sentences = source.document.content_text.split('.')
                            key_sentence = next(
                                (s.strip() for s in sentences 
                                 if len(s.strip()) > 30 and any(word in s.lower() for word in query.lower().split())),
                                None
                            )
                            if key_sentence:
                                answer += f"• {key_sentence}.\n"
                
                answer += f"\nSource: {best_source.document.source_path}"
                return answer
        
        return self._generate_general_answer(query, context, sources)
    
    def _generate_example_answer(self, query: str, context: str, sources: List[SearchResult]) -> str:
        """Generate an answer with examples."""
        examples = []
        
        for source in sources:
            if source.document.content_text:
                content = source.document.content_text
                
                # Look for code blocks
                code_blocks = re.findall(r'```[\w]*\n(.*?)```', content, re.DOTALL)
                for code in code_blocks:
                    if len(code.strip()) > 20:
                        examples.append(('code', code.strip(), source.document.source_path))
                
                # Look for example sections
                lines = content.split('\n')
                in_example = False
                example_content = []
                
                for line in lines:
                    if 'example' in line.lower() and ':' in line:
                        in_example = True
                        example_content = [line]
                    elif in_example:
                        if line.strip() and not line.startswith('#'):
                            example_content.append(line)
                        elif len(example_content) > 2:
                            examples.append(('text', '\n'.join(example_content), source.document.source_path))
                            in_example = False
                            example_content = []
        
        if examples:
            answer = f"Here are examples related to your query:\n\n"
            
            for i, (example_type, content, source_path) in enumerate(examples[:3], 1):
                answer += f"**Example {i}** (from {source_path}):\n"
                if example_type == 'code':
                    answer += f"```\n{content}\n```\n\n"
                else:
                    answer += f"{content}\n\n"
            
            return answer
        
        return self._generate_general_answer(query, context, sources)
    
    def _generate_general_answer(self, query: str, context: str, sources: List[SearchResult]) -> str:
        """Generate a general answer."""
        if not sources:
            return "I couldn't find specific information about your query in the available documentation."
        
        # Create a summary from the top sources
        answer_parts = []
        
        # Use the most relevant source as the primary answer
        primary_source = sources[0]
        if primary_source.document.content_text:
            # Extract the most relevant paragraph
            content = primary_source.document.content_text
            paragraphs = [p.strip() for p in content.split('\n\n') if len(p.strip()) > 50]
            
            if paragraphs:
                # Find paragraph most similar to query (simple word overlap)
                query_words = set(query.lower().split())
                best_paragraph = max(
                    paragraphs,
                    key=lambda p: len(query_words.intersection(set(p.lower().split())))
                )
                answer_parts.append(best_paragraph)
        
        # Add supplementary information from other sources
        if len(sources) > 1:
            supplementary_info = []
            for source in sources[1:3]:
                if source.document.content_text:
                    # Extract key sentences related to the query
                    sentences = source.document.content_text.split('.')
                    for sentence in sentences:
                        sentence = sentence.strip()
                        if (len(sentence) > 30 and 
                            any(word in sentence.lower() for word in query.lower().split())):
                            supplementary_info.append(sentence)
                            break
            
            if supplementary_info:
                answer_parts.append("Additional information:\n" + '\n'.join(f"• {info}." for info in supplementary_info))
        
        if answer_parts:
            answer = '\n\n'.join(answer_parts)
            answer += f"\n\nThis information is compiled from {len(sources)} relevant sources."
            return answer
        
        return "I found some relevant sources but couldn't extract a clear answer. Please try being more specific with your query."
    
    def _update_session_context(self, session_id: str, query: SearchQuery, response: RAGResponse):
        """Update session context for future queries."""
        if session_id not in self.session_contexts:
            self.session_contexts[session_id] = {
                'queries': [],
                'successful_queries': [],
                'content_preferences': {},
                'topic_interests': {}
            }
        
        context = self.session_contexts[session_id]
        
        # Add query to history
        context['queries'].append({
            'query': query.query_text,
            'timestamp': datetime.utcnow().isoformat(),
            'confidence': response.confidence,
            'sources_found': len(response.sources)
        })
        
        # Track successful queries (high confidence)
        if response.confidence > self.config['confidence_threshold']:
            context['successful_queries'].append(query.query_text)
        
        # Update content type preferences
        if query.content_types:
            for content_type in query.content_types:
                context['content_preferences'][content_type] = context['content_preferences'].get(content_type, 0) + 1
        
        # Keep only recent history
        context['queries'] = context['queries'][-20:]
        context['successful_queries'] = context['successful_queries'][-10:]
    
    async def get_session_context(self, session_id: str) -> Dict[str, Any]:
        """Get session context information."""
        return self.session_contexts.get(session_id, {})
    
    async def clear_session_context(self, session_id: str):
        """Clear session context."""
        if session_id in self.session_contexts:
            del self.session_contexts[session_id]
    
    def get_agent_status(self) -> Dict[str, Any]:
        """Get current agent status and statistics."""
        return {
            'configuration': {
                'multimodal_enabled': self.enable_multimodal,
                'query_expansion_enabled': bool(self.query_expander),
                'reranking_enabled': bool(self.reranker),
                'max_sources': self.config['max_sources'],
                'confidence_threshold': self.config['confidence_threshold']
            },
            'cache_status': {
                'documents_cached': len(self.document_cache),
                'embeddings_cached': len(self.embedding_cache),
                'active_sessions': len(self.session_contexts)
            },
            'capabilities': [
                'multi_modal_search',
                'hybrid_retrieval',
                'query_expansion',
                'result_reranking',
                'contextual_understanding',
                'session_awareness'
            ]
        }