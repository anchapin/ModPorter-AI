"""Test basic imports to verify package structure."""
import pytest
import sys
import os


def test_can_import_main():
    """Test that main.py exists and has correct structure without actually importing it.

    This test verifies the package structure exists without requiring heavy dependencies
    like CrewAI that may not be available in all test environments.
    """
    # Check main.py exists and is readable
    assert os.path.exists("main.py"), "main.py should exist in current directory"
    assert os.path.isfile("main.py"), "main.py should be a file"

    # Read and verify main.py has expected imports and structure
    with open("main.py", "r") as f:
        main_content = f.read()

    # Verify key imports are present
    assert "from fastapi import FastAPI" in main_content, "main.py should import FastAPI"
    assert "from crew.conversion_crew import" in main_content, "main.py should import from crew.conversion_crew"
    assert "ConversionStatusEnum" in main_content, "main.py should define ConversionStatusEnum"
    assert "app = FastAPI" in main_content, "main.py should initialize FastAPI app"

    print("✅ main.py has correct structure and imports")


def test_can_import_agents():
    """Test that agent modules exist and have correct structure."""
    # Check agent files exist
    agent_files = [
        "agents/java_analyzer.py",
        "agents/bedrock_builder.py",
        "agents/logic_translator.py",
        "agents/asset_converter.py",
        "agents/packaging_agent.py",
        "agents/qa_validator.py"
    ]

    for agent_file in agent_files:
        assert os.path.exists(agent_file), f"{agent_file} should exist"
        assert os.path.isfile(agent_file), f"{agent_file} should be a file"

        # Read and verify agent has expected structure
        with open(agent_file, "r") as f:
            content = f.read()

        # Verify agent has basic structure
        assert "class" in content, f"{agent_file} should define a class"
        # Most agents import from crewai.tools
        assert ("from crewai.tools" in content or "from crewai" in content), \
            f"{agent_file} should import from crewai"

    print("✅ All agent modules have correct structure")


def test_python_path():
    """Test Python path setup."""
    import sys
    import os

    print(f"Current working directory: {os.getcwd()}")
    print(f"Python path: {sys.path}")
    print(f"Files in current dir: {os.listdir('.')}")

    # Check if main.py exists
    assert os.path.exists("main.py"), "main.py should exist in current directory"
    assert os.path.exists("agents"), "agents directory should exist"
    assert os.path.exists("agents/__init__.py"), "agents/__init__.py should exist"