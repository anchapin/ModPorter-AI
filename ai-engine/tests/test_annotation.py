"""Tests for Annotation Conversion (Phase 14-01).

This test suite validates annotation detection, mapping, and extraction
for Java to Bedrock conversion.
"""

import pytest
import sys
import os

# Import from utils directly (within ai-engine package)
from utils.annotation_detector import (
    AnnotationDetector,
    JavaAnnotation,
    AnnotationParameter,
    detect_annotations,
    has_override_annotation,
    has_deprecated_annotation,
)

from utils.annotation_mapper import (
    AnnotationMapper,
    ConversionStyle,
    MappedAnnotation,
    AnnotationMappingResult,
    map_annotations,
    annotation_to_jsdoc,
)

from utils.annotation_extractor import (
    AnnotationExtractor,
    ExtractionResult,
    AnnotationMetadata,
    ExtractionTarget,
    extract_annotations,
)


# ===== Annotation Detector Tests =====

class TestAnnotationDetection:
    """Test annotation detection."""
    
    def test_detect_override(self):
        """Test detection of @Override annotation."""
        source = """
        @Override
        public void doSomething() {
            // implementation
        }
        """
        
        detector = AnnotationDetector()
        annotations = detector.detect_from_source(source)
        
        assert detector.get_annotation_count() == 1
        assert detector.has_override() is True
        ann = annotations[0]
        assert ann.name == 'Override'
        assert ann.is_standard is True
    
    def test_detect_deprecated(self):
        """Test detection of @Deprecated annotation."""
        source = """
        @Deprecated
        public void oldMethod() {
            // old implementation
        }
        """
        
        detector = AnnotationDetector()
        annotations = detector.detect_from_source(source)
        
        assert detector.has_deprecated() is True
        ann = annotations[0]
        assert ann.name == 'Deprecated'
    
    def test_detect_nullable(self):
        """Test detection of @Nullable annotation."""
        source = """
        public String getValue() {
            return null;
        }
        @Nullable
        private String cachedValue;
        """
        
        detector = AnnotationDetector()
        annotations = detector.detect_from_source(source)
        
        assert detector.has_nullable() is True
        ann = detector.get_annotation_by_name('Nullable')[0]
        assert ann.name == 'Nullable'
    
    def test_detect_annotation_with_parameters(self):
        """Test detection of annotation with parameters."""
        source = """
        @SuppressWarnings(value = "unchecked")
        public void process() {
            // code
        }
        """
        
        detector = AnnotationDetector()
        annotations = detector.detect_from_source(source)
        
        assert detector.get_annotation_count() == 1
        ann = annotations[0]
        assert ann.name == 'SuppressWarnings'
        assert len(ann.parameters) == 1
        assert ann.parameters[0].name == 'value'
        assert ann.parameters[0].value == 'unchecked'
    
    def test_detect_custom_annotation(self):
        """Test detection of custom annotation."""
        source = """
        @MyCustomAnnotation(param1 = "value1", param2 = "value2")
        public void custom() {
            // code
        }
        """
        
        detector = AnnotationDetector()
        annotations = detector.detect_from_source(source)
        
        assert detector.get_annotation_count() == 1
        ann = annotations[0]
        assert ann.name == 'MyCustomAnnotation'
        assert ann.is_custom is True
        assert ann.is_standard is False
    
    def test_detect_multiple_annotations(self):
        """Test detection of multiple annotations."""
        source = """
        @Override
        @Deprecated
        public void oldOverride() {
            // code
        }
        """
        
        detector = AnnotationDetector()
        annotations = detector.detect_from_source(source)
        
        assert detector.get_annotation_count() == 2
        assert detector.has_override() is True
        assert detector.has_deprecated() is True
    
    def test_detect_annotation_single_value(self):
        """Test detection of annotation with single value."""
        source = """
        @SuppressWarnings("unchecked")
        public void process() {
            // code
        }
        """
        
        detector = AnnotationDetector()
        annotations = detector.detect_from_source(source)
        
        assert detector.get_annotation_count() == 1
        ann = annotations[0]
        assert ann.name == 'SuppressWarnings'
        # Single value should have empty name
        assert len(ann.parameters) >= 1
    
    def test_detect_non_null(self):
        """Test detection of @NonNull annotation."""
        source = """
        @NonNull
        private String name;
        """
        
        detector = AnnotationDetector()
        annotations = detector.detect_from_source(source)
        
        assert detector.get_annotation_count() == 1
        ann = annotations[0]
        assert ann.name == 'NonNull'
    
    def test_detect_functional_interface(self):
        """Test detection of @FunctionalInterface annotation."""
        source = """
        @FunctionalInterface
        public interface MyFunction {
            void apply(String input);
        }
        """
        
        detector = AnnotationDetector()
        annotations = detector.detect_from_source(source)
        
        assert detector.get_annotation_count() == 1
        ann = annotations[0]
        assert ann.name == 'FunctionalInterface'
    
    def test_detect_safe_varargs(self):
        """Test detection of @SafeVarargs annotation."""
        source = """
        @SafeVarargs
        public final void process(T... elements) {
            // code
        }
        """
        
        detector = AnnotationDetector()
        annotations = detector.detect_from_source(source)
        
        assert detector.get_annotation_count() == 1
        ann = annotations[0]
        assert ann.name == 'SafeVarargs'
    
    def test_convenience_functions(self):
        """Test convenience functions."""
        source = """
        @Override
        @Deprecated
        public void oldMethod() {
            // code
        }
        """
        
        assert has_override_annotation(source) is True
        assert has_deprecated_annotation(source) is True


# ===== Annotation Mapper Tests =====

class TestAnnotationMapping:
    """Test annotation mapping to Bedrock format."""
    
    def test_map_override_to_jsdoc(self):
        """Test mapping @Override to JSDoc."""
        source = """
        @Override
        public void doSomething() {}
        """
        
        mapper = AnnotationMapper()
        result = mapper.map_from_source(source)
        
        assert len(result.mapped) == 1
        mapped = result.mapped[0]
        assert mapped.converted_comment is not None
        assert 'override' in mapped.converted_comment.lower()
    
    def test_map_deprecated_to_jsdoc(self):
        """Test mapping @Deprecated to JSDoc."""
        source = """
        @Deprecated
        public void oldMethod() {}
        """
        
        mapper = AnnotationMapper()
        result = mapper.map_from_source(source)
        
        assert len(result.mapped) == 1
        mapped = result.mapped[0]
        assert mapped.converted_comment is not None
        assert 'deprecated' in mapped.converted_comment.lower()
    
    def test_map_nullable_to_typescript(self):
        """Test mapping @Nullable to TypeScript."""
        source = """
        @Nullable
        private String value;
        """
        
        mapper = AnnotationMapper()
        result = mapper.map_from_source(source)
        
        assert len(result.mapped) == 1
        mapped = result.mapped[0]
        assert mapped.typescript_type is not None
        assert 'null' in mapped.typescript_type.lower()
    
    def test_map_custom_to_comment(self):
        """Test mapping custom annotation to comment."""
        source = """
        @CustomAnnotation(param = "value")
        public void custom() {}
        """
        
        mapper = AnnotationMapper()
        result = mapper.map_from_source(source)
        
        assert len(result.mapped) == 1
        mapped = result.mapped[0]
        assert mapped.converted_comment is not None
        assert 'CustomAnnotation' in mapped.converted_comment
    
    def test_build_jsdoc_comment(self):
        """Test building JSDoc comment from multiple annotations."""
        source = """
        @Override
        @Deprecated
        public void oldMethod() {}
        """
        
        mapper = AnnotationMapper()
        result = mapper.map_from_source(source)
        
        assert result.jsdoc_comment is not None
        assert '/**' in result.jsdoc_comment
        assert '*/' in result.jsdoc_comment
    
    def test_convenience_function(self):
        """Test convenience map_annotations function."""
        source = """
        @Override
        public void doSomething() {}
        """
        
        result = map_annotations(source)
        assert isinstance(result, AnnotationMappingResult)
        assert len(result.mapped) >= 1


# ===== Annotation Extractor Tests =====

class TestAnnotationExtraction:
    """Test annotation value extraction."""
    
    def test_extract_basic(self):
        """Test basic annotation extraction."""
        source = """
        @Override
        public void doSomething() {}
        """
        
        extractor = AnnotationExtractor()
        result = extractor.extract(source)
        
        assert result.total_count() == 1
        assert result.has_override() is True
    
    def test_extract_summary(self):
        """Test extraction summary."""
        source = """
        @Override
        @Deprecated
        @Override
        public void oldMethod() {}
        """
        
        extractor = AnnotationExtractor()
        result = extractor.extract(source)
        
        assert result.summary['Override'] == 2
        assert result.summary['Deprecated'] == 1
    
    def test_extract_metadata(self):
        """Test extraction metadata."""
        source = """
        @Override
        public void doSomething() {}
        """
        
        extractor = AnnotationExtractor()
        result = extractor.extract(source)
        
        assert len(result.metadata) == 1
        metadata = result.metadata[0]
        assert isinstance(metadata, AnnotationMetadata)
        assert metadata.annotation_name == 'Override'
        assert metadata.line_number > 0
    
    def test_extract_custom_annotations(self):
        """Test custom annotation extraction."""
        source = """
        @CustomAnnotation
        public void custom() {}
        """
        
        extractor = AnnotationExtractor()
        result = extractor.extract(source)
        
        assert 'CustomAnnotation' in result.custom_annotations
    
    def test_extract_parameters(self):
        """Test parameter extraction."""
        source = """
        @SuppressWarnings(value = "unchecked")
        public void process() {}
        """
        
        extractor = AnnotationExtractor()
        result = extractor.extract(source)
        
        assert len(result.metadata) == 1
        metadata = result.metadata[0]
        assert 'value' in metadata.parameters
        assert metadata.parameters['value'] == 'unchecked'
    
    def test_convenience_function(self):
        """Test convenience extract_annotations function."""
        source = """
        @Override
        public void doSomething() {}
        """
        
        result = extract_annotations(source)
        assert isinstance(result, ExtractionResult)
        assert result.total_count() >= 1
    
    def test_extract_multiple_annotation_types(self):
        """Test extracting multiple different annotation types."""
        source = """
        @Override
        @Deprecated
        @Nullable
        @SuppressWarnings("rawtypes")
        public void complex() {}
        """
        
        extractor = AnnotationExtractor()
        result = extractor.extract(source)
        
        assert result.total_count() == 4
        assert result.has_override() is True
        assert result.has_deprecated() is True
        assert result.has_nullable() is True


# ===== Integration Tests =====

class TestAnnotationIntegration:
    """Integration tests for annotation pipeline."""
    
    def test_full_pipeline(self):
        """Test full detection -> mapping -> extraction pipeline."""
        source = """
        @Override
        @Deprecated(since = "1.0", forRemoval = true)
        public void oldMethod(@Nullable String param) {
            // implementation
        }
        """
        
        # Step 1: Detect
        detector = AnnotationDetector()
        annotations = detector.detect_from_source(source)
        assert len(annotations) >= 2
        
        # Step 2: Map
        mapper = AnnotationMapper()
        mapping_result = mapper.map_from_source(source)
        assert len(mapping_result.mapped) >= 2
        
        # Step 3: Extract
        extractor = AnnotationExtractor()
        extraction_result = extractor.extract(source)
        assert extraction_result.total_count() >= 2
        assert extraction_result.has_override() is True
        assert extraction_result.has_deprecated() is True
    
    def test_complex_source_with_annotations(self):
        """Test annotations in complex source code."""
        source = """
        package com.example.mod;
        
        import java.util.List;
        
        public class ExampleMod {
            @Override
            public void onInitialize() {
                // initialization
            }
            
            @Deprecated
            private void legacyMethod() {}
            
            @Nullable
            private List<String> cachedList;
            
            @SuppressWarnings(value = "unchecked")
            public <T> T castObject(Object obj) {
                return (T) obj;
            }
            
            @SafeVarargs
            public final void registerHandlers(Handler<T>... handlers) {
                // registration
            }
        }
        
        @FunctionalInterface
        interface EventHandler {
            void handleEvent(Event event);
        }
        """
        
        detector = AnnotationDetector()
        annotations = detector.detect_from_source(source)
        
        # Should detect: @Override, @Deprecated, @Nullable, @SuppressWarnings, @SafeVarargs, @FunctionalInterface
        assert detector.get_annotation_count() >= 6
        assert detector.has_override() is True
        assert detector.has_deprecated() is True
        assert detector.has_nullable() is True
        
        mapper = AnnotationMapper()
        result = mapper.map_from_source(source)
        assert len(result.mapped) >= 6
        
        extractor = AnnotationExtractor()
        extraction_result = extractor.extract(source)
        assert extraction_result.total_count() >= 6


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
