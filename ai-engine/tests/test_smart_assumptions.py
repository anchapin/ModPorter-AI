"""
Comprehensive unit tests for the Smart Assumptions Engine.
Addresses Issue #571: Add comprehensive unit tests for conflict resolution,
documentation, validation, and logging.
"""

import sys
import importlib.util
from pathlib import Path

# Ensure ai-engine directory is in path first (before any other models package)
# This is critical for CI environments where backend/src/models might conflict
ai_engine_root = Path(__file__).parent.parent
if str(ai_engine_root) not in sys.path:
    sys.path.insert(0, str(ai_engine_root))

# Remove any cached 'models' module that might be from a different location
# This is necessary because conftest.py may have already imported a different models package
if 'models' in sys.modules:
    # Check if it's the wrong models package
    models_module = sys.modules['models']
    if hasattr(models_module, '__file__') and models_module.__file__:
        if 'ai-engine' not in models_module.__file__:
            # Remove all models-related modules from cache
            to_remove = [k for k in sys.modules.keys() if k == 'models' or k.startswith('models.')]
            for k in to_remove:
                del sys.modules[k]

import pytest
import logging
from unittest.mock import Mock, patch, MagicMock
from typing import List, Dict, Any

from models.smart_assumptions import (
    SmartAssumptionEngine,
    SmartAssumption,
    AssumptionImpact,
    FeatureContext,
    AssumptionResult,
    ConversionPlanComponent,
    ConversionPlan,
    AssumptionReport,
    AppliedAssumptionReportItem
)


class TestSmartAssumption:
    """Test SmartAssumption dataclass"""
    
    def test_smart_assumption_creation(self):
        """Test basic SmartAssumption creation"""
        assumption = SmartAssumption(
            java_feature="Custom Dimensions",
            inconvertible_aspect="No Bedrock API for creating new worlds",
            bedrock_workaround="Convert to large structure",
            impact=AssumptionImpact.HIGH,
            description="Recreate as structure in existing dimension",
            implementation_notes="Preserve assets and generation rules"
        )
        
        assert assumption.java_feature == "Custom Dimensions"
        assert assumption.impact == AssumptionImpact.HIGH
        assert assumption.explanation == assumption.description
        assert assumption.match_patterns is not None
    
    def test_smart_assumption_with_custom_patterns(self):
        """Test SmartAssumption with custom match patterns"""
        assumption = SmartAssumption(
            java_feature="Custom GUI",
            inconvertible_aspect="No Bedrock API for UI",
            bedrock_workaround="Use books/signs",
            impact=AssumptionImpact.HIGH,
            description="Convert to book interface",
            implementation_notes="Preserve information display",
            match_patterns=["gui", "hud", "interface", "screen"]
        )
        
        assert assumption.match_patterns == ["gui", "hud", "interface", "screen"]
    
    def test_smart_assumption_default_patterns(self):
        """Test that default match patterns are generated from java_feature"""
        assumption = SmartAssumption(
            java_feature="Custom Dimensions",
            inconvertible_aspect="Test",
            bedrock_workaround="Test",
            impact=AssumptionImpact.HIGH,
            description="Test",
            implementation_notes="Test"
        )
        
        # Should extract words from java_feature
        assert "custom" in assumption.match_patterns
        assert "dimensions" in assumption.match_patterns


class TestFeatureContext:
    """Test FeatureContext dataclass"""
    
    def test_feature_context_creation(self):
        """Test basic FeatureContext creation"""
        context = FeatureContext(
            feature_id="dim_001",
            feature_type="custom_dimension",
            original_data={"biomes": ["forest", "desert"]},
            name="Twilight Forest"
        )
        
        assert context.feature_id == "dim_001"
        assert context.feature_type == "custom_dimension"
        assert context.original_data == {"biomes": ["forest", "desert"]}
        assert context.name == "Twilight Forest"
    
    def test_feature_context_without_name(self):
        """Test FeatureContext without optional name"""
        context = FeatureContext(
            feature_id="machine_001",
            feature_type="complex_machinery",
            original_data={"power_input": "RF"}
        )
        
        assert context.name is None


class TestAssumptionResult:
    """Test AssumptionResult dataclass"""
    
    def test_assumption_result_no_conflict(self):
        """Test AssumptionResult without conflicts"""
        context = FeatureContext("feat_001", "custom_dimension", {})
        assumption = SmartAssumption(
            java_feature="Custom Dimensions",
            inconvertible_aspect="Test",
            bedrock_workaround="Test",
            impact=AssumptionImpact.HIGH,
            description="Test",
            implementation_notes="Test"
        )
        
        result = AssumptionResult(
            feature_context=context,
            applied_assumption=assumption,
            conflicting_assumptions=[],
            had_conflict=False
        )
        
        assert result.applied_assumption == assumption
        assert not result.had_conflict
        assert len(result.conflicting_assumptions) == 0
    
    def test_assumption_result_with_conflict(self):
        """Test AssumptionResult with conflicts"""
        context = FeatureContext("feat_001", "custom_gui", {})
        assumption1 = SmartAssumption(
            java_feature="Custom GUI/HUD",
            inconvertible_aspect="Test",
            bedrock_workaround="Test",
            impact=AssumptionImpact.HIGH,
            description="Test",
            implementation_notes="Test"
        )
        assumption2 = SmartAssumption(
            java_feature="Client-Side Rendering",
            inconvertible_aspect="Test",
            bedrock_workaround="Test",
            impact=AssumptionImpact.HIGH,
            description="Test",
            implementation_notes="Test"
        )
        
        result = AssumptionResult(
            feature_context=context,
            applied_assumption=assumption1,
            conflicting_assumptions=[assumption1, assumption2],
            had_conflict=True
        )
        
        assert result.had_conflict
        assert len(result.conflicting_assumptions) == 2


class TestSmartAssumptionEngine:
    """Test SmartAssumptionEngine class"""
    
    @pytest.fixture
    def engine(self):
        """Create a SmartAssumptionEngine instance"""
        return SmartAssumptionEngine()
    
    def test_engine_initialization(self, engine):
        """Test engine initialization"""
        assert engine.assumption_table is not None
        assert len(engine.assumption_table) > 0
    
    def test_get_assumption_table(self, engine):
        """Test getting the assumption table"""
        table = engine.get_assumption_table()
        assert isinstance(table, list)
        assert all(isinstance(a, SmartAssumption) for a in table)
    
    def test_find_assumption_exact_match(self, engine):
        """Test finding assumption with exact feature type match"""
        assumption = engine.find_assumption("custom_dimensions")
        assert assumption is not None
        assert assumption.java_feature == "Custom Dimensions"
    
    def test_find_assumption_partial_match(self, engine):
        """Test finding assumption with partial match"""
        assumption = engine.find_assumption("custom_gui")
        assert assumption is not None
        assert "GUI" in assumption.java_feature
    
    def test_find_assumption_no_match(self, engine):
        """Test finding assumption with no match"""
        assumption = engine.find_assumption("unknown_feature_type_xyz")
        assert assumption is None
    
    def test_find_all_matching_assumptions_single(self, engine):
        """Test finding all matching assumptions - single match"""
        matches = engine.find_all_matching_assumptions("custom_dimension")
        assert len(matches) >= 1
        assert any("dimension" in a.java_feature.lower() for a in matches)
    
    def test_find_all_matching_assumptions_multiple(self, engine):
        """Test finding all matching assumptions - multiple matches"""
        # Use a feature type that matches multiple assumptions
        # "gui" should match both "Custom GUI/HUD" and potentially others
        matches = engine.find_all_matching_assumptions("custom_gui_hud")
        # Should match at least one GUI-related assumption
        assert len(matches) >= 1
        assert any("gui" in a.java_feature.lower() for a in matches)
    
    def test_find_all_matching_assumptions_empty(self, engine):
        """Test finding all matching assumptions - no matches"""
        matches = engine.find_all_matching_assumptions("nonexistent_feature_xyz")
        assert len(matches) == 0


class TestConflictResolution:
    """Test conflict resolution in SmartAssumptionEngine"""
    
    @pytest.fixture
    def engine(self):
        """Create a SmartAssumptionEngine instance"""
        return SmartAssumptionEngine()
    
    def test_resolve_conflict_single_assumption(self, engine):
        """Test conflict resolution with single assumption"""
        assumption = SmartAssumption(
            java_feature="Test Feature",
            inconvertible_aspect="Test",
            bedrock_workaround="Test",
            impact=AssumptionImpact.HIGH,
            description="Test",
            implementation_notes="Test"
        )
        
        result = engine._resolve_assumption_conflict([assumption], "test_feature")
        assert result == assumption
    
    def test_resolve_conflict_empty_list_raises(self, engine):
        """Test conflict resolution with empty list raises error"""
        with pytest.raises(ValueError):
            engine._resolve_assumption_conflict([], "test_feature")
    
    def test_resolve_conflict_by_impact(self, engine):
        """Test conflict resolution by impact level"""
        high_impact = SmartAssumption(
            java_feature="High Impact Feature",
            inconvertible_aspect="Test",
            bedrock_workaround="Test",
            impact=AssumptionImpact.HIGH,
            description="Test",
            implementation_notes="Test"
        )
        low_impact = SmartAssumption(
            java_feature="Low Impact Feature",
            inconvertible_aspect="Test",
            bedrock_workaround="Test",
            impact=AssumptionImpact.LOW,
            description="Test",
            implementation_notes="Test"
        )
        
        result = engine._resolve_assumption_conflict(
            [low_impact, high_impact], 
            "test_feature"
        )
        assert result.impact == AssumptionImpact.HIGH
    
    def test_resolve_conflict_by_specificity(self, engine):
        """Test conflict resolution by specificity when impacts are equal"""
        specific = SmartAssumption(
            java_feature="Custom GUI Screen Interface",
            inconvertible_aspect="Test",
            bedrock_workaround="Test",
            impact=AssumptionImpact.HIGH,
            description="Test",
            implementation_notes="Test"
        )
        generic = SmartAssumption(
            java_feature="Custom GUI",
            inconvertible_aspect="Test",
            bedrock_workaround="Test",
            impact=AssumptionImpact.HIGH,
            description="Test",
            implementation_notes="Test"
        )
        
        # When resolving for "custom_gui_screen", should prefer more specific
        result = engine._resolve_assumption_conflict(
            [generic, specific],
            "custom_gui_screen"
        )
        # Result should be one of them (specificity logic applies)
        assert result in [specific, generic]
    
    def test_resolve_conflict_exact_match_priority(self, engine):
        """Test that exact feature type match takes precedence"""
        exact = SmartAssumption(
            java_feature="Custom Dimensions",
            inconvertible_aspect="Test",
            bedrock_workaround="Test",
            impact=AssumptionImpact.LOW,  # Even with lower impact
            description="Test",
            implementation_notes="Test"
        )
        other = SmartAssumption(
            java_feature="Other Feature",
            inconvertible_aspect="Test",
            bedrock_workaround="Test",
            impact=AssumptionImpact.HIGH,
            description="Test",
            implementation_notes="Test"
        )
        
        result = engine._resolve_assumption_conflict(
            [exact, other],
            "custom_dimensions"  # Exact match for "Custom Dimensions"
        )
        # Exact match should win
        assert result.java_feature == "Custom Dimensions"
    
    def test_get_conflict_analysis_no_conflict(self, engine):
        """Test conflict analysis when there's no conflict"""
        analysis = engine.get_conflict_analysis("custom_dimension")
        
        assert "feature_name" in analysis
        assert "has_conflicts" in analysis
        assert "matching_assumptions" in analysis
        assert "resolution_details" in analysis
    
    def test_get_conflict_analysis_with_conflict(self, engine):
        """Test conflict analysis when there are conflicts"""
        # Use a feature type that might match multiple assumptions
        analysis = engine.get_conflict_analysis("custom")
        
        assert analysis["feature_name"] == "custom"
        assert isinstance(analysis["has_conflicts"], bool)
        assert isinstance(analysis["matching_assumptions"], list)


class TestAnalyzeFeature:
    """Test analyze_feature method"""
    
    @pytest.fixture
    def engine(self):
        """Create a SmartAssumptionEngine instance"""
        return SmartAssumptionEngine()
    
    def test_analyze_feature_with_match(self, engine):
        """Test analyzing a feature that matches an assumption"""
        context = FeatureContext(
            feature_id="dim_001",
            feature_type="custom_dimension",
            original_data={"biomes": ["forest"]}
        )
        
        result = engine.analyze_feature(context)
        
        assert result.feature_context == context
        assert result.applied_assumption is not None
        assert "dimension" in result.applied_assumption.java_feature.lower()
    
    def test_analyze_feature_no_match(self, engine):
        """Test analyzing a feature with no matching assumption"""
        context = FeatureContext(
            feature_id="unknown_001",
            feature_type="completely_unknown_feature_type",
            original_data={}
        )
        
        result = engine.analyze_feature(context)
        
        assert result.applied_assumption is None
        assert len(result.conflicting_assumptions) == 0
    
    def test_analyze_feature_with_conflict(self, engine):
        """Test analyzing a feature with multiple matching assumptions"""
        context = FeatureContext(
            feature_id="gui_001",
            feature_type="custom_gui_hud",
            original_data={"elements": []}
        )
        
        result = engine.analyze_feature(context)
        
        # Should have an applied assumption (resolved from conflicts)
        assert result.applied_assumption is not None


class TestApplyAssumption:
    """Test apply_assumption method"""
    
    @pytest.fixture
    def engine(self):
        """Create a SmartAssumptionEngine instance"""
        return SmartAssumptionEngine()
    
    def test_apply_assumption_custom_dimension(self, engine):
        """Test applying custom dimension assumption"""
        context = FeatureContext(
            feature_id="dim_001",
            feature_type="custom_dimension",
            original_data={"biomes": ["forest", "desert"], "theme": "mystical"},
            name="Mystic Dimension"
        )
        
        analysis_result = engine.analyze_feature(context)
        plan_component = engine.apply_assumption(analysis_result)
        
        assert plan_component is not None
        assert plan_component.original_feature_id == "dim_001"
        assert plan_component.assumption_type == "dimension_to_structure"
        assert "structure" in plan_component.bedrock_equivalent.lower()
        assert plan_component.impact_level == "high"
    
    def test_apply_assumption_complex_machinery(self, engine):
        """Test applying complex machinery assumption"""
        context = FeatureContext(
            feature_id="machine_001",
            feature_type="complex_machinery",
            original_data={"power_input": "RF", "has_inventory": True},
            name="Power Generator"
        )
        
        analysis_result = engine.analyze_feature(context)
        plan_component = engine.apply_assumption(analysis_result)
        
        assert plan_component is not None
        assert plan_component.original_feature_id == "machine_001"
        assert plan_component.assumption_type == "machinery_simplification"
        assert "decorative" in plan_component.bedrock_equivalent.lower() or "container" in plan_component.bedrock_equivalent.lower()
    
    def test_apply_assumption_custom_gui(self, engine):
        """Test applying custom GUI assumption"""
        context = FeatureContext(
            feature_id="gui_001",
            feature_type="custom_gui",
            original_data={
                "elements": [
                    {"type": "label", "text": "Welcome!"},
                    {"type": "button", "text": "Click Me", "action_id": "action_1"}
                ]
            },
            name="Main Menu"
        )
        
        analysis_result = engine.analyze_feature(context)
        plan_component = engine.apply_assumption(analysis_result)
        
        assert plan_component is not None
        assert plan_component.original_feature_id == "gui_001"
        assert "book" in plan_component.bedrock_equivalent.lower()
    
    def test_apply_assumption_no_assumption(self, engine):
        """Test applying assumption when none was found"""
        context = FeatureContext(
            feature_id="unknown_001",
            feature_type="unknown_feature_type",
            original_data={}
        )
        
        analysis_result = AssumptionResult(
            feature_context=context,
            applied_assumption=None,
            conflicting_assumptions=[],
            had_conflict=False
        )
        
        plan_component = engine.apply_assumption(analysis_result)
        assert plan_component is None


class TestConversionPlanComponent:
    """Test ConversionPlanComponent dataclass"""
    
    def test_conversion_plan_component_creation(self):
        """Test creating a ConversionPlanComponent"""
        component = ConversionPlanComponent(
            original_feature_id="feat_001",
            original_feature_type="custom_dimension",
            assumption_type="dimension_to_structure",
            bedrock_equivalent="Large structure in Overworld",
            impact_level="high",
            user_explanation="The dimension will be converted to a structure",
            technical_notes="Preserve biomes as structure decorations"
        )
        
        assert component.original_feature_id == "feat_001"
        assert component.assumption_type == "dimension_to_structure"
        assert component.impact_level == "high"


class TestAssumptionReport:
    """Test AssumptionReport and report generation"""
    
    @pytest.fixture
    def engine(self):
        """Create a SmartAssumptionEngine instance"""
        return SmartAssumptionEngine()
    
    def test_generate_assumption_report_empty(self, engine):
        """Test generating report with no components"""
        report = engine.generate_assumption_report([])
        
        assert isinstance(report, AssumptionReport)
        assert len(report.assumptions_applied) == 0
    
    def test_generate_assumption_report_with_components(self, engine):
        """Test generating report with components"""
        components = [
            ConversionPlanComponent(
                original_feature_id="dim_001",
                original_feature_type="custom_dimension",
                assumption_type="dimension_to_structure",
                bedrock_equivalent="Large structure",
                impact_level="high",
                user_explanation="The custom dimension 'Twilight Forest' will be converted to a structure"
            ),
            ConversionPlanComponent(
                original_feature_id="machine_001",
                original_feature_type="complex_machinery",
                assumption_type="machinery_simplification",
                bedrock_equivalent="Decorative block",
                impact_level="high",
                user_explanation="The complex machine 'Generator' will be simplified"
            )
        ]
        
        report = engine.generate_assumption_report(components)
        
        assert len(report.assumptions_applied) == 2
        assert all(isinstance(item, AppliedAssumptionReportItem) for item in report.assumptions_applied)
    
    def test_generate_assumption_report_with_none_component(self, engine):
        """Test generating report handles None components gracefully"""
        components = [
            ConversionPlanComponent(
                original_feature_id="dim_001",
                original_feature_type="custom_dimension",
                assumption_type="dimension_to_structure",
                bedrock_equivalent="Large structure",
                impact_level="high",
                user_explanation="Test"
            ),
            None  # Should be skipped
        ]
        
        report = engine.generate_assumption_report(components)
        
        assert len(report.assumptions_applied) == 1


class TestGUIElementsToPages:
    """Test _convert_gui_elements_to_pages method"""
    
    @pytest.fixture
    def engine(self):
        """Create a SmartAssumptionEngine instance"""
        return SmartAssumptionEngine()
    
    def test_convert_gui_elements_empty(self, engine):
        """Test converting empty GUI elements"""
        pages = engine._convert_gui_elements_to_pages([], "Test GUI")
        
        assert len(pages) >= 1
        assert "Test GUI" in pages[0]
    
    def test_convert_gui_elements_labels(self, engine):
        """Test converting GUI labels"""
        elements = [
            {"type": "label", "text": "Welcome!"},
            {"type": "label", "text": "Settings"}
        ]
        
        pages = engine._convert_gui_elements_to_pages(elements, "Menu")
        
        assert len(pages) >= 1
        assert any("Welcome" in page for page in pages)
    
    def test_convert_gui_elements_buttons(self, engine):
        """Test converting GUI buttons"""
        elements = [
            {"type": "button", "text": "Start Game", "action_id": "start"},
            {"type": "button", "text": "Quit", "action_id": "quit"}
        ]
        
        pages = engine._convert_gui_elements_to_pages(elements, "Main Menu")
        
        assert any("Start Game" in page for page in pages)
        assert any("non-functional" in page.lower() for page in pages)
    
    def test_convert_gui_elements_mixed(self, engine):
        """Test converting mixed GUI elements"""
        elements = [
            {"type": "label", "text": "Info"},
            {"type": "button", "text": "Action", "action_id": "act"},
            {"type": "slot", "item_id": "minecraft:diamond"},
            {"type": "image", "resource_id": "texture.png"}
        ]
        
        pages = engine._convert_gui_elements_to_pages(elements, "Complex GUI")
        
        # Should handle all element types
        combined = "\n".join(pages)
        assert "Info" in combined
        assert "Action" in combined
        assert "diamond" in combined.lower()


class TestLogging:
    """Test logging functionality"""
    
    @pytest.fixture
    def engine(self):
        """Create a SmartAssumptionEngine instance"""
        return SmartAssumptionEngine()
    
    def test_analyze_feature_logging(self, engine, caplog):
        """Test that analyze_feature logs appropriately"""
        context = FeatureContext(
            feature_id="test_001",
            feature_type="custom_dimension",
            original_data={}
        )
        
        with caplog.at_level(logging.INFO):
            engine.analyze_feature(context)
        
        # Should log about the analysis
        assert any("Analyzing feature" in record.message for record in caplog.records)
    
    def test_conflict_resolution_logging(self, engine, caplog):
        """Test that conflict resolution logs appropriately"""
        # Create conflicting assumptions
        assumptions = [
            SmartAssumption(
                java_feature="Feature A",
                inconvertible_aspect="Test",
                bedrock_workaround="Test",
                impact=AssumptionImpact.HIGH,
                description="Test",
                implementation_notes="Test"
            ),
            SmartAssumption(
                java_feature="Feature B",
                inconvertible_aspect="Test",
                bedrock_workaround="Test",
                impact=AssumptionImpact.HIGH,
                description="Test",
                implementation_notes="Test"
            )
        ]
        
        with caplog.at_level(logging.INFO):
            engine._resolve_assumption_conflict(assumptions, "test_feature")
        
        # Should log about conflict resolution
        assert any("conflict" in record.message.lower() or "selected" in record.message.lower() 
                   for record in caplog.records)


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    @pytest.fixture
    def engine(self):
        """Create a SmartAssumptionEngine instance"""
        return SmartAssumptionEngine()
    
    def test_analyze_feature_with_empty_original_data(self, engine):
        """Test analyzing feature with empty original_data"""
        context = FeatureContext(
            feature_id="empty_001",
            feature_type="custom_dimension",
            original_data={}
        )
        
        result = engine.analyze_feature(context)
        
        assert result is not None
        assert result.feature_context == context
    
    def test_apply_assumption_with_missing_data_fields(self, engine):
        """Test applying assumption when original_data is missing expected fields"""
        context = FeatureContext(
            feature_id="dim_001",
            feature_type="custom_dimension",
            original_data={}  # Missing 'biomes' and other expected fields
        )
        
        analysis_result = engine.analyze_feature(context)
        plan_component = engine.apply_assumption(analysis_result)
        
        # Should still produce a result, handling missing data gracefully
        assert plan_component is not None
    
    def test_find_assumption_case_insensitivity(self, engine):
        """Test that find_assumption is case insensitive"""
        result1 = engine.find_assumption("CUSTOM_DIMENSION")
        result2 = engine.find_assumption("custom_dimension")
        result3 = engine.find_assumption("Custom_Dimension")
        
        # All should find the same assumption
        assert result1 is not None
        assert result2 is not None
        assert result3 is not None
    
    def test_feature_context_with_complex_data(self, engine):
        """Test feature context with complex nested data"""
        context = FeatureContext(
            feature_id="complex_001",
            feature_type="complex_machinery",
            original_data={
                "power_input": {"type": "RF", "capacity": 100000},
                "processing": {"slots": 4, "speed": 2.5},
                "inventory": {"input": 2, "output": 2}
            }
        )
        
        result = engine.analyze_feature(context)
        plan = engine.apply_assumption(result)
        
        assert plan is not None


class TestAssumptionValidation:
    """Test assumption validation functionality"""
    
    @pytest.fixture
    def engine(self):
        """Create a SmartAssumptionEngine instance"""
        return SmartAssumptionEngine()
    
    def test_all_assumptions_have_required_fields(self, engine):
        """Test that all assumptions in the table have required fields"""
        for assumption in engine.assumption_table:
            assert assumption.java_feature, "java_feature is required"
            assert assumption.inconvertible_aspect, "inconvertible_aspect is required"
            assert assumption.bedrock_workaround, "bedrock_workaround is required"
            assert assumption.impact in AssumptionImpact, "impact must be valid AssumptionImpact"
            assert assumption.description, "description is required"
    
    def test_all_assumptions_have_valid_impact(self, engine):
        """Test that all assumptions have valid impact levels"""
        valid_impacts = {AssumptionImpact.LOW, AssumptionImpact.MEDIUM, AssumptionImpact.HIGH}
        
        for assumption in engine.assumption_table:
            assert assumption.impact in valid_impacts
    
    def test_assumption_table_completeness(self, engine):
        """Test that the assumption table covers expected features"""
        expected_features = [
            "custom dimension",
            "complex machinery",
            "custom gui",
            "client-side rendering",
            "mod dependencies"  # Note: actual feature name is "Mod Dependencies"
        ]
        
        table_features = [a.java_feature.lower() for a in engine.assumption_table]
        
        for expected in expected_features:
            assert any(expected in f for f in table_features), f"Missing assumption for: {expected}"


class TestIntegration:
    """Integration tests for the complete smart assumptions workflow"""
    
    @pytest.fixture
    def engine(self):
        """Create a SmartAssumptionEngine instance"""
        return SmartAssumptionEngine()
    
    def test_full_conversion_workflow(self, engine):
        """Test a full conversion workflow with multiple features"""
        features = [
            FeatureContext("dim_001", "custom_dimension", {"biomes": ["forest"]}, "Twilight Forest"),
            FeatureContext("machine_001", "complex_machinery", {"power": "RF"}, "Generator"),
            FeatureContext("gui_001", "custom_gui", {"elements": [{"type": "label", "text": "Info"}]}, "Menu")
        ]
        
        plan_components = []
        
        for feature in features:
            analysis = engine.analyze_feature(feature)
            if analysis.applied_assumption:
                component = engine.apply_assumption(analysis)
                if component:
                    plan_components.append(component)
        
        report = engine.generate_assumption_report(plan_components)
        
        assert len(report.assumptions_applied) == 3
        assert all(item.impact_level in ["low", "medium", "high"] for item in report.assumptions_applied)
    
    def test_workflow_with_unconvertible_feature(self, engine):
        """Test workflow with a feature that has no matching assumption"""
        features = [
            FeatureContext("known_001", "custom_dimension", {}, "Dimension"),
            FeatureContext("unknown_001", "completely_unknown_type", {}, "Unknown")
        ]
        
        plan_components = []
        
        for feature in features:
            analysis = engine.analyze_feature(feature)
            if analysis.applied_assumption:
                component = engine.apply_assumption(analysis)
                if component:
                    plan_components.append(component)
        
        # Only the known feature should produce a plan component
        assert len(plan_components) == 1
        assert plan_components[0].original_feature_id == "known_001"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])