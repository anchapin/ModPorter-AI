"""
Tests for Steering Evaluation module.
"""

import pytest

from steering.evaluation import (
    SteeringEvaluator,
    IdiomCategory,
    IdiomMetrics,
    IdiomPattern,
    EvaluationResult,
    evaluate_steering_effectiveness,
    JAVA_IDIOM_PATTERNS,
)


class TestSteeringEvaluator:
    """Tests for SteeringEvaluator class."""

    def test_init(self):
        """Test evaluator initialization."""
        evaluator = SteeringEvaluator()
        assert evaluator._idiom_detector is not None
        assert len(evaluator._patterns) > 0

    def test_evaluate_generation_no_steering(self):
        """Test evaluation without steering."""
        evaluator = SteeringEvaluator()
        java_code = "public class MyItem extends Item { }"
        bedrock_code = "const myItem = { name: 'test' };"

        result = evaluator.evaluate_generation(
            original_java=java_code,
            generated_bedrock=bedrock_code,
            steering_applied=False,
        )

        assert isinstance(result, EvaluationResult)
        assert result.steering_applied is False
        assert result.overall_score >= 0

    def test_evaluate_generation_with_steering(self):
        """Test evaluation with steering applied."""
        evaluator = SteeringEvaluator()
        java_code = """
        @SubscribeEvent
        public class MyBlock extends Block {
            Minecraft.getInstance();
        }
        """
        bedrock_code = """
        import { world } from '@minecraft/server';
        world.afterEvents.chatSend.subscribe((event) => {
            // Bedrock idioms
        });
        """

        result = evaluator.evaluate_generation(
            original_java=java_code,
            generated_bedrock=bedrock_code,
            steering_applied=True,
            steering_features=[1008, 1003],
        )

        assert result.steering_applied is True
        assert len(result.feature_ids) == 2

    def test_suppression_metrics(self):
        """Test that suppression metrics are calculated correctly."""
        evaluator = SteeringEvaluator()
        java_code = "public class Test extends Item { @SubscribeEvent }"
        bedrock_code = "const test = {};"  # No Java idioms

        result = evaluator.evaluate_generation(
            original_java=java_code,
            generated_bedrock=bedrock_code,
        )

        # Should have high suppression since Java idioms were suppressed
        assert result.idioms_suppressed >= 2

    def test_category_metrics(self):
        """Test per-category metrics calculation."""
        evaluator = SteeringEvaluator()
        java_code = """
        @SubscribeEvent
        public class Test extends Item {
            Minecraft.getInstance();
        }
        """
        bedrock_code = "const test = {};"

        result = evaluator.evaluate_generation(
            original_java=java_code,
            generated_bedrock=bedrock_code,
        )

        assert len(result.category_metrics) > 0
        forge_metrics = next(
            (m for m in result.category_metrics if m.category == IdiomCategory.FORGE_PATTERN),
            None
        )
        assert forge_metrics is not None

    def test_overall_score_calculation(self):
        """Test overall score is between 0 and 100."""
        evaluator = SteeringEvaluator()

        result = evaluator.evaluate_generation(
            original_java="",
            generated_bedrock="",
        )

        assert 0 <= result.overall_score <= 100

    def test_warnings_generated(self):
        """Test that warnings are generated for low scores."""
        evaluator = SteeringEvaluator(
            config={"min_quality_score": 90.0}
        )
        java_code = "@SubscribeEvent public class Test extends Item { }"
        bedrock_code = "@SubscribeEvent public class Test extends Item { }"  # Same = no suppression

        result = evaluator.evaluate_generation(
            original_java=java_code,
            generated_bedrock=bedrock_code,
        )

        assert len(result.warnings) > 0

    def test_to_dict(self):
        """Test serialization to dict."""
        evaluator = SteeringEvaluator()
        result = evaluator.evaluate_generation(
            original_java="public class Test extends Item { }",
            generated_bedrock="const test = {};",
        )

        d = result.to_dict()
        assert "overall_score" in d
        assert "category_metrics" in d
        assert "idioms_suppressed" in d

    def test_to_json(self):
        """Test serialization to JSON."""
        evaluator = SteeringEvaluator()
        result = evaluator.evaluate_generation(
            original_java="public class Test { }",
            generated_bedrock="const test = {};",
        )

        json_str = result.to_json()
        assert "overall_score" in json_str


class TestEvaluateSteeringEffectiveness:
    """Tests for the evaluate_steering_effectiveness convenience function."""

    def test_basic_evaluation(self):
        """Test basic evaluation works."""
        result = evaluate_steering_effectiveness(
            java_code="public class Test extends Item { }",
            bedrock_code="const test = {};",
            steering_applied=True,
        )
        assert result.overall_score >= 0

    def test_steering_applied_flag(self):
        """Test steering applied flag is preserved."""
        result = evaluate_steering_effectiveness(
            java_code="public class Test { }",
            bedrock_code="const test = {};",
            steering_applied=True,
        )
        assert result.steering_applied is True

        result2 = evaluate_steering_effectiveness(
            java_code="public class Test { }",
            bedrock_code="const test = {};",
            steering_applied=False,
        )
        assert result2.steering_applied is False


class TestIdiomMetrics:
    """Tests for IdiomMetrics dataclass."""

    def test_to_dict(self):
        """Test IdiomMetrics serialization."""
        metrics = IdiomMetrics(
            category=IdiomCategory.FORGE_PATTERN,
            detected_count=5,
            suppression_rate=0.8,
        )
        d = metrics.to_dict()
        assert d["category"] == "forge_pattern"
        assert d["detected_count"] == 5
        assert d["suppression_rate"] == 0.8


class TestIdiomPatterns:
    """Tests for JAVA_IDIOM_PATTERNS."""

    def test_patterns_exist(self):
        """Test that pattern list is not empty."""
        assert len(JAVA_IDIOM_PATTERNS) > 0

    def test_pattern_structure(self):
        """Test each pattern has required fields."""
        for pattern in JAVA_IDIOM_PATTERNS:
            assert isinstance(pattern.name, str)
            assert isinstance(pattern.category, IdiomCategory)
            assert isinstance(pattern.pattern, str)
            assert isinstance(pattern.replacement, str)

    def test_pattern_categories(self):
        """Test patterns cover multiple categories."""
        categories = set(p.category for p in JAVA_IDIOM_PATTERNS)
        assert IdiomCategory.FORGE_PATTERN in categories
        assert IdiomCategory.CLASS_PATTERN in categories
        assert IdiomCategory.API_PATTERN in categories


class TestBatchEvaluation:
    """Tests for batch evaluation."""

    def test_evaluate_batch(self):
        """Test batch evaluation of multiple generations."""
        evaluator = SteeringEvaluator()
        evaluations = [
            ("public class A extends Item { }", "const a = {};", True),
            ("public class B extends Block { }", "const b = {};", True),
            ("public class C { }", "const c = {};", False),
        ]

        results = evaluator.evaluate_batch(evaluations)

        assert "total_evaluations" in results
        assert results["total_evaluations"] == 3
        assert "average_score" in results
        assert "category_aggregates" in results