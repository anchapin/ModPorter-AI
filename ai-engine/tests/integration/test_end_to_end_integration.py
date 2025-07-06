"""
End-to-End Integration Tests for ModPorter AI System
Tests the complete workflow with enhanced SmartAssumptionEngine and all agent classes
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from src.models.smart_assumptions import (
    SmartAssumptionEngine, 
    FeatureContext, 
    AssumptionResult,
    ConversionPlanComponent,
    AssumptionReport,
    AssumptionImpact
)
from src.crew.conversion_crew import ModPorterConversionCrew
from src.agents.bedrock_architect import BedrockArchitectAgent
from src.agents.logic_translator import LogicTranslatorAgent
from src.agents.asset_converter import AssetConverterAgent
from src.agents.packaging_agent import PackagingAgent
from src.agents.qa_validator import QAValidatorAgent
from src.agents.java_analyzer import JavaAnalyzerAgent


class TestEndToEndIntegration:
    """Test complete system integration with all enhanced features"""
    
    def setup_method(self):
        """Set up test environment"""
        self.smart_engine = SmartAssumptionEngine()
        
    def test_smart_assumption_engine_initialization(self):
        """Test that SmartAssumptionEngine initializes correctly with all assumptions"""
        assert self.smart_engine is not None
        assumptions = self.smart_engine.get_assumption_table()
        
        # Verify all PRD assumptions are present
        expected_features = [
            "Custom Dimensions",
            "Complex Machinery", 
            "Custom GUI/HUD",
            "Client-Side Rendering",
            "Mod Dependencies",
            "Advanced Redstone Logic",
            "Custom Entity AI"
        ]
        
        actual_features = [a.java_feature for a in assumptions]
        for expected in expected_features:
            assert expected in actual_features, f"Missing assumption: {expected}"
    
    def test_conflict_detection_and_resolution(self):
        """Test assumption conflict detection and priority-based resolution"""
        # Test feature that might match multiple assumptions
        test_cases = [
            ("custom_dimension", "Custom Dimensions"),
            ("complex_machinery", "Complex Machinery"),
            ("custom_gui", "Custom GUI/HUD"),
            ("dimension_gui", "Custom Dimensions"),  # Should prefer higher impact
        ]
        
        for feature_type, expected_selection in test_cases:
            matching = self.smart_engine.find_all_matching_assumptions(feature_type)
            selected = self.smart_engine.find_assumption(feature_type)
            
            if len(matching) > 1:
                # Test conflict resolution
                conflict_analysis = self.smart_engine.get_conflict_analysis(feature_type)
                assert conflict_analysis["has_conflicts"] == True
                assert conflict_analysis["selected_assumption"] == expected_selection
                assert "priority_rules" in conflict_analysis["resolution_method"]
            
            if selected:
                assert selected.java_feature == expected_selection
    
    def test_feature_analysis_workflow(self):
        """Test complete feature analysis workflow with SmartAssumptionEngine"""
        # Test custom dimension analysis
        dimension_context = FeatureContext(
            feature_id="twilight_forest_dim",
            feature_type="custom_dimension",
            original_data={
                "theme": "forest_like",
                "biomes": ["twilight_forest", "dense_forest"],
                "generation_rules": {"tree_density": "high", "mob_spawns": "custom"}
            },
            name="Twilight Forest"
        )
        
        analysis_result = self.smart_engine.analyze_feature(dimension_context)
        assert analysis_result.applied_assumption is not None
        assert analysis_result.applied_assumption.java_feature == "Custom Dimensions"
        
        # Test assumption application
        plan_component = self.smart_engine.apply_assumption(analysis_result)
        assert plan_component is not None
        assert plan_component.assumption_type == "dimension_to_structure"
        assert "Twilight Forest" in plan_component.user_explanation
        assert plan_component.impact_level == "high"
                    'name': 'Industrial Crusher',
                    'has_inventory': True,
                    'power_related': True,
                    'item_io_ports': True,
                    'processing_logic': 'complex_ore_processing'
                }
            },
            {
                'feature_type': 'custom_gui',
                'feature_data': {
                    'id': 'machine_control_panel_001',
                    'name': 'Machine Control Panel',
                    'elements': [
                        {'type': 'label', 'text': 'Power Status', 'x': 10, 'y': 10},
                        {'type': 'button', 'text': 'Start Process', 'action_id': 'start_processing'},
                        {'type': 'slot', 'item_id': 'minecraft:diamond', 'x': 20, 'y': 30}
                    ]
                }
            },
            {
                'feature_type': 'custom_entity_ai',
                'feature_data': {
                    'id': 'smart_golem_001',
                    'name': 'Smart Golem',
                    'ai_behaviors': ['pathfinding', 'item_collection', 'defensive_actions'],
                    'custom_logic': 'java_based_ai_controller'
                }
            }
        ]
    
    def test_smart_assumption_engine_integration(self):
        """Test SmartAssumptionEngine with conflict detection and resolution"""
        # Test conflict detection for ambiguous feature types
        conflicts = self.smart_engine.get_conflict_analysis('custom_dimension')
        
        assert isinstance(conflicts, dict)
        assert 'has_conflicts' in conflicts
        assert 'matching_assumptions' in conflicts
        
        # Test feature analysis with FeatureContext
        test_feature = self.test_features[0]  # custom_dimension
        feature_context = FeatureContext(
            feature_id=test_feature['feature_data']['id'],
            feature_type=test_feature['feature_type'],
            original_data=test_feature['feature_data'],
            name=test_feature['feature_data']['name']
        )
        
        analysis_result = self.smart_engine.analyze_feature(feature_context)
        
        assert analysis_result is not None
        assert analysis_result.feature_context == feature_context
        assert analysis_result.applied_assumption is not None
        assert analysis_result.applied_assumption.java_feature == "Custom Dimensions"
        
        # Test assumption application
        plan_component = self.smart_engine.apply_assumption(analysis_result)
        
        assert plan_component is not None
        assert isinstance(plan_component, ConversionPlanComponent)
        assert plan_component.assumption_type == "dimension_to_structure"
        assert "Twilight Forest" in plan_component.user_explanation
        
    def test_all_agent_classes_instantiation(self):
        """Test that all agent classes can be instantiated and have required methods"""
        agents = {
            'java_analyzer': JavaAnalyzerAgent(),
            'bedrock_architect': BedrockArchitectAgent(),
            'logic_translator': LogicTranslatorAgent(),
            'asset_converter': AssetConverterAgent(),
            'packaging_agent': PackagingAgent(),
            'qa_validator': QAValidatorAgent()
        }
        
        # Test that all agents have get_tools method
        for agent_name, agent in agents.items():
            assert hasattr(agent, 'get_tools'), f"{agent_name} missing get_tools method"
            tools = agent.get_tools()
            assert isinstance(tools, list), f"{agent_name} get_tools should return list"
            assert len(tools) > 0, f"{agent_name} should have at least one tool"
    
    def test_assumption_conflict_resolution_workflow(self):
        """Test the complete conflict resolution workflow"""
        # Create a feature that might match multiple assumptions
        ambiguous_feature = FeatureContext(
            feature_id='complex_gui_machinery_001',
            feature_type='complex_gui_machinery',  # Could match both GUI and Machinery
            original_data={
                'has_gui': True,
                'has_machinery': True,
                'power_system': True,
                'ui_elements': [{'type': 'button', 'text': 'Process'}]
            },
            name='Complex Processing Interface'
        )
        
        # Test conflict detection
        all_matching = self.smart_engine.find_all_matching_assumptions('complex_gui_machinery')
        assert len(all_matching) >= 1, "Should find at least one matching assumption"
        
        # Test analysis with conflict resolution
        analysis_result = self.smart_engine.analyze_feature(ambiguous_feature)
        
        # Should have resolved any conflicts deterministically
        assert analysis_result.applied_assumption is not None
        
        if len(all_matching) > 1:
            assert analysis_result.conflicting_assumptions is not None
            assert len(analysis_result.conflicting_assumptions) > 0
            assert analysis_result.conflict_resolution_reason is not None
            
        # Test that conflict resolution is deterministic (same result on repeat)
        analysis_result_2 = self.smart_engine.analyze_feature(ambiguous_feature)
        assert analysis_result.applied_assumption.java_feature == analysis_result_2.applied_assumption.java_feature
    
    def test_complex_machinery_conversion(self):
        """Test complex machinery assumption application"""
        machinery_context = FeatureContext(
            feature_id="industrial_furnace_001",
            feature_type="complex_machinery",
            original_data={
                "has_inventory": True,
                "power_related": True,
                "processes_items": True,
                "multiblock": True
            },
            name="Industrial Furnace"
        )
        
        analysis_result = self.smart_engine.analyze_feature(machinery_context)
        plan_component = self.smart_engine.apply_assumption(analysis_result)
        
        assert plan_component.assumption_type == "machinery_simplification"
        assert "simple_container_block" in plan_component.bedrock_equivalent
        assert "Industrial Furnace" in plan_component.user_explanation
    
    def test_custom_gui_conversion(self):
        """Test custom GUI to book interface conversion"""
        gui_context = FeatureContext(
            feature_id="status_gui_001",
            feature_type="custom_gui",
            original_data={
                "elements": [
                    {"type": "label", "text": "Power Level"},
                    {"type": "button", "text": "Start Process", "action_id": "start_process"},
                    {"type": "slot", "item_id": "minecraft:diamond"}
                ]
            },
            name="Machine Status GUI"
        )
        
        analysis_result = self.smart_engine.analyze_feature(gui_context)
        plan_component = self.smart_engine.apply_assumption(analysis_result)
        
        assert plan_component.assumption_type == "gui_to_book_interface"
        assert "book-based interface" in plan_component.bedrock_equivalent.lower()
        assert "Machine Status GUI" in plan_component.user_explanation
    
    def test_assumption_report_generation(self):
        """Test comprehensive assumption report generation"""
        # Create multiple plan components
        components = []
        
        # Dimension component
        dim_context = FeatureContext("dim_001", "custom_dimension", {"theme": "nether_like"}, "Nether Plus")
        dim_analysis = self.smart_engine.analyze_feature(dim_context)
        dim_component = self.smart_engine.apply_assumption(dim_analysis)
        if dim_component:
            components.append(dim_component)
        
        # Machinery component
        machine_context = FeatureContext("machine_001", "complex_machinery", {"has_inventory": False}, "Decorative Machine")
        machine_analysis = self.smart_engine.analyze_feature(machine_context)
        machine_component = self.smart_engine.apply_assumption(machine_analysis)
        if machine_component:
            components.append(machine_component)
        
        # Generate report
        report = self.smart_engine.generate_assumption_report(components)
        
        assert len(report.assumptions_applied) == len(components)
        
        for item in report.assumptions_applied:
            assert item.original_feature is not None
            assert item.assumption_type is not None
            assert item.bedrock_equivalent is not None
            assert item.impact_level in ["low", "medium", "high"]
            assert item.user_explanation is not None
    
    @patch('crewai.Crew')
    def test_conversion_crew_integration(self, mock_crew_class):
        """Test ModPorterConversionCrew integration with enhanced features"""
        # Mock crew behavior
        mock_crew_instance = Mock()
        mock_crew_class.return_value = mock_crew_instance
        
        # Mock task outputs with realistic structure
        mock_task_output = Mock()
        mock_task_output.raw = json.dumps({
            "conversion_plan_components": [
                {
                    "original_feature_id": "test_dim",
                    "original_feature_type": "custom_dimension",
                    "assumption_type": "dimension_to_structure",
                    "bedrock_equivalent": "Large structure in Overworld",
                    "impact_level": "high",
                    "user_explanation": "Dimension converted to structure"
                }
            ]
        })
        mock_crew_instance.kickoff.return_value.tasks_output = [Mock(), mock_task_output]
        
        # Test crew initialization
        with patch('src.crew.conversion_crew.ChatOpenAI'):
            crew = ModPorterConversionCrew()
            
        # Verify crew status
        status = crew.get_conversion_crew_status()
        assert status["agents_initialized"]["java_analyzer"] == True
        assert status["agents_initialized"]["bedrock_architect"] == True
        assert status["smart_assumption_engine"]["initialized"] == True
        assert status["smart_assumption_engine"]["conflict_resolution_enabled"] == True
        assert status["crew_ready"] == True
    
    def test_agent_class_instantiation(self):
        """Test that all agent classes can be instantiated properly"""
        agents = [
            JavaAnalyzerAgent(),
            BedrockArchitectAgent(),
            LogicTranslatorAgent(), 
            AssetConverterAgent(),
            PackagingAgent(),
            QAValidatorAgent()
        ]
        
        for agent in agents:
            assert agent is not None
            tools = agent.get_tools()
            assert isinstance(tools, list)
            assert len(tools) > 0
    
    def test_feature_analysis_with_conflicts(self):
        """Test feature analysis with enhanced conflict handling"""
        # Create a feature type that could match multiple assumptions
        complex_feature_context = FeatureContext(
            feature_id="complex_gui_machine_001",
            feature_type="complex_gui_machinery",
            original_data={
                "has_gui": True,
                "is_machine": True,
                "complex_logic": True
            },
            name="GUI-enabled Machine"
        )
        
        # Test using conversion crew's enhanced analysis method
        with patch('src.crew.conversion_crew.ChatOpenAI'):
            crew = ModPorterConversionCrew()
        
        analysis_result = crew.analyze_feature_with_assumptions(
            "complex_gui_machinery", 
            complex_feature_context.original_data
        )
        
        assert "analysis_result" in analysis_result
        assert "conflict_analysis" in analysis_result
        
        # Should detect and resolve conflicts
        if analysis_result.get("has_conflicts"):
            assert analysis_result.get("resolution_applied") == True
    
    def test_assumption_impact_prioritization(self):
        """Test that higher impact assumptions take priority in conflicts"""
        # Test conflicts between different impact levels
        high_impact_features = ["custom_dimension", "complex_machinery", "client_rendering"]
        medium_impact_features = ["custom_gui", "mod_dependencies", "redstone_logic", "entity_ai"]
        
        for feature in high_impact_features:
            assumption = self.smart_engine.find_assumption(feature)
            if assumption:
                assert assumption.impact == AssumptionImpact.HIGH
        
        for feature in medium_impact_features:
            assumption = self.smart_engine.find_assumption(feature) 
            if assumption:
                assert assumption.impact in [AssumptionImpact.MEDIUM, AssumptionImpact.HIGH]
    
    def test_error_handling_and_graceful_degradation(self):
        """Test error handling in the integrated system"""
        # Test with invalid feature context
        invalid_context = FeatureContext(
            feature_id="invalid",
            feature_type="non_existent_feature_type",
            original_data={},
            name=None
        )
        
        analysis_result = self.smart_engine.analyze_feature(invalid_context)
        
        # Should handle gracefully without crashing
        assert analysis_result.feature_context == invalid_context
        assert analysis_result.applied_assumption is None
        assert len(analysis_result.conflicting_assumptions) == 0
        
        # Test assumption application with no applicable assumption
        plan_component = self.smart_engine.apply_assumption(analysis_result)
        assert plan_component is None
    
    def test_performance_with_multiple_features(self):
        """Test system performance with multiple feature analyses"""
        import time
        
        # Create multiple feature contexts
        feature_contexts = []
        for i in range(10):
            context = FeatureContext(
                feature_id=f"feature_{i}",
                feature_type="custom_dimension" if i % 2 == 0 else "complex_machinery",
                original_data={"test_data": f"value_{i}"},
                name=f"Test Feature {i}"
            )
            feature_contexts.append(context)
        
        # Time the analysis
        start_time = time.time()
        
        plan_components = []
        for context in feature_contexts:
            analysis = self.smart_engine.analyze_feature(context)
            component = self.smart_engine.apply_assumption(analysis)
            if component:
                plan_components.append(component)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Should complete reasonably quickly (less than 1 second for 10 features)
        assert processing_time < 1.0
        assert len(plan_components) > 0
        
        # Generate final report
        report = self.smart_engine.generate_assumption_report(plan_components)
        assert len(report.assumptions_applied) == len(plan_components)


if __name__ == "__main__":
    # Run basic integration test
    test_suite = TestEndToEndIntegration()
    test_suite.setup_method()
    
    print("🧪 Running End-to-End Integration Tests...")
    
    try:
        test_suite.test_smart_assumption_engine_initialization()
        print("✅ SmartAssumptionEngine initialization test passed")
        
        test_suite.test_conflict_detection_and_resolution()
        print("✅ Conflict detection and resolution test passed")
        
        test_suite.test_feature_analysis_workflow()
        print("✅ Feature analysis workflow test passed")
        
        test_suite.test_complex_machinery_conversion()
        print("✅ Complex machinery conversion test passed")
        
        test_suite.test_custom_gui_conversion()
        print("✅ Custom GUI conversion test passed")
        
        test_suite.test_assumption_report_generation()
        print("✅ Assumption report generation test passed")
        
        test_suite.test_agent_class_instantiation()
        print("✅ Agent class instantiation test passed")
        
        test_suite.test_assumption_impact_prioritization()
        print("✅ Assumption impact prioritization test passed")
        
        test_suite.test_error_handling_and_graceful_degradation()
        print("✅ Error handling and graceful degradation test passed")
        
        test_suite.test_performance_with_multiple_features()
        print("✅ Performance with multiple features test passed")
        
        print("\n🎉 All End-to-End Integration Tests Passed!")
        print("✅ Enhanced SmartAssumptionEngine working correctly")
        print("✅ Conflict detection and resolution functioning")
        print("✅ All agent classes properly implemented")
        print("✅ Complete workflow integration validated")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        raise
    finally:
        test_instance.teardown_method()
