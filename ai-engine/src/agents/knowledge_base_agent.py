from typing import List
from crewai.tools import BaseTool
from ..tools.search_tool import SearchTool # Assuming relative import path

class KnowledgeBaseAgent:
    """
    An agent specialized in retrieving information from a knowledge base
    using a search tool.
    """

    def __init__(self):
        # Potentially initialize other agent-specific attributes here
        pass

    def get_tools(self) -> List[BaseTool]:
        """
        Instantiates and returns a list of tools available to this agent.
        """
        return [SearchTool()]

# Example usage (optional, for testing):
# if __name__ == "__main__":
#     agent = KnowledgeBaseAgent()
#     tools = agent.get_tools()
#     for tool in tools:
#         print(f"Tool: {tool.name}, Description: {tool.description}")
#         # To test the tool's run method (requires SearchTool._run to be functional):
#         # if isinstance(tool, SearchTool):
#         #     try:
#         #         print(tool._run("example query"))
#         #     except Exception as e:
#         #         print(f"Error running tool: {e}")
