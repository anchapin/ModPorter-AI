from crewai import Agent, Task, Crew, Process
from langchain_openai import ChatOpenAI
import os
import yaml

# Import the actual SearchTool
from ..tools.search_tool import SearchTool

# Mapping tool names from YAML to actual tool classes/functions
AVAILABLE_TOOLS = {
    "SearchTool": SearchTool
}

class RAGCrew:
    def __init__(self, model_name: str = "gpt-4"):
        self.llm = ChatOpenAI(model_name=model_name, temperature=0.1)
        self._load_agent_configs()
        self._setup_agents()
        self._setup_crew()

    def _load_agent_configs(self):
        # Construct the absolute path to the YAML file
        base_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(base_dir, "..", "config", "rag_agents.yaml")

        try:
            with open(config_path, 'r') as f:
                self.agent_configs = yaml.safe_load(f)
            if not self.agent_configs or 'agents' not in self.agent_configs:
                raise ValueError("YAML config is empty or missing 'agents' key.")
            self.researcher_config = self.agent_configs['agents']['researcher']
            self.writer_config = self.agent_configs['agents']['writer']
        except FileNotFoundError:
            print(f"ERROR: Agent configuration file not found at {config_path}")
            # Fallback to default configurations if YAML is not found
            self.researcher_config = {
                "role": "Default Information Researcher",
                "goal": "To find relevant information.",
                "backstory": "Default researcher.",
                "tools": [], "verbose": True, "allow_delegation": False
            }
            self.writer_config = {
                "role": "Default Content Synthesizer",
                "goal": "To synthesize information.",
                "backstory": "Default writer.",
                "tools": [], "verbose": True, "allow_delegation": False
            }
        except Exception as e:
            print(f"ERROR: Could not load or parse agent configurations: {e}")
            # Fallback for other errors
            self.researcher_config = {
                "role": "Fallback Information Researcher",
                "goal": "To find relevant information.",
                "backstory": "Fallback researcher.",
                "tools": [], "verbose": True, "allow_delegation": False
            }
            self.writer_config = {
                "role": "Fallback Content Synthesizer",
                "goal": "To synthesize information.",
                "backstory": "Fallback writer.",
                "tools": [], "verbose": True, "allow_delegation": False
            }


    def _get_tools_from_config(self, tool_names: list) -> list:
        tools_instances = []
        for tool_name in tool_names:
            if tool_name in AVAILABLE_TOOLS:
                # Get the SearchTool instance and its available tools
                tool_class = AVAILABLE_TOOLS[tool_name]
                if tool_name == "SearchTool":
                    # For SearchTool, get the instance and its available tools
                    search_tool_instance = tool_class.get_instance()
                    tools_instances.extend(search_tool_instance.get_tools())
                else:
                    # For other tools, instantiate normally
                    tools_instances.append(tool_class())
            else:
                print(f"Warning: Tool '{tool_name}' not found in AVAILABLE_TOOLS.")
        return tools_instances

    def _setup_agents(self):
        researcher_tools_config = self.researcher_config.get('tools', [])
        writer_tools_config = self.writer_config.get('tools', [])

        researcher_agent_tools = self._get_tools_from_config(researcher_tools_config)
        writer_agent_tools = self._get_tools_from_config(writer_tools_config)

        self.researcher = Agent(
            role=self.researcher_config['role'],
            goal=self.researcher_config['goal'],
            backstory=self.researcher_config['backstory'],
            verbose=self.researcher_config.get('verbose', True),
            allow_delegation=self.researcher_config.get('allow_delegation', False),
            llm=self.llm,
            tools=researcher_agent_tools
        )

        self.writer = Agent(
            role=self.writer_config['role'],
            goal=self.writer_config['goal'],
            backstory=self.writer_config['backstory'],
            verbose=self.writer_config.get('verbose', True),
            allow_delegation=self.writer_config.get('allow_delegation', False),
            llm=self.llm,
            tools=writer_agent_tools
        )

    def _setup_crew(self):
        self.research_task = Task(
            description="Use the SearchTool to find information relevant to the given query: {query}.",
            agent=self.researcher,
            expected_output="A comprehensive list of relevant information snippets and their sources."
        )

        self.write_task = Task(
            description="Synthesize the information provided by the Researcher Agent to answer the query: {query}. Ensure the output is a single, coherent, and well-written text.",
            agent=self.writer,
            expected_output="A well-synthesized answer to the query, based on the researched information.",
            context=[self.research_task]
        )

        self.crew = Crew(
            agents=[self.researcher, self.writer],
            tasks=[self.research_task, self.write_task],
            process=Process.sequential,
            verbose=True
        )

    def run(self, query: str):
        inputs = {'query': query}
        result = self.crew.kickoff(inputs=inputs)
        return result

if __name__ == '__main__':
    rag_crew = RAGCrew()
    example_query = "What are the latest advancements in AI-powered search technology?"

    print(f"Attempting to run RAG crew with query: '{example_query}'")
    # This will use the SearchToolPlaceholder
    try:
        result = rag_crew.run(example_query)
        print("\n\n########################")
        print("## RAG Crew Result:")
        print("########################\n")
        print(result)
    except Exception as e:
        print(f"An error occurred during RAG crew execution: {e}")
        print("This might be expected if SearchTool is a placeholder or has issues.")

    print(f"Loaded Researcher tools: {[tool.__name__ if hasattr(tool, '__name__') else str(tool) for tool in rag_crew.researcher.tools]}")
    print(f"Loaded Writer tools: {[tool.__name__ if hasattr(tool, '__name__') else str(tool) for tool in rag_crew.writer.tools]}")
