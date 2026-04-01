
import pytest
from models.smart_assumptions import (
    SmartAssumptionEngine, 
    SmartAssumption, 
    AssumptionImpact, 
    FeatureContext, 
    AssumptionResult,
    ConversionPlanComponent
)

class TestSmartAssumptionEngine:
    @pytest.fixture
    def engine(self):
        return SmartAssumptionEngine()

    def test_initialization(self, engine):
        assert len(engine.get_assumption_table()) > 0
        summary = engine.get_impact_summary()
        assert summary[AssumptionImpact.HIGH.value] > 0

    def test_validate_single_assumption_invalid(self, engine):
        # Missing required fields
        invalid = SmartAssumption(
            java_feature="", 
            inconvertible_aspect="", 
            bedrock_workaround="", 
            impact=AssumptionImpact.LOW, 
            description="", 
            implementation_notes=""
        )
        with pytest.raises(ValueError):
            engine._validate_single_assumption(invalid)

    def test_add_remove_assumption(self, engine):
        new_a = SmartAssumption(
            java_feature="Test Feature",
            inconvertible_aspect="None",
            bedrock_workaround="None",
            impact=AssumptionImpact.LOW,
            description="Test",
            implementation_notes="Test"
        )
        engine.add_assumption(new_a)
        assert engine.get_assumption_by_java_feature("Test Feature") is not None
        
        assert engine.remove_assumption("Test Feature") is True
        assert engine.get_assumption_by_java_feature("Test Feature") is None

    def test_find_assumption_conflict(self, engine):
        # "Custom Dimensions" and "Custom Biomes" might conflict if feature_type is "Custom"
        # but the engine has specific logic to handle this.
        
        # Test "Dimension"
        a = engine.find_assumption("my_new_dimension")
        assert a is not None
        assert "Dimension" in a.java_feature

        # Test "GUI"
        a = engine.find_assumption("fancy_gui_screen")
        assert a is not None
        assert "GUI" in a.java_feature

    def test_analyze_feature(self, engine):
        ctx = FeatureContext(
            feature_id="dim_1",
            feature_type="custom_dimension",
            original_data={"theme": "nether_like", "biomes": ["Hell"]}
        )
        res = engine.analyze_feature(ctx)
        assert isinstance(res, AssumptionResult)
        assert res.applied_assumption is not None
        assert "Dimension" in res.applied_assumption.java_feature

    def test_apply_assumption_dimension(self, engine):
        ctx = FeatureContext(
            feature_id="dim_1",
            feature_type="custom_dimension",
            original_data={"theme": "nether_like", "biomes": ["Hell"]},
            name="My Dimension"
        )
        res = engine.analyze_feature(ctx)
        plan = engine.apply_assumption(res)
        assert isinstance(plan, ConversionPlanComponent)
        assert plan.assumption_type == "dimension_to_structure"
        assert "The Nether" in plan.bedrock_equivalent

    def test_apply_assumption_machinery(self, engine):
        ctx = FeatureContext(
            feature_id="mach_1",
            feature_type="complex_machinery",
            original_data={"has_inventory": True},
            name="My Machine"
        )
        res = engine.analyze_feature(ctx)
        plan = engine.apply_assumption(res)
        assert plan.assumption_type == "machinery_simplification"
        assert "simple container block" in plan.bedrock_equivalent

    def test_apply_assumption_gui(self, engine):
        ctx = FeatureContext(
            feature_id="gui_1",
            feature_type="custom_gui",
            original_data={"elements": [{"type": "label", "text": "Hello"}]},
            name="My GUI"
        )
        res = engine.analyze_feature(ctx)
        plan = engine.apply_assumption(res)
        assert plan.assumption_type == "gui_to_book_interface"
        assert "Book-based interface" in plan.bedrock_equivalent

    def test_generate_assumption_report(self, engine):
        comp = ConversionPlanComponent(
            original_feature_id="f1",
            original_feature_type="custom_dimension",
            assumption_type="dimension_to_structure",
            bedrock_equivalent="Structure",
            impact_level="high",
            user_explanation="The custom dimension 'My Dim' ..."
        )
        report = engine.generate_assumption_report([comp])
        assert len(report.assumptions_applied) == 1
        assert "My Dim" in report.assumptions_applied[0].original_feature

    def test_get_assumptions_by_impact(self, engine):
        lows = engine.get_assumptions_by_impact(AssumptionImpact.LOW)
        assert isinstance(lows, list)

    def test_get_conflict_analysis(self, engine):
        analysis = engine.get_conflict_analysis("custom_dimension")
        assert "feature_name" in analysis
        assert "has_conflicts" in analysis

    def test_convert_gui_elements_to_pages_pagination(self, engine):
        elements = [{"type": "label", "text": f"Line {i}"} for i in range(20)]
        pages = engine._convert_gui_elements_to_pages(elements, "Test GUI")
        assert len(pages) > 1
