#!/usr/bin/env python3
"""
Test CrewAI with tools to identify parameter passing issues
"""

import os
import sys
import logging
import tempfile
from pathlib import Path

# Add the ai-engine directory to the Python path
sys.path.insert(0, os.path.dirname(__file__))

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_crew_with_tools():
    """Test CrewAI with tools to identify parameter passing issues"""
    try:
        # Set environment variables
        os.environ["USE_OLLAMA"] = "true"
        os.environ["OLLAMA_MODEL"] = "llama3.2"
        os.environ["OLLAMA_BASE_URL"] = "http://localhost:11434"
        
        from crewai import Agent, Task, Crew, Process
        from src.utils.rate_limiter import create_ollama_llm
        from src.agents.java_analyzer import JavaAnalyzerAgent
        
        # Create optimized Ollama LLM
        llm = create_ollama_llm(
            model_name="llama3.2",
            base_url="http://localhost:11434",
            temperature=0.1,
            max_tokens=512,
            request_timeout=120,
            num_ctx=2048,
            num_batch=256,
            num_thread=4,
            streaming=False
        )
        
        # Enable CrewAI mode
        if hasattr(llm, 'enable_crew_mode'):
            llm.enable_crew_mode()
            
        print("✅ LLM created and configured for CrewAI")
        
        # Create Java analyzer agent with tools
        analyzer_agent = JavaAnalyzerAgent()
        tools = analyzer_agent.get_tools()
        
        print(f"✅ JavaAnalyzerAgent has {len(tools)} tools:")
        for tool in tools:
            print(f"  - {tool.name}: {tool.description}")
        
        # Create agent with tools
        agent = Agent(
            role="Java Analysis Agent",
            goal="Analyze Java mod files using available tools",
            backstory="You are a specialized agent for analyzing Java mod files.",
            verbose=True,
            allow_delegation=False,
            llm=llm,
            memory=False,
            tools=tools
        )
        
        print("✅ Agent created with tools")
        
        # Create a test mod file
        test_mod = Path("/tmp/test_mod.jar")
        test_mod.write_text("fake mod content")
        
        # Create task that uses tools
        task = Task(
            description=f"""Use the extract_assets_tool to analyze the mod file at {test_mod}.
            Pass the mod_path parameter as a string: "{test_mod}"
            Keep the response brief and report any errors encountered.""",
            agent=agent,
            expected_output="Analysis results from extract_assets_tool or error message"
        )
        
        print("✅ Task created with tool usage")
        
        # Create crew
        crew = Crew(
            agents=[agent],
            tasks=[task],
            process=Process.sequential,
            verbose=True
        )
        
        print("✅ Crew created")
        
        # Test execution
        print("🚀 Starting crew execution with tools...")
        result = crew.kickoff()
        
        print(f"✅ Crew executed successfully: {result}")
        return True
        
    except Exception as e:
        print(f"❌ Crew tool test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_crew_with_tools()
    sys.exit(0 if success else 1)