
import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from pathlib import Path
from crew.conversion_crew import ModPorterConversionCrew

class TestModPorterConversionCrew:
    @pytest.fixture
    def mock_crewai(self):
        with patch('crew.conversion_crew.Agent') as mock_agent, \
             patch('crew.conversion_crew.Task') as mock_task, \
             patch('crew.conversion_crew.Crew') as mock_crew, \
             patch('crew.conversion_crew.Process') as mock_process, \
             patch('crew.conversion_crew.create_rate_limited_llm') as mock_llm, \
             patch('crew.conversion_crew.create_ollama_llm') as mock_ollama:
            mock_llm.return_value = MagicMock()
            mock_ollama.return_value = MagicMock()
            yield {
                'Agent': mock_agent,
                'Task': mock_task,
                'Crew': mock_crew,
                'Process': mock_process,
                'create_rate_limited_llm': mock_llm,
                'create_ollama_llm': mock_ollama
            }

    @pytest.fixture
    def mock_agents(self):
        with patch('crew.conversion_crew.JavaAnalyzerAgent') as mock_java, \
             patch('crew.conversion_crew.BedrockArchitectAgent') as mock_architect, \
             patch('crew.conversion_crew.LogicTranslatorAgent') as mock_logic, \
             patch('crew.conversion_crew.AssetConverterAgent') as mock_asset, \
             patch('crew.conversion_crew.PackagingAgent') as mock_packaging, \
             patch('crew.conversion_crew.QAValidatorAgent') as mock_qa:
            yield {
                'JavaAnalyzerAgent': mock_java,
                'BedrockArchitectAgent': mock_architect,
                'LogicTranslatorAgent': mock_logic,
                'AssetConverterAgent': mock_asset,
                'PackagingAgent': mock_packaging,
                'QAValidatorAgent': mock_qa
            }

    def test_initialization(self, mock_crewai, mock_agents):
        crew = ModPorterConversionCrew()
        assert crew.llm is not None
        assert mock_agents['JavaAnalyzerAgent'].called
        assert mock_agents['BedrockArchitectAgent'].called
        
    def test_should_use_enhanced_orchestration(self, mock_crewai, mock_agents):
        crew = ModPorterConversionCrew()
        
        # Test default
        assert crew._should_use_enhanced_orchestration(None) is True
        
        # Test variant
        assert crew._should_use_enhanced_orchestration("parallel_basic") is True
        assert crew._should_use_enhanced_orchestration("control") is False
        
        # Test env override
        with patch.dict('os.environ', {'USE_ENHANCED_ORCHESTRATION': 'false'}):
            assert crew._should_use_enhanced_orchestration(None) is False

    @patch('crew.conversion_crew.EnhancedConversionCrew')
    def test_convert_mod_enhanced(self, mock_enhanced_cls, mock_crewai, mock_agents):
        mock_enhanced = mock_enhanced_cls.return_value
        mock_enhanced.convert_mod.return_value = {"status": "completed"}
        
        crew = ModPorterConversionCrew(variant_id="parallel_basic")
        res = crew.convert_mod(Path("test.jar"), Path("out/"))
        
        assert res["status"] == "completed"
        assert mock_enhanced.convert_mod.called

    def test_convert_block_mvp_success(self, mock_crewai, mock_agents):
        crew = ModPorterConversionCrew()
        
        # Mock agent methods
        crew.java_analyzer_agent.analyze_jar_for_mvp.return_value = {
            "success": True,
            "registry_name": "test:block",
            "properties": {"hardness": 1.0}
        }
        crew.logic_translator_agent.generate_bedrock_block_json.return_value = {
            "success": True,
            "block_name": "test:block",
            "block_json": {"format_version": "1.20.10"}
        }
        crew.logic_translator_agent._validate_block_json.return_value = {"is_valid": True}
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.mkdir'), \
             patch('builtins.open', MagicMock()):
            
            res = crew.convert_block_mvp(Path("test.jar"), Path("out/"))
            
            assert res["status"] == "completed"
            assert res["block_json"] == {"format_version": "1.20.10"}

    def test_convert_block_mvp_failure(self, mock_crewai, mock_agents):
        crew = ModPorterConversionCrew()
        
        crew.java_analyzer_agent.analyze_jar_for_mvp.return_value = {
            "success": False,
            "errors": ["Some error"]
        }
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.mkdir'):
            
            res = crew.convert_block_mvp(Path("test.jar"), Path("out/"))
            
            assert res["status"] == "failed"
            assert "Some error" in res["errors"][0]
