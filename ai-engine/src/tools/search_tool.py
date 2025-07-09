import importlib
import logging
from crewai.tools import BaseTool
from ..utils.config import Config

logger = logging.getLogger(__name__)

class SearchTool(BaseTool):
    name: str = "Search Tool"
    description: str = "A tool to perform similarity searches in a vector database. Can fallback to other search tools."

    def _perform_primary_search(self, query: str) -> list:
        """
        Internal method to perform the primary search.
        This method can be mocked for testing.
        """
        # TODO(autogpt): Connect to the vector database and perform actual search.
        # Placeholder: Returns empty list by default to enable fallback testing.
        # To test with primary results, mock this method to return non-empty list.
        # Example of returning actual results:
        # return [
        #     {"id": 1, "score": 0.9, "text": f"Primary result for {query} 1"},
        #     {"id": 2, "score": 0.85, "text": f"Primary result for {query} 2"},
        # ]
        return []

    def _run(self, query: str) -> str:
        """
        Performs a similarity search in the vector database based on the query.
        If results are insufficient and fallback is enabled, uses a fallback search tool.
        """
        search_results = self._perform_primary_search(query)

        # Check if results are insufficient (e.g., empty)
        if not search_results: # Replace with actual relevance check if needed
            if Config.SEARCH_FALLBACK_ENABLED:
                tool_name = Config.FALLBACK_SEARCH_TOOL
                # Construct module and class names
                # e.g., "web_search_tool" -> module "src.tools.web_search_tool", class "WebSearchTool"
                module_path = f"src.tools.{tool_name}"
                class_name_parts = [part.capitalize() for part in tool_name.split('_')]
                class_name = "".join(class_name_parts)

                try:
                    module = importlib.import_module(module_path)
                    FallbackToolClass = getattr(module, class_name)
                    fallback_tool_instance = FallbackToolClass()
                    # Assuming the fallback tool also has a _run method
                    logger.info(f"Primary search failed, attempting fallback with {tool_name}")
                    return fallback_tool_instance._run(query=query)
                except ImportError:
                    # Log or handle the error that the module couldn't be imported
                    # For now, return a message or the original empty results
                    return f"Fallback tool '{tool_name}' module not found at '{module_path}'. Returning original (empty) results."
                except AttributeError:
                    # Log or handle the error that the class couldn't be found in the module
                    return f"Fallback tool class '{class_name}' not found in module '{module_path}'. Returning original (empty) results."
                except Exception as e:
                    return f"Error during fallback to {tool_name}: {str(e)}. Returning original (empty) results."

        # Format and return original results if not empty or fallback not used
        if not search_results: # If still no results after potential fallback failure
            return f"No results found for query '{query}' after attempting primary search and potential fallback."

        formatted_results = f"Found {len(search_results)} results for query '{query}':\n"
        for result in search_results:
            formatted_results += f"- (Score: {result['score']}) {result['text']}\n"

        return formatted_results

# Example usage (optional, for testing purposes):
# if __name__ == "__main__":
#     # To test fallback, ensure SEARCH_FALLBACK_ENABLED=true and FALLBACK_SEARCH_TOOL=your_tool in .env
#     # And that your_tool.py exists with YourTool class in src/tools/
#     search_tool = SearchTool()
#     sample_query = "What are the latest advancements in AI?"
#     output = search_tool._run(sample_query)
#     print(output)
