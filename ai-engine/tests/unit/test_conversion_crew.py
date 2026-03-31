
import pytest
import json
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

    def test_initialization_ollama(self, mock_crewai, mock_agents):
        """Test initialization with Ollama enabled."""
        with patch.dict('os.environ', {'USE_OLLAMA': 'true', 'OLLAMA_MODEL': 'llama3'}):
            crew = ModPorterConversionCrew()
            assert mock_crewai['create_ollama_llm'].called
            # Check if ollama_model was passed correctly
            args, kwargs = mock_crewai['create_ollama_llm'].call_args
            assert kwargs['model'] == 'llama3'

    def test_convert_mod_original_path(self, mock_crewai, mock_agents):
        """Test convert_mod falling back to original crew."""
        with patch.dict('os.environ', {'USE_ENHANCED_ORCHESTRATION': 'false'}):
            crew = ModPorterConversionCrew()
            
            # Mock original crew kickoff
            mock_crew_instance = mock_crewai['Crew'].return_value
            mock_result = MagicMock()
            mock_result.raw = "success"
            mock_result.tasks_output = []
            mock_crew_instance.kickoff.return_value = mock_result
            
            # Manually set crew to avoid _setup_crew issues
            crew.crew = mock_crew_instance
            
            with patch('pathlib.Path.exists', return_value=True), \
                 patch('tempfile.mkdtemp', return_value="/tmp/test"), \
                 patch('shutil.rmtree'):
                
                res = crew.convert_mod(Path("/app/test.jar"), Path("/app/out"))
                assert res["status"] == "completed"
                assert mock_crew_instance.kickoff.called

    def test_convert_mod_file_not_found(self, mock_crewai, mock_agents):
        """Test convert_mod with missing file."""
        with patch.dict('os.environ', {'USE_ENHANCED_ORCHESTRATION': 'false'}):
            crew = ModPorterConversionCrew()
            with patch('pathlib.Path.exists', return_value=False):
                res = crew.convert_mod(Path("missing.jar"), Path("out"))
                assert res["status"] == "failed"
                assert "Mod file not found" in res["error"]

    def test_extract_plan_components(self, mock_crewai, mock_agents):
        """Test plan component extraction from crew result."""
        crew = ModPorterConversionCrew()
        
        # Mock crew result with tasks_output
        mock_result = MagicMock()
        mock_task_output = MagicMock()
        mock_task_output.raw = json.dumps({
            "components": [
                {
                    "original_feature_id": "feat1",
                    "original_feature_type": "block",
                    "assumption_type": "proxy",
                    "bedrock_equivalent": "stone",
                    "impact_level": "low",
                    "user_explanation": "exp"
                }
            ]
        })
        mock_result.tasks_output = [MagicMock(), mock_task_output] # Plan is index 1
        
        components = crew._extract_plan_components(mock_result)
        assert len(components) == 1
        assert components[0].original_feature_id == "feat1"

    def test_format_conversion_report(self, mock_crewai, mock_agents):
        """Test conversion report formatting."""
        crew = ModPorterConversionCrew()
        mock_result = MagicMock()
        mock_task_output = MagicMock()
        mock_task_output.raw = "Success result"
        mock_result.tasks_output = [mock_task_output]
        
        from models.smart_assumptions import ConversionPlanComponent
        comp = ConversionPlanComponent(
            original_feature_id="f", original_feature_type="t", 
            assumption_type="a", bedrock_equivalent="e", 
            impact_level="low", user_explanation="exp"
        )
        
        # Mock smart_assumption_engine
        crew.smart_assumption_engine = MagicMock()
        mock_report = MagicMock()
        mock_report.assumptions_applied = []
        crew.smart_assumption_engine.generate_assumption_report.return_value = mock_report
        
        report = crew._format_conversion_report(mock_result, [comp])
        assert report["status"] == "completed"
        assert "overall_success_rate" in report

    def test_get_conversion_crew_status(self, mock_crewai, mock_agents):
        """Test status retrieval."""
        crew = ModPorterConversionCrew()
        crew.smart_assumption_engine = MagicMock()
        status = crew.get_conversion_crew_status()
        assert status["agents_initialized"]["java_analyzer"] is True
        assert status["smart_assumption_engine"]["initialized"] is True

    def test_convert_blocks_batch_mvp(self, mock_crewai, mock_agents):
        """Test batch conversion MVP."""
        crew = ModPorterConversionCrew()
        with patch.object(crew, 'convert_block_mvp') as mock_convert:
            mock_convert.return_value = {"status": "completed", "output_path": "out.json"}
            
            res = crew.convert_blocks_batch_mvp([Path("a.jar"), Path("b.jar")], Path("out/"))
            assert res["total"] == 2
            assert res["successful"] == 2
            assert len(res["conversions"]) == 2

    def test_get_pipeline_status(self, mock_crewai, mock_agents):
        """Test pipeline status retrieval."""
        crew = ModPorterConversionCrew()
        status = crew.get_pipeline_status()
        assert status["pipeline_type"] == "mvp_block_conversion"
        assert "stages" in status

    @pytest.mark.asyncio
    async def test_report_progress(self, mock_crewai, mock_agents):
        """Test progress reporting."""
        mock_callback = MagicMock()
        mock_callback.send_progress = AsyncMock()
        crew = ModPorterConversionCrew(progress_callback=mock_callback)
        
        await crew._report_progress("agent", "status", 50, "msg")
        mock_callback.send_progress.assert_called_once_with(
            agent="agent", status="status", progress=50, message="msg"
        )

from unittest.mock import AsyncMock
