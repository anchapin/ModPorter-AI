
import pytest
from unittest.mock import MagicMock, patch
from crew.rag_crew import RAGCrew, get_llm_instance

class TestRAGCrew:
    @pytest.fixture
    def mock_dependencies(self):
        with patch('crew.rag_crew.ChatOpenAI') as mock_llm, \
             patch('crew.rag_crew.Agent') as mock_agent, \
             patch('crew.rag_crew.Task') as mock_task, \
             patch('crew.rag_crew.Crew') as mock_crew, \
             patch('crew.rag_crew.get_tool_registry') as mock_registry:
            
            mock_llm.return_value = MagicMock()
            mock_registry.return_value = MagicMock()
            
            yield {
                'ChatOpenAI': mock_llm,
                'Agent': mock_agent,
                'Task': mock_task,
                'Crew': mock_crew,
                'get_tool_registry': mock_registry
            }

    def test_get_llm_instance_mock(self):
        with patch.dict('os.environ', {'MOCK_AI_RESPONSES': 'true'}):
            llm = get_llm_instance()
            assert isinstance(llm, MagicMock)
            assert llm.invoke("test") == "Mock summarization based on search results."

    def test_rag_crew_initialization(self, mock_dependencies):
        crew = RAGCrew(model_name="gpt-4", use_tool_registry=True)
        assert crew.llm is not None
        assert mock_dependencies['get_tool_registry'].called
        assert mock_dependencies['Agent'].called
        assert mock_dependencies['Crew'].called

    def test_rag_crew_run(self, mock_dependencies):
        crew = RAGCrew(model_name="gpt-4")
        mock_crew_instance = mock_dependencies['Crew'].return_value
        mock_crew_instance.kickoff.return_value = "Search result"
        
        res = crew.run("test query")
        assert res == "Search result"
        mock_crew_instance.kickoff.assert_called_once()

    def test_get_system_status(self, mock_dependencies):
        crew = RAGCrew(model_name="gpt-4")
        # Mock researcher and writer tools
        crew.researcher = MagicMock()
        crew.researcher.tools = []
        crew.writer = MagicMock()
        crew.writer.tools = []
        
        status = crew.get_system_status()
        assert "llm_model" in status
        assert "total_agents" in status

    def test_test_web_search_integration_not_found(self, mock_dependencies):
        crew = RAGCrew(model_name="gpt-4")
        crew.researcher = MagicMock()
        crew.researcher.tools = [] # No web search tool
        
        res = crew.test_web_search_integration("query")
        assert res["status"] == "error"
        assert "not found" in res["message"]
