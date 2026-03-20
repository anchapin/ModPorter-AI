"""
Tests for Java Generics Conversion
Phase 13-01: Generics Conversion
"""

import pytest
import sys
import os

# Add ai-engine to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ai-engine'))

from utils.type_parameter_extractor import (
    TypeParameterExtractor,
    TypeParameter,
    GenericDeclaration,
    extract_generics
)
from utils.generic_type_mapper import (
    GenericTypeMapper,
    map_java_to_bedrock
)


class TestTypeParameterExtractor:
    """Tests for TypeParameterExtractor"""
    
    def test_simple_class_generics(self):
        """Test extraction of simple generic class"""
        code = """
        public class Box<T> {
            private T content;
        }
        """
        extractor = TypeParameterExtractor()
        declarations = extractor.extract_from_source(code)
        
        assert len(declarations) == 1
        assert declarations[0].name == "Box"
        assert len(declarations[0].type_parameters) == 1
        assert declarations[0].type_parameters[0].name == "T"
    
    def test_class_with_multiple_type_params(self):
        """Test extraction of class with multiple type parameters"""
        code = """
        public class Pair<K, V> {
            private K key;
            private V value;
        }
        """
        extractor = TypeParameterExtractor()
        declarations = extractor.extract_from_source(code)
        
        assert len(declarations) == 1
        assert declarations[0].name == "Pair"
        assert len(declarations[0].type_parameters) == 2
        names = [tp.name for tp in declarations[0].type_parameters]
        assert "K" in names
        assert "V" in names
    
    def test_class_with_bounds(self):
        """Test extraction of type parameters with bounds"""
        code = """
        public class Container<T extends Entity> {
            private T entity;
        }
        """
        extractor = TypeParameterExtractor()
        declarations = extractor.extract_from_source(code)
        
        assert len(declarations) == 1
        tp = declarations[0].type_parameters[0]
        assert tp.name == "T"
        assert "Entity" in tp.bounds
    
    def test_generic_method(self):
        """Test extraction of generic method"""
        code = """
        public class Utils {
            public <T> T convert(Object input) {
                return (T) input;
            }
        }
        """
        extractor = TypeParameterExtractor()
        declarations = extractor.extract_from_source(code)
        
        assert len(declarations) >= 1
        # Find the method declaration
        method_decl = None
        for decl in declarations:
            if decl.is_method and decl.name == "convert":
                method_decl = decl
                break
        
        assert method_decl is not None
        assert method_decl.is_method
        assert len(method_decl.type_parameters) == 1
        assert method_decl.type_parameters[0].name == "T"
    
    def test_method_with_bounded_type_param(self):
        """Test generic method with bounded type parameter"""
        code = """
        public class Helpers {
            public <T extends Comparable> void sort(List<T> items) {
            }
        }
        """
        extractor = TypeParameterExtractor()
        declarations = extractor.extract_from_source(code)
        
        assert len(declarations) >= 1
        method_decl = None
        for decl in declarations:
            if decl.is_method and decl.name == "sort":
                method_decl = decl
                break
        
        assert method_decl is not None
        assert method_decl.type_parameters[0].bounds
    
    def test_nested_generics(self):
        """Test extraction of nested generic types in code"""
        code = """
        public class Manager {
            private List<Map<String, Integer>> data;
        }
        """
        extractor = TypeParameterExtractor()
        # This mainly tests that parsing doesn't fail
        declarations = extractor.extract_from_source(code)
        # We mainly care that it doesn't crash
    
    def test_no_generics(self):
        """Test code with no generics"""
        code = """
        public class Simple {
            private String name;
            private int value;
        }
        """
        extractor = TypeParameterExtractor()
        declarations = extractor.extract_from_source(code)
        
        # Should not find any generic declarations
        generic_decls = [d for d in declarations if d.type_parameters]
        assert len(generic_decls) == 0


class TestGenericTypeMapper:
    """Tests for GenericTypeMapper"""
    
    def test_primitive_mapping(self):
        """Test mapping of primitive types"""
        mapper = GenericTypeMapper()
        
        assert mapper.map_type("int") == "number"
        assert mapper.map_type("boolean") == "boolean"
        assert mapper.map_type("float") == "number"
    
    def test_object_type_mapping(self):
        """Test mapping of common object types"""
        mapper = GenericTypeMapper()
        
        assert mapper.map_type("String") == "string"
        assert mapper.map_type("Integer") == "number"
        assert mapper.map_type("Object") == "any"
    
    def test_collection_mapping(self):
        """Test mapping of collection types"""
        mapper = GenericTypeMapper()
        
        assert mapper.map_type("List") == "Array"
        assert mapper.map_type("Map") == "Object"
        assert mapper.map_type("Set") == "Array"
    
    def test_array_mapping(self):
        """Test mapping of array types"""
        mapper = GenericTypeMapper()
        
        assert mapper.map_type("int[]") == "Array<number>"
        assert mapper.map_type("String[]") == "Array<string>"
    
    def test_type_parameter_substitution(self):
        """Test type parameter substitution"""
        mapper = GenericTypeMapper()
        mapper.set_type_parameter("T", "string")
        
        # Map with type params
        result = mapper.map_generic_type("List<T>", mapper.type_parameters)
        assert result == "Array<string>"
    
    def test_multiple_type_params(self):
        """Test mapping with multiple type parameters"""
        mapper = GenericTypeMapper()
        type_params = {"K": "string", "V": "number"}
        
        result = mapper.map_generic_type("Map<K, V>", type_params)
        assert result == "Object<string, number>"
    
    def test_nested_generics_mapping(self):
        """Test mapping of nested generic types"""
        mapper = GenericTypeMapper()
        
        result = mapper.map_generic_type("List<Map<String, Integer>>", {})
        assert "Array" in result
        assert "Map" in result
    
    def test_convenience_function(self):
        """Test convenience function"""
        result = map_java_to_bedrock("String")
        assert result == "string"
        
        result = map_java_to_bedrock("List", {"T": "Entity"})
        assert result == "Array"


class TestIntegration:
    """Integration tests for complete generics pipeline"""
    
    def test_full_extraction_and_mapping(self):
        """Test full pipeline: extract generics then map types"""
        code = """
        public class DataStore<T extends Entity> {
            private Map<String, T> entities;
            
            public <V extends Comparable> V find(String id) {
                return null;
            }
        }
        """
        # Extract
        extractor = TypeParameterExtractor()
        declarations = extractor.extract_from_source(code)
        
        # Map
        mapper = GenericTypeMapper()
        
        # Verify we got the class declaration
        class_decl = None
        for decl in declarations:
            if not decl.is_method:
                class_decl = decl
                break
        
        assert class_decl is not None
        assert class_decl.name == "DataStore"
        assert len(class_decl.type_parameters) == 1
        assert class_decl.type_parameters[0].name == "T"
    
    def test_complex_generic_pattern(self):
        """Test handling of complex generic patterns"""
        code = """
        public class Repository<T, K, V> {
            private Map<K, List<V>> data;
            private T item;
        }
        """
        extractor = TypeParameterExtractor()
        declarations = extractor.extract_from_source(code)
        
        mapper = GenericTypeMapper()
        # Should handle without errors
        assert len(declarations) >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
