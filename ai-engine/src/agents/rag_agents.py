from crewai import Agent
from langchain_openai import ChatOpenAI # Or any other LLM you plan to use
import os

# Placeholder for initializing an LLM, similar to conversion_crew.py
# This could be enhanced to use create_rate_limited_llm or MockLLM
def get_llm():
    if os.getenv("MOCK_AI_RESPONSES", "false").lower() == "true":
        try:
            # Try importing from the current project structure
            import sys
            from pathlib import Path
            # Assuming this file is in ai-engine/src/agents/
            # Adjust path to reach ai-engine/tests/mocks/
            mock_llm_path = Path(__file__).parent.parent.parent / "tests" / "mocks"
            
            # Verify the mock_llm_path exists and contains the expected file
            if not mock_llm_path.exists():
                raise ImportError(f"Mock LLM path does not exist: {mock_llm_path}")
            
            mock_llm_file = mock_llm_path / "mock_llm.py"
            if not mock_llm_file.exists():
                raise ImportError(f"Mock LLM file does not exist: {mock_llm_file}")
            
            sys.path.insert(0, str(mock_llm_path))
            from mock_llm import MockLLM
            return MockLLM(responses=["Mock search agent response", "Mock summarization agent response"])
        except (ImportError, OSError, FileNotFoundError):
            # Fallback to MagicMock if mock_llm import fails for any reason
            from unittest.mock import MagicMock
            llm = MagicMock()
            llm.invoke.return_value = "Mock LLM response due to import error"
            return llm
    else:
        # In a real scenario, initialize your actual LLM
        # For example, using ChatOpenAI or a custom rate-limited LLM
        # from src.utils.rate_limiter import create_rate_limited_llm
        # return create_rate_limited_llm(model_name="gpt-3.5-turbo")
        return ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0.7) # Default, replace as needed

class RAGAgents:
    def search_agent(self, llm, tools):
        agent_kwargs = {
            "role": 'Research Specialist',
            "goal": 'To find the most relevant and up-to-date information on a given topic using available search tools.',
            "backstory": (
                "You are an expert researcher, skilled in sifting through vast amounts of data "
                "to find nuggets of truth. You are proficient in using various search tools and techniques "
                "to quickly locate information critical to answering complex queries."
            ),
            "verbose": True,
            "allow_delegation": False,
            "llm": llm,
            "tools": tools # Expecting search_tool to be passed here
        }
        
        # Disable memory in test environment to avoid validation issues
        if os.getenv("MOCK_AI_RESPONSES", "false").lower() == "true":
            agent_kwargs["memory"] = False
        
        return Agent(**agent_kwargs)

    def summarization_agent(self, llm):
        agent_kwargs = {
            "role": 'Content Summarizer',
            "goal": 'To synthesize information gathered from search results into a concise and easy-to-understand summary that directly answers the user\'s query.',
            "backstory": (
                "You are a master of brevity and clarity. You can take complex information from multiple sources "
                "and distill it into a short, yet comprehensive summary. Your summaries are known for being highly "
                "accurate and tailored to the user's original question."
            ),
            "verbose": True,
            "allow_delegation": False,
            "llm": llm,
            # No specific tools needed for summarization beyond LLM capabilities
        }
        
        # Disable memory in test environment to avoid validation issues
        if os.getenv("MOCK_AI_RESPONSES", "false").lower() == "true":
            agent_kwargs["memory"] = False
        
        return Agent(**agent_kwargs)

if __name__ == '__main__':
    # Example of how to instantiate the agents
    # This part is for testing and might be removed or moved later
    from src.tools.search_tool import SearchTool # Adjust import if necessary

    llm_instance = get_llm()
    search_tool_instance = SearchTool()

    agents = RAGAgents()

    searcher = agents.search_agent(llm_instance, [search_tool_instance])
    summarizer = agents.summarization_agent(llm_instance)

    print("Search Agent:")
    print(f"  Role: {searcher.role}")
    print(f"  Goal: {searcher.goal}")
    print(f"  Tools: {[tool.name for tool in searcher.tools]}")

    print("\nSummarization Agent:")
    print(f"  Role: {summarizer.role}")
    print(f"  Goal: {summarizer.goal}")
