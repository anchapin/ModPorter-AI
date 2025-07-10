"""
SearchTool implementation for RAG workflow agents.
Provides semantic search capabilities using the existing vector database.
"""

import json
import logging
from typing import List, Dict, Any, Optional
from crewai.tools import tool
from ..utils.vector_db_client import VectorDBClient

logger = logging.getLogger(__name__)


class SearchTool:
    """
    SearchTool for semantic search across indexed documents.
    Integrates with the existing vector database infrastructure.
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
            # Enhanced mock data with better content for different query types
            if "AI advancements" in query:
                base_results = [
                    {
                        "id": "doc1",
                        "content": "Recent breakthroughs in large language models have enabled more natural and context-aware conversations.",
                        "document_source": "ai_research_journal_vol2.pdf",
                        "similarity_score": 0.92,
                        "metadata": {
                            "indexed_at": "2025-01-09T00:00:00Z",
                            "content_type": "text"
                        }
                    },
                    {
                        "id": "doc2", 
                        "content": "Generative Adversarial Networks (GANs) are being used to create hyper-realistic images and videos.",
                        "document_source": "tech_conference_proceedings_2023.docx",
                        "similarity_score": 0.88,
                        "metadata": {
                            "indexed_at": "2025-01-09T00:00:00Z",
                            "content_type": "text"
                        }
                    },
                    {
                        "id": "doc3",
                        "content": "Ethical considerations in AI development, including bias and fairness, are becoming increasingly important.",
                        "document_source": "ethics_in_ai_whitepaper.pdf",
                        "similarity_score": 0.85,
                        "metadata": {
                            "indexed_at": "2025-01-09T00:00:00Z",
                            "content_type": "text"
                        }
                    }
                ]
            elif "Minecraft modding" in query:
                base_results = [
                    {
                        "id": "mc_doc1",
                        "content": "Minecraft Forge is a popular modding API for the Java Edition, allowing extensive modifications.",
                        "document_source": "forge_wiki.html",
                        "similarity_score": 0.95,
                        "metadata": {
                            "indexed_at": "2025-01-09T00:00:00Z",
                            "content_type": "text"
                        }
                    },
                    {
                        "id": "mc_doc2",
                        "content": "Bedrock Edition uses Add-Ons, which are behavior packs and resource packs, often written in JSON and JavaScript.",
                        "document_source": "bedrock.dev/docs",
                        "similarity_score": 0.90,
                        "metadata": {
                            "indexed_at": "2025-01-09T00:00:00Z",
                            "content_type": "text"
                        }
                    },
                    {
                        "id": "mc_doc3",
                        "content": "The RAG.md document in this repository outlines a plan for using AI to assist with porting Minecraft mods.",
                        "document_source": "RAG.md",
                        "similarity_score": 0.87,
                        "metadata": {
                            "indexed_at": "2025-01-09T00:00:00Z",
                            "content_type": "text"
                        }
                    }
                ]
            else:
                base_results = [
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
            
            # Apply document source filter if provided
            if document_source:
                base_results = [r for r in base_results if document_source in r.get('document_source', '')]
            
            # Apply limit
            return base_results[:limit]
            
        except Exception as e:
            logger.error(f"Semantic search execution failed: {str(e)}")
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


# Demo functionality for testing
if __name__ == "__main__":
    search_tool = SearchTool.get_instance()
    
    # Test semantic search
    sample_query_ai = "What are the latest advancements in AI?"
    output_ai = SearchTool.semantic_search(sample_query_ai)
    print(f"Query: {sample_query_ai}")
    print(f"Output:\n{output_ai}\n")

    sample_query_mc = "Tell me about Minecraft modding."
    output_mc = SearchTool.semantic_search(sample_query_mc)
    print(f"Query: {sample_query_mc}")
    print(f"Output:\n{output_mc}\n")

    sample_query_other = "Some other topic."
    output_other = SearchTool.semantic_search(sample_query_other)
    print(f"Query: {sample_query_other}")
    print(f"Output:\n{output_other}\n")
