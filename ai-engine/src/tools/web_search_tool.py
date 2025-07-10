"""
WebSearchTool implementation for fallback search functionality.
This tool serves as a fallback when the primary SearchTool fails to return results.
"""

import logging
from crewai.tools import BaseTool

logger = logging.getLogger(__name__)


class WebSearchTool(BaseTool):
    """
    WebSearchTool for performing web searches as a fallback mechanism.
    This tool is used when the primary vector database search fails.
    """
    
    name: str = "Web Search Tool"
    description: str = "A tool to perform web searches as a fallback when primary search fails."
    
    def _run(self, query: str) -> str:
        """
        Perform a web search query.
        
        Args:
            query: The search query string
            
        Returns:
            String representation of search results
        """
        try:
            logger.info(f"Performing web search for query: {query}")
            
            # TODO: Implement actual web search functionality
            # For now, return a mock response that indicates web search was used
            mock_result = f"Web search results for '{query}':\n"
            mock_result += "- Result 1: Mock web search result for your query\n"
            mock_result += "- Result 2: Additional web search information\n"
            mock_result += "- Result 3: More relevant web search content\n"
            mock_result += "\n(Note: This is a mock implementation. Actual web search would be implemented here.)"
            
            logger.info(f"Web search completed for query: {query}")
            return mock_result
            
        except Exception as e:
            logger.error(f"Web search failed: {str(e)}")
            return f"Web search failed for query '{query}': {str(e)}"