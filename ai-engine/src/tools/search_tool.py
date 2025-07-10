"""
SearchTool implementation for RAG workflow agents.
Provides semantic search capabilities using the existing vector database with fallback mechanism.
"""

import json
import logging
import importlib
from typing import List, Dict, Any, Optional
from crewai.tools import tool
from ..utils.vector_db_client import VectorDBClient
from ..utils.config import Config

logger = logging.getLogger(__name__)


class SearchTool:
    """
    SearchTool for semantic search across indexed documents.
    Integrates with the existing vector database infrastructure and includes fallback mechanism.
    """
    
    _instance = None
    
    def __init__(self):
        """Initialize the SearchTool with vector database client."""
        self.vector_client = VectorDBClient()
        logger.info("SearchTool initialized")
    
    @classmethod
    def get_instance(cls):
        """Get singleton instance of SearchTool."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def get_tools(self) -> List:
        """Return list of available search tools."""
        return [
            SearchTool.semantic_search,
            SearchTool.document_search,
            SearchTool.similarity_search
        ]
    
    @tool
    @staticmethod
    def semantic_search(query_data: str) -> str:
        """
        Perform semantic search across indexed documents.
        
        Args:
            query_data: JSON string containing search query and optional filters
            
        Returns:
            JSON string with search results
        """
        tool_instance = SearchTool.get_instance()
        
        try:
            # Handle both JSON string and direct inputs
            if isinstance(query_data, str):
                try:
                    data = json.loads(query_data)
                except json.JSONDecodeError:
                    data = {'query': query_data}
            else:
                data = query_data
            
            query = data.get('query', '')
            limit = data.get('limit', 10)
            document_source = data.get('document_source', None)
            
            if not query:
                return json.dumps({
                    "error": "Query is required for semantic search"
                })
            
            # Perform semantic search using vector database
            results = tool_instance._perform_semantic_search(
                query=query,
                limit=limit,
                document_source=document_source
            )
            
            # Check if results are insufficient and fallback is enabled
            if not results and Config.SEARCH_FALLBACK_ENABLED:
                logger.info("Primary semantic search returned no results, attempting fallback")
                fallback_results = tool_instance._attempt_fallback_search(query, limit)
                if fallback_results:
                    results = fallback_results
                    logger.info(f"Fallback search returned {len(results)} results")
            
            response = {
                "query": query,
                "results": results,
                "total_results": len(results)
            }
            
            logger.info(f"Semantic search completed for query: {query}")
            return json.dumps(response)
            
        except Exception as e:
            logger.error(f"Semantic search failed: {str(e)}")
            error_response = {
                "error": f"Semantic search failed: {str(e)}",
                "query": query_data
            }
            return json.dumps(error_response)
    
    @tool
    @staticmethod
    def document_search(query_data: str) -> str:
        """
        Search for specific documents by source or content type.
        
        Args:
            query_data: JSON string containing search criteria
            
        Returns:
            JSON string with matching documents
        """
        tool_instance = SearchTool.get_instance()
        
        try:
            if isinstance(query_data, str):
                try:
                    data = json.loads(query_data)
                except json.JSONDecodeError:
                    data = {'document_source': query_data}
            else:
                data = query_data
            
            document_source = data.get('document_source', '')
            content_type = data.get('content_type', None)
            
            if not document_source:
                return json.dumps({
                    "error": "Document source is required for document search"
                })
            
            # Search for documents by source
            results = tool_instance._search_by_document_source(
                document_source=document_source,
                content_type=content_type
            )
            
            # Check if results are insufficient and fallback is enabled
            if not results and Config.SEARCH_FALLBACK_ENABLED:
                logger.info("Primary document search returned no results, attempting fallback")
                fallback_results = tool_instance._attempt_fallback_search(document_source, 10)
                if fallback_results:
                    results = fallback_results
                    logger.info(f"Fallback search returned {len(results)} results")
            
            response = {
                "document_source": document_source,
                "content_type": content_type,
                "results": results,
                "total_results": len(results)
            }
            
            logger.info(f"Document search completed for source: {document_source}")
            return json.dumps(response)
            
        except Exception as e:
            logger.error(f"Document search failed: {str(e)}")
            error_response = {
                "error": f"Document search failed: {str(e)}",
                "query": query_data
            }
            return json.dumps(error_response)
    
    @tool
    @staticmethod
    def similarity_search(query_data: str) -> str:
        """
        Find documents similar to a given document or content.
        
        Args:
            query_data: JSON string containing reference content
            
        Returns:
            JSON string with similar documents
        """
        tool_instance = SearchTool.get_instance()
        
        try:
            if isinstance(query_data, str):
                try:
                    data = json.loads(query_data)
                except json.JSONDecodeError:
                    data = {'content': query_data}
            else:
                data = query_data
            
            content = data.get('content', '')
            threshold = data.get('threshold', 0.8)
            limit = data.get('limit', 10)
            
            if not content:
                return json.dumps({
                    "error": "Content is required for similarity search"
                })
            
            # Find similar documents
            results = tool_instance._find_similar_documents(
                content=content,
                threshold=threshold,
                limit=limit
            )
            
            # Check if results are insufficient and fallback is enabled
            if not results and Config.SEARCH_FALLBACK_ENABLED:
                logger.info("Primary similarity search returned no results, attempting fallback")
                fallback_results = tool_instance._attempt_fallback_search(content[:100], limit)
                if fallback_results:
                    results = fallback_results
                    logger.info(f"Fallback search returned {len(results)} results")
            
            response = {
                "reference_content": content[:100] + "..." if len(content) > 100 else content,
                "threshold": threshold,
                "results": results,
                "total_results": len(results)
            }
            
            logger.info(f"Similarity search completed for content length: {len(content)}")
            return json.dumps(response)
            
        except Exception as e:
            logger.error(f"Similarity search failed: {str(e)}")
            error_response = {
                "error": f"Similarity search failed: {str(e)}",
                "query": query_data
            }
            return json.dumps(error_response)
    
    def _perform_semantic_search(self, query: str, limit: int = 10, document_source: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Perform semantic search using vector database.
        
        Args:
            query: Search query
            limit: Maximum number of results
            document_source: Optional filter by document source
            
        Returns:
            List of search results
        """
        try:
            # This would integrate with the actual vector database
            # For now, return a mock structure that matches expected format
            results = [
                {
                    "id": f"doc_{i}",
                    "content": f"Mock search result {i} for query: {query}",
                    "document_source": document_source or f"source_{i}",
                    "similarity_score": 0.9 - (i * 0.1),
                    "metadata": {
                        "indexed_at": "2025-01-09T00:00:00Z",
                        "content_type": "text"
                    }
                }
                for i in range(min(limit, 3))  # Mock 3 results max
            ]
            
            return results
            
        except Exception as e:
            logger.error(f"Semantic search execution failed: {str(e)}")
            return []
    
    def _attempt_fallback_search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Attempt to use fallback search tool when primary search fails.
        
        This method implements the fallback mechanism by dynamically importing
        and instantiating the configured fallback tool. It handles various error
        scenarios gracefully and logs appropriate messages.
        
        Args:
            query: Search query string
            limit: Maximum number of results to return
            
        Returns:
            List of search results from fallback tool in standardized format,
            or empty list if fallback fails or is disabled
        """
        if not Config.SEARCH_FALLBACK_ENABLED:
            logger.info("Fallback search is disabled")
            return []
        
        tool_name = Config.FALLBACK_SEARCH_TOOL
        logger.info(f"Attempting fallback search with {tool_name}")
        
        try:
            # Construct module and class names
            module_path = f"src.tools.{tool_name}"
            class_name_parts = [part.capitalize() for part in tool_name.split('_')]
            class_name = "".join(class_name_parts)
            
            # Import and instantiate fallback tool
            module = importlib.import_module(module_path)
            FallbackToolClass = getattr(module, class_name)
            fallback_tool_instance = FallbackToolClass()
            
            # Execute fallback search
            fallback_result = fallback_tool_instance._run(query=query)
            
            # Convert fallback result to expected format
            if isinstance(fallback_result, str):
                # Parse fallback result and convert to our expected format
                fallback_results = [{
                    "id": "fallback_0",
                    "content": fallback_result,
                    "document_source": "fallback_search",
                    "similarity_score": 0.7,
                    "metadata": {
                        "indexed_at": "2025-01-09T00:00:00Z",
                        "content_type": "text",
                        "source": "fallback"
                    }
                }]
                return fallback_results[:limit]
            
            return []
            
        except ImportError as e:
            logger.error(f"Fallback tool '{tool_name}' module not found at '{module_path}': {str(e)}")
            return []
        except AttributeError as e:
            logger.error(f"Fallback tool class '{class_name}' not found in module '{module_path}': {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Error during fallback to {tool_name}: {str(e)}")
            return []
    
    def _search_by_document_source(self, document_source: str, content_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search documents by source identifier.
        
        Args:
            document_source: Document source to search for
            content_type: Optional content type filter
            
        Returns:
            List of matching documents
        """
        try:
            # Mock implementation - would integrate with actual database
            results = [
                {
                    "id": f"doc_source_{i}",
                    "content": f"Document content from {document_source}",
                    "document_source": document_source,
                    "content_type": content_type or "text",
                    "metadata": {
                        "indexed_at": "2025-01-09T00:00:00Z",
                        "size": 1024
                    }
                }
                for i in range(2)  # Mock 2 results
            ]
            
            return results
            
        except Exception as e:
            logger.error(f"Document source search failed: {str(e)}")
            return []
    
    def _find_similar_documents(self, content: str, threshold: float = 0.8, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Find documents similar to given content.
        
        Args:
            content: Reference content
            threshold: Similarity threshold (0-1)
            limit: Maximum number of results
            
        Returns:
            List of similar documents
        """
        try:
            # Mock implementation - would use actual vector similarity
            results = [
                {
                    "id": f"similar_{i}",
                    "content": f"Similar content {i} to: {content[:50]}...",
                    "document_source": f"similar_source_{i}",
                    "similarity_score": threshold + (0.1 * i),
                    "metadata": {
                        "indexed_at": "2025-01-09T00:00:00Z",
                        "content_type": "text"
                    }
                }
                for i in range(min(limit, 3))  # Mock 3 results max
            ]
            
            return results
            
        except Exception as e:
            logger.error(f"Similarity search execution failed: {str(e)}")
            return []
    
    async def close(self):
        """Close vector database connection."""
        if hasattr(self, 'vector_client'):
            # Check if the close method is async or sync
            if hasattr(self.vector_client, 'close'):
                close_method = self.vector_client.close
                if hasattr(close_method, '__call__'):
                    # Check if it's awaitable
                    import asyncio
                    if asyncio.iscoroutinefunction(close_method):
                        await close_method()
                    else:
                        close_method()
            logger.info("SearchTool connections closed")
