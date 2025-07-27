"""
SearchTool implementation for RAG workflow agents.
Provides semantic search capabilities using the existing vector database with fallback mechanism.
"""

import json
import asyncio
import logging
import importlib
from typing import List, Dict, Any, Optional
from crewai.tools import tool
from utils.vector_db_client import VectorDBClient
from utils.config import Config

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
            SearchTool.similarity_search,
            SearchTool.bedrock_api_search,
            SearchTool.component_lookup,
            SearchTool.conversion_examples,
            SearchTool.schema_validation_lookup
        ]
    
    @tool
    @staticmethod
    async def semantic_search(query_data: str) -> str:
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
            results = await tool_instance._perform_semantic_search(
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
    async def document_search(query_data: str) -> str:
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
            results = await tool_instance._search_by_document_source(
                document_source=document_source,
                content_type=content_type, # content_type filter might be applied client-side if needed
                limit=data.get('limit', 10) # Pass limit
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
    async def similarity_search(query_data: str) -> str:
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
            results = await tool_instance._find_similar_documents(
                content=content,
                threshold=threshold, # threshold might be applied client-side if needed
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
    
    @tool
    @staticmethod
    async def bedrock_api_search(query_data: str) -> str:
        """
        Search for Bedrock Edition API documentation.
        Input can be a simple query string or a JSON string:
        '{"query": "player events", "api_category": "Scripting API"}'
        or simply "player events".
        `api_category` is optional and can be things like 'Scripting API', 'Gametest Framework', etc.
        """
        tool_instance = SearchTool.get_instance()
        query = ""
        api_category = None
        try:
            if isinstance(query_data, str):
                try:
                    data = json.loads(query_data)
                    query = data.get("query", "")
                    api_category = data.get("api_category")
                except json.JSONDecodeError:
                    query = query_data # Treat as plain string query
            else: # Should not happen if called by CrewAI with string arg
                query = str(query_data)

            if not query:
                return json.dumps({"error": "Query parameter is required for Bedrock API search."})

            formatted_query = f"Bedrock API {api_category if api_category else ''} {query}".strip()
            logger.info(f"Bedrock API search for: {formatted_query}")

            # Utilize existing semantic_search tool
            return await SearchTool.semantic_search(json.dumps({
                "query": formatted_query,
                "limit": 10 # Default limit for API search
            }))
        except Exception as e:
            logger.error(f"Bedrock API search failed: {str(e)}")
            return json.dumps({
                "error": f"Bedrock API search failed: {str(e)}",
                "original_query": query_data
            })

    @tool
    @staticmethod
    async def component_lookup(query_data: str) -> str:
        """
        Lookup documentation for specific Bedrock Edition components (e.g., minecraft:loot, minecraft:behavior.float_wander).
        Input can be a simple component name string or a JSON string:
        '{"component_name": "minecraft:behavior.float_wander"}'
        or simply "minecraft:behavior.float_wander".
        """
        tool_instance = SearchTool.get_instance()
        component_name = ""
        try:
            if isinstance(query_data, str):
                try:
                    data = json.loads(query_data)
                    component_name = data.get("component_name", "")
                except json.JSONDecodeError:
                    component_name = query_data
            else:
                component_name = str(query_data)

            if not component_name:
                return json.dumps({"error": "Component name is required for component lookup."})

            formatted_query = f"Bedrock component documentation for {component_name}"
            logger.info(f"Component lookup for: {formatted_query}")

            return await SearchTool.semantic_search(json.dumps({
                "query": formatted_query,
                "limit": 5 # More focused search
            }))
        except Exception as e:
            logger.error(f"Component lookup failed: {str(e)}")
            return json.dumps({
                "error": f"Component lookup failed: {str(e)}",
                "original_query": query_data
            })

    @tool
    @staticmethod
    async def conversion_examples(query_data: str) -> str:
        """
        Search for examples of converting game elements or mechanics from Java Edition to Bedrock Edition.
        Input can be a simple query string describing the element or a JSON string:
        '{"query": "potion effects"}' or simply "potion effects".
        """
        tool_instance = SearchTool.get_instance()
        query = ""
        try:
            if isinstance(query_data, str):
                try:
                    data = json.loads(query_data)
                    query = data.get("query", "")
                except json.JSONDecodeError:
                    query = query_data
            else:
                query = str(query_data)

            if not query:
                return json.dumps({"error": "Query is required for conversion examples."})

            formatted_query = f"Java to Bedrock conversion example for {query}"
            logger.info(f"Conversion examples search for: {formatted_query}")

            return await SearchTool.semantic_search(json.dumps({
                "query": formatted_query,
                "limit": 5
            }))
        except Exception as e:
            logger.error(f"Conversion examples search failed: {str(e)}")
            return json.dumps({
                "error": f"Conversion examples search failed: {str(e)}",
                "original_query": query_data
            })

    @tool
    @staticmethod
    async def schema_validation_lookup(query_data: str) -> str:
        """
        Search for Bedrock JSON schema information (e.g., for entities, blocks, items).
        Input can be a simple schema name string or a JSON string:
        '{"schema_name": "entity definition"}' or "entity definition".
        """
        tool_instance = SearchTool.get_instance() # Not strictly needed since we call static SearchTool.semantic_search
        schema_name = ""
        try:
            if isinstance(query_data, str):
                try:
                    data = json.loads(query_data)
                    schema_name = data.get("schema_name", "")
                except json.JSONDecodeError:
                    schema_name = query_data
            else:
                schema_name = str(query_data)

            if not schema_name:
                return json.dumps({"error": "Schema name/topic is required for schema validation lookup."})

            formatted_query = f"Bedrock JSON schema for {schema_name}"
            logger.info(f"Schema validation lookup for: {formatted_query}")

            return await SearchTool.semantic_search(json.dumps({
                "query": formatted_query,
                "limit": 3 # Schemas are often specific
            }))
        except Exception as e:
            logger.error(f"Schema validation lookup failed: {str(e)}")
            return json.dumps({
                "error": f"Schema validation lookup failed: {str(e)}",
                "original_query": query_data
            })

    async def _perform_semantic_search(self, query: str, limit: int = 10, document_source: Optional[str] = None) -> List[Dict[str, Any]]:
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
            results = await self.vector_client.search_documents(
                query_text=query,
                top_k=limit,
                document_source_filter=document_source
            )
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
    
    async def _search_by_document_source(self, document_source: str, content_type: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search documents by source identifier.
        
        Args:
            document_source: Document source to search for
            content_type: Optional content type filter (currently not used in backend call)
            limit: Maximum number of results
            
        Returns:
            List of matching documents
        """
        try:
            # Using document_source as query_text for now.
            # The backend's search logic will determine how this is interpreted.
            # If specific "get by source" functionality is needed, backend API should support it.
            results = await self.vector_client.search_documents(
                query_text=document_source, # Or a more generic query if appropriate
                top_k=limit,
                document_source_filter=document_source # This is the key filter
            )
            # Client-side content_type filtering could be done here if results have 'content_type'
            if content_type and results:
                results = [r for r in results if r.get('metadata', {}).get('content_type') == content_type or r.get('content_type') == content_type]
            return results
        except Exception as e:
            logger.error(f"Document source search failed: {str(e)}")
            return []
    
    async def _find_similar_documents(self, content: str, threshold: float = 0.8, limit: int = 10) -> List[Dict[str, Any]]:
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
            results = await self.vector_client.search_documents(
                query_text=content,
                top_k=limit
            )
            # Client-side threshold filtering could be done here if results have 'similarity_score'
            if threshold > 0 and results: # Assuming threshold=0 means no filtering
                results = [r for r in results if r.get('similarity_score', 0.0) >= threshold]
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
    import asyncio
    search_tool = SearchTool.get_instance()

    async def demo():
        # Test semantic search
        sample_query_ai = "What are the latest advancements in AI?"
        output_ai = await SearchTool.semantic_search(sample_query_ai)
        print(f"Query: {sample_query_ai}")
        print(f"Output:\n{output_ai}\n")

        sample_query_mc = "Tell me about Minecraft modding."
        output_mc = await SearchTool.semantic_search(sample_query_mc)
        print(f"Query: {sample_query_mc}")
        print(f"Output:\n{output_mc}\n")

        sample_query_other = "Some other topic."
        output_other = await SearchTool.semantic_search(sample_query_other)
        print(f"Query: {sample_query_other}")
        print(f"Output:\n{output_other}\n")

    asyncio.run(demo())
