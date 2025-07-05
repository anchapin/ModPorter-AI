"""
Test-driven development for ModPorter AI Conversion Crew
Testing PRD Feature 2: AI Conversion Engine requirements
"""

import pytest
from unittest.mock import patch
from pathlib import Path
import tempfile

from src.crew.conversion_crew import ModPorterConversionCrew


class TestModPorterConversionCrew:
    """Test the main conversion crew functionality"""
    
    @pytest.fixture
    def conversion_crew(self):
        """Fixture providing a configured conversion crew"""
        with patch('src.crew.conversion_crew.ChatOpenAI'):
            crew = ModPorterConversionCrew(model_name="gpt-4")
            return crew
    
    @pytest.fixture
    def temp_mod_file(self):
        """Fixture providing a temporary mod file for testing"""
        with tempfile.NamedTemporaryFile(suffix='.jar', delete=False) as f:
            f.write(b'mock jar content')
            yield Path(f.name)
        Path(f.name).unlink()  # Cleanup
    
    @pytest.fixture
    def temp_output_dir(self):
        """Fixture providing a temporary output directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    def test_crew_initialization(self, conversion_crew):
        """Test PRD Feature 2: Multi-agent system initialization"""
        # Verify all required agents are created
        assert conversion_crew.java_analyzer is not None
        assert conversion_crew.bedrock_architect is not None
        assert conversion_crew.logic_translator is not None
        assert conversion_crew.asset_converter is not None
        assert conversion_crew.packaging_agent is not None
        assert conversion_crew.qa_validator is not None
        
        # Verify crew is properly configured
        assert conversion_crew.crew is not None
        assert len(conversion_crew.crew.agents) == 6
        assert len(conversion_crew.crew.tasks) == 6
    
    def test_agent_roles_match_prd(self, conversion_crew):
        """Test that agent roles match PRD Feature 2 specifications"""
        # PRD Feature 2: Analyzer Agent
        assert "Java Mod Analyzer" in conversion_crew.java_analyzer.role
        
        # PRD Feature 2: Planner Agent (Bedrock Architect)
        assert "Bedrock Conversion Architect" in conversion_crew.bedrock_architect.role
        
        # PRD Feature 2: Logic Translation Agent
        assert "Code Logic Translator" in conversion_crew.logic_translator.role
        
        # PRD Feature 2: Asset Conversion Agent
        assert "Asset Conversion Specialist" in conversion_crew.asset_converter.role
        
        # PRD Feature 2: Packaging Agent
        assert "Bedrock Package Builder" in conversion_crew.packaging_agent.role
        
        # PRD Feature 2: QA Agent
        assert "Quality Assurance Validator" in conversion_crew.qa_validator.role
    
    def test_task_sequence_follows_prd(self, conversion_crew):
        """Test that task sequence follows PRD conversion workflow"""
        tasks = conversion_crew.crew.tasks
        
        # Verify correct task order
        assert "analyze" in tasks[0].description.lower()
        assert "plan" in tasks[1].description.lower()
        assert "translate" in tasks[2].description.lower()
        assert "convert" in tasks[3].description.lower()
        assert "package" in tasks[4].description.lower()
        assert "validate" in tasks[5].description.lower()
        
        # Verify task dependencies are set correctly
        assert tasks[1].context == [tasks[0]]  # Plan depends on analyze
        assert tasks[0] in tasks[2].context  # Translate depends on analyze & plan
    
    @patch('src.crew.conversion_crew.Crew.kickoff')
    def test_convert_mod_success_flow(self, mock_kickoff, conversion_crew, temp_mod_file, temp_output_dir):
        """Test successful mod conversion following PRD requirements"""
        # Mock crew execution result
        mock_crew_result = {
            'analysis': {'features': ['blocks', 'items'], 'dependencies': []},
            'conversion_plan': {'smart_assumptions': ['dimension_to_structure']},
            'converted_files': ['behavior_pack/', 'resource_pack/'],
            'package_path': 'output.mcaddon'
        }
        mock_kickoff.return_value = mock_crew_result
        
        # Execute conversion
        result = conversion_crew.convert_mod(
            mod_path=temp_mod_file,
            output_path=temp_output_dir,
            smart_assumptions=True,
            include_dependencies=True
        )
        
        # Verify PRD Feature 3: Interactive Conversion Report structure
        assert 'status' in result
        assert 'overall_success_rate' in result
        assert 'converted_mods' in result
        assert 'failed_mods' in result
        assert 'smart_assumptions_applied' in result
        assert 'detailed_report' in result
        
        # Verify successful status
        assert result['status'] in ['completed', 'processing']
        assert isinstance(result['overall_success_rate'], (int, float))
        
        # Verify crew was called with correct inputs
        mock_kickoff.assert_called_once()
        call_args = mock_kickoff.call_args[1]['inputs']
        assert call_args['mod_path'] == str(temp_mod_file)
        assert call_args['smart_assumptions_enabled'] is True
        assert call_args['include_dependencies'] is True
    
    @patch('src.crew.conversion_crew.Crew.kickoff')
    def test_convert_mod_failure_handling(self, mock_kickoff, conversion_crew, temp_mod_file, temp_output_dir):
        """Test conversion failure handling and error reporting"""
        # Mock crew execution failure
        mock_kickoff.side_effect = Exception("Mock conversion error")
        
        # Execute conversion
        result = conversion_crew.convert_mod(
            mod_path=temp_mod_file,
            output_path=temp_output_dir
        )
        
        # Verify failure is properly handled per PRD requirements
        assert result['status'] == 'failed'
        assert result['overall_success_rate'] == 0.0
        assert len(result['failed_mods']) > 0
        assert 'Mock conversion error' in result['error']
        
        # Verify detailed report contains error information
        assert result['detailed_report']['stage'] == 'error'
        assert result['detailed_report']['progress'] == 0
    
    def test_smart_assumptions_integration(self, conversion_crew):
        """Test PRD smart assumptions are properly integrated"""
        # Verify smart assumption engine is initialized
        assert conversion_crew.smart_assumption_engine is not None
        
        # Test that assumption table is available
        assumption_table = conversion_crew.smart_assumption_engine.get_assumption_table()
        assert assumption_table is not None
        
        # Verify PRD table entries are present
        expected_features = [
            'custom_dimensions',
            'complex_machinery', 
            'custom_gui',
            'client_side_rendering',
            'mod_dependencies'
        ]
        
        for feature in expected_features:
            assert any(feature.replace('_', ' ').lower() in str(assumption).lower() 
                      for assumption in assumption_table)


class TestAgentSpecialization:
    """Test individual agent capabilities per PRD specifications"""
    
    @pytest.fixture
    def mock_agents(self):
        """Mock agents for isolated testing"""
        with patch('src.crew.conversion_crew.ChatOpenAI'):
            crew = ModPorterConversionCrew()
            return crew
    
    def test_java_analyzer_capabilities(self, mock_agents):
        """Test PRD Feature 2: Analyzer Agent requirements"""
        analyzer = mock_agents.java_analyzer
        
        # Verify analyzer can identify required elements per PRD
        expected_capabilities = [
            'assets', 'code logic', 'dependencies', 'feature types'
        ]
        
        goal_and_backstory = f"{analyzer.goal} {analyzer.backstory}".lower()
        
        for capability in expected_capabilities:
            assert capability in goal_and_backstory
    
    def test_bedrock_architect_smart_assumptions(self, mock_agents):
        """Test PRD Feature 2: Planner Agent (Smart Assumptions)"""
        architect = mock_agents.bedrock_architect
        
        # Verify architect understands smart assumptions concept
        role_description = f"{architect.role} {architect.goal} {architect.backstory}".lower()
        
        assert 'smart assumptions' in role_description or 'workarounds' in role_description
        assert 'bedrock' in role_description
        assert 'limitations' in role_description or 'compromises' in role_description
    
    def test_logic_translator_paradigm_shift(self, mock_agents):
        """Test PRD Feature 2: Logic Translation Agent handles paradigm shift"""
        translator = mock_agents.logic_translator
        
        description = f"{translator.role} {translator.goal} {translator.backstory}".lower()
        
        # Verify understanding of both paradigms
        assert 'java' in description and 'javascript' in description
        assert 'object-oriented' in description or 'event-driven' in description
        assert 'api' in description
    
    def test_asset_converter_format_handling(self, mock_agents):
        """Test PRD Feature 2: Asset Conversion Agent format requirements"""
        converter = mock_agents.asset_converter
        
        description = f"{converter.role} {converter.goal} {converter.backstory}".lower()
        
        # Verify asset type handling
        asset_types = ['textures', 'models', 'sounds']
        for asset_type in asset_types:
            assert asset_type in description or asset_type[:-1] in description
        
        assert 'bedrock' in description
        assert 'format' in description
    
    def test_packaging_agent_mcaddon_creation(self, mock_agents):
        """Test PRD Feature 2: Packaging Agent .mcaddon creation"""
        packager = mock_agents.packaging_agent
        
        description = f"{packager.role} {packager.goal} {packager.backstory}".lower()
        
        assert 'mcaddon' in description or 'add-on' in description
        assert 'manifest' in description or 'package' in description
        assert 'structure' in description
    
    def test_qa_validator_report_generation(self, mock_agents):
        """Test PRD Feature 2: QA Agent report generation"""
        validator = mock_agents.qa_validator
        
        description = f"{validator.role} {validator.goal} {validator.backstory}".lower()
        
        assert 'quality' in description or 'validate' in description
        assert 'report' in description
        assert 'test' in description or 'check' in description


class TestSmartAssumptionEngine:
    """Test smart assumption logic per PRD specifications"""
    
    @pytest.fixture
    def assumption_engine(self):
        """Fixture providing smart assumption engine"""
        from src.models.smart_assumptions import SmartAssumptionEngine
        return SmartAssumptionEngine()
    
    def test_prd_assumption_table_coverage(self, assumption_engine):
        """Test that all PRD table assumptions are implemented"""
        table = assumption_engine.get_assumption_table()
        
        # PRD Table of Smart Assumptions coverage
        prd_assumptions = {
            'custom_dimensions': 'skybox.*structure.*overworld',
            'complex_machinery': 'decorative.*container',
            'custom_gui': 'books.*signs',
            'client_side_rendering': 'exclude.*notification',
            'mod_dependencies': 'bundle.*flag.*critical'
        }
        
        for assumption_key, pattern in prd_assumptions.items():
            # Find matching assumption in table
            found = False
            for assumption in table:
                if any(keyword in str(assumption).lower() 
                      for keyword in assumption_key.split('_')):
                    found = True
                    break
            
            assert found, f"PRD assumption '{assumption_key}' not found in table"
    
    def test_assumption_application_logic(self, assumption_engine):
        """Test smart assumption application follows PRD logic"""
        # Test custom dimension assumption
        result = assumption_engine.apply_assumption(
            feature_type='custom_dimension',
            feature_data={'name': 'twilight_forest', 'biomes': ['dark_forest']}
        )
        
        assert result is not None
        assert 'structure' in str(result).lower() or 'overworld' in str(result).lower()
        
        # Test complex machinery assumption  
        machinery_result = assumption_engine.apply_assumption(
            feature_type='complex_machinery',
            feature_data={'power_system': True, 'multiblock': True}
        )
        
        assert machinery_result is not None
        # Should simplify to decorative or container per PRD