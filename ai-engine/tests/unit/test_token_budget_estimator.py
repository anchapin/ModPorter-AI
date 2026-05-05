"""
Unit tests for TokenBudgetEstimator

Tests pre-conversion estimation, per-phase tracking, budget checking,
and cost report generation for B2B transparency.

Issue: #1188 - Implement per-conversion token budget prediction and cost monitoring
"""

import pytest
from agent_metrics.token_budget_estimator import (
    TokenBudgetEstimator,
    ModMetadata,
    EstimatedTokenUsage,
    PhaseEstimate,
    ConversionPhase,
    ConversionCostReport,
    estimate_conversion_cost,
    get_estimator,
)


class TestModMetadata:
    """Tests for ModMetadata dataclass"""

    def test_default_values(self):
        """Test default metadata values"""
        metadata = ModMetadata()
        assert metadata.file_count == 0
        assert metadata.total_loc == 0
        assert metadata.class_count == 0
        assert metadata.max_class_depth == 0
        assert metadata.dependency_count == 0

    def test_custom_values(self):
        """Test creating metadata with custom values"""
        metadata = ModMetadata(
            file_count=50,
            total_loc=2500,
            class_count=100,
            max_class_depth=6,
            dependency_count=3,
            has_gui=True,
            has_entities=True,
        )
        assert metadata.file_count == 50
        assert metadata.total_loc == 2500
        assert metadata.class_count == 100
        assert metadata.has_gui is True
        assert metadata.has_entities is True


class TestPhaseEstimate:
    """Tests for PhaseEstimate dataclass"""

    def test_total_tokens(self):
        """Test total_tokens property"""
        estimate = PhaseEstimate(
            phase=ConversionPhase.ANALYSIS,
            input_tokens=1000,
            output_tokens=500,
        )
        assert estimate.total_tokens == 1500

    def test_confidence_defaults(self):
        """Test confidence bounds"""
        estimate = PhaseEstimate(
            phase=ConversionPhase.TRANSLATION,
            input_tokens=2000,
            output_tokens=1000,
        )
        assert estimate.confidence_low == 0.8
        assert estimate.confidence_high == 1.2


class TestEstimatedTokenUsage:
    """Tests for EstimatedTokenUsage dataclass"""

    def test_to_dict(self):
        """Test dictionary conversion"""
        estimate = EstimatedTokenUsage(
            total_input_tokens=10000,
            total_output_tokens=5000,
            estimated_cost_usd=0.25,
            model_used="gpt-4o",
            complexity_tier="moderate",
        )
        result = estimate.to_dict()

        assert result["total_input_tokens"] == 10000
        assert result["total_output_tokens"] == 5000
        assert result["total_tokens"] == 15000
        assert result["estimated_cost_usd"] == 0.25
        assert result["model_used"] == "gpt-4o"
        assert result["complexity_tier"] == "moderate"
        assert "by_phase" in result
        assert "confidence_interval" in result


class TestTokenBudgetEstimator:
    """Tests for TokenBudgetEstimator class"""

    def test_initialization(self):
        """Test estimator initialization"""
        estimator = TokenBudgetEstimator()
        assert estimator.default_model == "gpt-4o"
        assert estimator.cost_alert_threshold == 5.0

    def test_custom_initialization(self):
        """Test estimator with custom settings"""
        estimator = TokenBudgetEstimator(
            default_model="gpt-4",
            cost_alert_threshold=10.0,
        )
        assert estimator.default_model == "gpt-4"
        assert estimator.cost_alert_threshold == 10.0

    def test_determine_complexity_tier_simple(self):
        """Test simple complexity tier detection"""
        estimator = TokenBudgetEstimator()
        metadata = ModMetadata(total_loc=300, class_count=15)

        tier = estimator._determine_complexity_tier(metadata)
        assert tier == "simple"

    def test_determine_complexity_tier_moderate(self):
        """Test moderate complexity tier detection"""
        estimator = TokenBudgetEstimator()
        metadata = ModMetadata(total_loc=1500, class_count=80)

        tier = estimator._determine_complexity_tier(metadata)
        assert tier == "moderate"

    def test_determine_complexity_tier_complex(self):
        """Test complex complexity tier detection"""
        estimator = TokenBudgetEstimator()
        metadata = ModMetadata(total_loc=4000, class_count=200)

        tier = estimator._determine_complexity_tier(metadata)
        assert tier == "complex"

    def test_determine_complexity_tier_very_complex(self):
        """Test very complex tier detection"""
        estimator = TokenBudgetEstimator()
        metadata = ModMetadata(total_loc=10000, class_count=500)

        tier = estimator._determine_complexity_tier(metadata)
        assert tier == "very_complex"

    def test_estimate_basic(self):
        """Test basic estimation"""
        estimator = TokenBudgetEstimator()
        metadata = ModMetadata(
            file_count=30,
            total_loc=1000,
            class_count=50,
            max_class_depth=4,
        )

        result = estimator.estimate(metadata)

        assert result.total_input_tokens > 0
        assert result.total_output_tokens > 0
        assert result.estimated_cost_usd > 0
        assert result.complexity_tier in ["simple", "moderate", "complex", "very_complex"]
        assert len(result.by_phase) == 4

    def test_estimate_phases_present(self):
        """Test all phases are represented in estimate"""
        estimator = TokenBudgetEstimator()
        metadata = ModMetadata(total_loc=500, class_count=20)

        result = estimator.estimate(metadata)

        for phase in ConversionPhase:
            assert phase in result.by_phase

    def test_estimate_cost_calculation(self):
        """Test cost is calculated correctly"""
        estimator = TokenBudgetEstimator()
        metadata = ModMetadata(total_loc=100, class_count=5)

        result = estimator.estimate(metadata)

        from agent_metrics.llm_usage_tracker import estimate_cost

        expected = estimate_cost(
            result.model_used,
            result.total_input_tokens,
            result.total_output_tokens,
        )
        assert abs(result.estimated_cost_usd - expected) < 0.0001

    def test_check_budget_allow(self):
        """Test budget check when within 80%"""
        estimator = TokenBudgetEstimator(cost_alert_threshold=5.0)

        result = estimator.check_budget(3.0)

        assert result["within_budget"] is True
        assert result["budget_action"] == "allow"

    def test_check_budget_warn(self):
        """Test budget check when approaching limit"""
        estimator = TokenBudgetEstimator(cost_alert_threshold=5.0)

        result = estimator.check_budget(4.5)

        assert result["within_budget"] is True
        assert result["budget_action"] == "warn"

    def test_check_budget_block(self):
        """Test budget check when exceeding limit"""
        estimator = TokenBudgetEstimator(cost_alert_threshold=5.0)

        result = estimator.check_budget(7.0)

        assert result["within_budget"] is False
        assert result["budget_action"] == "block"

    def test_check_budget_custom_limit(self):
        """Test budget check with custom limit"""
        estimator = TokenBudgetEstimator(cost_alert_threshold=5.0)

        result = estimator.check_budget(4.0, budget_limit=3.0)

        assert result["within_budget"] is False

    def test_start_phase_tracking(self):
        """Test starting phase tracking"""
        estimator = TokenBudgetEstimator()
        estimator.start_phase_tracking("test_conv_123")

        assert "test_conv_123" in estimator._phase_trackers
        for phase in ConversionPhase:
            assert estimator._phase_trackers["test_conv_123"][phase] == 0

    def test_record_phase_tokens(self):
        """Test recording tokens for a phase"""
        estimator = TokenBudgetEstimator()
        estimator.start_phase_tracking("test_conv_456")

        estimator.record_phase_tokens(
            "test_conv_456",
            ConversionPhase.ANALYSIS,
            input_tokens=1000,
            output_tokens=500,
        )

        assert estimator._phase_trackers["test_conv_456"][ConversionPhase.ANALYSIS] == 1500

    def test_get_phase_totals(self):
        """Test getting phase totals"""
        estimator = TokenBudgetEstimator()
        estimator.start_phase_tracking("test_conv_789")

        estimator.record_phase_tokens("test_conv_789", ConversionPhase.ANALYSIS, 1000, 500)
        estimator.record_phase_tokens("test_conv_789", ConversionPhase.TRANSLATION, 2000, 1000)

        totals = estimator.get_phase_totals("test_conv_789")

        assert totals[ConversionPhase.ANALYSIS] == 1500
        assert totals[ConversionPhase.TRANSLATION] == 3000
        assert totals[ConversionPhase.MAPPING] == 0

    def test_generate_cost_report(self):
        """Test generating post-conversion cost report"""
        estimator = TokenBudgetEstimator()
        metadata = ModMetadata(total_loc=1000, class_count=50)
        estimated = estimator.estimate(metadata)

        actual_by_phase = {
            ConversionPhase.ANALYSIS: {"input_tokens": 3000, "output_tokens": 1500},
            ConversionPhase.MAPPING: {"input_tokens": 2000, "output_tokens": 1000},
            ConversionPhase.TRANSLATION: {"input_tokens": 5000, "output_tokens": 2500},
            ConversionPhase.QA: {"input_tokens": 1500, "output_tokens": 800},
        }

        report = estimator.generate_cost_report(
            conversion_id="test_conv_report",
            estimated=estimated,
            actual_by_phase=actual_by_phase,
            duration_seconds=120.0,
            budget_limit=2.0,
        )

        assert report.conversion_id == "test_conv_report"
        assert report.actual_input_tokens > 0
        assert report.actual_output_tokens > 0
        assert report.duration_seconds == 120.0
        assert report.budget_limit_usd == 2.0

    def test_generate_cost_report_over_budget(self):
        """Test cost report when conversion exceeds budget"""
        estimator = TokenBudgetEstimator()
        metadata = ModMetadata(total_loc=5000, class_count=200)
        estimated = estimator.estimate(metadata)

        actual_by_phase = {
            ConversionPhase.ANALYSIS: {"input_tokens": 100000, "output_tokens": 50000},
            ConversionPhase.MAPPING: {"input_tokens": 80000, "output_tokens": 40000},
            ConversionPhase.TRANSLATION: {"input_tokens": 150000, "output_tokens": 80000},
            ConversionPhase.QA: {"input_tokens": 50000, "output_tokens": 25000},
        }

        report = estimator.generate_cost_report(
            conversion_id="over_budget_conv",
            estimated=estimated,
            actual_by_phase=actual_by_phase,
            duration_seconds=300.0,
            budget_limit=1.0,
        )

        assert report.budget_exceeded is True
        assert report.over_budget_by > 0

    def test_accuracy_stats_empty(self):
        """Test accuracy stats with no historical data"""
        estimator = TokenBudgetEstimator()

        stats = estimator.get_accuracy_stats()

        assert "message" in stats

    def test_accuracy_stats_with_data(self):
        """Test accuracy stats after recording historical data"""
        estimator = TokenBudgetEstimator()
        metadata = ModMetadata(total_loc=500, class_count=20)
        estimated = estimator.estimate(metadata)

        estimator._record_historical(estimated, 15000, "hist_conv_1")
        estimator._record_historical(estimated, 14000, "hist_conv_2")
        estimator._record_historical(estimated, 16000, "hist_conv_3")

        stats = estimator.get_accuracy_stats()

        assert "sample_count" in stats
        assert stats["sample_count"] == 3
        assert stats["avg_ratio"] > 0


class TestGlobalEstimator:
    """Tests for global estimator functions"""

    def test_get_estimator_singleton(self):
        """Test get_estimator returns singleton"""
        est1 = get_estimator()
        est2 = get_estimator()

        assert est1 is est2

    def test_estimate_conversion_cost_structure(self):
        """Test estimate_conversion_cost returns expected structure"""
        result = estimate_conversion_cost("/nonexistent/path.jar")

        assert "metadata" in result
        assert "estimate" in result
        assert "budget_check" in result

        assert "file_count" in result["metadata"]
        assert "total_loc" in result["metadata"]
        assert "class_count" in result["metadata"]
        assert "complexity_tier" in result["metadata"]

        assert "total_tokens" in result["estimate"]
        assert "estimated_cost_usd" in result["estimate"]
        assert "confidence_interval" in result["estimate"]


class TestConversionCostReport:
    """Tests for ConversionCostReport"""

    def test_cost_vs_estimate_ratio(self):
        """Test cost vs estimate ratio calculation"""
        estimator = TokenBudgetEstimator()
        metadata = ModMetadata(total_loc=500, class_count=25)
        estimated = estimator.estimate(metadata)

        report = ConversionCostReport(
            conversion_id="ratio_test",
            estimated=estimated,
            actual_input_tokens=8000,
            actual_output_tokens=4000,
            actual_cost_usd=estimated.estimated_cost_usd * 0.9,
        )

        assert abs(report.cost_vs_estimate_ratio - 0.9) < 0.01

    def test_actual_total_tokens(self):
        """Test actual total tokens property"""
        estimator = TokenBudgetEstimator()
        metadata = ModMetadata(total_loc=500, class_count=25)
        estimated = estimator.estimate(metadata)

        report = ConversionCostReport(
            conversion_id="total_tokens_test",
            estimated=estimated,
            actual_input_tokens=10000,
            actual_output_tokens=5000,
            actual_cost_usd=0.15,
        )

        assert report.actual_total_tokens == 15000

    def test_to_dict(self):
        """Test dictionary conversion"""
        estimator = TokenBudgetEstimator()
        metadata = ModMetadata(total_loc=500, class_count=25)
        estimated = estimator.estimate(metadata)

        report = ConversionCostReport(
            conversion_id="dict_test",
            estimated=estimated,
            actual_input_tokens=8000,
            actual_output_tokens=4000,
            actual_cost_usd=0.12,
            duration_seconds=60.0,
        )

        result = report.to_dict()

        assert result["conversion_id"] == "dict_test"
        assert "estimated" in result
        assert "actual" in result
        assert result["budget_exceeded"] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])