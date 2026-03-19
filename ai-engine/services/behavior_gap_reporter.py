"""
Behavior Gap Reporter Service
Generates reports for behavioral differences between Java and Bedrock
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import json
from datetime import datetime
from pathlib import Path
import logging

from services.behavior_analyzer import (
    BehaviorGap,
    BehaviorGapSeverity,
    BehaviorGapCategory,
    BehaviorAnalysisResult,
)

logger = logging.getLogger(__name__)


class ReportFormat(Enum):
    """Output format for reports."""
    JSON = "json"
    MARKDOWN = "markdown"
    HTML = "html"
    TEXT = "text"


@dataclass
class GapReportConfig:
    """Configuration for gap reporting."""
    include_fix_suggestions: bool = True
    include_affected_files: bool = True
    group_by_severity: bool = True
    group_by_category: bool = False
    min_severity: BehaviorGapSeverity = BehaviorGapSeverity.MINOR
    max_gaps: int = 100  # Maximum gaps to include


class BehaviorGapReporter:
    """
    Generates reports for behavioral gaps between Java and Bedrock.
    """
    
    def __init__(self, config: Optional[GapReportConfig] = None):
        self.config = config or GapReportConfig()
        
    def generate_report(
        self,
        analysis_result: BehaviorAnalysisResult,
        format: ReportFormat = ReportFormat.JSON,
    ) -> str:
        """
        Generate a gap report from analysis results.
        
        Args:
            analysis_result: The behavior analysis result
            format: Output format
            
        Returns:
            Formatted report string
        """
        # Filter gaps by minimum severity
        gaps = [
            g for g in analysis_result.gaps
            if self._severity_order(g.severity) <= self._severity_order(self.config.min_severity)
        ]
        
        # Limit gaps
        gaps = gaps[:self.config.max_gaps]
        
        if format == ReportFormat.JSON:
            return self._generate_json_report(analysis_result, gaps)
        elif format == ReportFormat.MARKDOWN:
            return self._generate_markdown_report(analysis_result, gaps)
        elif format == ReportFormat.HTML:
            return self._generate_html_report(analysis_result, gaps)
        elif format == ReportFormat.TEXT:
            return self._generate_text_report(analysis_result, gaps)
        
        return str(analysis_result)
    
    def _generate_json_report(
        self,
        result: BehaviorAnalysisResult,
        gaps: List[BehaviorGap],
    ) -> str:
        """Generate JSON format report."""
        report = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "java_source": result.java_source_path,
                "bedrock_output": result.bedrock_output_path,
                "analysis_summary": {
                    "analyzed_functions": result.analyzed_functions,
                    "analyzed_events": result.analyzed_events,
                    "analyzed_state_vars": result.analyzed_state_vars,
                    "total_gaps": result.total_gaps,
                    "preservation_score": result.preservation_score,
                },
            },
            "gaps": [g.to_dict() for g in gaps],
            "mappings": {
                "function_mappings": result.function_mappings,
                "event_mappings": result.event_mappings,
            },
            "severity_summary": {
                "critical": len(result.critical_gaps),
                "major": len(result.major_gaps),
                "minor": len(result.minor_gaps),
            },
        }
        
        return json.dumps(report, indent=2)
    
    def _generate_markdown_report(
        self,
        result: BehaviorAnalysisResult,
        gaps: List[BehaviorGap],
    ) -> str:
        """Generate Markdown format report."""
        lines = []
        
        # Header
        lines.append("# Behavior Preservation Analysis Report")
        lines.append("")
        lines.append(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        
        # Summary
        lines.append("## Summary")
        lines.append("")
        lines.append(f"| Metric | Value |")
        lines.append(f"|--------|-------|")
        lines.append(f"| Preservation Score | {result.preservation_score:.1f}% |")
        lines.append(f"| Analyzed Functions | {result.analyzed_functions} |")
        lines.append(f"| Analyzed Events | {result.analyzed_events} |")
        lines.append(f"| Analyzed State Variables | {result.analyzed_state_vars} |")
        lines.append(f"| Total Gaps | {result.total_gaps} |")
        lines.append("")
        
        # Severity breakdown
        lines.append("## Severity Breakdown")
        lines.append("")
        lines.append(f"- 🔴 **Critical**: {len(result.critical_gaps)}")
        lines.append(f"- 🟠 **Major**: {len(result.major_gaps)}")
        lines.append(f"- 🟡 **Minor**: {len(result.minor_gaps)}")
        lines.append("")
        
        # Critical gaps first
        if result.critical_gaps:
            lines.append("## 🔴 Critical Gaps")
            lines.append("")
            for gap in result.critical_gaps:
                lines.append(f"### {gap.title}")
                lines.append("")
                lines.append(f"**Category**: {gap.category.value}")
                lines.append("")
                lines.append(f"**Description**: {gap.description}")
                lines.append("")
                lines.append(f"**Java Element**: `{gap.java_element}`")
                if gap.bedrock_element:
                    lines.append(f"**Bedrock Element**: `{gap.bedrock_element}`")
                if gap.affected_files and self.config.include_affected_files:
                    lines.append(f"**Affected Files**: {', '.join(gap.affected_files)}")
                if gap.fix_suggestion and self.config.include_fix_suggestions:
                    lines.append("")
                    lines.append(f"**Fix Suggestion**: {gap.fix_suggestion}")
                lines.append("")
        
        # Major gaps
        if result.major_gaps:
            lines.append("## 🟠 Major Gaps")
            lines.append("")
            for gap in result.major_gaps:
                lines.append(f"### {gap.title}")
                lines.append("")
                lines.append(f"**Category**: {gap.category.value}")
                lines.append("")
                lines.append(f"**Description**: {gap.description}")
                lines.append("")
                lines.append(f"**Java Element**: `{gap.java_element}`")
                if gap.bedrock_element:
                    lines.append(f"**Bedrock Element**: `{gap.bedrock_element}`")
                if gap.affected_files and self.config.include_affected_files:
                    lines.append(f"**Affected Files**: {', '.join(gap.affected_files)}")
                if gap.fix_suggestion and self.config.include_fix_suggestions:
                    lines.append("")
                    lines.append(f"**Fix Suggestion**: {gap.fix_suggestion}")
                lines.append("")
        
        # Minor gaps
        if result.minor_gaps:
            lines.append("## 🟡 Minor Gaps")
            lines.append("")
            for gap in result.minor_gaps[:20]:  # Limit minor gaps
                lines.append(f"- **{gap.title}** ({gap.category.value})")
                lines.append(f"  - {gap.description}")
            if len(result.minor_gaps) > 20:
                lines.append(f"- ... and {len(result.minor_gaps) - 20} more minor gaps")
            lines.append("")
        
        # Event mappings
        if result.event_mappings:
            lines.append("## Event Mappings")
            lines.append("")
            lines.append("| Java Event | Bedrock Event |")
            lines.append("|------------|---------------|")
            for java, bedrock in result.event_mappings.items():
                lines.append(f"| {java} | {bedrock} |")
            lines.append("")
        
        # Function mappings
        if result.function_mappings:
            lines.append("## Function Mappings")
            lines.append("")
            lines.append(f"Total: {len(result.function_mappings)} functions mapped")
            lines.append("")
        
        return "\n".join(lines)
    
    def _generate_html_report(
        self,
        result: BehaviorAnalysisResult,
        gaps: List[BehaviorGap],
    ) -> str:
        """Generate HTML format report."""
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Behavior Preservation Report</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 40px; }}
        h1 {{ color: #333; }}
        h2 {{ color: #555; border-bottom: 1px solid #eee; padding-bottom: 10px; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background-color: #f5f5f5; }}
        .critical {{ color: #d32f2f; font-weight: bold; }}
        .major {{ color: #f57c00; font-weight: bold; }}
        .minor {{ color: #fbc02d; }}
        .score {{ font-size: 48px; font-weight: bold; color: {self._score_color(result.preservation_score)}; }}
        .gap {{ background: #f9f9f9; padding: 15px; margin: 10px 0; border-radius: 5px; }}
        .code {{ background: #f5f5f5; padding: 2px 6px; border-radius: 3px; font-family: monospace; }}
    </style>
</head>
<body>
    <h1>Behavior Preservation Analysis Report</h1>
    <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    
    <h2>Summary</h2>
    <div class="score">{result.preservation_score:.1f}%</div>
    <table>
        <tr><th>Metric</th><th>Value</th></tr>
        <tr><td>Analyzed Functions</td><td>{result.analyzed_functions}</td></tr>
        <tr><td>Analyzed Events</td><td>{result.analyzed_events}</td></tr>
        <tr><td>Analyzed State Variables</td><td>{result.analyzed_state_vars}</td></tr>
        <tr><td>Total Gaps</td><td>{result.total_gaps}</td></tr>
    </table>
    
    <h2>Severity Breakdown</h2>
    <ul>
        <li class="critical">Critical: {len(result.critical_gaps)}</li>
        <li class="major">Major: {len(result.major_gaps)}</li>
        <li class="minor">Minor: {len(result.minor_gaps)}</li>
    </ul>
"""
        
        # Add gaps sections
        for severity, severity_name in [
            (result.critical_gaps, "Critical"),
            (result.major_gaps, "Major"),
            (result.minor_gaps, "Minor"),
        ]:
            if severity:
                html += f"\n<h2>{severity_name} Gaps</h2>\n"
                for gap in severity:
                    html += f"""
    <div class="gap">
        <h3>{gap.title}</h3>
        <p><strong>Category:</strong> {gap.category.value}</p>
        <p>{gap.description}</p>
        <p><strong>Java:</strong> <span class="code">{gap.java_element}</span></p>
"""
                    if gap.bedrock_element:
                        html += f'        <p><strong>Bedrock:</strong> <span class="code">{gap.bedrock_element}</span></p>\n'
                    if gap.fix_suggestion:
                        html += f'        <p><strong>Fix:</strong> {gap.fix_suggestion}</p>\n'
                    html += "    </div>\n"
        
        html += """
</body>
</html>"""
        
        return html
    
    def _generate_text_report(
        self,
        result: BehaviorAnalysisResult,
        gaps: List[BehaviorGap],
    ) -> str:
        """Generate plain text report."""
        lines = []
        
        lines.append("=" * 60)
        lines.append("BEHAVIOR PRESERVATION ANALYSIS REPORT")
        lines.append("=" * 60)
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        
        lines.append("SUMMARY")
        lines.append("-" * 40)
        lines.append(f"Preservation Score: {result.preservation_score:.1f}%")
        lines.append(f"Analyzed Functions:  {result.analyzed_functions}")
        lines.append(f"Analyzed Events:     {result.analyzed_events}")
        lines.append(f"Analyzed State Vars:{result.analyzed_state_vars}")
        lines.append(f"Total Gaps:         {result.total_gaps}")
        lines.append("")
        
        lines.append("SEVERITY BREAKDOWN")
        lines.append("-" * 40)
        lines.append(f"Critical: {len(result.critical_gaps)}")
        lines.append(f"Major:    {len(result.major_gaps)}")
        lines.append(f"Minor:    {len(result.minor_gaps)}")
        lines.append("")
        
        # Gaps
        for severity_name, gaps_list in [
            ("CRITICAL GAPS", result.critical_gaps),
            ("MAJOR GAPS", result.major_gaps),
            ("MINOR GAPS", result.minor_gaps),
        ]:
            if gaps_list:
                lines.append(f"{severity_name}")
                lines.append("-" * 40)
                for gap in gaps_list:
                    lines.append(f"  [{gap.severity.value.upper()}] {gap.title}")
                    lines.append(f"    Category: {gap.category.value}")
                    lines.append(f"    Java:     {gap.java_element}")
                    if gap.bedrock_element:
                        lines.append(f"    Bedrock:  {gap.bedrock_element}")
                    if gap.fix_suggestion:
                        lines.append(f"    Fix:      {gap.fix_suggestion[:80]}...")
                    lines.append("")
        
        return "\n".join(lines)
    
    def _severity_order(self, severity: BehaviorGapSeverity) -> int:
        """Get numeric order for severity."""
        orders = {
            BehaviorGapSeverity.CRITICAL: 0,
            BehaviorGapSeverity.MAJOR: 1,
            BehaviorGapSeverity.MINOR: 2,
        }
        return orders.get(severity, 3)
    
    def _score_color(self, score: float) -> str:
        """Get color for score."""
        if score >= 80:
            return "#4caf50"  # Green
        elif score >= 60:
            return "#ff9800"  # Orange
        else:
            return "#f44336"  # Red
    
    def save_report(
        self,
        analysis_result: BehaviorAnalysisResult,
        output_path: Path,
        format: ReportFormat = ReportFormat.JSON,
    ) -> None:
        """
        Save report to file.
        
        Args:
            analysis_result: The analysis result
            output_path: Path to save the report
            format: Output format
        """
        content = self.generate_report(analysis_result, format)
        output_path.write_text(content, encoding="utf-8")
        logger.info(f"Report saved to {output_path}")


def generate_gap_report(
    analysis_result: BehaviorAnalysisResult,
    format: ReportFormat = ReportFormat.JSON,
) -> str:
    """
    Convenience function to generate a gap report.
    
    Args:
        analysis_result: The behavior analysis result
        format: Output format
        
    Returns:
        Formatted report string
    """
    reporter = BehaviorGapReporter()
    return reporter.generate_report(analysis_result, format)


def save_gap_report(
    analysis_result: BehaviorAnalysisResult,
    output_path: Path,
    format: ReportFormat = ReportFormat.JSON,
) -> None:
    """
    Convenience function to save a gap report.
    
    Args:
        analysis_result: The behavior analysis result
        output_path: Path to save the report
        format: Output format
    """
    reporter = BehaviorGapReporter()
    reporter.save_report(analysis_result, output_path, format)
