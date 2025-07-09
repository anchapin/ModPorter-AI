from crewai import Task, Crew, Process
from langchain_openai import ChatOpenAI # Or your preferred LLM
import os
import json # For handling JSON output from search tool

# Import RAGAgents and SearchTool
from ai_engine.src.agents.rag_agents import RAGAgents
from ai_engine.src.tools.search_tool import SearchTool

# Placeholder for LLM initialization (similar to rag_agents.py or conversion_crew.py)
def get_llm_instance():
    if os.getenv("MOCK_AI_RESPONSES", "false").lower() == "true":
        try:
            import sys
            from pathlib import Path
            mock_llm_path = Path(__file__).parent.parent.parent / "tests" / "mocks"
            if str(mock_llm_path) not in sys.path:
                 sys.path.insert(0, str(mock_llm_path))
            from mock_llm import MockLLM
            # Provide enough mock responses for crew execution
            return MockLLM(responses=[
                json.dumps([{"id": "mock_doc1", "score": 0.9, "text": "This is a mock document from search."}]), # Search Agent's tool usage
                "Mock summarization based on search results." # Summarization Agent's response
            ])
        except ImportError as e:
            print(f"Error importing MockLLM: {e}")
            from unittest.mock import MagicMock
            llm = MagicMock()
            llm.invoke.return_value = "Mock LLM response due to import error"
            return llm
    else:
        return ChatOpenAI(model_name=os.getenv("OPENAI_MODEL_NAME", "gpt-3.5-turbo"), temperature=0.7)


class RAGTasks:
    def search_task(self, agent, query):
        return Task(
            description=f"Search for information on the topic: '{query}'. Utilize your search tool to find relevant documents and data. Focus on accuracy and relevance.",
            agent=agent,
            expected_output="A JSON string containing a list of search results, including document text, source, and relevance score for each result."
        )

    def summarize_task(self, agent, query, search_context_task):
        return Task(
            description=f"Summarize the search results related to the query: '{query}'. Your summary should be concise, directly answer the query, and be based *only* on the provided search results. Do not add external information.",
            agent=agent,
            expected_output="A clear and concise summary of the information found in the search results, directly addressing the user's query.",
            context=[search_context_task]
        )

class RAGCrew:
    def __init__(self, llm=None):
        self.llm = llm if llm else get_llm_instance()
        self._setup_agents_and_tools()
        self._setup_tasks("dummy_query_for_initialization") # Tasks will be setup when execute_query is called, as they depend on the query
        self._setup_crew()

    def _setup_agents_and_tools(self):
        # Initialize tools
        self.search_tool = SearchTool()

        # Initialize agent classes
        rag_agent_defs = RAGAgents()

        # Instantiate specific agents
        self.search_agent_instance = rag_agent_defs.search_agent(self.llm, [self.search_tool])
        self.summarization_agent_instance = rag_agent_defs.summarization_agent(self.llm)

    def _setup_tasks(self, query: str):
        # Initialize task definer
        rag_task_defs = RAGTasks()

        # Define tasks with the specific query
        self.search_task_instance = rag_task_defs.search_task(self.search_agent_instance, query)
        self.summarize_task_instance = rag_task_defs.summarize_task(
            self.summarization_agent_instance,
            query,
            self.search_task_instance # Pass the search task as context
        )

    def _setup_crew(self):
        self.crew = Crew(
            agents=[self.search_agent_instance, self.summarization_agent_instance],
            # Tasks are dynamic and will be added during kickoff
            tasks=[],
            process=Process.sequential,
            verbose=True # Set to True for detailed logs, or 2 for even more detail
        )

    def execute_query(self, query: str):
        """
        Takes a user query, sets up the tasks dynamically for that query,
        and executes the RAG workflow.
        """
        # Setup tasks specifically for this query
        self._setup_tasks(query)

        # Update the crew's tasks
        self.crew.tasks = [self.search_task_instance, self.summarize_task_instance]

        # Kickoff the crew with the query as input to the first task
        # The 'inputs' dictionary allows passing specific data to the first task if its description uses placeholders.
        # However, our search_task description directly incorporates the query.
        # For CrewAI, the input to the first task is often implicitly handled if the description is clear.
        # If direct input passing is needed, it's usually like: inputs={'topic': query}
        # and the task description would use {topic}.
        # Here, the query is already in the task description.

        print(f"Executing RAG query: {query}")
        result = self.crew.kickoff() # inputs can be passed if tasks are structured to receive them

        return result


if __name__ == '__main__':
    # Example Usage
    print("Initializing RAG Crew...")
    rag_crew_instance = RAGCrew()

    sample_query_1 = "What are the latest AI advancements?"
    print(f"\n--- Running query: '{sample_query_1}' ---")
    crew_result_1 = rag_crew_instance.execute_query(sample_query_1)
    print(f"\n--- Result for query: '{sample_query_1}' ---")
    print(crew_result_1)

    # To demonstrate with a different query, the crew tasks get redefined
    sample_query_2 = "Tell me about Minecraft modding."
    print(f"\n--- Running query: '{sample_query_2}' ---")
    crew_result_2 = rag_crew_instance.execute_query(sample_query_2)
    print(f"\n--- Result for query: '{sample_query_2}' ---")
    print(crew_result_2)

    # If using a non-mock LLM, you might see actual LLM outputs.
    # With MockLLM, you'll see the predefined mock responses.
