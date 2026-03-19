"""
Tests for Phase 12-01: Semantic Equivalence Scoring

Tests the embedding-based semantic equivalence checking between
Java source and Bedrock output.
"""

import pytest
import asyncio
import sys
import os

# Add the ai-engine directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import directly from the module to avoid __init__.py import issues
from services.semantic_equivalence import (
    SemanticEquivalenceChecker,
    check_semantic_equivalence,
    ScoreCategory,
    EquivalenceResult,
    DataFlowAnalyzer,
    ControlFlowAnalyzer,
)


class TestEmbeddingSimilarity:
    """Tests for embedding-based similarity computation."""
    
    @pytest.mark.asyncio
    async def test_embedding_similarity_identical_code(self):
        """Test that identical code gets high similarity score."""
        code = '''
        public class TestBlock extends Block {
            public void onPlace() {
                int damage = 5;
            }
        }
        '''
        checker = SemanticEquivalenceChecker()
        result = await checker.check_equivalence(code, code, compute_embedding=True)
        
        # Identical code should have very high similarity
        assert result.embedding_similarity >= 0.9
    
    @pytest.mark.asyncio
    async def test_embedding_similarity_similar_code(self):
        """Test that similar code gets high similarity score."""
        java_code = '''
        public class TestBlock extends Block {
            public void onPlace() {
                int damage = 5;
            }
        }
        '''
        
        # Similar but slightly different
        bedrock_code = '''
        TestBlock.prototype.onPlace = function(event) {
            let damage = 5;
        };
        '''
        
        checker = SemanticEquivalenceChecker()
        result = await checker.check_equivalence(java_code, bedrock_code, compute_embedding=True)
        
        # Similar code should have decent similarity
        assert result.embedding_similarity >= 0.3
    
    @pytest.mark.asyncio
    async def test_embedding_similarity_different_code(self):
        """Test that different code gets low similarity score."""
        java_code = '''
        public class TestBlock extends Block {
            public void onPlace() {
                int damage = 5;
            }
        }
        '''
        
        # Completely different code
        different_code = '''
        public class DifferentClass {
            public String getName() {
                return "something else";
            }
        }
        '''
        
        checker = SemanticEquivalenceChecker()
        result = await checker.check_equivalence(java_code, different_code, compute_embedding=True)
        
        # Different code should have lower similarity
        assert result.embedding_similarity < 0.8


class TestThresholdCategorization:
    """Tests for threshold categorization."""
    
    def test_apply_thresholds_excellent(self):
        """Test 90%+ returns EXCELLENT."""
        assert EquivalenceResult.apply_thresholds(0.95) == ScoreCategory.EXCELLENT
        assert EquivalenceResult.apply_thresholds(0.90) == ScoreCategory.EXCELLENT
    
    def test_apply_thresholds_good(self):
        """Test 70-89% returns GOOD."""
        assert EquivalenceResult.apply_thresholds(0.89) == ScoreCategory.GOOD
        assert EquivalenceResult.apply_thresholds(0.75) == ScoreCategory.GOOD
        assert EquivalenceResult.apply_thresholds(0.70) == ScoreCategory.GOOD
    
    def test_apply_thresholds_needs_work(self):
        """Test <70% returns NEEDS_WORK."""
        assert EquivalenceResult.apply_thresholds(0.69) == ScoreCategory.NEEDS_WORK
        assert EquivalenceResult.apply_thresholds(0.50) == ScoreCategory.NEEDS_WORK
        assert EquivalenceResult.apply_thresholds(0.0) == ScoreCategory.NEEDS_WORK
    
    @pytest.mark.asyncio
    async def test_result_score_category(self):
        """Test that EquivalenceResult gets correct score_category."""
        java_code = "public void test() { int x = 1; }"
        bedrock_code = "function test() { let x = 1; }"
        
        result = await check_semantic_equivalence(java_code, bedrock_code)
        
        # Should have a valid score category
        assert result.score_category in [ScoreCategory.EXCELLENT, ScoreCategory.GOOD, ScoreCategory.NEEDS_WORK]


class TestJavaScriptParsing:
    """Tests for JavaScript/Bedrock parsing support."""
    
    def test_dataflow_analyzer_javascript(self):
        """Test DataFlowAnalyzer can analyze JavaScript."""
        analyzer = DataFlowAnalyzer()
        
        js_code = '''
        let x = 5;
        let y = x + 1;
        function test() {
            return y;
        }
        '''
        
        dfg = analyzer.analyze_javascript(js_code)
        
        # Should have nodes for variables
        assert len(dfg.nodes) > 0
        assert 'x' in dfg.variables or 'y' in dfg.variables
    
    def test_controlflow_analyzer_javascript(self):
        """Test ControlFlowAnalyzer can analyze JavaScript."""
        analyzer = ControlFlowAnalyzer()
        
        js_code = '''
        if (x > 0) {
            doSomething();
        } else {
            doOther();
        }
        '''
        
        cfg = analyzer.analyze_javascript(js_code)
        
        # Should have nodes
        assert len(cfg.nodes) > 0


class TestSemanticDrift:
    """Tests for semantic drift identification."""
    
    @pytest.mark.asyncio
    async def test_identify_drift_missing_methods(self):
        """Test identification of missing methods."""
        java_code = '''
        public void method1() {}
        public void method2() {}
        '''
        
        # Bedrock has only one method
        bedrock_code = '''
        function method1() {}
        '''
        
        checker = SemanticEquivalenceChecker()
        result = await checker.check_equivalence(java_code, bedrock_code, compute_embedding=True)
        
        # Should identify missing method
        assert len(result.semantic_drift) > 0
    
    @pytest.mark.asyncio
    async def test_identify_drift_async_mismatch(self):
        """Test identification of async/await mismatch."""
        java_code = '''
        public CompletableFuture<String> getData() {
            return CompletableFuture.supplyAsync(() -> "data");
        }
        '''
        
        # No async in Bedrock
        bedrock_code = '''
        function getData() {
            return "data";
        }
        '''
        
        checker = SemanticEquivalenceChecker()
        result = await checker.check_equivalence(java_code, bedrock_code, compute_embedding=True)
        
        # Should identify async mismatch
        assert any("async" in drift.lower() for drift in result.semantic_drift)


class TestIntegrationWithQAValidator:
    """Integration tests with QAValidatorAgent."""
    
    @pytest.mark.asyncio
    async def test_full_equivalence_check(self):
        """Test full equivalence check with all metrics."""
        java_code = '''
        public class MyBlock extends Block {
            private int damage = 0;
            
            public void onPlace() {
                damage = 5;
            }
            
            public int getDamage() {
                return damage;
            }
        }
        '''
        
        bedrock_code = '''
        const MyBlock = {
            damage: 0,
            onPlace: function(event) {
                this.damage = 5;
            },
            getDamage: function() {
                return this.damage;
            }
        };
        '''
        
        result = await check_semantic_equivalence(java_code, bedrock_code)
        
        # Should have all metrics
        assert result.dfg_similarity >= 0.0
        assert result.cfg_similarity >= 0.0
        assert result.embedding_similarity >= 0.0
        assert result.score_category is not None
        assert isinstance(result.to_dict(), dict)
        assert "embedding_similarity" in result.to_dict()
        assert "score_category" in result.to_dict()
        assert "semantic_drift" in result.to_dict()


class TestConvenienceFunction:
    """Tests for the convenience function."""
    
    @pytest.mark.asyncio
    async def test_check_semantic_equivalence_function(self):
        """Test the convenience function."""
        java_code = "public void test() {}"
        bedrock_code = "function test() {}"
        
        result = await check_semantic_equivalence(java_code, bedrock_code)
        
        assert isinstance(result, EquivalenceResult)
        assert result.confidence >= 0.0
        assert result.confidence <= 1.0


# Run tests if executed directly
if __name__ == '__main__':
    pytest.main([__file__, '-v'])
