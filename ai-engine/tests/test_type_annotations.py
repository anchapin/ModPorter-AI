"""Tests for Type Annotation detection and mapping (Phase 14-04)."""

import pytest
import sys
import os

# Import from utils directly (within ai-engine package)
from utils.type_annotation_detector import (
    TypeAnnotationDetector,
    TypeAnnotation,
    AnnotatedType,
    detect_type_annotations,
)

from utils.type_annotation_mapper import (
    TypeAnnotationMapper,
    GenericTypeAnnotationHandler,
    TypeMappingResult,
    to_nullable_typescript,
    convert_java_to_ts_nullable,
)


class TestTypeAnnotationDetection:
    """Tests for TypeAnnotationDetector."""
    
    def test_detect_nullable(self):
        """Test detecting @Nullable annotation."""
        source = """
        public class Example {
            public @Nullable String getName() { return null; }
        }
        """
        detector = TypeAnnotationDetector()
        annotations = detector.detect(source)
        
        assert len(annotations) >= 1
        nullable_annots = [a for a in annotations if a.annotation_type == 'nullable']
        assert len(nullable_annots) >= 1
    
    def test_detect_not_null(self):
        """Test detecting @NotNull annotation."""
        source = """
        public class Example {
            public void setName(@NotNull String name) { }
        }
        """
        detector = TypeAnnotationDetector()
        annotations = detector.detect(source)
        
        not_null = [a for a in annotations if a.annotation_type == 'not_null']
        assert len(not_null) >= 1
    
    def test_detect_custom_type_annotation(self):
        """Test detecting custom type annotations."""
        source = """
        public class Example {
            private @MyCustomAnnotation String field;
        }
        """
        detector = TypeAnnotationDetector()
        annotations = detector.detect(source)
        
        assert len(annotations) >= 1
    
    def test_convenience_function(self):
        """Test convenience function."""
        source = """
        public class Example {
            public @Nullable String test() { return null; }
        }
        """
        annotations = detect_type_annotations(source)
        assert isinstance(annotations, list)


class TestAnnotatedType:
    """Tests for AnnotatedType class."""
    
    def test_to_typescript_basic(self):
        """Test basic TypeScript conversion."""
        at = AnnotatedType(base_type='String', is_nullable=True)
        assert at.to_typescript() == 'String | null'
    
    def test_to_typescript_non_nullable(self):
        """Test non-nullable TypeScript conversion."""
        at = AnnotatedType(base_type='String', is_nullable=False)
        assert at.to_typescript() == 'String'
    
    def test_to_typescript_with_generics(self):
        """Test generic type conversion."""
        at = AnnotatedType(
            base_type='List',
            generic_params=[AnnotatedType(base_type='String', is_nullable=False)],
            is_nullable=False
        )
        assert 'List<String>' in at.to_typescript()


class TestTypeAnnotationMapper:
    """Tests for TypeAnnotationMapper."""
    
    def test_map_nullable_to_typescript(self):
        """Test mapping nullable to TypeScript."""
        mapper = TypeAnnotationMapper()
        
        # Test with empty annotations - should not add null
        result = mapper.map_nullable('String', [])
        assert result == 'string'
    
    def test_convert_primitives(self):
        """Test converting Java primitives to TypeScript."""
        mapper = TypeAnnotationMapper()
        
        assert mapper._convert_to_typescript_type('int') == 'number'
        assert mapper._convert_to_typescript_type('boolean') == 'boolean'
        assert mapper._convert_to_typescript_type('String') == 'string'
    
    def test_convert_arrays(self):
        """Test converting Java arrays to TypeScript."""
        mapper = TypeAnnotationMapper()
        
        assert mapper._convert_to_typescript_type('String[]') == 'string[]'
        assert mapper._convert_to_typescript_type('int[]') == 'number[]'


class TestGenericTypeAnnotationHandler:
    """Tests for GenericTypeAnnotationHandler."""
    
    def test_handle_generic_param(self):
        """Test handling generic parameters with annotations."""
        handler = GenericTypeAnnotationHandler()
        
        # Without nullable
        result = handler.handle_generic_param('String', [])
        assert result == 'string'
    
    def test_convert_minecraft_generic(self):
        """Test converting Minecraft generics."""
        handler = GenericTypeAnnotationHandler()
        
        result = handler.convert_minecraft_generic('List<NBTTagCompound>')
        assert result == 'NBTTagCompound[]'


class TestConvenienceFunctions:
    """Test module-level convenience functions."""
    
    def test_to_nullable_typescript(self):
        """Test convenience function."""
        result = to_nullable_typescript('String', True)
        assert result == 'string | null'
        
        result = to_nullable_typescript('String', False)
        assert result == 'string'


class TestEdgeCases:
    """Test edge cases."""
    
    def test_empty_source(self):
        """Test with empty source."""
        detector = TypeAnnotationDetector()
        annotations = detector.detect('')
        assert annotations == []
    
    def test_no_annotations(self):
        """Test source without annotations."""
        source = """
        public class Example {
            private String name;
        }
        """
        detector = TypeAnnotationDetector()
        annotations = detector.detect(source)
        # Should find no type annotations
        type_annots = [a for a in annotations if a.annotation_type in ('nullable', 'not_null')]
        assert len(type_annots) == 0


class TestTypeAnnotationIntegration:
    """Integration tests for full pipeline."""
    
    def test_full_pipeline(self):
        """Test full detection and mapping pipeline."""
        source = """
        public class Example {
            public @Nullable String getName() { return null; }
            public void setName(@NotNull String name) { }
        }
        """
        
        # Detect
        detector = TypeAnnotationDetector()
        annotations = detector.detect(source)
        
        # Map
        mapper = TypeAnnotationMapper()
        mappings = mapper.map(source)
        
        assert isinstance(mappings, dict)
    
    def test_complex_source_with_annotations(self):
        """Test complex source with multiple annotations."""
        source = """
        public class User {
            private @Nullable String nickname;
            private @NotNull String email;
            private List<@Nullable String> aliases;
        }
        """
        
        detector = TypeAnnotationDetector()
        annotations = detector.detect(source)
        
        assert len(annotations) >= 2  # At least nullable and not_null


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
