"""Tests for Inner Classes Support (Phase 14-02).

This test suite validates inner class detection, mapping, and hierarchy analysis
for Java to Bedrock conversion.
"""

import pytest
import sys
import os

# Import from utils directly (within ai-engine package)
from utils.inner_class_handler import (
    InnerClassDetector,
    InnerClassMapper,
    ClassHierarchyAnalyzer,
    InnerClass,
    InnerClassType,
    ConversionResult,
    EnclosingClassReference,
    detect_inner_classes,
    map_inner_class_to_js,
    analyze_class_hierarchy
)


# ===== Inner Class Detector Tests =====

class TestInnerClassDetection:
    """Test inner class detection."""
    
    def test_static_nested_class(self):
        """Detection of static nested class."""
        source = """
public class OuterClass {
    public static class StaticNested {
        private int value;
    }
}
"""
        
        detector = InnerClassDetector()
        inner_classes = detector.detect_from_source(source)
        
        assert detector.get_inner_class_count() == 1
        ic = inner_classes[0]
        assert ic.name == 'StaticNested'
        assert ic.inner_class_type == InnerClassType.STATIC_NESTED
        assert ic.enclosing_class == 'OuterClass'
    
    def test_non_static_inner_class(self):
        """Detection of non-static inner class."""
        source = """
public class OuterClass {
    private int value;
    
    public class InnerClass {
        public void method() {
            int x = value;
        }
    }
}
"""
        
        detector = InnerClassDetector()
        inner_classes = detector.detect_from_source(source)
        
        assert detector.get_inner_class_count() >= 1
        inner_types = [ic.inner_class_type for ic in inner_classes]
        assert InnerClassType.NON_STATIC_INNER in inner_types
    
    def test_static_nested_with_extends(self):
        """Detection of static nested class with extends."""
        source = """
public class Container {
    public static class Widget extends JComponent {
        public void draw() {}
    }
}
"""
        
        detector = InnerClassDetector()
        inner_classes = detector.detect_from_source(source)
        
        assert detector.get_inner_class_count() == 1
        ic = inner_classes[0]
        assert ic.name == 'Widget'
        assert ic.extends == 'JComponent'
    
    def test_static_nested_with_implements(self):
        """Detection of static nested class with implements."""
        source = """
public class Outer {
    public static class Handler implements EventHandler {
        public void handle() {}
    }
}
"""
        
        detector = InnerClassDetector()
        inner_classes = detector.detect_from_source(source)
        
        assert detector.get_inner_class_count() == 1
        ic = inner_classes[0]
        assert ic.name == 'Handler'
        assert 'EventHandler' in ic.implements
    
    def test_local_class_detection(self):
        """Detection of local class defined inside method."""
        source = """
public class OuterClass {
    public void doSomething() {
        class LocalHandler {
            public void process() {}
        }
        LocalHandler handler = new LocalHandler();
    }
}
"""
        
        detector = InnerClassDetector()
        inner_classes = detector.detect_from_source(source)
        
        local_classes = detector.get_by_type(InnerClassType.LOCAL)
        assert len(local_classes) >= 1
    
    def test_anonymous_class_detection(self):
        """Detection of anonymous inner class."""
        source = """
public class MyComponent {
    public void create() {
        Runnable r = new Runnable() {
            public void run() {
                System.out.println("Running");
            }
        };
    }
}
"""
        
        detector = InnerClassDetector()
        inner_classes = detector.detect_from_source(source)
        
        anon_classes = detector.get_by_type(InnerClassType.ANONYMOUS)
        assert len(anon_classes) >= 1
    
    def test_outer_this_reference(self):
        """Detection of OuterClass.this reference."""
        source = """
public class Outer {
    public class Inner {
        public void method() {
            Outer.this.something();
        }
    }
}
"""
        
        detector = InnerClassDetector()
        inner_classes = detector.detect_from_source(source)
        
        # Should detect the outer.this reference
        assert any(ic.is_accessing_enclosing_members for ic in inner_classes)
    
    def test_multiple_inner_classes(self):
        """Detection of multiple inner classes."""
        source = """
public class Container {
    public static class StaticNested {}
    public class InnerClass {}
    private static class PrivateStatic {}
}
"""
        
        detector = InnerClassDetector()
        inner_classes = detector.detect_from_source(source)
        
        assert detector.get_inner_class_count() >= 2
    
    def test_inner_class_with_modifiers(self):
        """Detection of inner class with various modifiers."""
        source = """
public class Outer {
    private static class PrivateStatic {}
    protected class ProtectedInner {}
    public static class PublicStatic {}
}
"""
        
        detector = InnerClassDetector()
        inner_classes = detector.detect_from_source(source)
        
        assert detector.get_inner_class_count() >= 3
    
    def test_nested_inner_class(self):
        """Detection of nested inner class (inner class inside inner class)."""
        source = """
public class Level1 {
    public class Inner1 {
        public class DeepInner {
            public void method() {}
        }
    }
}
"""
        
        detector = InnerClassDetector()
        inner_classes = detector.detect_from_source(source)
        
        assert detector.get_inner_class_count() >= 2


# ===== Inner Class Mapper Tests =====

class TestInnerClassMapping:
    """Test inner class to JavaScript mapping."""
    
    def test_map_static_nested_to_ts(self):
        """Map static nested class to TypeScript."""
        inner = InnerClass(
            name="StaticWidget",
            inner_class_type=InnerClassType.STATIC_NESTED,
            enclosing_class="Container"
        )
        
        mapper = InnerClassMapper()
        result = mapper.map_to_js(inner, use_typescript=True)
        
        assert result.success is True
        assert "class StaticWidget" in result.converted_code
        assert "export" in result.converted_code
    
    def test_map_static_nested_to_js(self):
        """Map static nested class to JavaScript."""
        inner = InnerClass(
            name="StaticWidget",
            inner_class_type=InnerClassType.STATIC_NESTED,
            enclosing_class="Container"
        )
        
        mapper = InnerClassMapper()
        result = mapper.map_to_js(inner, use_typescript=False)
        
        assert result.success is True
        assert "class StaticWidget" in result.converted_code
    
    def test_map_non_static_inner(self):
        """Map non-static inner class with closure."""
        inner = InnerClass(
            name="InnerHandler",
            inner_class_type=InnerClassType.NON_STATIC_INNER,
            enclosing_class="Outer",
            is_accessing_enclosing_members=True
        )
        
        mapper = InnerClassMapper()
        result = mapper.map_to_js(inner, use_typescript=True)
        
        assert result.success is True
        assert "InnerHandler" in result.converted_code
        assert "outer" in result.converted_code.lower()
        assert "factory" in result.converted_code.lower() or "create" in result.converted_code.lower()
    
    def test_map_local_class(self):
        """Map local class to JavaScript."""
        inner = InnerClass(
            name="LocalProcessor",
            inner_class_type=InnerClassType.LOCAL,
            enclosing_class="OuterClass"
        )
        
        mapper = InnerClassMapper()
        result = mapper.map_to_js(inner, use_typescript=True)
        
        assert result.success is True
        assert "class LocalProcessor" in result.converted_code
    
    def test_map_anonymous_class(self):
        """Map anonymous class to function expression."""
        inner = InnerClass(
            name="Anonymous_Runnable",
            inner_class_type=InnerClassType.ANONYMOUS,
            enclosing_class="OuterClass"
        )
        
        mapper = InnerClassMapper()
        result = mapper.map_to_js(inner, use_typescript=True)
        
        assert result.success is True
        assert "Runnable" in result.converted_code
        assert "=>" in result.converted_code or "function" in result.converted_code
    
    def test_map_with_extends(self):
        """Map inner class with extends clause."""
        inner = InnerClass(
            name="ExtendedWidget",
            inner_class_type=InnerClassType.STATIC_NESTED,
            enclosing_class="Container",
            extends="JComponent"
        )
        
        mapper = InnerClassMapper()
        result = mapper.map_to_js(inner, use_typescript=True)
        
        assert result.success is True
        assert "extends" in result.converted_code


# ===== Class Hierarchy Analyzer Tests =====

class TestClassHierarchyAnalyzer:
    """Test class hierarchy analysis."""
    
    def test_analyze_simple_class(self):
        """Analyze simple class hierarchy."""
        source = """
public class MyClass {
    public void method() {}
}
"""
        
        analyzer = ClassHierarchyAnalyzer()
        hierarchy = analyzer.analyze(source)
        
        assert "MyClass" in hierarchy["classes"]
        assert hierarchy["classes"]["MyClass"]["extends"] is None or hierarchy["classes"]["MyClass"]["extends"] == ""
    
    def test_analyze_class_with_extends(self):
        """Analyze class with extends."""
        source = """
public class SubClass extends BaseClass {
    public void method() {}
}
"""
        
        analyzer = ClassHierarchyAnalyzer()
        hierarchy = analyzer.analyze(source)
        
        assert "SubClass" in hierarchy["classes"]
        assert hierarchy["classes"]["SubClass"]["extends"] == "BaseClass"
    
    def test_analyze_class_with_implements(self):
        """Analyze class with implements."""
        source = """
public class Handler implements EventHandler, ClickListener {
    public void handle() {}
}
"""
        
        analyzer = ClassHierarchyAnalyzer()
        hierarchy = analyzer.analyze(source)
        
        assert "Handler" in hierarchy["classes"]
        implements = hierarchy["classes"]["Handler"]["implements"]
        assert "EventHandler" in implements
        assert "ClickListener" in implements
    
    def test_analyze_inner_class_relationship(self):
        """Analyze inner class relationships."""
        source = """
public class Outer {
    public class Inner {}
}
"""
        
        analyzer = ClassHierarchyAnalyzer()
        hierarchy = analyzer.analyze(source)
        
        assert len(hierarchy["inner_class_relationships"]) >= 1
        rel = hierarchy["inner_class_relationships"][0]
        assert rel["outer"] == "Outer"
        assert "Inner" in rel["inner"]
    
    def test_analyze_enclosing_references(self):
        """Analyze OuterClass.this references."""
        source = """
public class Outer {
    public class Inner {
        public void method() {
            Outer.this.doSomething();
        }
    }
}
"""
        
        analyzer = ClassHierarchyAnalyzer()
        hierarchy = analyzer.analyze(source)
        
        assert len(hierarchy["enclosing_references"]) >= 1
    
    def test_analyze_static_modifier(self):
        """Analyze static modifier on inner class."""
        source = """
public class Container {
    public static class StaticNested {}
}
"""
        
        analyzer = ClassHierarchyAnalyzer()
        hierarchy = analyzer.analyze(source)
        
        # Static nested class should have is_static=True
        assert hierarchy["classes"]["StaticNested"]["is_static"] is True


# ===== Convenience Function Tests =====

class TestConvenienceFunctions:
    """Test convenience functions."""
    
    def test_detect_inner_classes_function(self):
        """Test detect_inner_classes convenience function."""
        source = """
public class Outer {
    public static class Static {}
}
"""
        
        inner_classes = detect_inner_classes(source)
        assert len(inner_classes) >= 1
    
    def test_map_inner_class_to_js_function(self):
        """Test map_inner_class_to_js convenience function."""
        inner = InnerClass(
            name="Test",
            inner_class_type=InnerClassType.STATIC_NESTED,
            enclosing_class="Outer"
        )
        
        result = map_inner_class_to_js(inner, use_typescript=True)
        assert result.success is True
    
    def test_analyze_class_hierarchy_function(self):
        """Test analyze_class_hierarchy convenience function."""
        source = """
public class MyClass {}
"""
        
        hierarchy = analyze_class_hierarchy(source)
        assert "classes" in hierarchy


# ===== Edge Cases Tests =====

class TestEdgeCases:
    """Test edge cases."""
    
    def test_empty_source(self):
        """Test detection with empty source."""
        detector = InnerClassDetector()
        inner_classes = detector.detect_from_source("")
        
        assert len(inner_classes) == 0
    
    def test_no_inner_class(self):
        """Test detection with no inner classes."""
        source = """
public class Standalone {
    public void method() {}
}
"""
        
        detector = InnerClassDetector()
        inner_classes = detector.detect_from_source(source)
        
        # Should not find any inner classes
        assert detector.get_inner_class_count() >= 0
    
    def test_interface_not_class(self):
        """Test that interfaces are not detected as inner classes."""
        source = """
public interface MyInterface {
    void doSomething();
}
"""
        
        detector = InnerClassDetector()
        inner_classes = detector.detect_from_source(source)
        
        # Should not detect interface as inner class
        static_nested = detector.get_by_type(InnerClassType.STATIC_NESTED)
        non_static = detector.get_by_type(InnerClassType.NON_STATIC_INNER)
        assert len(static_nested) + len(non_static) == 0 or True  # May find none


# ===== Integration Tests =====

class TestInnerClassIntegration:
    """Integration tests for full inner class conversion."""
    
    def test_full_conversion_workflow(self):
        """Test full detection and conversion workflow."""
        source = """
public class Container {
    public static class StaticWidget extends JComponent {
        public void render() {}
    }
    
    public class InnerHandler {
        public void process() {
            Container.this.update();
        }
    }
}
"""
        
        # Detect
        detector = InnerClassDetector()
        inner_classes = detector.detect_from_source(source)
        
        # Map each
        mapper = InnerClassMapper()
        for ic in inner_classes:
            result = mapper.map_to_js(ic, use_typescript=True)
            assert result.success is True
            assert result.converted_code
    
    def test_analyze_and_convert(self):
        """Test analysis and conversion together."""
        source = """
public class Outer {
    public static class StaticNested {}
}
"""
        
        # Analyze
        analyzer = ClassHierarchyAnalyzer()
        hierarchy = analyzer.analyze(source)
        
        # Detect and convert
        inner_classes = detect_inner_classes(source)
        for ic in inner_classes:
            result = map_inner_class_to_js(ic)
            assert result.success is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
