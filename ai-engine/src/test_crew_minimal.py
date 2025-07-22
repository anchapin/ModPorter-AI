#!/usr/bin/env python3
"""
Test CrewAI with minimal setup to isolate LLM response processing issue
"""

import os
import sys
import logging
from pathlib import Path

# Add the ai-engine directory to the Python path
sys.path.insert(0, os.path.dirname(__file__))

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_crew_minimal():
    """Test CrewAI with minimal setup and no tool usage"""
    try:
        # Set environment variables
        os.environ["USE_OLLAMA"] = "true"
        os.environ["OLLAMA_MODEL"] = "llama3.2"
        os.environ["OLLAMA_BASE_URL"] = "http://localhost:11434"
        
        from crewai import Agent, Task, Crew, Process
        from src.utils.rate_limiter import create_ollama_llm
        
        # Create Ollama LLM
        llm = create_ollama_llm(
            model_name="llama3.2",
            base_url="http://localhost:11434",
            temperature=0.1,
            max_tokens=100,
            request_timeout=60,
            streaming=False
        )
        
        print("✅ LLM created")
        
        # Create simple agent with NO tools
        agent = Agent(
            role="Simple Agent",
            goal="Provide brief responses",
            backstory="You are a simple agent that provides brief, helpful responses.",
            verbose=True,
            allow_delegation=False,
            llm=llm,
            memory=False,
            tools=[]
        )
        
        print("✅ Agent created")
        
        # Create simple task
        task = Task(
            description="Say 'Hello world' and nothing else. Keep response under 10 words.",
            agent=agent,
            expected_output="A simple greeting message under 10 words"
        )
        
        print("✅ Task created")
        
        # Create crew
        crew = Crew(
            agents=[agent],
            tasks=[task],
            process=Process.sequential,
            verbose=True
        )
        
        print("✅ Crew created")
        
        # Test execution
        print("🚀 Starting crew execution...")
        result = crew.kickoff()
        
        print(f"✅ Crew executed successfully: {result}")
        return True
        
    except Exception as e:
        print(f"❌ Crew test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_crew_minimal()
    sys.exit(0 if success else 1)