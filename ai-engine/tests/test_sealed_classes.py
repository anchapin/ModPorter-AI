"""Tests for Sealed Class detection and mapping (Phase 14-07)."""

import pytest
import sys
import os

from utils.sealed_class_detector import (
    SealedClassDetector,
    SealedClass,
    PermittedSubclass,
    detect_sealed_classes,
    is_sealed_class,
)

from utils.sealed_class_mapper import (
    SealedClassMapper,
    TypeHierarchyAnalyzer,
    TypeScriptSealedOutput,
    map_sealed_class,
    sealed_classes_to_typescript,
)


class TestSealedClassDetection:
    """Tests for SealedClassDetector."""
    
    def test_detect_simple_sealed_class(self):
        """Test detecting a simple sealed class."""
        source = """
        public sealed class Shape permits Circle, Square {}
        """
        detector = SealedClassDetector()
        sealed_classes = detector.detect(source)
        
        assert len(sealed_classes) >= 1
    
    def test_detect_sealed_interface(self):
        """Test detecting a sealed interface."""
        source = """
        public sealed interface Command permits LoginCommand, LogoutCommand {}
        """
        detector = SealedClassDetector()
        sealed_classes = detector.detect(source)
        
        assert len(sealed_classes) >= 1
    
    def test_convenience_function(self):
        """Test convenience function."""
        source = """
        public sealed class Shape permits Circle {}
        """
        sealed = detect_sealed_classes(source)
        assert isinstance(sealed, list)


class TestSealedClassMapper:
    """Tests for SealedClassMapper."""
    
    def test_map_simple_sealed_class(self):
        """Test mapping a simple sealed class."""
        sealed = SealedClass(
            name="Shape",
            permits=["Circle", "Square"]
        )
        
        mapper = SealedClassMapper()
        result = mapper.map_sealed_class(sealed, [])
        
        assert result.union_name == "Shape"
        assert len(result.union_members) == 2
        assert "Circle" in result.union_members
        assert "Square" in result.union_members
    
    def test_generate_type_guard(self):
        """Test type guard generation."""
        mapper = SealedClassMapper()
        
        result = mapper._generate_type_guard("Shape", ["Circle", "Square"])
        
        assert "isShape" in result
        assert "Circle" in result
        assert "Square" in result
    
    def test_generate_jsdoc(self):
        """Test JSDoc generation."""
        sealed = SealedClass(name="Shape", permits=["Circle", "Square"])
        
        mapper = SealedClassMapper()
        jsdoc = mapper._generate_jsdoc(sealed, [])
        
        assert "Shape" in jsdoc
        assert "permitted" in jsdoc.lower()


class TestTypeHierarchyAnalyzer:
    """Tests for TypeHierarchyAnalyzer."""
    
    def test_build_hierarchy_tree(self):
        """Test building hierarchy tree."""
        source = """
        public sealed class Shape permits Circle, Square {}
        """
        
        analyzer = TypeHierarchyAnalyzer()
        tree = analyzer.build_hierarchy_tree(source)
        
        assert isinstance(tree, dict)
    
    def test_generate_exhaustive_switch(self):
        """Test generating exhaustive switch."""
        analyzer = TypeHierarchyAnalyzer()
        
        switch = analyzer.generate_exhaustive_switch("Shape", ["Circle", "Square"])
        
        assert "switch" in switch
        assert "Shape" in switch
    
    def test_validate_exhaustiveness(self):
        """Test exhaustiveness validation."""
        sealed = SealedClass(name="Shape", permits=["Circle", "Square"])
        
        analyzer = TypeHierarchyAnalyzer()
        
        # All handled
        assert analyzer.validate_exhaustiveness(sealed, ["Circle", "Square"]) == True
        
        # Not all handled
        assert analyzer.validate_exhaustiveness(sealed, ["Circle"]) == False


class TestConvenienceFunctions:
    """Test module-level convenience functions."""
    
    def test_map_sealed_class_function(self):
        """Test convenience function."""
        sealed = SealedClass(
            name="Command",
            permits=["LoginCommand", "LogoutCommand"]
        )
        
        result = map_sealed_class(sealed, [])
        assert isinstance(result, TypeScriptSealedOutput)
        assert result.union_name == "Command"


class TestEdgeCases:
    """Test edge cases."""
    
    def test_empty_source(self):
        """Test with empty source."""
        detector = SealedClassDetector()
        sealed_classes = detector.detect('')
        assert sealed_classes == []
    
    def test_no_sealed_classes(self):
        """Test source without sealed classes."""
        source = """
        public class Example {
            private String name;
        }
        """
        detector = SealedClassDetector()
        sealed_classes = detector.detect(source)
        assert len(sealed_classes) == 0


class TestSealedClassIntegration:
    """Integration tests for full pipeline."""
    
    def test_full_pipeline(self):
        """Test full detection and mapping pipeline."""
        source = """
        public sealed class Shape permits Circle, Square {}
        """
        
        # Detect
        detector = SealedClassDetector()
        sealed_classes = detector.detect(source)
        
        # Map
        mapper = SealedClassMapper()
        mappings = mapper.map(source)
        
        assert isinstance(mappings, dict)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
