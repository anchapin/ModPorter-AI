"""
Tests for Phase 08-01: Semantic Understanding Enhancement

Tests the semantic context engine, data flow analysis, and pattern matching
for improved code translation.
"""

import pytest
import json
from utils.semantic_context import SemanticContextEngine, create_semantic_context_engine
from utils.data_flow import DataFlowAnalyzer, create_data_flow_analyzer
from utils.pattern_matcher import PatternMatcher, create_pattern_matcher
from utils.enhanced_translation import EnhancedTranslationEngine, get_enhanced_translation_engine


class TestSemanticContextEngine:
    """Tests for the SemanticContextEngine."""
    
    def test_parse_basic_class(self):
        """Test parsing a basic Java class."""
        engine = create_semantic_context_engine()
        
        java_code = '''
        public class MyBlock extends Block {
            public static final Block MY_BLOCK;
        }
        '''
        
        result = engine.parse_with_context(java_code, 'MyBlock')
        
        assert 'classes' in result
        assert len(result['classes']) > 0
        assert result['classes'][0]['name'] == 'MyBlock'
        assert result['classes'][0]['extends'] == 'Block'
    
    def test_parse_method_context(self):
        """Test extracting method context."""
        engine = create_semantic_context_engine()
        
        java_code = '''
        public class MyBlock extends Block {
            public void onPlace() {
                int damage = 5;
            }
        }
        '''
        
        result = engine.parse_with_context(java_code, 'MyBlock')
        
        assert 'methods' in result
        assert any(m['name'] == 'onPlace' for m in result['methods'])
    
    def test_translation_memory(self):
        """Test translation memory functionality."""
        engine = create_semantic_context_engine()
        
        # Add translation
        engine.add_translation_memory(
            "public void onPlace()", 
            "onPlace(event) {", 
            {"class": "Block", "method": "onPlace"}
        )
        
        # Find match
        match = engine.find_translation_match(
            "public void onPlace()",
            {"class": "Block", "method": "onPlace"}
        )
        
        assert match is not None
        assert match.target_pattern == "onPlace(event) {"
    
    def test_build_context_prompt(self):
        """Test building context prompt for LLM."""
        engine = create_semantic_context_engine()
        
        context = {
            'classes': [{'name': 'MyBlock', 'extends': 'Block', 'implements': []}],
            'method_contexts': [],
            'fields': []
        }
        
        prompt = engine.build_context_prompt(context)
        
        assert 'MyBlock' in prompt
        assert 'Block' in prompt


class TestDataFlowAnalyzer:
    """Tests for the DataFlowAnalyzer."""
    
    def test_analyze_method(self):
        """Test analyzing a method for data flow."""
        analyzer = create_data_flow_analyzer()
        
        java_code = '''
        public class MyBlock extends Block {
            private int damage = 0;
            
            public void onPlace() {
                damage = 5;
            }
        }
        '''
        
        graph = analyzer.analyze_method(java_code, 'onPlace')
        
        assert graph is not None
        assert len(graph.nodes) >= 1
    
    def test_variable_mutation_tracking(self):
        """Test tracking variable mutations."""
        analyzer = create_data_flow_analyzer()
        
        java_code = '''
        public class Test {
            public void test() {
                int x = 10;
                x = 20;
            }
        }
        '''
        
        graph = analyzer.analyze_method(java_code)
        
        # Should have tracked mutations
        assert graph.variable_mutations is not None
    
    def test_map_to_bedrock_operations(self):
        """Test mapping to Bedrock operations."""
        analyzer = create_data_flow_analyzer()
        
        java_code = '''
        public class Test {
            public void test() {
                int x = 10;
            }
        }
        '''
        
        analyzer.analyze_method(java_code)
        ops = analyzer.map_to_bedrock_operations()
        
        assert ops is not None


class TestPatternMatcher:
    """Tests for the PatternMatcher."""
    
    def test_block_pattern_matching(self):
        """Test matching block patterns."""
        matcher = create_pattern_matcher()
        
        java_code = '''
        public class MyBlock extends Block {
            public static final Block MY_BLOCK;
        }
        '''
        
        matches = matcher.find_matches(java_code)
        
        assert len(matches) > 0
        # Should find block_basic pattern
        assert any(p.pattern_id == 'block_basic' for p in matches)
    
    def test_item_pattern_matching(self):
        """Test matching item patterns."""
        matcher = create_pattern_matcher()
        
        java_code = '''
        public class MyItem extends Item {
            public static final Item DIAMOND_SWORD;
        }
        '''
        
        matches = matcher.find_matches(java_code)
        
        assert len(matches) > 0
        assert any(p.pattern_id == 'item_basic' for p in matches)
    
    def test_entity_pattern_matching(self):
        """Test matching entity patterns."""
        matcher = create_pattern_matcher()
        
        java_code = '''
        public class ZombieMob extends Mob {
        }
        '''
        
        matches = matcher.find_matches(java_code)
        
        assert len(matches) > 0
    
    def test_recommend_patterns(self):
        """Test pattern recommendations."""
        matcher = create_pattern_matcher()
        
        java_code = '''
        public class MyBlock extends Block {
            public static final Block MY_BLOCK;
        }
        '''
        
        recommendations = matcher.recommend_patterns(java_code)
        
        assert len(recommendations) > 0
        # Should recommend block patterns
        assert any(p[0].pattern_type.value == 'block' for p in recommendations)
    
    def test_inheritance_recognition(self):
        """Test recognizing inheritance hierarchies."""
        matcher = create_pattern_matcher()
        
        java_code = '''
        public class MyBlock extends Block implements IBlockProvider {
        }
        '''
        
        hierarchy = matcher.recognize_inheritance(java_code)
        
        assert 'MyBlock' in hierarchy
        assert 'Block' in hierarchy['MyBlock']


class TestEnhancedTranslationEngine:
    """Tests for the EnhancedTranslationEngine."""
    
    def test_analyze_and_translate(self):
        """Test full analysis and translation."""
        engine = EnhancedTranslationEngine()
        
        java_code = '''
        public class MyBlock extends Block {
            public static final Block MY_BLOCK;
            private int damage = 0;
            
            public void onPlace() {
                damage = 5;
            }
        }
        '''
        
        result = engine.analyze_and_translate(java_code, 'MyBlock')
        
        # Should have all required keys
        assert 'translation' in result
        assert 'semantic_context' in result
        assert 'data_flow' in result
        assert 'patterns' in result
        assert 'confidence' in result
        assert 'context_prompt' in result
    
    def test_confidence_calculation(self):
        """Test confidence score calculation."""
        engine = EnhancedTranslationEngine()
        
        java_code = '''
        public class MyBlock extends Block {
            public static final Block MY_BLOCK;
        }
        '''
        
        result = engine.analyze_and_translate(java_code, 'MyBlock')
        
        # Should calculate confidence based on patterns
        assert result['confidence'] >= 0.0
        assert result['confidence'] <= 1.0
    
    def test_pattern_collection(self):
        """Test that patterns are collected."""
        engine = EnhancedTranslationEngine()
        
        java_code = '''
        public class MyBlock extends Block {
            public static final Block MY_BLOCK;
        }
        '''
        
        result = engine.analyze_and_translate(java_code, 'MyBlock')
        
        assert len(result['patterns']) > 0
    
    def test_context_prompt_generation(self):
        """Test context prompt is generated."""
        engine = EnhancedTranslationEngine()
        
        java_code = '''
        public class MyBlock extends Block {
            public static final Block MY_BLOCK;
        }
        '''
        
        result = engine.analyze_and_translate(java_code, 'MyBlock')
        
        assert result['context_prompt'] is not None
        assert len(result['context_prompt']) > 0


class TestIntegration:
    """Integration tests for the enhanced translation system."""
    
    def test_full_pipeline(self):
        """Test the full translation pipeline."""
        engine = get_enhanced_translation_engine()
        
        java_code = '''
        public class DiamondSword extends Sword {
            public static final Item DIAMOND_SWORD;
            private int damage = 10;
        }
        '''
        
        result = engine.analyze_and_translate(java_code, 'DiamondSword')
        
        # Verify all components work together
        assert result['confidence'] > 0
        assert len(result['patterns']) > 0
        assert 'recommendations' in result
    
    def test_error_handling(self):
        """Test error handling for invalid code."""
        engine = EnhancedTranslationEngine()
        
        # Invalid Java code
        java_code = 'this is not valid java'
        
        result = engine.analyze_and_translate(java_code)
        
        # Should handle gracefully
        assert 'error' in result or 'patterns' in result


# Run tests if executed directly
if __name__ == '__main__':
    pytest.main([__file__, '-v'])
