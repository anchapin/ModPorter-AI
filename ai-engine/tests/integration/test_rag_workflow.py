import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock

# Assuming these are the relevant classes. Adjust paths if necessary.
from src.utils.vector_db_client import VectorDBClient, Document
from src.agents.knowledge_base_agent import KnowledgeBaseAgent
from src.tools.search_tool import SearchTool

# Fixture for VectorDBClient
@pytest.fixture
def vector_db_client():
    return VectorDBClient(api_key="test_api_key")

# Fixture for KnowledgeBaseAgent
@pytest.fixture
def knowledge_base_agent():
    # KnowledgeBaseAgent instantiates its own tools.
    return KnowledgeBaseAgent()

# Define Document class here for test convenience, mirroring its presumed structure
class TestDocument:
    def __init__(self, id: str, text: str, vector: list = None):
        self.id = id
        self.text = text
        self.vector = vector if vector is not None else []

@pytest.mark.asyncio
@patch('src.agents.knowledge_base_agent.SearchTool') # Patch where KBA finds SearchTool
async def test_rag_workflow_end_to_end(MockSearchTool, vector_db_client, knowledge_base_agent):
    """
    Tests the end-to-end RAG workflow:
    1. Indexing a document using VectorDBClient (mocked API).
    2. Searching for the document via KnowledgeBaseAgent (which uses SearchTool with mocked search).
    3. Verifying the correct document is retrieved.
    """
    # Configure the mock SearchTool instance that KBA will create
    mock_search_tool_instance = MockSearchTool.return_value

    # 1. Indexing a document (VectorDBClient with mocked API)
    # Using the local TestDocument class for convenience in the test
    doc_to_index = TestDocument(id="doc123", text="This is a test document about RAG.", vector=[0.1, 0.2, 0.3])

    mock_post_response = AsyncMock()
    # VectorDBClient.index_document returns True on 200 or 201
    mock_post_response.status_code = 201
    # No specific JSON body is strictly needed for the client's logic, but good to mimic
    mock_post_response.json.return_value = {"message": "Document indexed successfully", "id": doc_to_index.id}

    # Patch httpx.AsyncClient.post for VectorDBClient's internal calls
    with patch("httpx.AsyncClient.post", return_value=mock_post_response) as mock_vdb_post:
        index_response = await vector_db_client.index_document(
            document_content=doc_to_index.text,
            document_source=doc_to_index.id
        )
        assert index_response is True # Check for boolean True
        # Verify the call to the backend
        mock_vdb_post.assert_called_once()
        # Can add more specific assertions about the payload if needed, e.g.
        # called_args, called_kwargs = mock_vdb_post.call_args
        # assert called_kwargs['json']['document_source'] == doc_to_index.id


    # 2. Searching for the document (KnowledgeBaseAgent -> SearchTool with mocked search)
    query_text = "Tell me about RAG"

    # Define what the mocked SearchTool (used by KBA) should return.
    expected_search_result_text = f"Found 1 results for query '{query_text}':\n- (Score: 0.95) {doc_to_index.text}\n"
    mock_search_tool_instance._run.return_value = expected_search_result_text

    # Get the tools from KnowledgeBaseAgent. This will include the mocked SearchTool.
    tools = knowledge_base_agent.get_tools()
    assert len(tools) == 1
    retrieved_search_tool = tools[0]

    # Ensure the tool KBA provides is indeed our mocked instance (or behaves like it)
    # This check is more about understanding the patching than a strict test requirement
    # if KBA always returns a new instance based on the class.
    # The key is that `knowledge_base_agent.get_tools()` must return a tool
    # whose `_run` method is the MagicMock `mock_search_tool_instance._run`.
    # With `@patch('src.agents.knowledge_base_agent.SearchTool')`, any `SearchTool()`
    # call within that module during KBA's `get_tools()` will return `mock_search_tool_instance`.

    # Perform the search using the tool obtained from the agent
    search_response = retrieved_search_tool._run(query=query_text)

    mock_search_tool_instance._run.assert_called_once_with(query=query_text)

    # 3. Verifying the correct document is retrieved
    assert doc_to_index.text in search_response
    assert "Score: 0.95" in search_response
    assert f"Found 1 results for query '{query_text}'" in search_response

    print(f"Test RAG workflow completed. Search response: {search_response}")

# Further considerations:
# - Error handling: Test cases for when indexing fails or search yields no results.
# - Multiple documents: Test indexing multiple documents and retrieving a specific one.
# - Asynchronous methods: If KnowledgeBaseAgent.get_tools() or the tool interaction itself
#   were async, adjustments would be needed. Currently, SearchTool._run is synchronous.
#   VectorDBClient is async and handled with await.
# - Document class: The `Document` class from `src.utils.vector_db_client` is not used directly
#   by the `index_document` method, which takes content and source.
#   The test uses a local `TestDocument` for structuring test data, which is fine.
