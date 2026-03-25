"""
Cost Tracker for AI Model Usage

Track and optimize costs across different models.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class CostRecord:
    """Single cost record."""

    model: str
    cost: float
    tokens_in: int
    tokens_out: int
    timestamp: datetime = field(default_factory=datetime.utcnow)
    duration_ms: float = 0.0


class CostTracker:
    """Track and analyze AI model costs."""

    # Cost per 1M tokens (as of 2024)
    MODEL_COSTS = {
        "modal": {"in": 0.0, "out": 0.0},  # GPU time, not token-based
        "deepseek": {"in": 0.14, "out": 0.28},
        "ollama": {"in": 0.0, "out": 0.0},  # Free
        "gpt4": {"in": 10.0, "out": 30.0},
        "claude": {"in": 3.0, "out": 15.0},
    }

    # Average cost per conversion (for Modal GPU time)
    MODAL_COST_PER_CONVERSION = 0.05  # ~$0.05 per conversion

    def __init__(self):
        self._records: List[CostRecord] = []
        self._daily_budget = 50.0  # $50/day budget
        self._budget_alerts: List[str] = []

    def record(
        self,
        model: str,
        tokens_in: int = 0,
        tokens_out: int = 0,
        duration_ms: float = 0.0,
        cost: Optional[float] = None,
    ):
        """
        Record a translation request.

        Args:
            model: Model name (modal, deepseek, ollama, etc.)
            tokens_in: Input tokens
            tokens_out: Output tokens
            duration_ms: Request duration in milliseconds
            cost: Optional explicit cost (uses model rates if not provided)
        """
        if cost is None:
            if model == "modal":
                cost = self.MODAL_COST_PER_CONVERSION
            else:
                rates = self.MODEL_COSTS.get(model, {"in": 0, "out": 0})
                cost = (tokens_in / 1_000_000) * rates["in"] + (tokens_out / 1_000_000) * rates[
                    "out"
                ]

        record = CostRecord(
            model=model,
            cost=cost,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            duration_ms=duration_ms,
        )
        self._records.append(record)

        # Check budget
        daily_cost = self.get_daily_cost()
        if daily_cost > self._daily_budget * 0.8:
            alert = f"Warning: Daily cost ${daily_cost:.2f} exceeds 80% of budget"
            if alert not in self._budget_alerts:
                self._budget_alerts.append(alert)
                logger.warning(alert)

        logger.debug(f"Cost recorded: {model} - ${cost:.4f}")

    def get_daily_cost(self, date: Optional[datetime] = None) -> float:
        """Get total cost for a specific date (or today)."""
        if date is None:
            date = datetime.utcnow()

        return sum(r.cost for r in self._records if r.timestamp.date() == date.date())

    def get_weekly_cost(self) -> float:
        """Get total cost for the last 7 days."""
        week_ago = datetime.utcnow() - timedelta(days=7)
        return sum(r.cost for r in self._records if r.timestamp >= week_ago)

    def get_monthly_cost(self) -> float:
        """Get total cost for the last 30 days."""
        month_ago = datetime.utcnow() - timedelta(days=30)
        return sum(r.cost for r in self._records if r.timestamp >= month_ago)

    def get_average_cost_per_conversion(self) -> float:
        """Get average cost per conversion."""
        if not self._records:
            return 0.0
        return sum(r.cost for r in self._records) / len(self._records)

    def get_model_breakdown(self) -> Dict[str, dict]:
        """Get cost breakdown by model."""
        breakdown = {}

        for model in self.MODEL_COSTS.keys():
            model_records = [r for r in self._records if r.model == model]
            if model_records:
                breakdown[model] = {
                    "count": len(model_records),
                    "total_cost": sum(r.cost for r in model_records),
                    "avg_cost": sum(r.cost for r in model_records) / len(model_records),
                    "total_tokens_in": sum(r.tokens_in for r in model_records),
                    "total_tokens_out": sum(r.tokens_out for r in model_records),
                }

        return breakdown

    def get_usage_stats(self) -> dict:
        """Get comprehensive usage statistics."""
        total_cost = sum(r.cost for r in self._records)
        total_conversions = len(self._records)

        return {
            "total_conversions": total_conversions,
            "total_cost": total_cost,
            "average_cost_per_conversion": (
                total_cost / total_conversions if total_conversions > 0 else 0
            ),
            "daily_cost": self.get_daily_cost(),
            "weekly_cost": self.get_weekly_cost(),
            "monthly_cost": self.get_monthly_cost(),
            "model_breakdown": self.get_model_breakdown(),
            "budget_remaining": self._daily_budget - self.get_daily_cost(),
            "budget_alerts": self._budget_alerts,
        }

    def get_optimization_recommendations(self) -> List[str]:
        """Get cost optimization recommendations."""
        recommendations = []

        breakdown = self.get_model_breakdown()

        # Check if using expensive models too much
        expensive_models = ["gpt4", "claude"]
        for model in expensive_models:
            if model in breakdown:
                pct = breakdown[model]["count"] / len(self._records) * 100
                if pct > 5:
                    recommendations.append(
                        f"Reduce {model} usage ({pct:.1f}% of conversions). "
                        f"Consider using Modal or DeepSeek for cost savings."
                    )

        # Check daily budget
        daily_cost = self.get_daily_cost()
        if daily_cost > self._daily_budget * 0.9:
            recommendations.append(
                f"Approaching daily budget limit (${daily_cost:.2f}/${self._daily_budget:.2f}). "
                "Consider reducing usage or increasing budget."
            )

        # Check average cost
        avg_cost = self.get_average_cost_per_conversion()
        if avg_cost > 0.20:
            recommendations.append(
                f"Average cost per conversion (${avg_cost:.2f}) is high. "
                "Target: <$0.10. Use Modal (CodeT5+) for most conversions."
            )

        return recommendations

    def export_report(self) -> str:
        """Export cost report as markdown."""
        stats = self.get_usage_stats()

        report = f"""# AI Model Cost Report

**Generated**: {datetime.utcnow().isoformat()}

## Summary

| Metric | Value |
|--------|-------|
| Total Conversions | {stats["total_conversions"]} |
| Total Cost | ${stats["total_cost"]:.2f} |
| Avg Cost/Conversion | ${stats["average_cost_per_conversion"]:.4f} |
| Daily Cost | ${stats["daily_cost"]:.2f} |
| Weekly Cost | ${stats["weekly_cost"]:.2f} |
| Monthly Cost | ${stats["monthly_cost"]:.2f} |

## Model Breakdown

| Model | Count | Total Cost | Avg Cost |
|-------|-------|------------|----------|
"""

        for model, data in stats["model_breakdown"].items():
            report += f"| {model} | {data['count']} | ${data['total_cost']:.2f} | ${data['avg_cost']:.4f} |\n"

        report += f"""
## Budget Status

- Daily Budget: ${self._daily_budget:.2f}
- Spent Today: ${stats["daily_cost"]:.2f}
- Remaining: ${stats["budget_remaining"]:.2f}

## Recommendations

"""

        recommendations = self.get_optimization_recommendations()
        if recommendations:
            for rec in recommendations:
                report += f"- {rec}\n"
        else:
            report += "- No recommendations at this time\n"

        return report


# Singleton instance
_tracker_instance = None


def get_cost_tracker() -> CostTracker:
    """Get or create cost tracker singleton."""
    global _tracker_instance
    if _tracker_instance is None:
        _tracker_instance = CostTracker()
    return _tracker_instance
