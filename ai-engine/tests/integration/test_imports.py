"""Test basic imports to verify package structure."""

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
    assert "from crew.conversion_crew import" in main_content, (
        "main.py should import from crew.conversion_crew"
    )
    assert "ConversionStatusEnum" in main_content, "main.py should define ConversionStatusEnum"
    assert "app = FastAPI" in main_content, "main.py should initialize FastAPI app"


def test_can_import_agents():
    """Test that agent modules exist and have correct structure."""
    # Check agent files exist
    # java_analyzer is now a package (directory), not a module (file)
    # For packages, we check the directory and the __init__.py file
    # For modules, we check the .py file
    agent_items = [
        ("agents/java_analyzer", "agents/java_analyzer/__init__.py"),  # package
        ("agents/bedrock_builder.py", None),  # module
        ("agents/logic_translator.py", None),  # module
        ("agents/asset_converter.py", None),  # module
        ("agents/packaging_agent.py", None),  # module
        ("agents/qa_validator.py", None),  # module
    ]

    for item_path, init_file in agent_items:
        is_package = init_file is not None
        if is_package:
            assert os.path.isdir(item_path), f"{item_path} should be a directory (package)"
            assert os.path.isfile(init_file), f"{init_file} should be a file"
            # Verify package has expected structure
            with open(init_file, "r") as f:
                content = f.read()
            assert "class" in content or "JavaAnalyzerAgent" in content, (
                f"{init_file} should define or re-export a class"
            )
        else:
            assert os.path.isfile(item_path), f"{item_path} should be a file"
            # Read and verify agent has expected structure
            with open(item_path, "r") as f:
                content = f.read()
            # Verify agent has basic structure
            assert "class" in content, f"{item_path} should define a class"
            # Most agents import from crewai.tools
            assert "from crewai.tools" in content or "from crewai" in content, (
                f"{item_path} should import from crewai"
            )


def test_python_path():
    """Test Python path setup."""
    import os

    # Check if main.py exists
    assert os.path.exists("main.py"), "main.py should exist in current directory"
    assert os.path.exists("agents"), "agents directory should exist"
    assert os.path.exists("agents/__init__.py"), "agents/__init__.py should exist"
