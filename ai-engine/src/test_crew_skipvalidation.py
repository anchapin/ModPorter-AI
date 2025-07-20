#!/usr/bin/env python3
"""
Test CrewAI with validation skipped
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

def test_crew_skip_validation():
    """Test CrewAI with validation skipped"""
    try:
        # Set environment variables
        os.environ["USE_OLLAMA"] = "true"
        os.environ["OLLAMA_MODEL"] = "llama3.2"
        os.environ["OLLAMA_BASE_URL"] = "http://localhost:11434"
        os.environ["CREW_AI_SKIP_VALIDATION"] = "true"
        
        from crewai import Agent, Task, Crew, Process
        from langchain_ollama import ChatOllama
        
        # Create raw ChatOllama instance
        llm = ChatOllama(
            model="llama3.2",
            base_url="http://localhost:11434",
            temperature=0.0,  # More deterministic
            num_predict=20,   # Very small output
            request_timeout=30,
            streaming=False
        )
        
        print("✅ Raw ChatOllama LLM created")
        
        # Create simple agent with raw LLM
        agent = Agent(
            role="Simple Agent",
            goal="Say exactly 'Hello world'",
            backstory="You are a simple agent that says exactly 'Hello world'.",
            verbose=True,
            allow_delegation=False,
            llm=llm,
            memory=False,
            tools=[]
        )
        
        print("✅ Agent created")
        
        # Create simple task
        task = Task(
            description="Say exactly 'Hello world' and nothing else.",
            agent=agent,
            expected_output="Hello world"
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
    success = test_crew_skip_validation()
    sys.exit(0 if success else 1)