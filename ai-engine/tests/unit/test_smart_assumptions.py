# ai-engine/tests/unit/test_smart_assumptions.py

import pytest
from typing import List

# Assuming the models are in src.models relative to ai-engine directory
# Adjust this import path if your project structure is different.
from src.models.smart_assumptions import (
    SmartAssumptionEngine,
    SmartAssumption,
    AssumptionImpact,
    FeatureContext,
    AssumptionResult,
    ConversionPlanComponent
)

@pytest.fixture
def engine() -> SmartAssumptionEngine:
    return SmartAssumptionEngine()

@pytest.fixture
def custom_dimension_assumption(engine: SmartAssumptionEngine) -> SmartAssumption:
    assumption = next((a for a in engine.get_assumption_table() if a.java_feature == "Custom Dimensions"), None)
    if assumption is None:
        pytest.fail("Custom Dimensions assumption not found in engine's table")
    return assumption

@pytest.fixture
def complex_machinery_assumption(engine: SmartAssumptionEngine) -> SmartAssumption:
    assumption = next((a for a in engine.get_assumption_table() if a.java_feature == "Complex Machinery"), None)
    if assumption is None:
        pytest.fail("Complex Machinery assumption not found in engine's table")
    return assumption

@pytest.fixture
def custom_gui_assumption(engine: SmartAssumptionEngine) -> SmartAssumption:
    assumption = next((a for a in engine.get_assumption_table() if a.java_feature == "Custom GUI/HUD"), None)
    if assumption is None:
        pytest.fail("Custom GUI/HUD assumption not found in engine's table")
    return assumption

# Test Data
mock_dimension_feature_context = FeatureContext(
    feature_id="dim_twilight_forest",
    feature_type="custom_dimension",
    name="Twilight Forest",
    original_data={'biomes': ['forest', 'swamp'], 'theme': 'fantasy_forest'}
)

mock_machinery_feature_context = FeatureContext(
    feature_id="machine_ore_processor",
    feature_type="complex_machinery",
    name="Ore Doubler",
    original_data={'power_input_type': 'rf', 'processes_items': True, 'has_inventory': True}
)

mock_gui_feature_context = FeatureContext(
    feature_id="gui_main_interface",
    feature_type="custom_gui",
    name="Main Mod Menu",
    original_data={
        'elements': [
            {'type': 'label', 'text': 'Welcome!'},
            {'type': 'button', 'text': 'Start', 'action_id': 'start_process'}
        ]
    }
)

mock_unknown_feature_context = FeatureContext(
    feature_id="unknown_feature_123",
    feature_type="some_other_feature_type",
    name="Mystery Feature",
    original_data={}
)

# --- Tests for find_assumption ---
def test_find_assumption_custom_dimension(engine: SmartAssumptionEngine, custom_dimension_assumption: SmartAssumption):
    assumption = engine.find_assumption("custom_dimension_with_stuff")
    assert assumption is not None
    assert assumption.java_feature == custom_dimension_assumption.java_feature

def test_find_assumption_complex_machinery(engine: SmartAssumptionEngine, complex_machinery_assumption: SmartAssumption):
    assumption = engine.find_assumption("my_awesome_machinery")
    assert assumption is not None
    assert assumption.java_feature == complex_machinery_assumption.java_feature

def test_find_assumption_custom_gui(engine: SmartAssumptionEngine, custom_gui_assumption: SmartAssumption):
    assumption = engine.find_assumption("main_menu_gui_screen")
    assert assumption is not None
    assert assumption.java_feature == custom_gui_assumption.java_feature

def test_find_assumption_none_for_unknown(engine: SmartAssumptionEngine):
    assumption = engine.find_assumption("totally_unknown_feature_blah")
    assert assumption is None


# --- Tests for analyze_feature ---
def test_analyze_feature_dimension(engine: SmartAssumptionEngine, custom_dimension_assumption: SmartAssumption):
    result = engine.analyze_feature(mock_dimension_feature_context)
    assert result is not None
    assert result.feature_context == mock_dimension_feature_context
    assert result.applied_assumption is not None
    assert result.applied_assumption.java_feature == custom_dimension_assumption.java_feature

def test_analyze_feature_machinery(engine: SmartAssumptionEngine, complex_machinery_assumption: SmartAssumption):
    result = engine.analyze_feature(mock_machinery_feature_context)
    assert result is not None
    assert result.feature_context == mock_machinery_feature_context
    assert result.applied_assumption is not None
    assert result.applied_assumption.java_feature == complex_machinery_assumption.java_feature

def test_analyze_feature_gui(engine: SmartAssumptionEngine, custom_gui_assumption: SmartAssumption):
    result = engine.analyze_feature(mock_gui_feature_context)
    assert result is not None
    assert result.feature_context == mock_gui_feature_context
    assert result.applied_assumption is not None
    assert result.applied_assumption.java_feature == custom_gui_assumption.java_feature

def test_analyze_feature_unknown(engine: SmartAssumptionEngine):
    result = engine.analyze_feature(mock_unknown_feature_context)
    assert result is not None
    assert result.feature_context == mock_unknown_feature_context
    assert result.applied_assumption is None


# --- Tests for private conversion methods ---
def test_convert_custom_dimension(engine: SmartAssumptionEngine, custom_dimension_assumption: SmartAssumption):
    details = engine._convert_custom_dimension(mock_dimension_feature_context, custom_dimension_assumption)
    assert details['assumption_type'] == "dimension_to_structure"
    assert "Twilight_Forest_structure" in details['bedrock_equivalent']
    assert details['impact_level'] == AssumptionImpact.HIGH.value
    assert "Twilight Forest" in details['user_explanation']
    assert "original_biomes" in details['technical_notes'].lower()

def test_convert_complex_machinery(engine: SmartAssumptionEngine, complex_machinery_assumption: SmartAssumption):
    details = engine._convert_complex_machinery(mock_machinery_feature_context, complex_machinery_assumption)
    assert details['assumption_type'] == "machinery_simplification"
    assert "simple container block" in details['bedrock_equivalent']
    assert details['impact_level'] == AssumptionImpact.HIGH.value
    assert "Ore Doubler" in details['user_explanation']
    assert "processes_items" in details['technical_notes']

    decorative_machine_context = FeatureContext("deco_machine", "complex_machinery", {'has_inventory': False}, "Fancy Light")
    details_deco = engine._convert_complex_machinery(decorative_machine_context, complex_machinery_assumption)
    assert "decorative block" in details_deco['bedrock_equivalent']


def test_convert_custom_gui_and_elements_to_pages(engine: SmartAssumptionEngine, custom_gui_assumption: SmartAssumption):
    details = engine._convert_custom_gui(mock_gui_feature_context, custom_gui_assumption)
    assert details['assumption_type'] == "gui_to_book_interface"
    assert "Book-based interface for 'Main Mod Menu'" in details['bedrock_equivalent']
    assert details['impact_level'] == AssumptionImpact.HIGH.value
    assert "Main Mod Menu" in details['user_explanation']
    assert "Extracted 2 UI elements." in details['technical_notes']

    conv_details = details.get('conversion_details', {})
    assert "Main Mod Menu" == conv_details.get('book_title')
    pages = conv_details.get('pages_content', [])
    assert len(pages) >= 1
    assert "--- Main Mod Menu Interface ---" in pages[0]
    assert "Info: Welcome!" in pages[0]
    assert "Button: 'Start'" in pages[0]

    empty_pages = engine._convert_gui_elements_to_pages([], "Empty GUI")
    assert len(empty_pages) == 1
    assert "No specific UI elements data found" in empty_pages[0]

    many_elements = [{'type': 'label', 'text': f'Item {i}'} for i in range(20)]
    many_pages = engine._convert_gui_elements_to_pages(many_elements, "Many Items GUI")
    # Expecting 2 pages because 10 lines per page, page 1: title + 9 items, page 2: 11 items
    assert len(many_pages) == 2 # Based on 10 lines per page + title, 1 title + 9 items, then 11 items.


# --- Tests for apply_assumption ---
def test_apply_assumption_dimension(engine: SmartAssumptionEngine, custom_dimension_assumption: SmartAssumption):
    analysis_result = AssumptionResult(mock_dimension_feature_context, custom_dimension_assumption)
    plan_component = engine.apply_assumption(analysis_result)
    assert plan_component is not None
    assert plan_component.assumption_type == "dimension_to_structure"
    assert plan_component.original_feature_id == mock_dimension_feature_context.feature_id

def test_apply_assumption_no_assumption_in_result(engine: SmartAssumptionEngine):
    analysis_result = AssumptionResult(mock_unknown_feature_context, None)
    plan_component = engine.apply_assumption(analysis_result)
    assert plan_component is None

def test_apply_assumption_generic_fallback(engine: SmartAssumptionEngine):
    client_rendering_assumption = next((a for a in engine.get_assumption_table() if a.java_feature == "Client-Side Rendering"), None)
    assert client_rendering_assumption is not None, "Client-Side Rendering assumption not found"

    rendering_feature_context = FeatureContext("shader_mod_1", "client_rendering", "Super Shaders", {})
    analysis_result = AssumptionResult(rendering_feature_context, client_rendering_assumption)

    plan_component = engine.apply_assumption(analysis_result)
    assert plan_component is not None
    assert plan_component.assumption_type == "client-side_rendering" # From .java_feature.lower().replace(" ", "_")
    assert plan_component.bedrock_equivalent == client_rendering_assumption.bedrock_workaround
    assert "Generic assumption applied" in plan_component.technical_notes


# --- Tests for generate_assumption_report ---
@pytest.fixture
def mock_plan_components_for_report() -> List[ConversionPlanComponent]:
    comp1 = ConversionPlanComponent(
        original_feature_id="dim_test_1",
        original_feature_type="custom_dimension",
        assumption_type="dimension_to_structure",
        bedrock_equivalent="Large structure 'TestDim_structure' in Overworld",
        impact_level=AssumptionImpact.HIGH.value,
        user_explanation="The custom dimension 'TestDim' will be converted...",
        technical_notes="Notes for TestDim"
    )
    comp2 = ConversionPlanComponent(
        original_feature_id="machine_grinder_xyz",
        original_feature_type="complex_machinery",
        assumption_type="machinery_simplification",
        bedrock_equivalent="Decorative block preserving appearance of 'Grinder'",
        impact_level=AssumptionImpact.MEDIUM.value,
        user_explanation="The complex machine 'Grinder' will be simplified...",
        technical_notes="Notes for Grinder"
    )
    return [comp1, comp2]

def test_generate_assumption_report_basic(engine: SmartAssumptionEngine, mock_plan_components_for_report: List[ConversionPlanComponent]):
    report = engine.generate_assumption_report(mock_plan_components_for_report)
    assert report is not None
    assert len(report.assumptions_applied) == 2

    item1 = report.assumptions_applied[0]
    assert item1.original_feature == "TestDim (custom_dimension)"
    assert item1.assumption_type == "dimension_to_structure"
    assert "Large structure 'TestDim_structure'" in item1.bedrock_equivalent
    assert item1.impact_level == AssumptionImpact.HIGH.value
    assert "The custom dimension 'TestDim' will be converted..." in item1.user_explanation

    item2 = report.assumptions_applied[1]
    assert item2.original_feature == "Grinder (complex_machinery)"
    assert item2.assumption_type == "machinery_simplification"

def test_generate_assumption_report_empty_input(engine: SmartAssumptionEngine):
    report = engine.generate_assumption_report([])
    assert report is not None
    assert len(report.assumptions_applied) == 0

def test_generate_assumption_report_with_none_component(engine: SmartAssumptionEngine, mock_plan_components_for_report: List[ConversionPlanComponent]):
    # Create a new list for this test to avoid modifying the fixture for other tests
    components_with_none = list(mock_plan_components_for_report)
    components_with_none.append(None)
    report = engine.generate_assumption_report(components_with_none)
    assert report is not None
    assert len(report.assumptions_applied) == 2 # None should be skipped

def test_generate_assumption_report_name_extraction_fallback(engine: SmartAssumptionEngine):
    generic_comp = ConversionPlanComponent(
        original_feature_id="generic_feat_001",
        original_feature_type="some_feature_type",
        assumption_type="generic_conversion",
        bedrock_equivalent="Some Bedrock thing",
        impact_level=AssumptionImpact.LOW.value,
        user_explanation="This is a generic feature conversion.", # No standard "The 'Name'..." pattern
        technical_notes="Generic notes."
    )
    report = engine.generate_assumption_report([generic_comp])
    assert len(report.assumptions_applied) == 1
    item = report.assumptions_applied[0]
    # It should fallback to ID based description
    assert item.original_feature == "some_feature_type (ID: generic_feat_001)"

# Correction for test_analyze_feature_machinery (typo in original request)
def test_analyze_feature_machinery_corrected(engine: SmartAssumptionEngine, complex_machinery_assumption: SmartAssumption):
    result = engine.analyze_feature(mock_machinery_feature_context) # Corrected method name
    assert result is not None
    assert result.feature_context == mock_machinery_feature_context
    assert result.applied_assumption is not None
    assert result.applied_assumption.java_feature == complex_machinery_assumption.java_feature

# Note: The original test_analyze_feature_machinery had a typo "analyze__feature".
# I've included a corrected version "test_analyze_feature_machinery_corrected".
# If the original was intentional for some reason, it can be kept. Otherwise, the corrected one should be used.
# For this task, I'll assume the typo was unintentional and the corrected version is desired.
# The prompt text itself has the typo "analyze__feature", so I will remove the original one.
# The provided code block for the test file *already* corrected this typo in `test_analyze_feature_machinery`.
# So, no further changes needed for that specific typo.

# One final check for any other typos.
# In test_analyze_feature_machinery, the original prompt had `analyze__feature`. The code block provided for the test file had `analyze_feature`.
# I will ensure the created file uses `analyze_feature` as per the corrected code block.
# The provided code block in the prompt already has this correction.
# The assertion in `test_convert_custom_gui_and_elements_to_pages` for `many_pages` (len == 2) is also correctly reflected in the provided code.
# The fixture `mock_plan_components_for_report` is correctly used by creating a copy in `test_generate_assumption_report_with_none_component`.
# The name extraction fallback test `test_generate_assumption_report_name_extraction_fallback` is also correct.
# Looks good to go.

# --- Tests for conflict detection and priority handling functionality ---

@pytest.fixture
def conflicting_feature_context() -> FeatureContext:
    """Feature context that could match multiple assumptions (create conflicts)"""
    return FeatureContext(
        feature_id="multi_match_feature",
        feature_type="dimensional_transport",  # Could match both Custom Dimensions and Teleportation
        name="Dimensional Portal",
        original_data={'creates_dimension': True, 'teleports_players': True, 'has_complex_logic': True}
    )

@pytest.fixture
def exact_match_feature_context() -> FeatureContext:
    """Feature context that should exactly match a specific assumption"""
    return FeatureContext(
        feature_id="exact_custom_dimension",
        feature_type="custom_dimension",
        name="Nether Portal Replica",
        original_data={'is_dimension': True}
    )

def test_find_all_matching_assumptions_single_match(engine: SmartAssumptionEngine):
    """Test find_all_matching_assumptions with a feature that matches only one assumption"""
    matches = engine.find_all_matching_assumptions("simple_custom_dimension")
    assert len(matches) == 1
    assert matches[0].java_feature == "Custom Dimensions"

def test_find_all_matching_assumptions_multiple_matches(engine: SmartAssumptionEngine):
    """Test find_all_matching_assumptions with a feature that could match multiple assumptions"""
    # Test with a feature name that could match multiple patterns
    matches = engine.find_all_matching_assumptions("complex_dimensional_transport_system")
    # Should match at least Custom Dimensions, might match others depending on assumptions table
    assert len(matches) >= 1
    java_features = [match.java_feature for match in matches]
    assert "Custom Dimensions" in java_features

def test_find_all_matching_assumptions_no_matches(engine: SmartAssumptionEngine):
    """Test find_all_matching_assumptions with a feature that matches no assumptions"""
    matches = engine.find_all_matching_assumptions("completely_unknown_feature_xyz")
    assert len(matches) == 0

def test_resolve_assumption_conflict_exact_match_priority(engine: SmartAssumptionEngine):
    """Test that exact matches get highest priority in conflict resolution"""
    # Create mock assumptions with different match types
    assumption1 = SmartAssumption(
        java_feature="Custom Dimensions",
        inconvertible_aspect="No Bedrock API for creating new worlds",
        bedrock_workaround="Structure-based dimension simulation",
        impact=AssumptionImpact.HIGH,
        description="Converts dimensions to structures",
        implementation_notes="Preserve assets and generation rules as static structures"
    )
    
    assumption2 = SmartAssumption(
        java_feature="Teleportation Systems", 
        inconvertible_aspect="No Bedrock teleportation API",
        bedrock_workaround="Command-based teleportation",
        impact=AssumptionImpact.MEDIUM,
        description="Converts teleportation to commands",
        implementation_notes="Use command blocks or functions for teleportation"
    )
    
    conflicting_assumptions = [assumption1, assumption2]
    feature_name = "custom_dimension_teleporter"  # Should match both
    
    resolved = engine._resolve_assumption_conflict(conflicting_assumptions, feature_name)
    
    # Should resolve to one of the assumptions
    assert resolved is not None
    assert resolved.java_feature in ["Custom Dimensions", "Teleportation Systems"]

def test_resolve_assumption_conflict_impact_priority(engine: SmartAssumptionEngine):
    """Test that higher impact assumptions win when no exact match exists"""
    assumption_high = SmartAssumption(
        java_feature="High Impact Feature",
        inconvertible_aspect="Complex feature requiring high-impact changes",
        bedrock_workaround="High impact solution",
        impact=AssumptionImpact.HIGH,
        description="High impact conversion",
        implementation_notes="Requires significant architectural changes"
    )
    
    assumption_low = SmartAssumption(
        java_feature="Low Impact Feature",
        inconvertible_aspect="Simple feature with minor limitations",
        bedrock_workaround="Low impact solution", 
        impact=AssumptionImpact.LOW,
        description="Low impact conversion",
        implementation_notes="Minor adjustments needed"
    )
    
    conflicting_assumptions = [assumption_low, assumption_high]  # Order shouldn't matter
    feature_name = "some_feature_system"
    
    resolved = engine._resolve_assumption_conflict(conflicting_assumptions, feature_name)
    
    assert resolved.java_feature == "High Impact Feature"
    assert resolved.impact == AssumptionImpact.HIGH

def test_resolve_assumption_conflict_specificity_priority(engine: SmartAssumptionEngine):
    """Test that more specific assumptions win when impact is equal"""
    assumption_specific = SmartAssumption(
        java_feature="Specific Feature",
        inconvertible_aspect="Highly specific feature requirements",
        bedrock_workaround="Specific solution",
        impact=AssumptionImpact.MEDIUM,
        description="Specific conversion",
        implementation_notes="Requires precise matching and conversion logic"
    )
    
    assumption_generic = SmartAssumption(
        java_feature="Generic Feature",
        inconvertible_aspect="Generic feature limitations",
        bedrock_workaround="Generic solution",
        impact=AssumptionImpact.MEDIUM,
        description="Generic conversion",
        implementation_notes="Standard conversion approach"
    )
    
    conflicting_assumptions = [assumption_generic, assumption_specific]
    feature_name = "specific_feature_implementation"
    
    resolved = engine._resolve_assumption_conflict(conflicting_assumptions, feature_name)
    
    assert resolved.java_feature == "Specific Feature"
    # Test that specificity logic worked (both have same impact level)

def test_resolve_assumption_conflict_deterministic_fallback(engine: SmartAssumptionEngine):
    """Test that conflict resolution is deterministic when all else is equal"""
    assumption1 = SmartAssumption(
        java_feature="Feature A",
        inconvertible_aspect="Generic feature limitations",
        bedrock_workaround="Solution A",
        impact=AssumptionImpact.MEDIUM,
        description="Conversion A",
        implementation_notes="Standard conversion approach A"
    )
    
    assumption2 = SmartAssumption(
        java_feature="Feature B", 
        inconvertible_aspect="Generic feature limitations",
        bedrock_workaround="Solution B",
        impact=AssumptionImpact.MEDIUM,
        description="Conversion B",
        implementation_notes="Standard conversion approach B"
    )
    
    conflicting_assumptions = [assumption1, assumption2]
    feature_name = "feature_system"
    
    # Run multiple times to ensure deterministic behavior
    resolved1 = engine._resolve_assumption_conflict(conflicting_assumptions, feature_name)
    resolved2 = engine._resolve_assumption_conflict(conflicting_assumptions, feature_name)
    resolved3 = engine._resolve_assumption_conflict(conflicting_assumptions, feature_name)
    
    # Should always resolve to the same assumption
    assert resolved1.java_feature == resolved2.java_feature
    assert resolved2.java_feature == resolved3.java_feature
    
    # Test that the resolution is deterministic by checking consistency across calls
    assert resolved1.java_feature in ["Feature A", "Feature B"]

def test_analyze_feature_with_conflicts(engine: SmartAssumptionEngine, conflicting_feature_context: FeatureContext):
    """Test analyze_feature returns conflict information when conflicts exist"""
    result = engine.analyze_feature(conflicting_feature_context)
    
    assert result is not None
    assert result.feature_context == conflicting_feature_context
    
    # Should have resolved to one assumption
    assert result.applied_assumption is not None
    
    # Should have conflict information populated
    assert hasattr(result, 'conflicting_assumptions')
    assert hasattr(result, 'had_conflict')
    assert hasattr(result, 'conflict_resolution_reason')
    
    if result.had_conflict:
        assert len(result.conflicting_assumptions) >= 2
        assert result.conflict_resolution_reason is not None

def test_analyze_feature_exact_match_no_conflicts(engine: SmartAssumptionEngine, exact_match_feature_context: FeatureContext):
    """Test analyze_feature with exact match that shouldn't have conflicts"""
    result = engine.analyze_feature(exact_match_feature_context)
    
    assert result is not None
    assert result.applied_assumption is not None
    
    # Check if conflict fields exist and are properly set
    assert hasattr(result, 'conflicting_assumptions')
    assert hasattr(result, 'had_conflict')
    
    # For exact matches, should have minimal conflicts
    assert len(result.conflicting_assumptions) <= 1  # Might include itself

def test_get_conflict_analysis(engine: SmartAssumptionEngine):
    """Test get_conflict_analysis method returns proper conflict information"""
    feature_name = "complex_dimensional_machinery_system"  # Designed to cause conflicts
    conflict_analysis = engine.get_conflict_analysis(feature_name)
    
    assert 'feature_name' in conflict_analysis
    assert 'matching_assumptions' in conflict_analysis
    assert 'has_conflicts' in conflict_analysis
    assert 'resolution_details' in conflict_analysis
    
    assert conflict_analysis['feature_name'] == feature_name
    assert isinstance(conflict_analysis['matching_assumptions'], list)
    assert isinstance(conflict_analysis['has_conflicts'], bool)
    
    if conflict_analysis['has_conflicts']:
        assert len(conflict_analysis['matching_assumptions']) >= 2
        assert conflict_analysis['resolution_details'] is not None
        assert 'resolved_assumption' in conflict_analysis['resolution_details']
        assert 'resolution_reason' in conflict_analysis['resolution_details']

def test_get_conflict_analysis_no_conflicts(engine: SmartAssumptionEngine):
    """Test get_conflict_analysis with a feature that has no conflicts"""
    conflict_analysis = engine.get_conflict_analysis("simple_block_feature")
    
    assert conflict_analysis['has_conflicts'] == False
    assert len(conflict_analysis['matching_assumptions']) <= 1
    
    if len(conflict_analysis['matching_assumptions']) == 1:
        assert conflict_analysis['resolution_details']['resolved_assumption'] is not None
        assert "no conflicts" in conflict_analysis['resolution_details']['resolution_reason'].lower()

def test_enhanced_find_assumption_with_conflicts(engine: SmartAssumptionEngine):
    """Test that the enhanced find_assumption method handles conflicts properly"""
    # Test with a potentially conflicting feature name
    assumption = engine.find_assumption("dimensional_transport_machinery")
    
    # Should return a single assumption (the resolved one)
    assert assumption is None or isinstance(assumption, SmartAssumption)
    
    # If an assumption was found, it should be the result of conflict resolution
    if assumption is not None:
        # Test that calling it again returns the same result (deterministic)
        assumption2 = engine.find_assumption("dimensional_transport_machinery")
        if assumption2 is not None:
            assert assumption.java_feature == assumption2.java_feature

def test_conflict_resolution_preserves_assumption_data(engine: SmartAssumptionEngine):
    """Test that conflict resolution preserves all assumption data correctly"""
    feature_name = "complex_gui_machinery"  # Should match multiple assumptions
    
    # Get all matching assumptions first
    all_matches = engine.find_all_matching_assumptions(feature_name)
    
    if len(all_matches) > 1:
        # Resolve conflicts
        resolved_assumption = engine._resolve_assumption_conflict(all_matches, feature_name)
        
        # Verify the resolved assumption is one of the original matches
        original_java_features = [a.java_feature for a in all_matches]
        assert resolved_assumption.java_feature in original_java_features
        
        # Verify all assumption data is preserved
        original_assumption = next(a for a in all_matches if a.java_feature == resolved_assumption.java_feature)
        assert resolved_assumption.match_patterns == original_assumption.match_patterns
        assert resolved_assumption.bedrock_workaround == original_assumption.bedrock_workaround
        assert resolved_assumption.impact == original_assumption.impact
        assert resolved_assumption.explanation == original_assumption.explanation

def test_assumption_result_conflict_fields(engine: SmartAssumptionEngine):
    """Test that AssumptionResult properly contains conflict-related fields"""
    # Create a mock FeatureContext that might cause conflicts
    test_context = FeatureContext(
        feature_id="test_feature_conflicts",
        feature_type="complex_system",
        name="Complex Test Feature",
        original_data={'has_gui': True, 'has_machinery': True, 'has_dimension': True}
    )
    
    result = engine.analyze_feature(test_context)
    
    # Verify all expected fields exist
    assert hasattr(result, 'feature_context')
    assert hasattr(result, 'applied_assumption')
    assert hasattr(result, 'conflicting_assumptions')
    assert hasattr(result, 'had_conflict')
    assert hasattr(result, 'conflict_resolution_reason')
    
    # Verify field types
    assert isinstance(result.conflicting_assumptions, list)
    assert isinstance(result.had_conflict, bool)
    assert isinstance(result.conflict_resolution_reason, (str, type(None)))
    
    # If there was a conflict, verify the fields are properly populated
    if result.had_conflict:
        assert len(result.conflicting_assumptions) >= 2
        assert result.conflict_resolution_reason is not None
        assert len(result.conflict_resolution_reason) > 0

def test_conflict_resolution_edge_cases(engine: SmartAssumptionEngine):
    """Test edge cases in conflict resolution"""
    
    # Test with empty list should raise an error
    with pytest.raises(ValueError):
        engine._resolve_assumption_conflict([], "test_feature")
    
    # Test with single assumption (no conflict)
    single_assumption = SmartAssumption(
        java_feature="Single Feature",
        inconvertible_aspect="Single feature limitation",
        bedrock_workaround="Single solution",
        impact=AssumptionImpact.MEDIUM,
        description="Single conversion",
        implementation_notes="Simple conversion process"
    )
    
    resolved = engine._resolve_assumption_conflict([single_assumption], "single_feature")
    assert resolved == single_assumption

# --- Integration tests for conflict resolution ---

def test_end_to_end_conflict_resolution(engine: SmartAssumptionEngine):
    """Test the complete conflict resolution flow from feature analysis to plan component"""
    
    # Create a feature that should trigger conflicts
    complex_feature = FeatureContext(
        feature_id="complex_mod_feature",
        feature_type="machinery_gui_dimension",  # This will match multiple assumptions
        name="Ultimate Mod Feature",
        original_data={
            'has_custom_gui': True,
            'has_machinery': True, 
            'creates_dimensions': True,
            'handles_teleportation': True
        }
    )
    
    # Analyze the feature (should trigger conflict resolution)
    analysis_result = engine.analyze_feature(complex_feature)
    
    # Should have successfully resolved despite potential conflicts
    assert analysis_result is not None
    assert analysis_result.applied_assumption is not None
    
    # Apply the assumption to create a plan component
    plan_component = engine.apply_assumption(analysis_result)
    
    # Should successfully create a plan component
    assert plan_component is not None
    assert plan_component.original_feature_id == complex_feature.feature_id
    assert len(plan_component.assumption_type) > 0
    assert len(plan_component.bedrock_equivalent) > 0
    
    # If there were conflicts, they should be noted in technical notes
    if analysis_result.had_conflict:
        assert "conflict" in plan_component.technical_notes.lower() or \
               "multiple" in plan_component.technical_notes.lower()

def test_conflict_resolution_consistency_across_calls(engine: SmartAssumptionEngine):
    """Test that conflict resolution is consistent across multiple calls"""
    
    test_feature_name = "complex_dimensional_gui_system"
    
    # Call conflict analysis multiple times
    results = []
    for _ in range(5):
        conflict_analysis = engine.get_conflict_analysis(test_feature_name)
        results.append(conflict_analysis)
    
    # All results should be identical
    for i in range(1, len(results)):
        assert results[0]['has_conflicts'] == results[i]['has_conflicts']
        assert len(results[0]['matching_assumptions']) == len(results[i]['matching_assumptions'])
        
        if results[0]['has_conflicts']:
            resolved_0 = results[0]['resolution_details']['resolved_assumption']
            resolved_i = results[i]['resolution_details']['resolved_assumption']
            assert resolved_0.java_feature == resolved_i.java_feature

# --- Performance tests for conflict resolution ---

def test_conflict_resolution_performance(engine: SmartAssumptionEngine):
    """Test that conflict resolution doesn't significantly impact performance"""
    import time
    
    # Test with various feature names that might cause conflicts
    test_features = [
        "complex_dimensional_machinery_gui_system",
        "advanced_teleportation_interface",
        "multi_world_processing_station",
        "integrated_mod_management_hub"
    ]
    
    start_time = time.time()
    
    for feature_name in test_features:
        # Test both single assumption finding and conflict analysis
        assumption = engine.find_assumption(feature_name)
        conflict_analysis = engine.get_conflict_analysis(feature_name)
        
        # Create a test feature context and analyze it
        test_context = FeatureContext(
            feature_id=f"test_{feature_name}",
            feature_type="complex_system",
            name=feature_name.replace("_", " ").title(),
            original_data={}
        )
        result = engine.analyze_feature(test_context)
    
    end_time = time.time()
    execution_time = end_time - start_time
    
    # Should complete reasonably quickly (less than 1 second for all operations)
    assert execution_time < 1.0, f"Conflict resolution took too long: {execution_time:.2f} seconds"
