"""Tests for Record detection and mapping (Phase 14-06)."""

import pytest
import sys
import os

from utils.record_detector import (
    RecordDetector,
    JavaRecord,
    RecordComponent,
    RecordMethod,
    detect_records,
    is_record,
)

from utils.record_mapper import (
    RecordMapper,
    RecordEqualityHandler,
    TypeScriptRecordOutput,
    map_record,
    records_to_typescript,
)


class TestRecordDetection:
    """Tests for RecordDetector."""
    
    def test_detect_simple_record(self):
        """Test detecting a simple record."""
        source = """
        public record Point(int x, int y) {}
        """
        detector = RecordDetector()
        records = detector.detect(source)
        
        assert len(records) >= 1
    
    def test_detect_record_with_implements(self):
        """Test detecting a record with implements clause."""
        source = """
        public record Point(int x, int y) implements Serializable {}
        """
        detector = RecordDetector()
        records = detector.detect(source)
        
        assert len(records) >= 1
    
    def test_convenience_function(self):
        """Test convenience function."""
        source = """
        public record Point(int x, int y) {}
        """
        records = detect_records(source)
        assert isinstance(records, list)


class TestRecordMapper:
    """Tests for RecordMapper."""
    
    def test_map_simple_record(self):
        """Test mapping a simple record."""
        record = JavaRecord(
            name="Point",
            components=[
                RecordComponent(name="x", type="int"),
                RecordComponent(name="y", type="int"),
            ]
        )
        
        mapper = RecordMapper()
        result = mapper.map_record(record)
        
        assert result.interface_name == "IPoint"
        assert "x" in result.interface_body
        assert "y" in result.interface_body
    
    def test_convert_primitives(self):
        """Test type conversion."""
        mapper = RecordMapper()
        
        assert mapper._convert_type('int') == 'number'
        assert mapper._convert_type('boolean') == 'boolean'
        assert mapper._convert_type('String') == 'string'
    
    def test_interface_name_generation(self):
        """Test interface name generation."""
        mapper = RecordMapper()
        
        assert mapper._to_interface_name('Point') == 'IPoint'
        assert mapper._to_interface_name('IPoint') == 'IPoint'  # No double prefix


class TestRecordEqualityHandler:
    """Tests for RecordEqualityHandler."""
    
    def test_generate_equals(self):
        """Test generating equals method."""
        record = JavaRecord(
            name="Point",
            components=[
                RecordComponent(name="x", type="int"),
                RecordComponent(name="y", type="int"),
            ]
        )
        
        handler = RecordEqualityHandler()
        equals_code = handler.generate_equals(record)
        
        assert 'equals' in equals_code
        assert 'Point' in equals_code
    
    def test_generate_tostring(self):
        """Test generating toString method."""
        record = JavaRecord(
            name="Point",
            components=[
                RecordComponent(name="x", type="int"),
                RecordComponent(name="y", type="int"),
            ]
        )
        
        handler = RecordEqualityHandler()
        tostring_code = handler.generate_tostring(record)
        
        assert 'toString' in tostring_code
        assert 'Point' in tostring_code


class TestConvenienceFunctions:
    """Test module-level convenience functions."""
    
    def test_map_record_function(self):
        """Test convenience function."""
        record = JavaRecord(
            name="User",
            components=[
                RecordComponent(name="name", type="String"),
                RecordComponent(name="age", type="int"),
            ]
        )
        
        result = map_record(record)
        assert isinstance(result, TypeScriptRecordOutput)
        assert result.interface_name == "IUser"


class TestEdgeCases:
    """Test edge cases."""
    
    def test_empty_source(self):
        """Test with empty source."""
        detector = RecordDetector()
        records = detector.detect('')
        assert records == []
    
    def test_no_records(self):
        """Test source without records."""
        source = """
        public class Example {
            private String name;
        }
        """
        detector = RecordDetector()
        records = detector.detect(source)
        assert len(records) == 0


class TestRecordIntegration:
    """Integration tests for full pipeline."""
    
    def test_full_pipeline(self):
        """Test full detection and mapping pipeline."""
        source = """
        public record Point(int x, int y) {}
        """
        
        # Detect
        detector = RecordDetector()
        records = detector.detect(source)
        
        # Map
        mapper = RecordMapper()
        mappings = mapper.map(source)
        
        assert isinstance(mappings, dict)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
