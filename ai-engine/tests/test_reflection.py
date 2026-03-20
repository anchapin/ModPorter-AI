"""
Tests for Reflection API Detection and Mapping

Tests the ReflectionDetector and ReflectionMapper utilities.
"""

import pytest
import sys
import os

# Import from utils directly (within ai-engine package)
from utils.reflection_detector import (
    ReflectionDetector,
    ReflectionCall,
    DynamicClassLoad,
    detect_reflection,
    detect_reflection_detailed,
)

from utils.reflection_mapper import (
    ReflectionMapper,
    ConversionResult,
    ReflectionWarning,
    Severity,
    PatternType,
    map_reflection,
    map_reflection_single,
)


# ============================================================================
# ReflectionDetector Tests
# ============================================================================

class TestReflectionDetector:
    """Tests for ReflectionDetector class."""
    
    def test_detect_class_for_name(self):
        """Test detection of Class.forName() dynamic loading."""
        source = '''
        public class MyMod {
            public void load() throws Exception {
                Class<?> clazz = Class.forName("com.example.MyItem");
            }
        }
        '''
        detector = ReflectionDetector()
        calls = detector.detect_from_source(source)
        
        # Should find the forName call
        method_names = [c.method_name for c in calls]
        assert 'forName' in method_names
    
    def test_detect_get_declared_fields(self):
        """Test detection of getDeclaredFields() introspection."""
        source = '''
        public class MyMod {
            public void analyze() {
                Field[] fields = clazz.getDeclaredFields();
            }
        }
        '''
        detector = ReflectionDetector()
        details = detector.detect_with_details(source)
        
        calls = details['reflection_calls']
        method_names = [c.method_name for c in calls]
        assert 'getDeclaredFields' in method_names
    
    def test_detect_method_invoke(self):
        """Test detection of Method.invoke() dynamic calls."""
        source = '''
        public class MyMod {
            public void invoke() throws Exception {
                Method method = clazz.getMethod("doSomething");
                method.invoke(target, arg1, arg2);
            }
        }
        '''
        detector = ReflectionDetector()
        details = detector.detect_with_details(source)
        
        calls = details['reflection_calls']
        method_names = [c.method_name for c in calls]
        assert 'invoke' in method_names
    
    def test_detect_constructor_new_instance(self):
        """Test detection of Constructor.newInstance() patterns."""
        source = '''
        public class MyMod {
            public void create() throws Exception {
                Constructor<?> cons = clazz.getDeclaredConstructor();
                Object obj = cons.newInstance();
            }
        }
        '''
        detector = ReflectionDetector()
        details = detector.detect_with_details(source)
        
        calls = details['reflection_calls']
        method_names = [c.method_name for c in calls]
        assert 'newInstance' in method_names
    
    def test_detect_annotation_access(self):
        """Test detection of annotation access patterns."""
        source = '''
        public class MyMod {
            public void checkAnnotation() {
                MyAnnotation ann = field.getAnnotation(MyAnnotation.class);
            }
        }
        '''
        detector = ReflectionDetector()
        details = detector.detect_with_details(source)
        
        calls = details['reflection_calls']
        method_names = [c.method_name for c in calls]
        assert 'getAnnotation' in method_names
    
    def test_no_reflection(self):
        """Test that non-reflection code returns empty list."""
        source = '''
        public class MyMod {
            public void regularMethod() {
                String s = "hello";
                int len = s.length();
                List<String> list = new ArrayList<>();
            }
        }
        '''
        detector = ReflectionDetector()
        calls = detector.detect_from_source(source)
        
        assert len(calls) == 0
    
    def test_detect_set_accessible(self):
        """Test detection of setAccessible() calls."""
        source = '''
        public class MyMod {
            public void accessPrivate() throws Exception {
                Field field = clazz.getDeclaredField("privateField");
                field.setAccessible(true);
            }
        }
        '''
        detector = ReflectionDetector()
        details = detector.detect_with_details(source)
        
        calls = details['reflection_calls']
        method_names = [c.method_name for c in calls]
        assert 'setAccessible' in method_names
    
    def test_detect_get_methods(self):
        """Test detection of getMethods() introspection."""
        source = '''
        public class MyMod {
            public void analyze() {
                Method[] methods = clazz.getMethods();
            }
        }
        '''
        detector = ReflectionDetector()
        calls = detector.detect_from_source(source)
        
        method_names = [c.method_name for c in calls]
        assert 'getMethods' in method_names
    
    def test_detect_get_simple_name(self):
        """Test detection of Class.getSimpleName()."""
        source = '''
        public class MyMod {
            public String getName() {
                return MyClass.class.getSimpleName();
            }
        }
        '''
        detector = ReflectionDetector()
        calls = detector.detect_from_source(source)
        
        method_names = [c.method_name for c in calls]
        assert 'getSimpleName' in method_names


# ============================================================================
# ReflectionMapper Tests
# ============================================================================

class TestReflectionMapper:
    """Tests for ReflectionMapper class."""
    
    def test_map_get_simple_name(self):
        """Test mapping Class.getSimpleName() correctly."""
        mapper = ReflectionMapper()
        result = mapper.map_single_pattern('getSimpleName')
        
        assert result.success is True
        assert result.converted_code == "class.name"
    
    def test_map_get_methods(self):
        """Test mapping getMethods() to Object.getOwnPropertyNames()."""
        mapper = ReflectionMapper()
        result = mapper.map_single_pattern('getMethods')
        
        assert result.success is True
        assert 'Object' in result.converted_code
    
    def test_warning_for_class_for_name(self):
        """Test warning for Class.forName() dynamic loading."""
        mapper = ReflectionMapper()
        result = mapper.map_single_pattern('forName')
        
        assert result.success is False
        assert len(result.warnings) > 0
        assert result.warnings[0].severity == Severity.HIGH
        assert 'dynamic' in result.warnings[0].message.lower()
    
    def test_warning_for_method_invoke(self):
        """Test warning for Method.invoke() dynamic calls."""
        mapper = ReflectionMapper()
        result = mapper.map_single_pattern('invoke')
        
        assert result.success is False
        assert len(result.warnings) > 0
        assert result.warnings[0].severity == Severity.HIGH
    
    def test_warning_for_set_accessible(self):
        """Test warning for setAccessible()."""
        mapper = ReflectionMapper()
        result = mapper.map_single_pattern('setAccessible')
        
        assert result.success is False
        assert len(result.warnings) > 0
        assert 'access' in result.warnings[0].message.lower()
    
    def test_multiple_patterns(self):
        """Test handling multiple reflection patterns in source."""
        source = '''
        public class MyMod {
            public void process() {
                String name = clazz.getSimpleName();
                Field[] fields = clazz.getDeclaredFields();
                Class.forName("com.example.DynamicClass");
            }
        }
        '''
        mapper = ReflectionMapper()
        result = mapper.map_reflection(source)
        
        assert len(result.warnings) >= 2
        # Should have warnings for forName and likely for getSimpleName/getDeclaredFields
    
    def test_no_reflection_returns_original(self):
        """Test that non-reflection code returns original."""
        source = '''
        public class MyMod {
            public void regular() {
                System.out.println("Hello");
            }
        }
        '''
        mapper = ReflectionMapper()
        result = mapper.map_reflection(source)
        
        assert result.converted_code == source
        assert len(result.warnings) == 0


# ============================================================================
# Integration Tests
# ============================================================================

class TestReflectionIntegration:
    """Integration tests for full reflection detection and mapping pipeline."""
    
    def test_full_pipeline(self):
        """Test full detection → mapping pipeline."""
        source = '''
        public class ItemRegistry {
            public void register() throws Exception {
                Class<?> itemClass = Class.forName("com.mod.CustomItem");
                Field[] fields = itemClass.getDeclaredFields();
                Method registerMethod = itemClass.getMethod("register");
            }
        }
        '''
        # Detect
        detector = ReflectionDetector()
        details = detector.detect_with_details(source)
        
        assert details['summary']['total_reflection_calls'] >= 2
        
        # Map
        mapper = ReflectionMapper()
        result = mapper.map_reflection(source)
        
        assert len(result.warnings) > 0
    
    def test_complex_reflection(self):
        """Test realistic reflection patterns from mods."""
        source = '''
        public class ModInitializer {
            public void initMod() throws Exception {
                // Dynamic class loading (should warn)
                Class.forName("com.example mod.BlockRegistrar");
                
                // Field introspection (convertible)
                for (Field field : getClass().getDeclaredFields()) {
                    field.setAccessible(true);
                    Object value = field.get(this);
                }
                
                // Method introspection (convertible)
                Method[] methods = clazz.getMethods();
                
                // Dynamic invocation (should warn)
                Method init = clazz.getMethod("initialize");
                init.invoke(instance);
            }
        }
        '''
        mapper = ReflectionMapper()
        result = mapper.map_reflection(source)
        
        # Should have multiple warnings
        high_severity = [w for w in result.warnings if w.severity == Severity.HIGH]
        assert len(high_severity) >= 2
    
    def test_convenience_functions(self):
        """Test top-level convenience functions."""
        source = '''
        public class Test {
            public void method() {
                Class.forName("test.Item");
            }
        }
        '''
        # Test convenience functions
        calls = detect_reflection(source)
        assert len(calls) > 0
        
        details = detect_reflection_detailed(source)
        assert details['summary']['total_reflection_calls'] > 0
        
        result = map_reflection(source)
        assert isinstance(result, ConversionResult)
        
        single_result = map_reflection_single('getSimpleName')
        assert single_result.success is True


# ============================================================================
# Additional Edge Case Tests
# ============================================================================

class TestReflectionEdgeCases:
    """Edge case tests for reflection handling."""
    
    def test_unparseable_code(self):
        """Test handling of unparseable code."""
        source = 'this is not valid java {'
        
        detector = ReflectionDetector()
        calls = detector.detect_from_source(source)
        
        # Should return empty list, not crash
        assert calls == []
    
    def test_empty_source(self):
        """Test handling of empty source."""
        source = ''
        
        detector = ReflectionDetector()
        calls = detector.detect_from_source(source)
        
        assert calls == []
    
    def test_annotation_methods_warnings(self):
        """Test that annotation methods generate warnings."""
        mapper = ReflectionMapper()
        
        for method in ['getAnnotation', 'getAnnotations', 'isAnnotationPresent']:
            result = mapper.map_single_pattern(method)
            assert len(result.warnings) > 0
            # Annotation methods are unsupported (HIGH severity)
            assert result.warnings[0].severity == Severity.HIGH
    
    def test_warning_summary(self):
        """Test warning summary generation."""
        source = '''
        public class Test {
            public void method() throws Exception {
                Class.forName("test.Item");
                Method m = clazz.getMethod("test");
                m.invoke(obj);
            }
        }
        '''
        mapper = ReflectionMapper()
        result = mapper.map_reflection(source)
        
        summary = mapper.get_warning_summary(result)
        
        assert summary['total'] > 0
        assert summary['high'] >= 2  # forName and invoke
        assert summary['has_blocking'] is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
