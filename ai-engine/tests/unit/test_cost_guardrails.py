"""
Tests for LLM Cost Monitoring and Budget Guardrails
Issue: #1205 - Pre-beta: LLM cost monitoring, per-conversion cost tracking, and budget guardrails
"""

import pytest



class TestBudgetGuardrails:
    """Test budget guardrails functionality"""

    def test_budget_config_defaults(self):
        """Test BudgetConfig default values"""
        from utils.cost_guardrails import BudgetConfig

        config = BudgetConfig()
        assert config.per_conversion_budget == 5.0
        assert config.daily_budget == 50.0
        assert config.monthly_budget == 500.0
        assert config.warn_threshold == 0.8
        assert config.block_threshold == 1.0
        assert config.enable_per_conversion_limit is True

    def test_conversion_cost_tracking(self):
        """Test tracking costs for a conversion"""
        from utils.cost_guardrails import BudgetGuardrails, BudgetConfig

        guardrails = BudgetGuardrails(BudgetConfig(per_conversion_budget=10.0))

        conversion_id = "test_conversion_1"
        cost = guardrails.start_conversion_tracking(conversion_id)

        assert cost.conversion_id == conversion_id
        assert cost.total_cost == 0.0
        assert cost.llm_calls == 0
        assert cost.blocked is False

    def test_per_conversion_budget_limit(self):
        """Test that per-conversion budget limits are enforced"""
        from utils.cost_guardrails import BudgetGuardrails, BudgetConfig, BudgetAction

        config = BudgetConfig(per_conversion_budget=1.0, enable_per_conversion_limit=True)
        guardrails = BudgetGuardrails(config)

        conversion_id = "test_conversion_2"
        guardrails.start_conversion_tracking(conversion_id)

        result = guardrails.check_budget_available(conversion_id, estimated_cost=0.5)
        assert result["allowed"] is True

        result = guardrails.check_budget_available("new_conversion_estimate_test", estimated_cost=1.5)
        assert result["allowed"] is False
        assert result["action"] == BudgetAction.BLOCK.value

    def test_record_llm_call(self):
        """Test recording LLM calls"""
        from utils.cost_guardrails import BudgetGuardrails, BudgetConfig

        config = BudgetConfig(per_conversion_budget=10.0)
        guardrails = BudgetGuardrails(config)

        conversion_id = "test_conversion_3"
        guardrails.start_conversion_tracking(conversion_id)

        cost = guardrails.record_llm_call(
            conversion_id=conversion_id,
            model="gpt-4",
            provider="openai",
            input_tokens=1000,
            output_tokens=500,
            duration=1.5,
            cost=0.05,
        )

        assert cost.llm_calls == 1
        assert cost.input_tokens == 1000
        assert cost.output_tokens == 500
        assert cost.total_cost > 0

    def test_budget_status(self):
        """Test getting budget status"""
        from utils.cost_guardrails import BudgetGuardrails, BudgetConfig

        config = BudgetConfig(daily_budget=100.0)
        guardrails = BudgetGuardrails(config)

        status = guardrails.get_budget_status()

        assert "daily" in status
        assert "monthly" in status
        assert "active_conversions" in status
        assert status["daily"]["budget"] == 100.0


class TestCostMiddleware:
    """Test cost budget middleware"""

    def test_set_conversion(self):
        """Test setting conversion ID for tracking"""
        from utils.cost_guardrails import CostBudgetMiddleware, BudgetGuardrails

        guardrails = BudgetGuardrails()
        middleware = CostBudgetMiddleware(guardrails)

        middleware.set_conversion("test_conv_1")
        assert middleware._conversion_id == "test_conv_1"

    def test_clear_conversion(self):
        """Test clearing conversion ID"""
        from utils.cost_guardrails import CostBudgetMiddleware, BudgetGuardrails

        guardrails = BudgetGuardrails()
        middleware = CostBudgetMiddleware(guardrails)

        middleware.set_conversion("test_conv_1")
        middleware.clear_conversion()
        assert middleware._conversion_id is None


class TestEstimateCost:
    """Test cost estimation"""

    def test_estimate_call_cost(self):
        """Test estimating LLM call cost"""
        from utils.cost_guardrails import estimate_call_cost

        cost = estimate_call_cost("gpt-4", 1000, 500)
        assert cost > 0

        cost_free = estimate_call_cost("local", 1000, 500)
        assert cost_free == 0.0


class TestGlobalFunctions:
    """Test global helper functions"""

    def test_start_conversion_cost_tracking(self):
        """Test starting cost tracking via global function"""
        from utils.cost_guardrails import (
            start_conversion_cost_tracking,
            get_budget_guardrails,
        )

        guardrails = get_budget_guardrails()
        guardrails.reset_all()

        cost = start_conversion_cost_tracking("test_global_1")
        assert cost.conversion_id == "test_global_1"
        assert cost.total_cost == 0.0

    def test_check_conversion_budget(self):
        """Test checking budget via global function"""
        from utils.cost_guardrails import check_conversion_budget

        result = check_conversion_budget("test_budget_1", estimated_cost=0.5)
        assert "allowed" in result
        assert "reason" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])