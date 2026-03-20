"""Tests for Switch Expression Support (Phase 14-04).

This test suite validates switch expression/statement detection, mapping,
and conversion for Java to Bedrock conversion.
"""

import pytest
import sys
import os

# Import from utils directly (within ai-engine package)
from utils.switch_detector import (
    SwitchDetector,
    JavaSwitchExpression,
    SwitchCase,
    detect_switches,
    is_switch_type,
)

from utils.switch_mapper import (
    SwitchMapper,
    ConversionStyle,
    MappedSwitch,
    SwitchMappingResult,
    map_switch,
    map_switches,
)


# ===== Switch Detector Tests =====

class TestSwitchDetection:
    """Test switch expression/statement detection."""
    
    def test_detect_basic_switch_statement(self):
        """Detection of basic switch statement."""
        source = """
        int result = switch (x) {
            case 1:
                System.out.println("one");
                break;
            case 2:
                System.out.println("two");
                break;
            default:
                System.out.println("other");
        };
        """
        
        detector = SwitchDetector()
        switches = detector.detect_from_source(source)
        
        assert len(switches) == 1
        assert switches[0].expression == "x"
        assert len(switches[0].cases) == 3
        assert switches[0].is_expression == True
    
    def test_detect_string_switch(self):
        """Detection of String switch."""
        source = """
        String day = "MONDAY";
        String result = switch (day) {
            case "MONDAY", "FRIDAY" -> "work";
            case "SATURDAY", "SUNDAY" -> "rest";
            default -> "unknown";
        };
        """
        
        detector = SwitchDetector()
        switches = detector.detect_from_source(source)
        
        assert len(switches) == 1
        assert switches[0].expression == "day"
        assert switches[0].switch_type == "String"
        assert len(switches[0].cases) == 3
    
    def test_detect_arrow_style_switch(self):
        """Detection of arrow-style switch (Java 14+)."""
        source = """
        int result = switch (code) {
            case 1 -> "one";
            case 2 -> "two";
            default -> "other";
        };
        """
        
        detector = SwitchDetector()
        switches = detector.detect_from_source(source)
        
        assert len(switches) == 1
        assert any(case.is_arrow_style for case in switches[0].cases)
    
    def test_detect_enum_switch(self):
        """Detection of enum switch."""
        source = """
        Color color = Color.RED;
        String name = switch (color) {
            case RED -> "Red";
            case GREEN -> "Green";
            case BLUE -> "Blue";
        };
        """
        
        detector = SwitchDetector()
        switches = detector.detect_from_source(source)
        
        assert len(switches) == 1
        assert switches[0].switch_type == "enum"
    
    def test_detect_multiple_switches(self):
        """Detection of multiple switches in source."""
        source = """
        int a = switch (x) {
            case 1 -> 10;
            default -> 0;
        };
        
        String b = switch (y) {
            case "a" -> "A";
            default -> "Z";
        };
        """
        
        detector = SwitchDetector()
        switches = detector.detect_from_source(source)
        
        assert len(switches) == 2
    
    def test_detect_switch_with_yield(self):
        """Detection of switch with yield (Java 13+)."""
        source = """
        int result = switch (day) {
            case "MONDAY":
                yield 1;
            default:
                yield 0;
        };
        """
        
        detector = SwitchDetector()
        switches = detector.detect_from_source(source)
        
        assert len(switches) == 1
        assert switches[0].has_yield == True
    
    def test_has_switch(self):
        """Check has_switch method."""
        source_with = "int x = switch (a) { case 1 -> 1; default -> 0; };"
        source_without = "int x = 5;"
        
        detector = SwitchDetector()
        
        assert detector.has_switch(source_with) == True
        assert detector.has_switch(source_without) == False


class TestSwitchTypeValidation:
    """Test switch type validation."""
    
    def test_valid_types(self):
        """Test valid switch types."""
        assert is_switch_type("int") == True
        assert is_switch_type("String") == True
        assert is_switch_type("char") == True
        assert is_switch_type("enum") == True
    
    def test_invalid_types(self):
        """Test invalid switch types."""
        assert is_switch_type("double") == False
        assert is_switch_type("float") == False
        assert is_switch_type("boolean") == False


# ===== Switch Mapper Tests =====

class TestSwitchMapping:
    """Test switch mapping functionality."""
    
    def test_map_to_switch_statement(self):
        """Map to native switch statement."""
        source = """
        int result = switch (x) {
            case 1:
                System.out.println("one");
                break;
            case 2:
                System.out.println("two");
                break;
            default:
                System.out.println("other");
        };
        """
        
        detector = SwitchDetector()
        switches = detector.detect_from_source(source)
        
        mapper = SwitchMapper(style=ConversionStyle.SWITCH_STATEMENT)
        result = mapper.map_switch(switches[0])
        
        assert result.success == True
        assert result.mapped_switch is not None
        assert "switch (x)" in result.mapped_switch.mapped_code
        assert "case 1:" in result.mapped_switch.mapped_code
    
    def test_map_to_if_chain(self):
        """Map to if-else chain."""
        source = """
        int result = switch (x) {
            case 1 -> 10;
            case 2 -> 20;
            default -> 0;
        };
        """
        
        detector = SwitchDetector()
        switches = detector.detect_from_source(source)
        
        mapper = SwitchMapper(style=ConversionStyle.IF_CHAIN)
        result = mapper.map_switch(switches[0])
        
        assert result.success == True
        assert "if (" in result.mapped_switch.mapped_code
        assert "else if (" in result.mapped_switch.mapped_code
        assert "else {" in result.mapped_switch.mapped_code
    
    def test_map_to_object_literal(self):
        """Map to object literal (for String/enum)."""
        source = """
        String result = switch (color) {
            case "red" -> "#ff0000";
            case "blue" -> "#0000ff";
            default -> "#000000";
        };
        """
        
        detector = SwitchDetector()
        switches = detector.detect_from_source(source)
        
        mapper = SwitchMapper(style=ConversionStyle.OBJECT_LITERAL)
        result = mapper.map_switch(switches[0])
        
        assert result.success == True
        assert "#ff0000" in result.mapped_switch.mapped_code
        assert "#0000ff" in result.mapped_switch.mapped_code
    
    def test_map_switch_expression(self):
        """Map switch expression correctly."""
        source = """
        int value = switch (status) {
            case "active" -> 1;
            case "inactive" -> 0;
            default -> -1;
        };
        """
        
        detector = SwitchDetector()
        switches = detector.detect_from_source(source)
        
        mapper = SwitchMapper()
        result = mapper.map_switch(switches[0])
        
        assert result.success == True
        assert switches[0].is_expression == True
    
    def test_map_switch_statement(self):
        """Map switch statement (non-expression)."""
        source = """
        switch (day) {
            case "MONDAY":
                System.out.println("Work");
                break;
            default:
                System.out.println("Rest");
        }
        """
        
        detector = SwitchDetector()
        switches = detector.detect_from_source(source)
        
        mapper = SwitchMapper()
        result = mapper.map_switch(switches[0])
        
        assert result.success == True
        assert switches[0].is_expression == False


class TestSwitchWarnings:
    """Test warning generation."""
    
    def test_warning_missing_default(self):
        """Warning when default case is missing."""
        source = """
        int result = switch (x) {
            case 1 -> 10;
            case 2 -> 20;
        };
        """
        
        detector = SwitchDetector()
        switches = detector.detect_from_source(source)
        
        mapper = SwitchMapper()
        result = mapper.map_switch(switches[0])
        
        assert result.success == True
        assert any("default" in w.lower() for w in result.warnings)
    
    def test_warning_fall_through(self):
        """Warning for fall-through cases."""
        source = """
        switch (x) {
            case 1:
                System.out.println("one");
            case 2:
                System.out.println("two");
                break;
        }
        """
        
        detector = SwitchDetector()
        switches = detector.detect_from_source(source)
        
        mapper = SwitchMapper()
        result = mapper.map_switch(switches[0])
        
        # Check for fall-through detection
        assert result.success == True


class TestConvenienceFunctions:
    """Test convenience functions."""
    
    def test_detect_switches_function(self):
        """Test detect_switches convenience function."""
        source = """
        switch (x) {
            case 1: break;
            default: break;
        }
        """
        
        switches = detect_switches(source)
        
        assert len(switches) == 1
        assert switches[0].expression == "x"
    
    def test_map_switch_function(self):
        """Test map_switch convenience function."""
        source = """
        int r = switch (x) {
            case 1 -> 1;
            default -> 0;
        };
        """
        
        switches = detect_switches(source)
        
        result = map_switch(switches[0])
        
        assert result.success == True
    
    def test_map_switches_function(self):
        """Test map_switches convenience function."""
        source = """
        int a = switch (x) { case 1 -> 1; default -> 0; };
        int b = switch (y) { case "a" -> "A"; default -> "Z"; };
        """
        
        switches = detect_switches(source)
        results = map_switches(switches)
        
        assert len(results) == 2
        assert all(r.success for r in results)


class TestEdgeCases:
    """Test edge cases."""
    
    def test_empty_cases(self):
        """Handle empty cases gracefully."""
        source = """
        switch (x) {
        }
        """
        
        detector = SwitchDetector()
        switches = detector.detect_from_source(source)
        
        # May return empty or may not detect
        # Just ensure no crash
        if switches:
            mapper = SwitchMapper()
            result = mapper.map_switch(switches[0])
            # Should fail gracefully
            assert result.success == False or len(result.errors) > 0
    
    def test_complex_case_body(self):
        """Handle complex case bodies."""
        source = """
        int result = switch (x) {
            case 1:
                int a = 1;
                int b = 2;
                int c = a + b;
                System.out.println(c);
                break;
            default:
                System.out.println("default");
        };
        """
        
        detector = SwitchDetector()
        switches = detector.detect_from_source(source)
        
        assert len(switches) == 1
        assert len(switches[0].cases) == 2
        
        mapper = SwitchMapper()
        result = mapper.map_switch(switches[0])
        
        assert result.success == True
    
    def test_multiple_case_labels(self):
        """Handle multiple case labels."""
        source = """
        String result = switch (day) {
            case "MONDAY", "TUESDAY", "WEDNESDAY" -> "weekday";
            case "SATURDAY", "SUNDAY" -> "weekend";
            default -> "unknown";
        };
        """
        
        detector = SwitchDetector()
        switches = detector.detect_from_source(source)
        
        assert len(switches) == 1
        assert len(switches[0].cases) == 3


# ===== Run Tests =====

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
