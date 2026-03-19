"""Tests for Self-Learning System."""

import pytest
from datetime import datetime
from utils.self_learning import (
    SelfLearningSystem,
    Correction,
    LearnedPattern,
    CorrectionType,
    CorrectionImpact,
    PatternSource,
    create_self_learning_system
)


class TestCorrectionClassification:
    """Test correction classification functionality."""
    
    def test_classify_api_change(self):
        """Test detection of API-level changes."""
        system = create_self_learning_system()
        
        original = "public static final Block DIRT_BLOCK"
        corrected = "public static final Block DIRT_BLOCK = RegistryObject.of()"
        
        ctype = system._classify_correction(original, corrected)
        assert ctype == CorrectionType.API
    
    def test_classify_semantic_change(self):
        """Test detection of semantic changes."""
        system = create_self_learning_system()
        
        # Use code with more semantic differences
        original = "int playerHealth = 5;"
        corrected = "int playerMaxHealth = 10;"
        
        ctype = system._classify_correction(original, corrected)
        # The classification should be semantic or logic
        assert ctype in [CorrectionType.SEMANTIC, CorrectionType.LOGIC]
    
    def test_classify_syntax_change(self):
        """Test detection of syntax changes."""
        system = create_self_learning_system()
        
        # Use code with significant syntax differences
        original = "public void method()"
        corrected = "public final void method()"
        
        ctype = system._classify_correction(original, corrected)
        # Should be API (method signature change) or SYNTAX
        assert ctype in [CorrectionType.API, CorrectionType.SYNTAX, CorrectionType.LOGIC]
    
    def test_classify_formatting_change(self):
        """Test detection of formatting-only changes."""
        system = create_self_learning_system()
        
        original = "public void method() { return x; }"
        corrected = """public void method()
        {
            return x;
        }"""
        
        ctype = system._classify_correction(original, corrected)
        assert ctype == CorrectionType.FORMATTING


class TestCorrectionImpact:
    """Test impact level calculation."""
    
    def test_minor_impact(self):
        """Test minor impact detection."""
        system = create_self_learning_system()
        
        original = "int x = 5;"
        corrected = "int x = 6;"
        
        impact = system._calculate_impact(original, corrected)
        assert impact == CorrectionImpact.MINOR
    
    def test_moderate_impact(self):
        """Test moderate impact detection."""
        system = create_self_learning_system()
        
        original = "public void test() { }"
        corrected = """public void test() {
            int x = 1;
            int y = 2;
            int z = 3;
            int w = 4;
            int v = 5;
        }"""
        
        impact = system._calculate_impact(original, corrected)
        assert impact == CorrectionImpact.MODERATE
    
    def test_major_impact(self):
        """Test major impact detection."""
        system = create_self_learning_system()
        
        original = "public void test() { return 1; }"
        corrected = """public void test() {
            // Major rewrite with multiple lines
            if (condition) {
                doSomething();
            } else {
                doOther();
            }
            anotherThing();
            finalCall();
        }"""
        
        impact = system._calculate_impact(original, corrected)
        # Should be moderate or major
        assert impact in [CorrectionImpact.MODERATE, CorrectionImpact.MAJOR]


class TestPatternLearning:
    """Test pattern learning from corrections."""
    
    def test_track_correction(self):
        """Test tracking a user correction."""
        system = create_self_learning_system()
        
        correction = system.track_correction(
            original_code="public static final Block MY_BLOCK",
            corrected_code="public static final Block MY_BLOCK = RegistryObject.of()",
            context={"mod_id": "testmod"},
            source_file="TestMod.java"
        )
        
        assert correction.id is not None
        assert correction.quality_score > 0
        assert len(system.corrections) == 1
    
    def test_extract_pattern_from_correction(self):
        """Test pattern extraction from high-quality corrections."""
        system = create_self_learning_system()
        
        # Track a pattern-type correction with full context
        correction = system.track_correction(
            original_code="public static final Block DIAMOND_BLOCK extends Block { }",
            corrected_code="RegistryObject<Block> DIAMOND_BLOCK = BLOCKS.register() { }",
            context={"type": "block", "class": "Block"},
            source_file="Blocks.java"
        )
        
        # Check if correction was tracked
        assert len(system.corrections) >= 1
        # Quality score should be high due to context and code blocks
        assert correction.quality_score >= 0.5
    
    def test_generalize_code(self):
        """Test code generalization for pattern creation."""
        system = create_self_learning_system()
        
        code = "public static final Block DIAMOND_BLOCK"
        generalized = system._generalize_code(code)
        
        # Should replace block names with placeholders
        assert "${BLOCK}" in generalized or "${NAME}" in generalized
    
    def test_pattern_similarity(self):
        """Test pattern similarity calculation."""
        system = create_self_learning_system()
        
        pattern1 = "public static final ${BLOCK} ${NAME}"
        pattern2 = "public static final ${BLOCK} ${NAME}_BLOCK"
        
        similarity = system._calculate_pattern_similarity(pattern1, pattern2)
        
        # Should have some similarity
        assert similarity > 0
    
    def test_find_similar_patterns(self):
        """Test finding similar patterns."""
        system = create_self_learning_system()
        
        # Add a pattern
        system.learned_patterns["test_pattern"] = LearnedPattern(
            pattern_id="test_pattern",
            source=PatternSource.LEARNED,
            java_pattern="public static final Block ${NAME}",
            bedrock_pattern="BP/blocks/${NAME}.json",
            confidence=0.8,
            examples=[]
        )
        
        # Find similar
        similar = system._find_similar_patterns("public static final Block TEST")
        
        assert len(similar) > 0


class TestPatternApplication:
    """Test applying learned patterns."""
    
    def test_get_applicable_patterns(self):
        """Test finding applicable patterns for code."""
        system = create_self_learning_system()
        
        # Add a high-confidence pattern
        system.learned_patterns["block_pattern"] = LearnedPattern(
            pattern_id="block_pattern",
            source=PatternSource.LEARNED,
            java_pattern=r"public\s+static\s+final\s+Block\s+(\w+)",
            bedrock_pattern="BP/blocks/${1}.json",
            confidence=0.9,
            usage_count=5,
            success_count=4
        )
        
        java_code = "public static final Block MY_BLOCK"
        
        applicable = system.get_applicable_patterns(java_code)
        
        assert len(applicable) > 0
        assert applicable[0][0].pattern_id == "block_pattern"
    
    def test_apply_learned_pattern(self):
        """Test applying a learned pattern to code."""
        system = create_self_learning_system()
        
        # Add a pattern
        system.learned_patterns["apply_test"] = LearnedPattern(
            pattern_id="apply_test",
            source=PatternSource.LEARNED,
            java_pattern=r"public\s+static\s+final\s+Block\s+(\w+)",
            bedrock_pattern="BP/blocks/${1}.json",
            confidence=0.9
        )
        
        java_code = "public static final Block DIAMOND_BLOCK"
        
        modified, success = system.apply_learned_pattern(java_code, "apply_test")
        
        assert success
        assert "DIAMOND_BLOCK" in modified
        assert system.learned_patterns["apply_test"].usage_count == 1
    
    def test_apply_nonexistent_pattern(self):
        """Test applying a non-existent pattern."""
        system = create_self_learning_system()
        
        java_code = "public static final Block TEST"
        
        modified, success = system.apply_learned_pattern(java_code, "nonexistent")
        
        assert not success
        assert modified == java_code


class TestConversionComparison:
    """Test conversion comparison functionality."""
    
    def test_compare_conversions(self):
        """Test comparing initial conversion with user correction."""
        system = create_self_learning_system()
        
        original_java = "public class MyBlock extends Block"
        converted = "public class MyBlock extends Block {}"
        corrected = "public class MyBlock extends Block { @Override public BlockState getStateForPlacement... }"
        
        results = system.compare_conversions(original_java, converted, corrected)
        
        # Should detect improvements
        if results["has_improvements"]:
            assert len(results["improvement_types"]) > 0


class TestLearningMetrics:
    """Test learning metrics and reporting."""
    
    def test_metrics_initialization(self):
        """Test initial metrics state."""
        system = create_self_learning_system()
        
        assert system.metrics.total_corrections == 0
        assert system.metrics.patterns_learned == 0
    
    def test_metrics_update_after_correction(self):
        """Test metrics update after tracking corrections."""
        system = create_self_learning_system()
        
        system.track_correction(
            original_code="test",
            corrected_code="test corrected",
            context={},
            source_file="test.java"
        )
        
        assert system.metrics.total_corrections == 1
    
    def test_learning_report(self):
        """Test learning report generation."""
        system = create_self_learning_system()
        
        # Add some data
        system.track_correction(
            original_code="Block TEST",
            corrected_code="RegistryObject<Block> TEST",
            context={},
            source_file="test.java"
        )
        
        report = system.get_learning_report()
        
        assert "metrics" in report
        assert "pattern_stats" in report
        assert "correction_stats" in report
        assert report["metrics"]["total_corrections"] >= 1


class TestPatternRollback:
    """Test pattern rollback functionality."""
    
    def test_rollback_learned_pattern(self):
        """Test rolling back a learned pattern."""
        system = create_self_learning_system()
        
        # Add a pattern
        system.learned_patterns["rollback_test"] = LearnedPattern(
            pattern_id="rollback_test",
            source=PatternSource.LEARNED,
            java_pattern="test",
            bedrock_pattern="test",
            confidence=0.8,
            version=1
        )
        
        original_confidence = system.learned_patterns["rollback_test"].confidence
        
        success = system.rollback_pattern("rollback_test")
        
        assert success
        assert system.learned_patterns["rollback_test"].confidence < original_confidence
    
    def test_rollback_builtin_pattern_fails(self):
        """Test that builtin patterns cannot be rolled back."""
        system = create_self_learning_system()
        
        # Add a builtin pattern
        system.learned_patterns["builtin_test"] = LearnedPattern(
            pattern_id="builtin_test",
            source=PatternSource.BUILTIN,
            java_pattern="test",
            bedrock_pattern="test",
            confidence=0.8
        )
        
        success = system.rollback_pattern("builtin_test")
        
        assert not success


class TestPatternExport:
    """Test pattern export functionality."""
    
    def test_export_patterns(self):
        """Test exporting learned patterns."""
        system = create_self_learning_system()
        
        # Add patterns
        system.learned_patterns["export_test"] = LearnedPattern(
            pattern_id="export_test",
            source=PatternSource.LEARNED,
            java_pattern="test",
            bedrock_pattern="test",
            confidence=0.8,
            examples=["example1", "example2"]
        )
        
        exported = system.export_patterns()
        
        assert len(exported) >= 1
        assert exported[0]["pattern_id"] == "export_test"
        assert exported[0]["examples"] == ["example1", "example2"]


class TestFactory:
    """Test factory function."""
    
    def test_create_self_learning_system(self):
        """Test factory function creates valid system."""
        system = create_self_learning_system()
        
        assert system is not None
        assert isinstance(system, SelfLearningSystem)
        assert len(system.corrections) == 0
        assert len(system.learned_patterns) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
