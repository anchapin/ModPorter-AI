import pytest
import os
import json
from ai_engine.src.crew.rag_crew import RAGCrew

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

    print(f"Executing query: {query} with mock responses enabled.")
    result = crew.execute_query(query)

    assert result is not None, "Result from execute_query should not be None"
    print(f"Raw result from crew.kickoff(): {result}")

    # The mock LLM in RAGCrew is set up to return:
    # 1. Search tool output: json.dumps([{"id": "mock_doc1", "score": 0.9, "text": "This is a mock document from search."}])
    # 2. Summarization agent output: "Mock summarization based on search results."
    # The final result of a CrewAI kickoff is typically the output of the last task.
    assert isinstance(result, str), f"Result should be a string, but got {type(result)}"
    assert "Mock summarization based on search results." in result, \
        "The result should contain the mock summarization."
    print(f"Successfully executed query and received expected mock summarization: '{result}'")

def test_rag_crew_search_tool_mock_output_structure(set_mock_env_vars):
    """
    Test that the search_task (which uses SearchTool) within the RAGCrew
    produces an output that the summarization_task can handle, using mocks.
    """
    crew = RAGCrew()
    query = "Test query for search output structure"

    # Manually trigger the search task to inspect its output with mocks
    # This requires a bit of understanding of CrewAI internals or adapting the class for this test
    # For simplicity, we'll rely on the overall flow tested in test_rag_crew_execute_query_mock
    # and the SearchTool's own __main__ block for direct tool testing.
    # However, we can check the first task's output if the crew stores task outputs.

    # Kick off the crew
    crew.execute_query(query)

    # The search_task_instance is updated within execute_query
    search_task_output_raw = crew.search_task_instance.output.raw if crew.search_task_instance.output else None

    assert search_task_output_raw is not None, "Search task output should not be None after execution"
    print(f"Search task raw output: {search_task_output_raw}")

    try:
        search_output_json = json.loads(search_task_output_raw)
        assert isinstance(search_output_json, list), "Search task output should be a JSON list"
        if search_output_json: # If the list is not empty
            assert isinstance(search_output_json[0], dict), "Elements of the list should be dictionaries"
            assert "text" in search_output_json[0], "Each search result should have a 'text' field"
        print("Search task output structure is valid JSON with expected fields.")
    except json.JSONDecodeError:
        pytest.fail(f"Search task output was not valid JSON: {search_task_output_raw}")
    except AssertionError as e:
        pytest.fail(f"Search task output JSON structure validation failed: {e}")

if __name__ == '__main__':
    # This allows running the tests directly with `python test_rag_crew.py`
    # You'd typically use `pytest`
    pytest.main([__file__])
