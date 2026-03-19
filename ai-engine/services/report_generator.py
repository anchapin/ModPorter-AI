"""
Conversion Report Schema and Generation Service

Enhanced conversion reports with comprehensive metrics, quality scores,
and multiple output formats.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Any


class ReportFormat(Enum):
    """Supported report output formats."""
    JSON = "json"
    HTML = "html"
    MARKDOWN = "markdown"


class ConversionResult(Enum):
    """Overall conversion result."""
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"


@dataclass
class ConversionMetadata:
    """Metadata about the conversion."""
    conversion_id: str
    mod_name: str
    mod_version: Optional[str] = None
    source_type: str = "java"
    target_type: str = "bedrock"
    complexity: str = "standard"
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None


@dataclass
class FileMetrics:
    """File-level conversion metrics."""
    total_files: int = 0
    converted_files: int = 0
    failed_files: int = 0
    skipped_files: int = 0
    total_functions: int = 0
    converted_functions: int = 0
    failed_functions: int = 0


@dataclass
class QualityMetrics:
    """Quality score metrics."""
    overall_score: float = 0.0
    quality_level: str = "needs_work"
    syntax_score: float = 0.0
    semantic_score: float = 0.0
    behavior_score: float = 0.0
    completeness_score: float = 0.0
    critical_issues: int = 0
    major_issues: int = 0
    minor_issues: int = 0


@dataclass
class RecommendationItem:
    """A single recommendation."""
    priority: int
    title: str
    description: str
    impact: str
    effort: str


@dataclass
class EnhancedConversionReport:
    """Complete conversion report with all enhancements."""
    # Header
    report_version: str = "2.0"
    generated_at: datetime = field(default_factory=datetime.now)
    
    # Conversion info
    metadata: Optional[ConversionMetadata] = None
    result: str = ConversionResult.SUCCESS.value
    
    # Metrics
    file_metrics: Optional[FileMetrics] = None
    quality_metrics: Optional[QualityMetrics] = None
    
    # Details
    issues: list = field(default_factory=list)
    recommendations: list = field(default_factory=list)
    
    # Additional context
    assumptions: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Convert report to dictionary."""
        return {
            "report_version": self.report_version,
            "generated_at": self.generated_at.isoformat() if isinstance(self.generated_at, datetime) else str(self.generated_at),
            "metadata": {
                "conversion_id": self.metadata.conversion_id if self.metadata else None,
                "mod_name": self.metadata.mod_name if self.metadata else None,
                "mod_version": self.metadata.mod_version if self.metadata else None,
                "source_type": self.metadata.source_type if self.metadata else None,
                "target_type": self.metadata.target_type if self.metadata else None,
                "complexity": self.metadata.complexity if self.metadata else None,
                "started_at": self.metadata.started_at.isoformat() if self.metadata and self.metadata.started_at else None,
                "completed_at": self.metadata.completed_at.isoformat() if self.metadata and self.metadata.completed_at else None,
                "duration_seconds": self.metadata.duration_seconds if self.metadata else None,
            } if self.metadata else None,
            "result": self.result,
            "file_metrics": {
                "total_files": self.file_metrics.total_files if self.file_metrics else 0,
                "converted_files": self.file_metrics.converted_files if self.file_metrics else 0,
                "failed_files": self.file_metrics.failed_files if self.file_metrics else 0,
                "skipped_files": self.file_metrics.skipped_files if self.file_metrics else 0,
                "total_functions": self.file_metrics.total_functions if self.file_metrics else 0,
                "converted_functions": self.file_metrics.converted_functions if self.file_metrics else 0,
                "failed_functions": self.file_metrics.failed_functions if self.file_metrics else 0,
            } if self.file_metrics else None,
            "quality_metrics": {
                "overall_score": self.quality_metrics.overall_score if self.quality_metrics else 0,
                "quality_level": self.quality_metrics.quality_level if self.quality_metrics else None,
                "syntax_score": self.quality_metrics.syntax_score if self.quality_metrics else 0,
                "semantic_score": self.quality_metrics.semantic_score if self.quality_metrics else 0,
                "behavior_score": self.quality_metrics.behavior_score if self.quality_metrics else 0,
                "completeness_score": self.quality_metrics.completeness_score if self.quality_metrics else 0,
                "critical_issues": self.quality_metrics.critical_issues if self.quality_metrics else 0,
                "major_issues": self.quality_metrics.major_issues if self.quality_metrics else 0,
                "minor_issues": self.quality_metrics.minor_issues if self.quality_metrics else 0,
            } if self.quality_metrics else None,
            "issues": self.issues,
            "recommendations": [
                {
                    "priority": r.priority,
                    "title": r.title,
                    "description": r.description,
                    "impact": r.impact,
                    "effort": r.effort,
                } for r in self.recommendations
            ],
            "assumptions": self.assumptions,
            "warnings": self.warnings,
        }


class ReportGenerator:
    """Generates conversion reports in multiple formats."""

    def __init__(self):
        """Initialize the report generator."""
        pass

    def generate_json(self, report: EnhancedConversionReport) -> str:
        """Generate JSON format report.
        
        Args:
            report: The conversion report to generate
            
        Returns:
            JSON string representation
        """
        import json
        return json.dumps(report.to_dict(), indent=2)

    def generate_html(self, report: EnhancedConversionReport) -> str:
        """Generate HTML format report with styling.
        
        Args:
            report: The conversion report to generate
            
        Returns:
            HTML string representation
        """
        md = self.generate_markdown(report)
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Conversion Report - {report.metadata.mod_name if report.metadata else 'Unknown'}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 20px;
        }}
        .header h1 {{
            margin: 0 0 10px 0;
        }}
        .card {{
            background: white;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .card h2 {{
            margin-top: 0;
            color: #333;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }}
        .score-display {{
            text-align: center;
            padding: 20px;
        }}
        .score-value {{
            font-size: 48px;
            font-weight: bold;
            color: {self._get_score_color(report.quality_metrics.overall_score if report.quality_metrics else 0)};
        }}
        .score-label {{
            font-size: 18px;
            color: #666;
        }}
        .metric-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }}
        .metric-card {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
        }}
        .metric-value {{
            font-size: 24px;
            font-weight: bold;
            color: #333;
        }}
        .metric-label {{
            font-size: 12px;
            color: #666;
            text-transform: uppercase;
        }}
        .progress-bar {{
            width: 100%;
            height: 20px;
            background: #e0e0e0;
            border-radius: 10px;
            overflow: hidden;
            margin: 5px 0;
        }}
        .progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            transition: width 0.3s ease;
        }}
        .badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: bold;
            margin: 2px;
        }}
        .badge-critical {{ background: #ff4444; color: white; }}
        .badge-major {{ background: #ff9800; color: white; }}
        .badge-minor {{ background: #4caf50; color: white; }}
        .badge-success {{ background: #4caf50; color: white; }}
        .badge-failed {{ background: #f44336; color: white; }}
        .result-{ConversionResult.SUCCESS.value} {{ color: #4caf50; }}
        .result-{ConversionResult.PARTIAL_SUCCESS.value} {{ color: #ff9800; }}
        .result-{ConversionResult.FAILED.value} {{ color: #f44336; }}
        .code-block {{
            background: #282c34;
            color: #abb2bf;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
            font-family: 'Courier New', monospace;
            font-size: 13px;
        }}
        .timestamp {{
            color: rgba(255,255,255,0.8);
            font-size: 14px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 Conversion Report</h1>
        <div class="timestamp">
            Generated: {report.generated_at.strftime('%Y-%m-%d %H:%M:%S') if isinstance(report.generated_at, datetime) else str(report.generated_at)}
        </div>
    </div>

    <div class="card">
        <h2>📋 Summary</h2>
        <div class="score-display">
            <div class="score-value">{report.quality_metrics.overall_score if report.quality_metrics else 0:.1f}%</div>
            <div class="score-label">{report.quality_metrics.quality_level if report.quality_metrics else 'N/A'}</div>
        </div>
        <div style="text-align: center; margin-top: 20px;">
            <span class="badge badge-{report.result}">{report.result.upper()}</span>
        </div>
    </div>

    <div class="card">
        <h2>📁 File Metrics</h2>
        <div class="metric-grid">
            <div class="metric-card">
                <div class="metric-value">{report.file_metrics.total_files if report.file_metrics else 0}</div>
                <div class="metric-label">Total Files</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{report.file_metrics.converted_files if report.file_metrics else 0}</div>
                <div class="metric-label">Converted</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{report.file_metrics.failed_files if report.file_metrics else 0}</div>
                <div class="metric-label">Failed</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{report.file_metrics.total_functions if report.file_metrics else 0}</div>
                <div class="metric-label">Total Functions</div>
            </div>
        </div>
    </div>

    <div class="card">
        <h2>⭐ Quality Scores</h2>
        <div class="metric-grid">
            <div>
                <div>Syntax ({report.quality_metrics.syntax_score if report.quality_metrics else 0:.1f}%)</div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {report.quality_metrics.syntax_score if report.quality_metrics else 0}%"></div>
                </div>
            </div>
            <div>
                <div>Semantic ({report.quality_metrics.semantic_score if report.quality_metrics else 0:.1f}%)</div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {report.quality_metrics.semantic_score if report.quality_metrics else 0}%"></div>
                </div>
            </div>
            <div>
                <div>Behavior ({report.quality_metrics.behavior_score if report.quality_metrics else 0:.1f}%)</div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {report.quality_metrics.behavior_score if report.quality_metrics else 0}%"></div>
                </div>
            </div>
            <div>
                <div>Completeness ({report.quality_metrics.completeness_score if report.quality_metrics else 0:.1f}%)</div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {report.quality_metrics.completeness_score if report.quality_metrics else 0}%"></div>
                </div>
            </div>
        </div>
    </div>

    <div class="card">
        <h2>⚠️ Issues</h2>
        <div>
            <span class="badge badge-critical">Critical: {report.quality_metrics.critical_issues if report.quality_metrics else 0}</span>
            <span class="badge badge-major">Major: {report.quality_metrics.major_issues if report.quality_metrics else 0}</span>
            <span class="badge badge-minor">Minor: {report.quality_metrics.minor_issues if report.quality_metrics else 0}</span>
        </div>
        {self._render_issues_html(report.issues) if report.issues else '<p>No issues found.</p>'}
    </div>

    {self._render_recommendations_html(report.recommendations) if report.recommendations else ''}

    {self._render_warnings_html(report.warnings) if report.warnings else ''}

</body>
</html>"""
        return html

    def generate_markdown(self, report: EnhancedConversionReport) -> str:
        """Generate Markdown format report.
        
        Args:
            report: The conversion report to generate
            
        Returns:
            Markdown string representation
        """
        lines = [
            "# 📊 Conversion Report",
            "",
            f"**Generated:** {report.generated_at.strftime('%Y-%m-%d %H:%M:%S') if isinstance(report.generated_at, datetime) else str(report.generated_at)}",
            f"**Report Version:** {report.report_version}",
            "",
            "---",
            "",
            "## 📋 Summary",
            "",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| **Overall Score** | {report.quality_metrics.overall_score if report.quality_metrics else 0:.1f}% |",
            f"| **Quality Level** | {report.quality_metrics.quality_level if report.quality_metrics else 'N/A'} |",
            f"| **Result** | {report.result.upper()} |",
        ]
        
        if report.metadata:
            lines.extend([
                f"| **Mod Name** | {report.metadata.mod_name} |",
                f"| **Complexity** | {report.metadata.complexity} |",
                f"| **Duration** | {report.metadata.duration_seconds if report.metadata.duration_seconds else 0:.1f}s |",
            ])
        
        lines.extend(["", "## 📁 File Metrics", "",
                      f"| Metric | Count |",
                      f"|--------|-------|",
                      f"| Total Files | {report.file_metrics.total_files if report.file_metrics else 0} |",
                      f"| Converted | {report.file_metrics.converted_files if report.file_metrics else 0} |",
                      f"| Failed | {report.file_metrics.failed_files if report.file_metrics else 0} |",
                      f"| Skipped | {report.file_metrics.skipped_files if report.file_metrics else 0} |",
                      f"| Total Functions | {report.file_metrics.total_functions if report.file_metrics else 0} |",
                      f"| Converted Functions | {report.file_metrics.converted_functions if report.file_metrics else 0} |",
                      "",
                      "## ⭐ Quality Scores", "",
                      f"| Component | Score |",
                      f"|----------|-------|",
                      f"| Syntax | {report.quality_metrics.syntax_score if report.quality_metrics else 0:.1f}% |",
                      f"| Semantic | {report.quality_metrics.semantic_score if report.quality_metrics else 0:.1f}% |",
                      f"| Behavior | {report.quality_metrics.behavior_score if report.quality_metrics else 0:.1f}% |",
                      f"| Completeness | {report.quality_metrics.completeness_score if report.quality_metrics else 0:.1f}% |",
        ])
        
        if report.issues:
            lines.extend([
                "",
                "## ⚠️ Issues",
                "",
                f"**Critical:** {report.quality_metrics.critical_issues if report.quality_metrics else 0} | "
                f"**Major:** {report.quality_metrics.major_issues if report.quality_metrics else 0} | "
                f"**Minor:** {report.quality_metrics.minor_issues if report.quality_metrics else 0}",
                "",
            ])
            for issue in report.issues:
                lines.append(f"- **{issue.get('severity', 'unknown').upper()}** [{issue.get('category', 'unknown')}]: {issue.get('message', '')}")
        
        if report.recommendations:
            lines.extend(["", "## 💡 Recommendations", ""])
            for rec in report.recommendations:
                lines.append(f"### {rec.priority}. {rec.title}")
                lines.append(f"{rec.description}")
                lines.append(f"- **Impact:** {rec.impact} | **Effort:** {rec.effort}")
                lines.append("")
        
        if report.warnings:
            lines.extend(["", "## ⚡ Warnings", ""])
            for warning in report.warnings:
                lines.append(f"- {warning}")
        
        if report.assumptions:
            lines.extend(["", "## 📝 Assumptions", ""])
            for assumption in report.assumptions:
                lines.append(f"- {assumption}")
        
        lines.append("---")
        lines.append("*Report generated by ModPorter-AI*")
        
        return "\n".join(lines)

    def generate(self, report: EnhancedConversionReport, format: str = "json") -> str:
        """Generate report in specified format.
        
        Args:
            report: The conversion report to generate
            format: Output format (json/html/markdown)
            
        Returns:
            Formatted report string
        """
        if format == ReportFormat.HTML.value:
            return self.generate_html(report)
        elif format == ReportFormat.MARKDOWN.value:
            return self.generate_markdown(report)
        else:
            return self.generate_json(report)

    def _get_score_color(self, score: float) -> str:
        """Get color for score value."""
        if score >= 90:
            return "#4caf50"
        elif score >= 70:
            return "#ff9800"
        else:
            return "#f44336"

    def _render_issues_html(self, issues: list) -> str:
        """Render issues as HTML."""
        if not issues:
            return "<p>No issues found.</p>"
        
        html = "<ul>"
        for issue in issues:
            severity = issue.get('severity', 'unknown')
            html += f'<li><span class="badge badge-{severity}">{severity.upper()}</span> '
            html += f'[{issue.get("category", "unknown")}] {issue.get("message", "")}</li>'
        html += "</ul>"
        return html

    def _render_recommendations_html(self, recommendations: list) -> str:
        """Render recommendations as HTML."""
        if not recommendations:
            return ""
        
        html = '<div class="card"><h2>💡 Recommendations</h2><ul>'
        for rec in recommendations:
            html += f'<li><strong>{rec.priority}. {rec.title}</strong><br>'
            html += f'{rec.description}<br>'
            html += f'<em>Impact: {rec.impact} | Effort: {rec.effort}</em></li>'
        html += '</ul></div>'
        return html

    def _render_warnings_html(self, warnings: list) -> str:
        """Render warnings as HTML."""
        if not warnings:
            return ""
        
        html = '<div class="card"><h2>⚡ Warnings</h2><ul>'
        for warning in warnings:
            html += f'<li>{warning}</li>'
        html += '</ul></div>'
        return html


class ReportBuilder:
    """Fluent API for building conversion reports."""

    def __init__(self):
        """Initialize the report builder."""
        self._report = EnhancedConversionReport()

    def with_metadata(self, conversion_id: str, mod_name: str, 
                     complexity: str = "standard") -> 'ReportBuilder':
        """Add conversion metadata."""
        self._report.metadata = ConversionMetadata(
            conversion_id=conversion_id,
            mod_name=mod_name,
            complexity=complexity,
            started_at=datetime.now()
        )
        return self

    def with_result(self, result: str) -> 'ReportBuilder':
        """Set conversion result."""
        self._report.result = result
        return self

    def with_file_metrics(self, total: int = 0, converted: int = 0,
                          failed: int = 0, skipped: int = 0,
                          total_funcs: int = 0, converted_funcs: int = 0,
                          failed_funcs: int = 0) -> 'ReportBuilder':
        """Add file metrics."""
        self._report.file_metrics = FileMetrics(
            total_files=total,
            converted_files=converted,
            failed_files=failed,
            skipped_files=skipped,
            total_functions=total_funcs,
            converted_functions=converted_funcs,
            failed_functions=failed_funcs
        )
        return self

    def with_quality_metrics(self, overall: float = 0, level: str = "needs_work",
                            syntax: float = 0, semantic: float = 0,
                            behavior: float = 0, completeness: float = 0,
                            critical: int = 0, major: int = 0, minor: int = 0) -> 'ReportBuilder':
        """Add quality metrics."""
        self._report.quality_metrics = QualityMetrics(
            overall_score=overall,
            quality_level=level,
            syntax_score=syntax,
            semantic_score=semantic,
            behavior_score=behavior,
            completeness_score=completeness,
            critical_issues=critical,
            major_issues=major,
            minor_issues=minor
        )
        return self

    def with_issue(self, category: str, severity: str, message: str,
                  location: str = None, suggestion: str = None) -> 'ReportBuilder':
        """Add an issue."""
        issue = {
            "category": category,
            "severity": severity,
            "message": message
        }
        if location:
            issue["location"] = location
        if suggestion:
            issue["suggestion"] = suggestion
        self._report.issues.append(issue)
        return self

    def with_recommendation(self, priority: int, title: str, description: str,
                           impact: str, effort: str) -> 'ReportBuilder':
        """Add a recommendation."""
        self._report.recommendations.append(RecommendationItem(
            priority=priority,
            title=title,
            description=description,
            impact=impact,
            effort=effort
        ))
        return self

    def with_assumption(self, assumption: str) -> 'ReportBuilder':
        """Add an assumption."""
        self._report.assumptions.append(assumption)
        return self

    def with_warning(self, warning: str) -> 'ReportBuilder':
        """Add a warning."""
        self._report.warnings.append(warning)
        return self

    def with_duration(self, seconds: float) -> 'ReportBuilder':
        """Set conversion duration."""
        if self._report.metadata:
            self._report.metadata.duration_seconds = seconds
            self._report.metadata.completed_at = datetime.now()
        return self

    def build(self) -> EnhancedConversionReport:
        """Build the report."""
        return self._report


def create_sample_report() -> EnhancedConversionReport:
    """Create a sample report for demonstration."""
    return (ReportBuilder()
        .with_metadata("conv-001", "MyAwesomeMod", "standard")
        .with_result(ConversionResult.SUCCESS.value)
        .with_file_metrics(
            total=10, converted=9, failed=1, skipped=0,
            total_funcs=50, converted_funcs=47, failed_funcs=3
        )
        .with_quality_metrics(
            overall=85.5, level="good",
            syntax=100, semantic=82, behavior=78, completeness=90,
            critical=0, major=2, minor=3
        )
        .with_issue("behavior", "minor", "Some event handlers not fully mapped")
        .with_issue("completeness", "major", "3 functions could not be converted")
        .with_recommendation(1, "Fix Behavior Gaps", "Review unmapped event handlers", "Medium", "Low")
        .with_assumption("Java 8 features are supported")
        .with_warning("Mod uses deprecated API")
        .with_duration(125.5)
        .build())
