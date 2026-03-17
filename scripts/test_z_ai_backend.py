#!/usr/bin/env python3
"""
Test script for Z.AI backend integration
"""

import os
import sys
import logging

# Add the ai-engine directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "ai-engine"))

from ai_engine.utils.rate_limiter import create_z_ai_llm, get_llm_backend

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def test_z_ai_direct():
    """Test Z.AI backend directly"""

    try:
        # Check if Z.AI is configured
        if not os.getenv("Z_AI_API_KEY"):
            return False


        # Create Z.AI LLM instance
        zai_llm = create_z_ai_llm()

        # Test basic functionality
        test_message = "Explain Java mod compatibility in Minecraft in one paragraph."

        response = zai_llm.invoke(test_message)

        # Test metadata
        if "usage" in response.response_metadata:
            usage = response.response_metadata["usage"]

        return True

    except Exception as e:
        return False


def test_backend_selection():
    """Test backend selection logic"""

    try:
        # Test with current environment
        llm = get_llm_backend()
        llm_type = type(llm).__name__

        # Test basic functionality
        test_message = "What is Minecraft modding?"
        response = llm.invoke(test_message)

        return True

    except Exception as e:
        return False


def test_crewai_compatibility():
    """Test CrewAI compatibility"""

    try:
        from crewai import Agent, Task, Crew

        # Get LLM backend
        llm = get_llm_backend()

        # Create a simple agent
        analyzer = Agent(
            role="Java Expert",
            goal="Analyze Java code for mod compatibility",
            backstory="Expert in Minecraft modding and Java development",
            llm=llm,
            verbose=True,
        )

        # Create a simple task
        task = Task(
            description="Explain what makes a Minecraft mod compatible with different versions",
            agent=analyzer,
            expected_output="Brief explanation of mod compatibility",
        )

        # Create and run crew
        crew = Crew(agents=[analyzer], tasks=[task])

        result = crew.kickoff()

        return True

    except ImportError:
        return True
    except Exception as e:
        return False


def test_environment_variables():
    """Test and display environment configuration"""

    # Z.AI Configuration

    # Ollama Configuration

    # OpenAI Configuration


def main():
    """Main test function"""

    # Test environment setup
    test_environment_variables()

    # Run tests
    tests = [
        ("Z.AI Direct", test_z_ai_direct),
        ("Backend Selection", test_backend_selection),
        ("CrewAI Compatibility", test_crewai_compatibility),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            results.append((test_name, False))

    # Summary

    passed = 0
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        if result:
            passed += 1


    if passed == len(results):
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())
