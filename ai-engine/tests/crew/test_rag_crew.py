import pytest
import os
import json
from src.crew.rag_crew import RAGCrew

@pytest.fixture(autouse=True)
def set_mock_env_vars():
    """Fixture to set environment variables for mock AI responses."""
    original_mock_responses = os.getenv("MOCK_AI_RESPONSES")
    original_openai_api_key = os.getenv("OPENAI_API_KEY")

    os.environ["MOCK_AI_RESPONSES"] = "true"
    # Ensure OPENAI_API_KEY is set to something, even if mock, as some underlying libraries might check for its presence
    os.environ["OPENAI_API_KEY"] = "mock_key_for_testing"

    yield

    # Restore original environment variables
    if original_mock_responses is None:
        del os.environ["MOCK_AI_RESPONSES"]
    else:
        os.environ["MOCK_AI_RESPONSES"] = original_mock_responses

    if original_openai_api_key is None:
        if "OPENAI_API_KEY" in os.environ: # Check if it was set by this fixture
            del os.environ["OPENAI_API_KEY"]
    else:
        os.environ["OPENAI_API_KEY"] = original_openai_api_key

def test_rag_crew_initialization(set_mock_env_vars):
    """Test that RAGCrew initializes without errors using mock LLM."""
    try:
        crew = RAGCrew()
        assert crew is not None, "RAGCrew instance should not be None"
        assert crew.llm is not None, "LLM should be initialized"
        # Check if agents are initialized (basic check)
        assert crew.researcher is not None
        assert crew.writer is not None
        assert crew.crew is not None
        print("RAGCrew initialized successfully with mock LLM.")
    except Exception as e:
        pytest.fail(f"RAGCrew initialization failed: {e}")

def test_rag_crew_has_required_methods(set_mock_env_vars):
    """Test that RAGCrew has all required methods."""
    crew = RAGCrew()
    
    # Check required methods exist
    assert hasattr(crew, 'run'), "RAGCrew should have run method"
    assert hasattr(crew, 'execute_query'), "RAGCrew should have execute_query method"
    assert hasattr(crew, '_setup_agents'), "RAGCrew should have _setup_agents method"
    assert hasattr(crew, '_setup_crew'), "RAGCrew should have _setup_crew method"
    assert hasattr(crew, '_load_agent_configs'), "RAGCrew should have _load_agent_configs method"
    
    print("RAGCrew has all required methods.")

def test_rag_crew_search_tool_integration(set_mock_env_vars):
    """Test that SearchTool is properly integrated with RAGCrew."""
    from src.tools.search_tool import SearchTool
    
    # Test SearchTool directly
    SearchTool.get_instance()
    query = "Test query for search output structure"

    # Test the semantic search tool
    search_output = SearchTool.semantic_search.func(query)
    
    assert search_output is not None, "Search tool output should not be None"
    print(f"Search tool raw output: {search_output}")

    try:
        search_output_json = json.loads(search_output)
        assert isinstance(search_output_json, dict), "Search tool output should be a JSON dict"
        assert "query" in search_output_json, "Search output should have 'query' field"
        assert "results" in search_output_json, "Search output should have 'results' field"
        assert "total_results" in search_output_json, "Search output should have 'total_results' field"
        
        if search_output_json["results"]: # If the list is not empty
            assert isinstance(search_output_json["results"][0], dict), "Elements of the results list should be dictionaries"
            assert "content" in search_output_json["results"][0], "Each search result should have a 'content' field"
            assert "similarity_score" in search_output_json["results"][0], "Each search result should have a 'similarity_score' field"
        
        print("Search tool output structure is valid JSON with expected fields.")
    except json.JSONDecodeError:
        pytest.fail(f"Search tool output was not valid JSON: {search_output}")
    except AssertionError as e:
        pytest.fail(f"Search tool output JSON structure validation failed: {e}")

def test_rag_crew_agent_tools_loaded(set_mock_env_vars):
    """Test that RAGCrew agents have tools loaded correctly."""
    crew = RAGCrew()
    
    # Check that researcher has tools
    assert len(crew.researcher.tools) > 0, "Researcher should have tools loaded"
    
    # Check that writer has no tools (as expected)
    assert len(crew.writer.tools) == 0, "Writer should have no tools"
    
    print(f"Researcher tools: {[tool.__name__ if hasattr(tool, '__name__') else str(tool) for tool in crew.researcher.tools]}")
    print(f"Writer tools: {[tool.__name__ if hasattr(tool, '__name__') else str(tool) for tool in crew.writer.tools]}")

def test_rag_crew_tasks_setup(set_mock_env_vars):
    """Test that RAGCrew has tasks properly set up."""
    crew = RAGCrew()
    
    # Check tasks are created
    assert crew.research_task is not None, "Research task should be created"
    assert crew.write_task is not None, "Write task should be created"
    
    # Check task descriptions contain query placeholder
    assert "{query}" in crew.research_task.description, "Research task should contain query placeholder"
    assert "{query}" in crew.write_task.description, "Write task should contain query placeholder"
    
    # Check task context
    assert crew.research_task in crew.write_task.context, "Write task should have research task as context"
    
    print("RAGCrew tasks are properly set up.")

def test_rag_crew_config_loading(set_mock_env_vars):
    """Test that RAGCrew loads agent configurations properly."""
    crew = RAGCrew()
    
    # Check that agent configs are loaded
    assert hasattr(crew, 'researcher_config'), "Should have researcher config"
    assert hasattr(crew, 'writer_config'), "Should have writer config"
    
    # Check basic config structure
    assert crew.researcher_config.get('role') is not None, "Researcher should have role defined"
    assert crew.writer_config.get('role') is not None, "Writer should have role defined"
    
    print(f"Researcher role: {crew.researcher_config.get('role')}")
    print(f"Writer role: {crew.writer_config.get('role')}")

if __name__ == '__main__':
    # This allows running the tests directly with `python test_rag_crew.py`
    # You'd typically use `pytest`
    pytest.main([__file__])