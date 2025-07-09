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
        assert crew.search_agent_instance is not None
        assert crew.summarization_agent_instance is not None
        print("RAGCrew initialized successfully with mock LLM.")
    except Exception as e:
        pytest.fail(f"RAGCrew initialization failed: {e}")

def test_rag_crew_execute_query_mock(set_mock_env_vars):
    """Test the RAGCrew's execute_query method with mock responses."""
    crew = RAGCrew()
    query = "What are the latest AI advancements?"

    print(f"Testing query setup: {query} with mock responses enabled.")
    
    # Setup tasks for the query
    crew._setup_tasks(query)
    
    # Verify tasks are created properly
    assert crew.search_task_instance is not None, "Search task should be created"
    assert crew.summarize_task_instance is not None, "Summarize task should be created"
    
    # Verify task descriptions contain the query
    assert query in crew.search_task_instance.description, "Search task should contain query"
    assert query in crew.summarize_task_instance.description, "Summarize task should contain query"
    
    print(f"Tasks created successfully for query: '{query}'")

def test_rag_crew_search_tool_mock_output_structure(set_mock_env_vars):
    """
    Test that the SearchTool produces properly structured output
    """
    from src.tools.search_tool import SearchTool
    
    search_tool = SearchTool()
    query = "Test query for search output structure"

    # Test the search tool directly
    search_output = search_tool._run(query)
    
    assert search_output is not None, "Search tool output should not be None"
    print(f"Search tool raw output: {search_output}")

    try:
        search_output_json = json.loads(search_output)
        assert isinstance(search_output_json, list), "Search tool output should be a JSON list"
        if search_output_json: # If the list is not empty
            assert isinstance(search_output_json[0], dict), "Elements of the list should be dictionaries"
            assert "text" in search_output_json[0], "Each search result should have a 'text' field"
        print("Search tool output structure is valid JSON with expected fields.")
    except json.JSONDecodeError:
        pytest.fail(f"Search tool output was not valid JSON: {search_output}")
    except AssertionError as e:
        pytest.fail(f"Search tool output JSON structure validation failed: {e}")

if __name__ == '__main__':
    # This allows running the tests directly with `python test_rag_crew.py`
    # You'd typically use `pytest`
    pytest.main([__file__])
