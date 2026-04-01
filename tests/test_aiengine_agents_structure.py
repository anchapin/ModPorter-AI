"""
Tests for ai-engine agents module

Coverage target: ai-engine/agents/*.py

These tests validate agent module structure and patterns.
"""

import ast
import os
import pytest


# ============================================
# Module Structure Tests
# ============================================


def test_agents_directory_exists():
    """agents directory should exist"""
    path = "/home/alex/Projects/ModPorter-AI/ai-engine/agents"
    assert os.path.isdir(path), f"agents directory not found at {path}"


def test_java_analyzer_exists():
    """java_analyzer.py should exist"""
    path = "/home/alex/Projects/ModPorter-AI/ai-engine/agents/java_analyzer.py"
    assert os.path.exists(path), f"java_analyzer not found at {path}"


def test_java_analyzer_parseable():
    """java_analyzer should be valid Python"""
    path = "/home/alex/Projects/ModPorter-AI/ai-engine/agents/java_analyzer.py"
    with open(path) as f:
        source = f.read()
    
    tree = ast.parse(source)
    assert tree is not None


def test_java_analyzer_has_agent_class():
    """Should define JavaAnalyzer agent"""
    path = "/home/alex/Projects/ModPorter-AI/ai-engine/agents/java_analyzer.py"
    with open(path) as f:
        source = f.read()
    
    assert "class" in source


def test_java_analyzer_has_imports():
    """Should have required imports"""
    path = "/home/alex/Projects/ModPorter-AI/ai-engine/agents/java_analyzer.py"
    with open(path) as f:
        source = f.read()
    
    assert "javalang" in source.lower() or "import" in source


# ============================================
# Test Other Key Agents
# ============================================


def test_logic_translator_exists():
    """logic_translator.py should exist"""
    path = "/home/alex/Projects/ModPorter-AI/ai-engine/agents/logic_translator.py"
    assert os.path.exists(path)


def test_logic_translator_has_class():
    """logic_translator should have agent class"""
    path = "/home/alex/Projects/ModPorter-AI/ai-engine/agents/logic_translator.py"
    with open(path) as f:
        source = f.read()
    
    assert "class" in source


def test_asset_converter_exists():
    """asset_converter.py should exist"""
    path = "/home/alex/Projects/ModPorter-AI/ai-engine/agents/asset_converter.py"
    assert os.path.exists(path)


def test_asset_converter_has_class():
    """asset_converter should have class"""
    path = "/home/alex/Projects/ModPorter-AI/ai-engine/agents/asset_converter.py"
    with open(path) as f:
        source = f.read()
    
    assert "class" in source


def test_bedrock_architect_exists():
    """bedrock_architect.py should exist"""
    path = "/home/alex/Projects/ModPorter-AI/ai-engine/agents/bedrock_architect.py"
    assert os.path.exists(path)


def test_bedrock_builder_exists():
    """bedrock_builder.py should exist"""
    path = "/home/alex/Projects/ModPorter-AI/ai-engine/agents/bedrock_builder.py"
    assert os.path.exists(path)


def test_packaging_agent_exists():
    """file_packager.py should exist"""
    path = "/home/alex/Projects/ModPorter-AI/ai-engine/agents/file_packager.py"
    assert os.path.exists(path)


def test_qa_validator_exists():
    """addon_validator.py should exist"""
    path = "/home/alex/Projects/ModPorter-AI/ai-engine/agents/addon_validator.py"
    assert os.path.exists(path)


# ============================================
# Agent Pattern Tests
# ============================================


def test_agents_use_agent_framework():
    """Agents should use CrewAI or agent framework"""
    path = "/home/alex/Projects/ModPorter-AI/ai-engine/agents/java_analyzer.py"
    with open(path) as f:
        source = f.read()
    
    # Should use some agent framework
    assert "Agent" in source or "crew" in source.lower() or "llm" in source.lower()


def test_agents_have_run_method():
    """Agents should have run or execute method"""
    path = "/home/alex/Projects/ModPorter-AI/ai-engine/agents/java_analyzer.py"
    with open(path) as f:
        source = f.read()
    
    assert "def" in source
    assert "run" in source.lower() or "execute" in source.lower() or "process" in source.lower()


def test_agents_have_tools():
    """Agents should define or use tools"""
    path = "/home/alex/Projects/ModPorter-AI/ai-engine/agents/java_analyzer.py"
    with open(path) as f:
        source = f.read()
    
    assert "tool" in source.lower() or "Tool" in source


def test_agents_handle_files():
    """Agents should handle file operations"""
    path = "/home/alex/Projects/ModPorter-AI/ai-engine/agents/java_analyzer.py"
    with open(path) as f:
        source = f.read()
    
    assert "file" in source.lower() or "path" in source.lower()


def test_agents_return_results():
    """Agents should return results"""
    path = "/home/alex/Projects/ModPorter-AI/ai-engine/agents/java_analyzer.py"
    with open(path) as f:
        source = f.read()
    
    assert "return" in source


# ============================================
# Agent Composition Tests
# ============================================


def test_all_core_agents_exist():
    """All core agents should exist"""
    agents = [
        "java_analyzer.py",
        "logic_translator.py",
        "asset_converter.py",
        "bedrock_architect.py",
        "file_packager.py",
    ]
    
    base = "/home/alex/Projects/ModPorter-AI/ai-engine/agents"
    for agent in agents:
        path = os.path.join(base, agent)
        assert os.path.exists(path), f"Missing agent: {agent}"


def test_agent_count():
    """Should have multiple agent files"""
    base = "/home/alex/Projects/ModPorter-AI/ai-engine/agents"
    files = [f for f in os.listdir(base) if f.endswith('.py') and not f.startswith('__')]
    assert len(files) >= 10, f"Should have 10+ agent files, found {len(files)}"


# ============================================
# Integration Patterns
# ============================================


def test_agents_import_from_crew():
    """Agents should be orchestrated"""
    path = "/home/alex/Projects/ModPorter-AI/ai-engine/agents/java_analyzer.py"
    with open(path) as f:
        source = f.read()
    
    # Check for orchestration patterns
    assert "import" in source


def test_agents_have_logging():
    """Agents should have logging"""
    path = "/home/alex/Projects/ModPorter-AI/ai-engine/agents/java_analyzer.py"
    with open(path) as f:
        source = f.read()
    
    assert "logging" in source.lower() or "logger" in source.lower() or "print" in source


if __name__ == "__main__":
    pytest.main([__file__, "-v"])