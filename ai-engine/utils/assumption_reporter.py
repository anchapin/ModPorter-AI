"""
Smart Assumptions Reporting Module

Generates comprehensive reports about smart assumptions applied during conversion.
Provides user-friendly explanations and technical details for transparency.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import json
import logging
from datetime import datetime

# Import from the smart_assumptions module
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models.smart_assumptions import (
    SmartAssumption,
    AssumptionImpact,
    FeatureContext,
    AssumptionResult,
    ConversionPlanComponent,
    AssumptionReport,
    AppliedAssumptionReportItem,
    SmartAssumptionEngine
)

logger = logging.getLogger(__name__)


class ReportFormat(Enum):
    """Supported report output formats"""
    JSON = "json"
    MARKDOWN = "markdown"
    HTML = "html"
    TEXT = "text"


@dataclass
class AssumptionSummaryStats:
    """Summary statistics for assumptions applied"""
    total_assumptions: int = 0
    high_impact_count: int = 0
    medium_impact_count: int = 0
    low_impact_count: int = 0
    features_analyzed: int = 0
    features_with_assumptions: int = 0
    features_without_assumptions: int = 0
    conflicts_resolved: int = 0
    

@dataclass
class DetailedAssumptionReport:
    """Comprehensive report with all assumption details"""
    job_id: str
    timestamp: str
    summary: AssumptionSummaryStats
    assumptions_applied: List[AppliedAssumptionReportItem]
    features_without_assumptions: List[Dict[str, Any]]
    recommendations: List[str]
    raw_data: Optional[Dict[str, Any]] = None


class AssumptionReporter:
    """
    Generates comprehensive reports about smart assumptions applied during conversion.
    
    Provides multiple output formats for different use cases:
    - JSON for API responses and programmatic access
    - Markdown for documentation and GitHub
    - HTML for web UI display
    - Text for console output and logs
    """
    
    def __init__(self, engine: Optional[SmartAssumptionEngine] = None):
        """Initialize reporter with optional SmartAssumptionEngine"""
        self.engine = engine or SmartAssumptionEngine()
    
    def generate_report(
        self,
        job_id: str,
        conversion_results: List[ConversionPlanComponent],
        features_analyzed: List[FeatureContext],
        include_raw_data: bool = False
    ) -> DetailedAssumptionReport:
        """
        Generate a comprehensive assumption report.
        
        Args:
            job_id: Unique identifier for the conversion job
            conversion_results: List of conversion plan components with assumptions
            features_analyzed: All features that were analyzed
            include_raw_data: Whether to include raw assumption data
            
        Returns:
            DetailedAssumptionReport with all information
        """
        # Calculate summary statistics
        summary = self._calculate_summary(conversion_results, features_analyzed)
        
        # Generate assumption report items
        assumptions_applied = self._generate_report_items(conversion_results)
        
        # Identify features without assumptions
        features_without = self._identify_features_without_assumptions(
            conversion_results, features_analyzed
        )
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            assumptions_applied, summary, features_without
        )
        
        # Build raw data if requested
        raw_data = None
        if include_raw_data:
            raw_data = {
                "engine_assumptions": [
                    {
                        "java_feature": a.java_feature,
                        "inconvertible_aspect": a.inconvertible_aspect,
                        "bedrock_workaround": a.bedrock_workaround,
                        "impact": a.impact.value,
                        "description": a.description
                    }
                    for a in self.engine.get_assumption_table()
                ],
                "conversion_components": [
                    {
                        "original_feature_id": c.original_feature_id,
                        "original_feature_type": c.original_feature_type,
                        "assumption_type": c.assumption_type,
                        "bedrock_equivalent": c.bedrock_equivalent,
                        "impact_level": c.impact_level,
                        "user_explanation": c.user_explanation,
                        "technical_notes": c.technical_notes
                    }
                    for c in conversion_results if c
                ]
            }
        
        return DetailedAssumptionReport(
            job_id=job_id,
            timestamp=datetime.utcnow().isoformat() + "Z",
            summary=summary,
            assumptions_applied=assumptions_applied,
            features_without_assumptions=features_without,
            recommendations=recommendations,
            raw_data=raw_data
        )
    
    def _calculate_summary(
        self,
        conversion_results: List[ConversionPlanComponent],
        features_analyzed: List[FeatureContext]
    ) -> AssumptionSummaryStats:
        """Calculate summary statistics from conversion results"""
        stats = AssumptionSummaryStats()
        stats.features_analyzed = len(features_analyzed)
        
        for component in conversion_results:
            if component is None:
                continue
                
            stats.total_assumptions += 1
            stats.features_with_assumptions += 1
            
            if component.impact_level == AssumptionImpact.HIGH.value:
                stats.high_impact_count += 1
            elif component.impact_level == AssumptionImpact.MEDIUM.value:
                stats.medium_impact_count += 1
            else:
                stats.low_impact_count += 1
        
        stats.features_without_assumptions = stats.features_analyzed - stats.features_with_assumptions
        
        return stats
    
    def _generate_report_items(
        self,
        conversion_results: List[ConversionPlanComponent]
    ) -> List[AppliedAssumptionReportItem]:
        """Generate report items from conversion components"""
        items = []
        
        for component in conversion_results:
            if component is None:
                continue
                
            item = AppliedAssumptionReportItem(
                original_feature=f"{component.original_feature_type} ({component.original_feature_id})",
                assumption_type=component.assumption_type or "unknown",
                bedrock_equivalent=component.bedrock_equivalent,
                impact_level=component.impact_level,
                user_explanation=component.user_explanation
            )
            items.append(item)
        
        return items
    
    def _identify_features_without_assumptions(
        self,
        conversion_results: List[ConversionPlanComponent],
        features_analyzed: List[FeatureContext]
    ) -> List[Dict[str, Any]]:
        """Find features that didn't require smart assumptions"""
        features_with_assumptions = {
            c.original_feature_id for c in conversion_results if c
        }
        
        features_without = []
        for feature in features_analyzed:
            if feature.feature_id not in features_with_assumptions:
                features_without.append({
                    "feature_id": feature.feature_id,
                    "feature_type": feature.feature_type,
                    "name": feature.name,
                    "status": "directly_convertible"
                })
        
        return features_without
    
    def _generate_recommendations(
        self,
        assumptions: List[AppliedAssumptionReportItem],
        summary: AssumptionSummaryStats,
        features_without: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate actionable recommendations based on assumptions applied"""
        recommendations = []
        
        # High impact warnings
        if summary.high_impact_count > 0:
            recommendations.append(
                f"⚠️ {summary.high_impact_count} feature(s) have HIGH impact changes. "
                "Review these carefully as significant functionality may be altered."
            )
        
        # Specific recommendations based on assumption types
        assumption_types = {a.assumption_type for a in assumptions}
        
        if "dimension_to_structure" in assumption_types:
            recommendations.append(
                "🗺️ Custom dimensions converted to structures may have limited exploration scope. "
                "Consider manually expanding the structure area if needed."
            )
        
        if "machinery_simplification" in assumption_types:
            recommendations.append(
                "⚙️ Complex machinery has been simplified. Original processing logic is lost. "
                "Consider using command blocks or behavior packs for advanced functionality."
            )
        
        if "gui_to_book_interface" in assumption_types:
            recommendations.append(
                "📖 Custom GUIs converted to books lose interactivity. "
                "Players will need to use commands or signs for input."
            )
        
        # Positive feedback
        if summary.features_without_assumptions > 0:
            recommendations.append(
                f"✅ {summary.features_without_assumptions} feature(s) converted directly without assumptions. "
                "These should work as expected in Bedrock Edition."
            )
        
        # General advice
        if summary.total_assumptions > 3:
            recommendations.append(
                "📋 This conversion has multiple smart assumptions. "
                "We recommend testing thoroughly in a creative world before using in survival."
            )
        
        return recommendations
    
    def format_report(
        self,
        report: DetailedAssumptionReport,
        format: ReportFormat = ReportFormat.JSON
    ) -> str:
        """
        Format a report in the specified output format.
        
        Args:
            report: The report to format
            format: Output format (JSON, MARKDOWN, HTML, TEXT)
            
        Returns:
            Formatted report string
        """
        if format == ReportFormat.JSON:
            return self._format_json(report)
        elif format == ReportFormat.MARKDOWN:
            return self._format_markdown(report)
        elif format == ReportFormat.HTML:
            return self._format_html(report)
        else:
            return self._format_text(report)
    
    def _format_json(self, report: DetailedAssumptionReport) -> str:
        """Format report as JSON"""
        return json.dumps({
            "job_id": report.job_id,
            "timestamp": report.timestamp,
            "summary": {
                "total_assumptions": report.summary.total_assumptions,
                "high_impact_count": report.summary.high_impact_count,
                "medium_impact_count": report.summary.medium_impact_count,
                "low_impact_count": report.summary.low_impact_count,
                "features_analyzed": report.summary.features_analyzed,
                "features_with_assumptions": report.summary.features_with_assumptions,
                "features_without_assumptions": report.summary.features_without_assumptions,
                "conflicts_resolved": report.summary.conflicts_resolved
            },
            "assumptions_applied": [
                {
                    "original_feature": a.original_feature,
                    "assumption_type": a.assumption_type,
                    "bedrock_equivalent": a.bedrock_equivalent,
                    "impact_level": a.impact_level,
                    "user_explanation": a.user_explanation
                }
                for a in report.assumptions_applied
            ],
            "features_without_assumptions": report.features_without_assumptions,
            "recommendations": report.recommendations
        }, indent=2)
    
    def _format_markdown(self, report: DetailedAssumptionReport) -> str:
        """Format report as Markdown"""
        lines = [
            f"# Smart Assumptions Report",
            f"",
            f"**Job ID:** {report.job_id}",
            f"**Generated:** {report.timestamp}",
            f"",
            f"## Summary",
            f"",
            f"| Metric | Count |",
            f"|--------|-------|",
            f"| Total Assumptions Applied | {report.summary.total_assumptions} |",
            f"| High Impact Changes | {report.summary.high_impact_count} |",
            f"| Medium Impact Changes | {report.summary.medium_impact_count} |",
            f"| Low Impact Changes | {report.summary.low_impact_count} |",
            f"| Features Analyzed | {report.summary.features_analyzed} |",
            f"",
            f"## Assumptions Applied",
            f""
        ]
        
        if not report.assumptions_applied:
            lines.append("*No smart assumptions were required for this conversion.*")
        else:
            for i, assumption in enumerate(report.assumptions_applied, 1):
                impact_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(
                    assumption.impact_level, "⚪"
                )
                lines.extend([
                    f"### {i}. {assumption.original_feature}",
                    f"",
                    f"**Impact:** {impact_emoji} {assumption.impact_level.upper()}",
                    f"",
                    f"**Assumption Type:** `{assumption.assumption_type}`",
                    f"",
                    f"**Bedrock Equivalent:** {assumption.bedrock_equivalent}",
                    f"",
                    f"**Explanation:** {assumption.user_explanation}",
                    f""
                ])
        
        if report.recommendations:
            lines.extend([
                f"## Recommendations",
                f""
            ])
            for rec in report.recommendations:
                lines.append(f"- {rec}")
            lines.append("")
        
        return "\n".join(lines)
    
    def _format_html(self, report: DetailedAssumptionReport) -> str:
        """Format report as HTML"""
        impact_colors = {"high": "#ef4444", "medium": "#f59e0b", "low": "#22c55e"}
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Smart Assumptions Report - {report.job_id}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
        h1 {{ color: #1e293b; }}
        .summary-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin: 20px 0; }}
        .summary-card {{ background: #f8fafc; padding: 15px; border-radius: 8px; text-align: center; }}
        .summary-card .value {{ font-size: 24px; font-weight: bold; color: #2563eb; }}
        .summary-card .label {{ font-size: 12px; color: #64748b; }}
        .assumption {{ background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 15px; margin: 15px 0; }}
        .impact-badge {{ display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: bold; color: white; }}
        .impact-high {{ background: #ef4444; }}
        .impact-medium {{ background: #f59e0b; }}
        .impact-low {{ background: #22c55e; }}
        .recommendations {{ background: #fefce8; border: 1px solid #fde047; border-radius: 8px; padding: 15px; margin: 20px 0; }}
        .recommendations li {{ margin: 8px 0; }}
    </style>
</head>
<body>
    <h1>Smart Assumptions Report</h1>
    <p><strong>Job ID:</strong> {report.job_id}<br>
    <strong>Generated:</strong> {report.timestamp}</p>
    
    <div class="summary-grid">
        <div class="summary-card">
            <div class="value">{report.summary.total_assumptions}</div>
            <div class="label">Total Assumptions</div>
        </div>
        <div class="summary-card">
            <div class="value" style="color: #ef4444;">{report.summary.high_impact_count}</div>
            <div class="label">High Impact</div>
        </div>
        <div class="summary-card">
            <div class="value" style="color: #f59e0b;">{report.summary.medium_impact_count}</div>
            <div class="label">Medium Impact</div>
        </div>
        <div class="summary-card">
            <div class="value" style="color: #22c55e;">{report.summary.low_impact_count}</div>
            <div class="label">Low Impact</div>
        </div>
    </div>
    
    <h2>Assumptions Applied</h2>
"""
        
        if not report.assumptions_applied:
            html += "<p><em>No smart assumptions were required for this conversion.</em></p>"
        else:
            for i, assumption in enumerate(report.assumptions_applied, 1):
                impact_class = f"impact-{assumption.impact_level}"
                html += f"""
    <div class="assumption">
        <h3>{i}. {assumption.original_feature}</h3>
        <p><span class="impact-badge {impact_class}">{assumption.impact_level.upper()} IMPACT</span></p>
        <p><strong>Assumption Type:</strong> <code>{assumption.assumption_type}</code></p>
        <p><strong>Bedrock Equivalent:</strong> {assumption.bedrock_equivalent}</p>
        <p><strong>Explanation:</strong> {assumption.user_explanation}</p>
    </div>
"""
        
        if report.recommendations:
            html += f"""
    <div class="recommendations">
        <h2>Recommendations</h2>
        <ul>
            {''.join(f'<li>{rec}</li>' for rec in report.recommendations)}
        </ul>
    </div>
"""
        
        html += """
</body>
</html>"""
        
        return html
    
    def _format_text(self, report: DetailedAssumptionReport) -> str:
        """Format report as plain text"""
        lines = [
            "=" * 60,
            "SMART ASSUMPTIONS REPORT",
            "=" * 60,
            "",
            f"Job ID: {report.job_id}",
            f"Generated: {report.timestamp}",
            "",
            "-" * 60,
            "SUMMARY",
            "-" * 60,
            f"Total Assumptions Applied: {report.summary.total_assumptions}",
            f"High Impact Changes: {report.summary.high_impact_count}",
            f"Medium Impact Changes: {report.summary.medium_impact_count}",
            f"Low Impact Changes: {report.summary.low_impact_count}",
            f"Features Analyzed: {report.summary.features_analyzed}",
            "",
            "-" * 60,
            "ASSUMPTIONS APPLIED",
            "-" * 60,
        ]
        
        if not report.assumptions_applied:
            lines.append("No smart assumptions were required for this conversion.")
        else:
            for i, assumption in enumerate(report.assumptions_applied, 1):
                lines.extend([
                    "",
                    f"{i}. {assumption.original_feature}",
                    f"   Impact: [{assumption.impact_level.upper()}]",
                    f"   Type: {assumption.assumption_type}",
                    f"   Bedrock Equivalent: {assumption.bedrock_equivalent}",
                    f"   Explanation: {assumption.user_explanation}",
                ])
        
        if report.recommendations:
            lines.extend([
                "",
                "-" * 60,
                "RECOMMENDATIONS",
                "-" * 60,
            ])
            for rec in report.recommendations:
                lines.append(f"• {rec}")
        
        lines.append("")
        lines.append("=" * 60)
        
        return "\n".join(lines)


def create_quick_report(
    job_id: str,
    conversion_results: List[ConversionPlanComponent],
    features_analyzed: List[FeatureContext],
    format: ReportFormat = ReportFormat.JSON
) -> str:
    """
    Convenience function to quickly generate a formatted report.
    
    Args:
        job_id: Unique identifier for the conversion job
        conversion_results: List of conversion plan components
        features_analyzed: All features that were analyzed
        format: Output format
        
    Returns:
        Formatted report string
    """
    reporter = AssumptionReporter()
    report = reporter.generate_report(job_id, conversion_results, features_analyzed)
    return reporter.format_report(report, format)