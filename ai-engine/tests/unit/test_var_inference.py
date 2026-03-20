"""Unit tests for Var Type Inference module.

Tests cover:
- Basic var declarations with different initializer types
- For-each loops with var
- Diamond operator inference
- Collection type conversions
- Literal type inference
- Generic type conversions
"""

import pytest
from utils.var_inference import (
    VarDetector, VarTypeInference, VarScopeHandler,
    VarDeclaration, detect_and_convert
)


class TestVarDetector:
    """Tests for VarDetector class."""
    
    def test_detect_basic_var(self):
        """Test detection of basic var with ArrayList."""
        code = '''
        public class Test {
            public void method() {
                var x = new ArrayList<String>();
            }
        }
        '''
        detector = VarDetector()
        result = detector.detect_from_source(code)
        
        assert len(result) == 1
        assert result[0].name == 'x'
        assert result[0].initializer_type == 'new'
    
    def test_detect_multiple_vars(self):
        """Test detection of multiple var declarations."""
        code = '''
        public class Test {
            public void method() {
                var a = new ArrayList<String>();
                var b = "hello";
                var c = 42;
            }
        }
        '''
        detector = VarDetector()
        result = detector.detect_from_source(code)
        
        assert len(result) == 3
        names = [v.name for v in result]
        assert 'a' in names
        assert 'b' in names
        assert 'c' in names
    
    def test_detect_diamond_operator(self):
        """Test detection with diamond operator."""
        code = '''
        public class Test {
            public void method() {
                var list = new ArrayList<>();
            }
        }
        '''
        detector = VarDetector()
        result = detector.detect_from_source(code)
        
        assert len(result) == 1
        assert result[0].name == 'list'
    
    def test_detect_for_each_var(self):
        """Test detection of var in for-each loop."""
        code = '''
        public class Test {
            public void method(List<String> items) {
                for (var item : items) {
                    System.out.println(item);
                }
            }
        }
        '''
        detector = VarDetector()
        result = detector.detect_from_source(code)
        
        assert len(result) == 1
        assert result[0].name == 'item'
        assert result[0].scope == 'for-loop'
    
    def test_detect_literals(self):
        """Test detection of var with literals."""
        code = '''
        public class Test {
            public void method() {
                var str = "hello";
                var num = 42;
                var flag = true;
                var d = 3.14;
            }
        }
        '''
        detector = VarDetector()
        result = detector.detect_from_source(code)
        
        assert len(result) == 4
        types = {v.initializer_type for v in result}
        assert 'literal' in types
    
    def test_ignores_non_var(self):
        """Test that non-var declarations are ignored."""
        code = '''
        public class Test {
            public void method() {
                String x = "hello";
                int y = 42;
            }
        }
        '''
        detector = VarDetector()
        result = detector.detect_from_source(code)
        
        # Should find LocalVariableDeclaration but not var type
        assert len(result) == 0
    
    def test_detects_collection_types(self):
        """Test detection of various collection types."""
        code = '''
        public class Test {
            public void method() {
                var list = new ArrayList<String>();
                var map = new HashMap<String, Integer>();
                var set = new HashSet<Item>();
            }
        }
        '''
        detector = VarDetector()
        result = detector.detect_from_source(code)
        
        assert len(result) == 3


class TestVarTypeInference:
    """Tests for VarTypeInference class."""
    
    def test_infer_arraylist(self):
        """Test inference of ArrayList."""
        code = '''
        public class Test {
            public void method() {
                var x = new ArrayList<String>();
            }
        }
        '''
        result = detect_and_convert(code)
        
        assert len(result) == 1
        # TypeScript uses lowercase primitive types
        assert result[0].inferred_type == 'Array<string>'
    
    def test_infer_linkedlist(self):
        """Test inference of LinkedList."""
        code = '''
        public class Test {
            public void method() {
                var x = new LinkedList<ItemStack>();
            }
        }
        '''
        result = detect_and_convert(code)
        
        assert len(result) == 1
        assert result[0].inferred_type == 'Array<ItemStack>'
    
    def test_infer_hashmap(self):
        """Test inference of HashMap."""
        code = '''
        public class Test {
            public void method() {
                var x = new HashMap<String, Integer>();
            }
        }
        '''
        result = detect_and_convert(code)
        
        assert len(result) == 1
        assert result[0].inferred_type == 'Map<string, number>'
    
    def test_infer_hashset(self):
        """Test inference of HashSet."""
        code = '''
        public class Test {
            public void method() {
                var x = new HashSet<String>();
            }
        }
        '''
        result = detect_and_convert(code)
        
        assert len(result) == 1
        assert result[0].inferred_type == 'Set<string>'
    
    def test_infer_string_literal(self):
        """Test inference from string literal."""
        code = '''
        public class Test {
            public void method() {
                var x = "hello";
            }
        }
        '''
        result = detect_and_convert(code)
        
        assert len(result) == 1
        assert result[0].inferred_type == 'string'
    
    def test_infer_int_literal(self):
        """Test inference from int literal."""
        code = '''
        public class Test {
            public void method() {
                var x = 42;
            }
        }
        '''
        result = detect_and_convert(code)
        
        assert len(result) == 1
        assert result[0].inferred_type == 'number'
    
    def test_infer_boolean_literal(self):
        """Test inference from boolean literal."""
        code = '''
        public class Test {
            public void method() {
                var x = true;
            }
        }
        '''
        result = detect_and_convert(code)
        
        assert len(result) == 1
        assert result[0].inferred_type == 'boolean'
    
    def test_diamond_operator(self):
        """Test diamond operator gives Array without type args."""
        code = '''
        public class Test {
            public void method() {
                var x = new ArrayList<>();
            }
        }
        '''
        result = detect_and_convert(code)
        
        assert len(result) == 1
        assert result[0].inferred_type == 'Array'
    
    def test_primitive_array(self):
        """Test var with int array."""
        code = '''
        public class Test {
            public void method() {
                var x = new int[5];
            }
        }
        '''
        result = detect_and_convert(code)
        
        # Should handle array creation
        assert len(result) == 1


class TestVarScopeHandler:
    """Tests for VarScopeHandler class."""
    
    def test_basic_scope(self):
        """Test basic scope operations."""
        handler = VarScopeHandler()
        
        # Add a var to root scope
        decl = VarDeclaration(name='x', inferred_type='string')
        handler.add_var(decl)
        
        # Should be retrievable
        found = handler.get_var('x')
        assert found is not None
        assert found.name == 'x'
    
    def test_nested_scope(self):
        """Test nested scope handling."""
        handler = VarScopeHandler()
        
        # Add to root
        decl1 = VarDeclaration(name='outer', inferred_type='number')
        handler.add_var(decl1)
        
        # Enter new scope
        handler.enter_scope('inner')
        
        # Add to inner
        decl2 = VarDeclaration(name='inner', inferred_type='string')
        handler.add_var(decl2)
        
        # Should find inner in current scope
        found = handler.get_var('inner')
        assert found is not None
        assert found.name == 'inner'
        
        # Should find outer in parent scope
        found = handler.get_var('outer')
        assert found is not None
        assert found.name == 'outer'
    
    def test_shadowing(self):
        """Test variable shadowing in nested scopes."""
        handler = VarScopeHandler()
        
        # Add to root
        decl1 = VarDeclaration(name='x', inferred_type='number')
        handler.add_var(decl1)
        
        # Enter new scope
        handler.enter_scope('inner')
        
        # Shadow in inner
        decl2 = VarDeclaration(name='x', inferred_type='string')
        handler.add_var(decl2)
        
        # Current scope should return shadowed version
        found = handler.get_var('x')
        assert found is not None
        assert found.inferred_type == 'string'
    
    def test_exit_scope(self):
        """Test exiting scope returns to parent."""
        handler = VarScopeHandler()
        
        handler.enter_scope('scope1')
        handler.add_var(VarDeclaration(name='a', inferred_type='string'))
        
        handler.enter_scope('scope2')
        handler.add_var(VarDeclaration(name='b', inferred_type='number'))
        
        # Exit to parent
        handler.exit_scope()
        
        # Should find a in current scope
        found = handler.get_var('a')
        assert found is not None
        
        # b should not be found in parent
        found = handler.get_var('b')
        assert found is None


class TestComprehensive:
    """Comprehensive integration tests."""
    
    def test_all_collection_types(self):
        """Test all major collection type conversions."""
        test_cases = [
            ('ArrayList<String>', 'Array<string>'),
            ('LinkedList<Integer>', 'Array<number>'),
            ('HashMap<String, Object>', 'Map<string, object>'),
            ('TreeMap<String, Integer>', 'Map<string, number>'),
            ('HashSet<Double>', 'Set<number>'),
            ('List<String>', 'Array<string>'),
            ('Map<String, String>', 'Map<string, string>'),
        ]
        
        for java_init, expected_ts in test_cases:
            code = f'''
            public class Test {{
                public void method() {{
                    var x = new {java_init}();
                }}
            }}
            '''
            result = detect_and_convert(code)
            assert len(result) == 1, f"Failed for {java_init}"
            assert result[0].inferred_type == expected_ts, \
                f"Expected {expected_ts} for {java_init}, got {result[0].inferred_type}"
    
    def test_minecraft_collection_types(self):
        """Test common Minecraft mod collection types."""
        # Common in Minecraft mods
        test_cases = [
            ('ArrayList<ItemStack>', 'Array<ItemStack>'),
            ('List<BlockPos>', 'Array<BlockPos>'),
            # UUID is a custom type, should pass through as-is
            ('Map<UUID, Entity>', 'Map<UUID, Entity>'),
        ]
        
        for java_init, expected_ts in test_cases:
            code = f'''
            public class Test {{
                public void method() {{
                    var x = new {java_init}();
                }}
            }}
            '''
            result = detect_and_convert(code)
            assert len(result) == 1, f"Failed for {java_init}"
            # Custom types should pass through
            assert result[0].inferred_type == expected_ts, \
                f"Expected {expected_ts} for {java_init}, got {result[0].inferred_type}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
