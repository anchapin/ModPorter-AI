"""Conversion-report formatter (issue #1201).

Replaces ``crew.conversion_crew.PortkitConversionCrew._format_conversion_report``
and ``_create_failure_response`` with framework-agnostic helpers that consume
the LangGraph ``ConversionState`` instead of the legacy ``CrewOutput``.

The output shape preserves the PRD Feature 3 contract so the frontend and
``backend.AIEngineClient`` continue to deserialize results unchanged.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from models.smart_assumptions import AssumptionReport, ConversionPlanComponent

logger = logging.getLogger(__name__)


def format_conversion_report(
    state: Dict[str, Any],
    plan_components: Optional[List[ConversionPlanComponent]] = None,
    smart_assumption_engine: Optional[Any] = None,
) -> Dict[str, Any]:
    """Build the PRD Feature 3 conversion report from a LangGraph state dict."""

    assumption_report_data: List[Dict[str, Any]] = []
    conflict_analysis: Dict[str, Any] = {}

    components = plan_components
    if components is None:
        plan = state.get("conversion_plan")
        components = list(getattr(plan, "components", []) or [])

    if smart_assumption_engine and components:
        try:
            assumption_report: AssumptionReport = (
                smart_assumption_engine.generate_assumption_report(components)
            )
            assumption_report_data = [
                {
                    "original_feature": item.original_feature,
                    "assumption_type": item.assumption_type,
                    "bedrock_equivalent": item.bedrock_equivalent,
                    "impact_level": item.impact_level,
                    "user_explanation": item.user_explanation,
                }
                for item in assumption_report.assumptions_applied
            ]
            if hasattr(smart_assumption_engine, "get_conflict_analysis"):
                conflicts = smart_assumption_engine.get_conflict_analysis("general") or []
                if conflicts:
                    conflict_analysis = {
                        "total_conflicts_detected": len(conflicts),
                        "conflicts_resolved": len(
                            [c for c in conflicts if c.get("resolved", False)]
                        ),
                        "resolution_method": "priority_based_deterministic",
                        "details": conflicts,
                    }
        except Exception as e:  # pragma: no cover - assumption-report is best-effort
            logger.warning(f"Failed to generate assumption report: {e}")

    qa = state.get("qa_results") or {}
    pass_rate = state.get("pass_rate")
    if pass_rate is None:
        pass_rate = qa.get("pass_rate", qa.get("overall_score", 0.85))

    converted_features = [
        {"name": s.get("name"), "type": s.get("type")}
        for s in (state.get("converted_scripts") or [])
        if isinstance(s, dict)
    ]
    failed_features = list(state.get("errors") or [])

    detailed_report = {
        "stage": "completed",
        "progress": 100,
        "logs": _collect_logs(state),
        "technical_details": {
            "node_status": state.get("node_status", {}),
            "retry_count": state.get("retry_count", 0),
        },
        "assumption_conflicts": conflict_analysis,
    }

    return {
        "status": "completed",
        "overall_success_rate": float(pass_rate),
        "converted_mods": converted_features,
        "failed_mods": failed_features,
        "smart_assumptions_applied": assumption_report_data,
        "assumption_conflicts_resolved": conflict_analysis,
        "download_url": state.get("output_path"),
        "detailed_report": detailed_report,
    }


def create_failure_response(error_message: str, mod_path: Path | str) -> Dict[str, Any]:
    """Build a PRD-shaped failure report when conversion fails irrecoverably."""
    return {
        "status": "failed",
        "overall_success_rate": 0.0,
        "converted_mods": [],
        "failed_mods": [
            {
                "name": Path(str(mod_path)).name,
                "error": error_message,
            }
        ],
        "smart_assumptions_applied": [],
        "assumption_conflicts_resolved": {},
        "download_url": None,
        "detailed_report": {
            "stage": "failed",
            "progress": 0,
            "logs": [],
            "technical_details": {},
            "error": error_message,
        },
    }


def _collect_logs(state: Dict[str, Any]) -> List[Dict[str, Any]]:
    logs: List[Dict[str, Any]] = []
    for key in ("converted_scripts", "converted_assets"):
        for entry in state.get(key) or []:
            if isinstance(entry, dict):
                name = entry.get("name") or entry.get("registry_name") or "unknown"
                logs.append({"task": key, "output": f"Produced {name}"})
    for warning in state.get("warnings") or []:
        logs.append({"task": "warning", "output": str(warning)})
    for error in state.get("errors") or []:
        logs.append({"task": "error", "output": str(error)})
    return logs


__all__ = ["format_conversion_report", "create_failure_response"]
