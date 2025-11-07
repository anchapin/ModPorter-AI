from crewai import Agent
import os

# Initialize LLM using the same logic as conversion_crew.py
def get_llm():
    from utils.rate_limiter import create_rate_limited_llm, create_ollama_llm
    
    # Check for Ollama configuration first (for local testing)
    if os.getenv("USE_OLLAMA", "false").lower() == "true":
        try:
            ollama_model = os.getenv("OLLAMA_MODEL", "llama3.2")
            # Auto-detect Ollama base URL based on environment
            default_base_url = "http://ollama:11434" if os.getenv("DOCKER_ENVIRONMENT") else "http://localhost:11434"
            base_url = os.getenv("OLLAMA_BASE_URL", default_base_url)
            
            llm = create_ollama_llm(
                model_name=ollama_model,
                base_url=base_url,
                temperature=0.7,
                max_tokens=1024,  # Reduced for faster responses
                request_timeout=300,  # Extended timeout
                num_ctx=4096,  # Context window
                num_batch=512,  # Batch processing
                num_thread=8,  # Multi-threading
                streaming=False  # Disable streaming for consistency
            )
            
            # Enable CrewAI compatibility mode if the wrapper supports it
            if hasattr(llm, 'enable_crew_mode'):
                llm.enable_crew_mode()
                
            return llm
        except Exception as e:
            raise RuntimeError(f"Ollama LLM initialization failed: {e}")
    else:
        # Use OpenAI with rate limiting for production
        return create_rate_limited_llm(
            model_name="gpt-3.5-turbo",
            temperature=0.7,
            max_tokens=2048
        )

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
    from tools.search_tool import SearchTool # Adjust import if necessary

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
