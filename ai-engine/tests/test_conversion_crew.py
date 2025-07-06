"""
Test-driven development for ModPorter AI Conversion Crew
Testing PRD Feature 2: AI Conversion Engine requirements
"""

import pytest

from src.crew.conversion_crew import ModPorterConversionCrew


class TestModPorterConversionCrew:
    """Test the main conversion crew functionality"""
    
    def test_crew_class_exists(self):
        """Test that the conversion crew class exists and can be imported"""
        assert ModPorterConversionCrew is not None
        
    def test_crew_has_required_methods(self):
        """Test that the crew class has required methods"""
        assert hasattr(ModPorterConversionCrew, '__init__')
        assert hasattr(ModPorterConversionCrew, 'convert_mod')
        assert callable(ModPorterConversionCrew.convert_mod)
    
    def test_convert_mod_method_signature(self):
        """Test that convert_mod method has correct signature"""
        import inspect
        sig = inspect.signature(ModPorterConversionCrew.convert_mod)
        params = list(sig.parameters.keys())
        
        # Verify method has expected parameters
        assert 'self' in params
        assert 'mod_path' in params
        assert 'output_path' in params
        assert 'smart_assumptions' in params
        assert 'include_dependencies' in params


class TestAgentSpecialization:
    """Test individual agent capabilities per PRD specifications"""
    
    def test_agent_classes_exist(self):
        """Test that all required agent classes exist"""
        from src.agents.java_analyzer import JavaAnalyzerAgent
        from src.agents.bedrock_architect import BedrockArchitectAgent
        from src.agents.logic_translator import LogicTranslatorAgent
        from src.agents.asset_converter import AssetConverterAgent
        from src.agents.packaging_agent import PackagingAgent
        from src.agents.qa_validator import QAValidatorAgent
        
        # Verify all classes can be imported
        assert JavaAnalyzerAgent is not None
        assert BedrockArchitectAgent is not None
        assert LogicTranslatorAgent is not None
        assert AssetConverterAgent is not None
        assert PackagingAgent is not None
        assert QAValidatorAgent is not None
    
    def test_agent_classes_have_get_tools_method(self):
        """Test that all agent classes have get_tools method"""
        from src.agents.java_analyzer import JavaAnalyzerAgent
        from src.agents.bedrock_architect import BedrockArchitectAgent
        from src.agents.logic_translator import LogicTranslatorAgent
        from src.agents.asset_converter import AssetConverterAgent
        from src.agents.packaging_agent import PackagingAgent
        from src.agents.qa_validator import QAValidatorAgent
        
        # Verify all classes have get_tools method
        assert hasattr(JavaAnalyzerAgent, 'get_tools')
        assert hasattr(BedrockArchitectAgent, 'get_tools')
        assert hasattr(LogicTranslatorAgent, 'get_tools')
        assert hasattr(AssetConverterAgent, 'get_tools')
        assert hasattr(PackagingAgent, 'get_tools')
        assert hasattr(QAValidatorAgent, 'get_tools')


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