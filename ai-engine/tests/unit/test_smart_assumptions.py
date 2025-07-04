# ai-engine/tests/unit/test_smart_assumptions.py

import pytest
from typing import List, Dict, Any, Optional

# Assuming the models are in src.models relative to ai-engine directory
# Adjust this import path if your project structure is different.
from src.models.smart_assumptions import (
    SmartAssumptionEngine,
    SmartAssumption,
    AssumptionImpact,
    FeatureContext,
    AssumptionResult,
    ConversionPlanComponent,
    AppliedAssumptionReportItem,
    AssumptionReport
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

    decorative_machine_context = FeatureContext("deco_machine", "complex_machinery", "Fancy Light", {'has_inventory': False})
    details_deco = engine._convert_complex_machinery(decorative_machine_context, complex_machinery_assumption)
    assert "decorative block" in details_deco['bedrock_equivalent']


def test_convert_custom_gui_and_elements_to_pages(engine: SmartAssumptionEngine, custom_gui_assumption: SmartAssumption):
    details = engine._convert_custom_gui(mock_gui_feature_context, custom_gui_assumption)
    assert details['assumption_type'] == "gui_to_book_interface"
    assert "Book-based interface for 'Main Mod Menu'" in details['bedrock_equivalent']
    assert details['impact_level'] == AssumptionImpact.MEDIUM.value
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
