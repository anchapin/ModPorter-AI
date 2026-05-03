"""
Unit tests for RAGCrew.
Tests initialization, agent setup, task creation, and tool integration.
"""

import pytest
from unittest.mock import MagicMock, patch, mock_open
import os
import yaml
from crew.rag_crew import RAGCrew, RAGTasks, get_llm_instance

@pytest.fixture
def mock_crewai():
    with patch('crew.rag_crew.Agent') as mock_agent, \
         patch('crew.rag_crew.Task') as mock_task, \
         patch('crew.rag_crew.Crew') as mock_crew, \
         patch('crew.rag_crew.Process') as mock_process, \
         patch('crew.rag_crew.ChatOpenAI') as mock_llm:
        yield {
            'Agent': mock_agent,
            'Task': mock_task,
            'Crew': mock_crew,
            'Process': mock_process,
            'ChatOpenAI': mock_llm
        }

@pytest.fixture
def mock_tools():
    with patch('crew.rag_crew.get_tool_registry') as mock_registry, \
         patch('crew.rag_crew.SearchTool') as mock_search, \
         patch('crew.rag_crew.WebSearchTool') as mock_web, \
         patch('crew.rag_crew.BedrockScraperTool') as mock_scraper:
        yield {
            'registry': mock_registry,
            'SearchTool': mock_search,
            'WebSearchTool': mock_web,
            'BedrockScraperTool': mock_scraper
        }

class TestRAGCrew:

    def test_initialization_basic(self, mock_crewai, mock_tools):
        """Test basic initialization of RAGCrew."""
        crew = RAGCrew(use_tool_registry=False)
        assert crew.llm is not None
        assert mock_crewai['Agent'].called
        assert mock_crewai['Crew'].called

    def test_initialization_with_registry(self, mock_crewai, mock_tools):
        """Test initialization with tool registry enabled."""
        mock_reg_instance = mock_tools['registry'].return_value
        mock_reg_instance.list_available_tools.return_value = []
        
        crew = RAGCrew(use_tool_registry=True)
        assert crew.tool_registry is not None
        mock_tools['registry'].assert_called_once()

    def test_load_agent_configs_fallback(self, mock_crewai, mock_tools):
        """Test fallback agent configs when YAML is missing."""
        with patch('builtins.open', side_effect=FileNotFoundError):
            crew = RAGCrew(use_tool_registry=False)
            assert crew.researcher_config["role"] == "Information Researcher"

    def test_load_agent_configs_invalid_yaml(self, mock_crewai, mock_tools):
        """Test fallback agent configs when YAML is invalid."""
        with patch('builtins.open', mock_open(read_data="invalid: yaml")), \
             patch('yaml.safe_load', return_value={}):
            crew = RAGCrew(use_tool_registry=False)
            assert "Fallback" in crew.researcher_config["role"]

    def test_get_tools_from_config_registry(self, mock_crewai, mock_tools):
        """Test loading tools from registry."""
        mock_reg = mock_tools['registry'].return_value
        mock_reg.get_tool_by_name.return_value = MagicMock()
        
        crew = RAGCrew(use_tool_registry=True)
        tools = crew._get_tools_from_config(["test_tool"])
        assert len(tools) == 1
        mock_reg.get_tool_by_name.assert_called_with("test_tool")

    def test_get_tools_from_config_legacy(self, mock_crewai, mock_tools):
        """Test loading tools from legacy AVAILABLE_TOOLS mapping."""
        with patch('crew.rag_crew.AVAILABLE_TOOLS') as mock_available:
            mock_web_class = MagicMock()
            mock_available.__contains__.side_effect = lambda x: x == "WebSearchTool"
            mock_available.__getitem__.side_effect = lambda x: mock_web_class if x == "WebSearchTool" else None
            
            crew = RAGCrew(use_tool_registry=False)
            
            # Test WebSearchTool
            tools = crew._get_tools_from_config(["WebSearchTool"])
            assert len(tools) == 1
            assert mock_web_class.called

    def test_run(self, mock_crewai, mock_tools):
        """Test running the crew."""
        crew = RAGCrew(use_tool_registry=False)
        mock_crew_instance = mock_crewai['Crew'].return_value
        mock_crew_instance.kickoff.return_value = "Search result"
        
        result = crew.run("test query")
        assert result == "Search result"
        mock_crew_instance.kickoff.assert_called_once_with(inputs={"query": "test query"})

    def test_execute_query(self, mock_crewai, mock_tools):
        """Test execute_query alias."""
        crew = RAGCrew(use_tool_registry=False)
        with patch.object(crew, 'run', return_value="ok") as mock_run:
            res = crew.execute_query("q")
            assert res == "ok"
            mock_run.assert_called_once_with("q")

    def test_get_available_tools(self, mock_crewai, mock_tools):
        """Test getting available tools list."""
        # Without registry
        crew = RAGCrew(use_tool_registry=False)
        tools = crew.get_available_tools()
        assert "SearchTool" in tools

        # With registry
        crew_reg = RAGCrew(use_tool_registry=True)
        mock_tools['registry'].return_value.list_available_tools.return_value = [{"name": "tool1"}]
        tools = crew_reg.get_available_tools()
        assert tools == [{"name": "tool1"}]

    def test_validate_tool_configuration(self, mock_crewai, mock_tools):
        """Test tool configuration validation."""
        crew = RAGCrew(use_tool_registry=True)
        mock_reg = mock_tools['registry'].return_value
        mock_reg.list_available_tools.return_value = [{"name": "t1", "description": "d1", "version": "v1"}]
        mock_reg.validate_tool_configuration.return_value = {
            "valid": True, "errors": [], "warnings": ["w1"]
        }
        
        res = crew.validate_tool_configuration()
        assert len(res["valid_tools"]) == 1
        assert res["valid_tools"][0]["name"] == "t1"
        assert "w1" in res["warnings"]

    def test_get_tool_registry_export(self, mock_crewai, mock_tools):
        """Test registry data export."""
        crew = RAGCrew(use_tool_registry=True)
        mock_reg = mock_tools['registry'].return_value
        mock_reg.export_registry.return_value = {"data": "..."}
        
        assert crew.get_tool_registry_export() == {"data": "..."}
        
        crew_no_reg = RAGCrew(use_tool_registry=False)
        assert "error" in crew_no_reg.get_tool_registry_export()

    def test_test_web_search_integration(self, mock_crewai, mock_tools):
        """Test web search integration test method."""
        crew = RAGCrew(use_tool_registry=False)
        # Manually add a mock WebSearchTool to researcher
        mock_web_instance = MagicMock()
        mock_web_instance.__class__.__name__ = "WebSearchTool"
        mock_web_instance._run.return_value = "results"
        crew.researcher.tools = [mock_web_instance]
        
        res = crew.test_web_search_integration("q")
        assert res["status"] == "success"
        assert res["result_preview"] == "results"

    def test_get_system_status(self, mock_crewai, mock_tools):
        """Test system status retrieval."""
        crew = RAGCrew(use_tool_registry=False)
        status = crew.get_system_status()
        assert status["total_agents"] == 0 # Mocked crew has no agents by default
        assert "tool_validation" in status

class TestRAGTasks:
    """Test RAGTasks class."""
    
    def test_tasks(self, mock_crewai):
        tasks = RAGTasks()
        # Use mock_crewai['Agent'] to get a valid-looking agent instance
        agent = mock_crewai['Agent'].return_value
        
        # Mock Task to avoid Pydantic validation if needed, 
        # but here we already patched Task in mock_crewai
        s_task = tasks.search_task(agent, "query")
        assert mock_crewai['Task'].called
        
        sum_task = tasks.summarize_task(agent, "query", s_task)
        assert mock_crewai['Task'].called

def test_get_llm_instance_mock():
    """Test get_llm_instance with mock enabled."""
    with patch.dict('os.environ', {'MOCK_AI_RESPONSES': 'true'}):
        llm = get_llm_instance()
        assert llm.invoke("test") == "Mock summarization based on search results."

def test_get_llm_instance_real():
    """Test get_llm_instance with real LLM (mocked ChatOpenAI)."""
    with patch.dict('os.environ', {'MOCK_AI_RESPONSES': 'false'}):
        with patch('crew.rag_crew.ChatOpenAI') as mock_chat:
            get_llm_instance()
            mock_chat.assert_called_once()
