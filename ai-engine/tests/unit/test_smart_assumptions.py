"""
Unit tests for Smart Assumption Engine
"""

import pytest
from unittest.mock import Mock, patch
from src.models.smart_assumptions import (
    SmartAssumptionEngine,
    SmartAssumption,
    AssumptionImpact
)


class TestSmartAssumptionEngine:
    """Test suite for SmartAssumptionEngine"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.engine = SmartAssumptionEngine()
    
    def test_initialization(self):
        """Test engine initializes with PRD assumption table"""
        assert self.engine.assumption_table is not None
        assert len(self.engine.assumption_table) > 0
        
        # Verify PRD assumptions are present
        assumption_features = [a.java_feature for a in self.engine.assumption_table]
        assert "Custom Dimensions" in assumption_features
        assert "Complex Machinery" in assumption_features
        assert "Custom GUI/HUD" in assumption_features
        assert "Client-Side Rendering" in assumption_features
        assert "Mod Dependencies" in assumption_features
    
    def test_get_assumption_table(self):
        """Test assumption table retrieval"""
        table = self.engine.get_assumption_table()
        assert isinstance(table, list)
        assert all(isinstance(a, SmartAssumption) for a in table)
        
        # Test specific PRD assumptions
        dimension_assumption = next(
            (a for a in table if "Custom Dimensions" in a.java_feature), None
        )
        assert dimension_assumption is not None
        assert dimension_assumption.impact == AssumptionImpact.HIGH
        assert "structure" in dimension_assumption.bedrock_workaround.lower()
    
    def test_find_assumption_exact_match(self):
        """Test finding assumption with exact feature match"""
        assumption = self.engine.find_assumption("Custom Dimensions")
        assert assumption is not None
        assert assumption.java_feature == "Custom Dimensions"
        assert assumption.impact == AssumptionImpact.HIGH
    
    def test_find_assumption_partial_match(self):
        """Test finding assumption with partial keyword match"""
        assumption = self.engine.find_assumption("custom dimension")
        assert assumption is not None
        assert "Dimensions" in assumption.java_feature
        
        assumption = self.engine.find_assumption("complex machinery")
        assert assumption is not None
        assert "Machinery" in assumption.java_feature
    
    def test_find_assumption_no_match(self):
        """Test finding assumption with no matches"""
        assumption = self.engine.find_assumption("nonexistent feature")
        assert assumption is None
    
    def test_apply_assumption_custom_dimension(self):
        """Test applying assumption for custom dimension"""
        feature_data = {
            'name': 'twilight_forest',
            'biomes': ['twilight_oak', 'dark_forest'],
            'dimension_type': 'custom'
        }
        
        result = self.engine.apply_assumption("custom_dimension", feature_data)
        
        assert result is not None
        assert result['conversion_type'] == 'dimension_to_structure'
        assert result['target_dimension'] == 'overworld'
        assert result['structure_name'] == 'twilight_forest_dimension_structure'
        assert result['original_biomes'] == ['twilight_oak', 'dark_forest']
        assert result['impact'] == 'high'
        assert 'user_note' in result
    
    def test_apply_assumption_complex_machinery(self):
        """Test applying assumption for complex machinery"""
        feature_data = {
            'name': 'advanced_furnace',
            'decorative': False,
            'power_requirements': 'RF',
            'multiblock': True
        }
        
        result = self.engine.apply_assumption("complex_machinery", feature_data)
        
        assert result is not None
        assert result['conversion_type'] == 'machinery_simplification'
        assert result['preserved_elements'] == ['model', 'texture', 'name']
        assert result['removed_elements'] == ['power_system', 'processing_logic', 'multiblock_structure']
        assert result['replacement_type'] == 'container'
        assert result['impact'] == 'high'
    
    def test_apply_assumption_custom_gui(self):
        """Test applying assumption for custom GUI"""
        feature_data = {
            'elements': [
                {'type': 'button', 'label': 'Start Process', 'action': 'start_machine'},
                {'type': 'display', 'content': 'Status: Ready'}
            ]
        }
        
        result = self.engine.apply_assumption("custom_gui", feature_data)
        
        assert result is not None
        assert result['conversion_type'] == 'gui_to_book_interface'
        assert result['interface_elements'] == feature_data['elements']
        assert len(result['book_pages']) == 2
        assert 'Button: Start Process' in result['book_pages'][0]
        assert 'Info: Status: Ready' in result['book_pages'][1]
        assert result['impact'] == 'high'
    
    def test_apply_assumption_client_rendering(self):
        """Test applying assumption for client-side rendering"""
        feature_data = {
            'rendering_features': ['custom_shaders', 'particle_effects'],
            'render_type': 'client_side'
        }
        
        result = self.engine.apply_assumption("client_rendering", feature_data)
        
        assert result is not None
        assert result['conversion_type'] == 'exclusion'
        assert result['reason'] == 'client_side_rendering_unsupported'
        assert result['excluded_features'] == ['custom_shaders', 'particle_effects']
        assert result['impact'] == 'high'
    
    def test_apply_assumption_simple_dependency(self):
        """Test applying assumption for simple mod dependency"""
        feature_data = {
            'dependency_name': 'simple_lib',
            'dependency_size': 50000,  # 50KB
            'dependency_type': 'library',
            'required_functions': ['utility_function', 'helper_method']
        }
        
        result = self.engine.apply_assumption("mod_dependency", feature_data)
        
        assert result is not None
        assert result['conversion_type'] == 'dependency_bundling'
        assert result['bundled_functions'] == ['utility_function', 'helper_method']
        assert result['impact'] == 'medium'
    
    def test_apply_assumption_complex_dependency(self):
        """Test applying assumption for complex mod dependency"""
        feature_data = {
            'dependency_name': 'complex_framework',
            'dependency_size': 2000000,  # 2MB
            'dependency_type': 'framework',
            'required_functions': ['complex_system']
        }
        
        result = self.engine.apply_assumption("mod_dependency", feature_data)
        
        assert result is not None
        assert result['conversion_type'] == 'dependency_failure'
        assert result['failed_dependency'] == 'complex_framework'
        assert result['reason'] == 'complex_dependency_unsupported'
        assert result['impact'] == 'medium'
    
    def test_apply_assumption_no_match(self):
        """Test applying assumption when no assumption matches"""
        with patch('src.models.smart_assumptions.logger') as mock_logger:
            result = self.engine.apply_assumption("unknown_feature", {})
            
            assert result is None
            mock_logger.warning.assert_called_once()
    
    def test_gui_elements_to_pages_conversion(self):
        """Test GUI elements to book pages conversion"""
        elements = [
            {'type': 'button', 'label': 'Test Button', 'action': 'test_action'},
            {'type': 'display', 'content': 'Test Content'},
            {'type': 'unknown', 'data': 'should_be_ignored'}
        ]
        
        pages = self.engine._convert_gui_elements_to_pages(elements)
        
        assert len(pages) == 2  # Unknown type should be ignored
        assert 'Button: Test Button' in pages[0]
        assert 'Action: test_action' in pages[0]
        assert 'Info: Test Content' in pages[1]
    
    def test_dependency_complexity_assessment(self):
        """Test dependency complexity assessment logic"""
        # Simple dependency
        simple_data = {
            'dependency_size': 50000,
            'dependency_type': 'library'
        }
        complexity = self.engine._assess_dependency_complexity(simple_data)
        assert complexity == 'simple'
        
        # Complex dependency (large size)
        complex_data = {
            'dependency_size': 200000,
            'dependency_type': 'library'
        }
        complexity = self.engine._assess_dependency_complexity(complex_data)
        assert complexity == 'complex'
        
        # Complex dependency (framework type)
        framework_data = {
            'dependency_size': 50000,
            'dependency_type': 'framework'
        }
        complexity = self.engine._assess_dependency_complexity(framework_data)
        assert complexity == 'complex'
    
    def test_assumption_impact_levels(self):
        """Test that all assumptions have appropriate impact levels"""
        table = self.engine.get_assumption_table()
        
        # Check that high-impact assumptions are properly categorized
        high_impact_features = [
            "Custom Dimensions", "Complex Machinery", "Client-Side Rendering"
        ]
        
        for feature in high_impact_features:
            assumption = next(
                (a for a in table if feature in a.java_feature), None
            )
            assert assumption is not None
            assert assumption.impact == AssumptionImpact.HIGH
    
    def test_generic_assumption_application(self):
        """Test generic assumption application for unspecified feature types"""
        feature_data = {'test': 'data'}
        result = self.engine.apply_assumption("unknown_feature_type", feature_data)
        
        # Unknown feature types should return None as there's no matching assumption
        assert result is None


class TestSmartAssumption:
    """Test suite for SmartAssumption dataclass"""
    
    def test_smart_assumption_creation(self):
        """Test SmartAssumption dataclass creation"""
        assumption = SmartAssumption(
            java_feature="Test Feature",
            inconvertible_aspect="Test aspect",
            bedrock_workaround="Test workaround",
            impact=AssumptionImpact.MEDIUM,
            description="Test description",
            implementation_notes="Test notes"
        )
        
        assert assumption.java_feature == "Test Feature"
        assert assumption.inconvertible_aspect == "Test aspect"
        assert assumption.bedrock_workaround == "Test workaround"
        assert assumption.impact == AssumptionImpact.MEDIUM
        assert assumption.description == "Test description"
        assert assumption.implementation_notes == "Test notes"


class TestAssumptionImpact:
    """Test suite for AssumptionImpact enum"""
    
    def test_assumption_impact_values(self):
        """Test AssumptionImpact enum values"""
        assert AssumptionImpact.LOW.value == "low"
        assert AssumptionImpact.MEDIUM.value == "medium"
        assert AssumptionImpact.HIGH.value == "high"
    
    def test_assumption_impact_comparison(self):
        """Test AssumptionImpact enum comparison"""
        assert AssumptionImpact.LOW != AssumptionImpact.HIGH
        assert AssumptionImpact.MEDIUM != AssumptionImpact.LOW
        assert AssumptionImpact.HIGH == AssumptionImpact.HIGH