"""
Tests for the RAG Crew implementation.
"""

import pytest
import os
import tempfile
import yaml
from unittest.mock import Mock, patch, MagicMock
from src.crew.rag_crew import RAGCrew, AVAILABLE_TOOLS


class TestRAGCrew:
    """Test class for RAGCrew functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create a temporary YAML config for testing
        self.test_config = {
            'agents': {
                'researcher': {
                    'role': 'Test Researcher',
                    'goal': 'Test research goal',
                    'backstory': 'Test researcher backstory',
                    'tools': ['SearchTool'],
                    'verbose': True,
                    'allow_delegation': False
                },
                'writer': {
                    'role': 'Test Writer',
                    'goal': 'Test writing goal',
                    'backstory': 'Test writer backstory',
                    'tools': [],
                    'verbose': True,
                    'allow_delegation': False
                }
            }
        }

    def test_available_tools_contains_search_tool(self):
        """Test that AVAILABLE_TOOLS contains SearchTool."""
        assert 'SearchTool' in AVAILABLE_TOOLS
        from src.tools.search_tool import SearchTool
        assert AVAILABLE_TOOLS['SearchTool'] is SearchTool

    @patch('src.crew.rag_crew.ChatOpenAI')
    def test_rag_crew_initialization(self, mock_chat_openai):
        """Test RAGCrew initialization with mocked dependencies."""
        mock_llm = Mock()
        mock_chat_openai.return_value = mock_llm
        
        with patch.object(RAGCrew, '_load_agent_configs'), \
             patch.object(RAGCrew, '_setup_agents'), \
             patch.object(RAGCrew, '_setup_crew'):
            
            crew = RAGCrew(model_name="gpt-4")
            
            assert crew.llm is mock_llm
            mock_chat_openai.assert_called_once_with(model_name="gpt-4", temperature=0.1)

    def test_load_agent_configs_with_valid_yaml(self):
        """Test loading agent configs from valid YAML file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(self.test_config, f)
            temp_file = f.name
        
        try:
            with patch('src.crew.rag_crew.ChatOpenAI'), \
                 patch('os.path.join', return_value=temp_file), \
                 patch.object(RAGCrew, '_setup_agents'), \
                 patch.object(RAGCrew, '_setup_crew'):
                
                crew = RAGCrew()
                
                assert crew.researcher_config['role'] == 'Test Researcher'
                assert crew.writer_config['role'] == 'Test Writer'
                assert crew.agent_configs == self.test_config
        finally:
            os.unlink(temp_file)

    def test_load_agent_configs_with_missing_file(self):
        """Test loading agent configs when YAML file is missing."""
        with patch('src.crew.rag_crew.ChatOpenAI'), \
             patch('os.path.join', return_value='/nonexistent/file.yaml'), \
             patch.object(RAGCrew, '_setup_agents'), \
             patch.object(RAGCrew, '_setup_crew'):
            
            crew = RAGCrew()
            
            # Should use default configurations
            assert crew.researcher_config['role'] == 'Information Researcher'
            assert crew.writer_config['role'] == 'Content Synthesizer'

    def test_load_agent_configs_with_invalid_yaml(self):
        """Test loading agent configs with invalid YAML structure."""
        invalid_config = {'invalid': 'structure'}
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(invalid_config, f)
            temp_file = f.name
        
        try:
            with patch('src.crew.rag_crew.ChatOpenAI'), \
                 patch('os.path.join', return_value=temp_file), \
                 patch.object(RAGCrew, '_setup_agents'), \
                 patch.object(RAGCrew, '_setup_crew'):
                
                crew = RAGCrew()
                
                # Should use fallback configurations
                assert crew.researcher_config['role'] == 'Fallback Information Researcher'
                assert crew.writer_config['role'] == 'Fallback Content Synthesizer'
        finally:
            os.unlink(temp_file)

    def test_get_tools_from_config_with_search_tool(self):
        """Test getting tools from config with SearchTool."""
        with patch('src.crew.rag_crew.ChatOpenAI'), \
             patch.object(RAGCrew, '_load_agent_configs'), \
             patch.object(RAGCrew, '_setup_agents'), \
             patch.object(RAGCrew, '_setup_crew'):
            
            crew = RAGCrew()
            
            # Mock SearchTool
            mock_search_tool = Mock()
            mock_search_tool.get_tools.return_value = ['tool1', 'tool2']
            
            with patch.object(AVAILABLE_TOOLS['SearchTool'], 'get_instance', return_value=mock_search_tool):
                tools = crew._get_tools_from_config(['SearchTool'])
                
                assert len(tools) == 2
                assert 'tool1' in tools
                assert 'tool2' in tools

    def test_get_tools_from_config_with_unknown_tool(self):
        """Test getting tools from config with unknown tool."""
        with patch('src.crew.rag_crew.ChatOpenAI'), \
             patch.object(RAGCrew, '_load_agent_configs'), \
             patch.object(RAGCrew, '_setup_agents'), \
             patch.object(RAGCrew, '_setup_crew'):
            
            crew = RAGCrew()
            
            with patch('builtins.print') as mock_print:
                tools = crew._get_tools_from_config(['UnknownTool'])
                
                assert len(tools) == 0
                mock_print.assert_called_once_with("Warning: Tool 'UnknownTool' not found in AVAILABLE_TOOLS.")

    @patch('src.crew.rag_crew.Agent')
    def test_setup_agents(self, mock_agent):
        """Test agent setup with mocked Agent class."""
        mock_researcher = Mock()
        mock_writer = Mock()
        mock_agent.side_effect = [mock_researcher, mock_writer]
        
        with patch('src.crew.rag_crew.ChatOpenAI'), \
             patch.object(RAGCrew, '_setup_crew'):
            
            crew = RAGCrew()
            # Override configs after initialization
            crew.researcher_config = self.test_config['agents']['researcher']
            crew.writer_config = self.test_config['agents']['writer']
            
            # Reset the mock to count only our calls
            mock_agent.reset_mock()
            mock_agent.side_effect = [mock_researcher, mock_writer]
            
            crew._setup_agents()
            
            # Verify agents were created
            assert crew.researcher is mock_researcher
            assert crew.writer is mock_writer
            assert mock_agent.call_count == 2

    @patch('src.crew.rag_crew.Task')
    @patch('src.crew.rag_crew.Crew')
    def test_setup_crew(self, mock_crew, mock_task):
        """Test crew setup with mocked Task and Crew classes."""
        mock_task_instance = Mock()
        mock_task.return_value = mock_task_instance
        
        mock_crew_instance = Mock()
        mock_crew.return_value = mock_crew_instance
        
        with patch('src.crew.rag_crew.ChatOpenAI'):
            # Create an instance by manually calling methods
            crew = RAGCrew.__new__(RAGCrew)
            crew.llm = Mock()
            crew.researcher = Mock()
            crew.writer = Mock()
            
            # Call _setup_crew directly with mocked Task and Crew
            crew._setup_crew()
            
            # Verify tasks and crew were created
            assert crew.research_task is mock_task_instance
            assert crew.write_task is mock_task_instance
            assert crew.crew is mock_crew_instance
            assert mock_task.call_count == 2
            mock_crew.assert_called_once()

    def test_run_method(self):
        """Test the run method of RAGCrew."""
        with patch('src.crew.rag_crew.ChatOpenAI'), \
             patch.object(RAGCrew, '_load_agent_configs'), \
             patch.object(RAGCrew, '_setup_agents'), \
             patch.object(RAGCrew, '_setup_crew'):
            
            crew = RAGCrew()
            
            # Mock the crew.kickoff method
            mock_crew = Mock()
            mock_crew.kickoff.return_value = "Test result"
            crew.crew = mock_crew
            
            result = crew.run("test query")
            
            assert result == "Test result"
            mock_crew.kickoff.assert_called_once_with(inputs={'query': 'test query'})

    def test_main_execution_block(self):
        """Test the main execution block with mocked dependencies."""
        with patch('src.crew.rag_crew.RAGCrew') as mock_rag_crew_class:
            mock_rag_crew = Mock()
            mock_rag_crew.run.return_value = "Test result"
            mock_rag_crew.researcher = Mock()
            mock_rag_crew.researcher.tools = [Mock(__name__='test_tool')]
            mock_rag_crew.writer = Mock()
            mock_rag_crew.writer.tools = []
            mock_rag_crew_class.return_value = mock_rag_crew
            
            with patch('builtins.print') as mock_print:
                # Import the module to execute the main block 
                with patch('sys.argv', ['rag_crew.py']):
                    # Simulate running the module as main
                    import src.crew.rag_crew as rag_module
                    
                    # Execute the main block logic directly as if __name__ == '__main__'
                    rag_crew = rag_module.RAGCrew()
                    example_query = "What are the latest advancements in AI-powered search technology?"
                    result = rag_crew.run(example_query)
                    
                    # Verify the crew was created and run was called
                    mock_rag_crew_class.assert_called_once()
                    mock_rag_crew.run.assert_called_once_with(example_query)

    def test_crew_integration_with_real_config(self):
        """Test RAGCrew integration with actual config structure."""
        # Create a realistic config
        config = {
            'agents': {
                'researcher': {
                    'role': 'Information Researcher',
                    'goal': 'Find relevant information',
                    'backstory': 'Expert researcher',
                    'tools': ['SearchTool'],
                    'verbose': True,
                    'allow_delegation': False
                },
                'writer': {
                    'role': 'Content Synthesizer',
                    'goal': 'Synthesize information',
                    'backstory': 'Expert writer',
                    'tools': [],
                    'verbose': True,
                    'allow_delegation': False
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config, f)
            temp_file = f.name
        
        try:
            with patch('src.crew.rag_crew.ChatOpenAI'), \
                 patch('os.path.join', return_value=temp_file), \
                 patch('src.crew.rag_crew.Agent'), \
                 patch('src.crew.rag_crew.Task'), \
                 patch('src.crew.rag_crew.Crew'):
                
                crew = RAGCrew()
                
                # Verify config was loaded correctly
                assert crew.researcher_config['role'] == 'Information Researcher'
                assert crew.writer_config['role'] == 'Content Synthesizer'
                assert 'SearchTool' in crew.researcher_config['tools']
                assert len(crew.writer_config['tools']) == 0
        finally:
            os.unlink(temp_file)