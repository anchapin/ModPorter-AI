"""
Validation Reporting System

This module provides comprehensive validation reporting for the QA Suite (Phase 09).

Features:
- Report generation engine
- Multi-format report support (JSON, HTML, Markdown)
- Historical reports
- Alert system integration
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class ValidationReport:
    """Complete validation report."""
    report_id: str
    conversion_id: str
    generated_at: str
    validation_results: Dict[str, Any]
    regression_results: Optional[Dict[str, Any]] = None
    coverage_metrics: Optional[Dict[str, Any]] = None
    quality_score: Optional[Dict[str, Any]] = None
    recommendations: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ReportGenerator:
    """Generates comprehensive validation reports."""
    
    def __init__(self, storage_path: str = "data/reports"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.reports: Dict[str, ValidationReport] = {}
        self._load_reports()
    
    def _load_reports(self):
        """Load existing reports from storage."""
        index_file = self.storage_path / "index.json"
        if index_file.exists():
            with open(index_file, 'r') as f:
                data = json.load(f)
                # Load recent reports only (last 100)
                for rid in list(data.keys())[-100:]:
                    self.reports[rid] = data[rid]
    
    def _save_reports(self):
        """Save reports index."""
        index_file = self.storage_path / "index.json"
        with open(index_file, 'w') as f:
            json.dump(self.reports, f, indent=2, default=str)
    
    def generate_report(
        self,
        conversion_id: str,
        validation_results: Dict[str, Any],
        regression_results: Optional[Dict[str, Any]] = None,
        coverage_metrics: Optional[Dict[str, Any]] = None,
        quality_score: Optional[Dict[str, Any]] = None
    ) -> ValidationReport:
        """Generate a comprehensive validation report."""
        
        report_id = f"report_{conversion_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Collect all recommendations
        recommendations = []
        
        if validation_results:
            if isinstance(validation_results, dict):
                if validation_results.get('recommendations'):
                    recommendations.extend(validation_results['recommendations'])
                if not validation_results.get('is_valid', True):
                    recommendations.append("Validation failed - review detailed results")
        
        if regression_results and regression_results.get('regression_detected'):
            recommendations.append(
                f"REGRESSION: {regression_results.get('severity', 'unknown')} severity detected"
            )
        
        if quality_score:
            if isinstance(quality_score, dict):
                if quality_score.get('recommendations'):
                    recommendations.extend(quality_score['recommendations'])
                if quality_score.get('grade') in ['D', 'F']:
                    recommendations.append(f"Low quality grade: {quality_score['grade']}")
        
        # Remove duplicates
        seen = set()
        unique_recommendations = []
        for r in recommendations:
            if r not in seen:
                seen.add(r)
                unique_recommendations.append(r)
        
        report = ValidationReport(
            report_id=report_id,
            conversion_id=conversion_id,
            generated_at=datetime.now().isoformat(),
            validation_results=validation_results,
            regression_results=regression_results,
            coverage_metrics=coverage_metrics,
            quality_score=quality_score,
            recommendations=unique_recommendations,
            metadata={
                'format_version': '1.0',
                'generated_by': 'QA Suite Phase 09-04'
            }
        )
        
        # Save report
        self.reports[report_id] = {
            'report_id': report.report_id,
            'conversion_id': report.conversion_id,
            'generated_at': report.generated_at,
            'validation_results': report.validation_results,
            'regression_results': report.regression_results,
            'coverage_metrics': report.coverage_metrics,
            'quality_score': report.quality_score,
            'recommendations': report.recommendations,
            'metadata': report.metadata
        }
        
        # Save to file
        report_file = self.storage_path / f"{report_id}.json"
        with open(report_file, 'w') as f:
            json.dump(self.reports[report_id], f, indent=2, default=str)
        
        self._save_reports()
        
        return report
    
    def get_report(self, report_id: str) -> Optional[ValidationReport]:
        """Get a specific report."""
        if report_id in self.reports:
            data = self.reports[report_id]
            return ValidationReport(**data)
        return None
    
    def get_reports_for_conversion(self, conversion_id: str) -> List[ValidationReport]:
        """Get all reports for a conversion."""
        reports = []
        for data in self.reports.values():
            if data.get('conversion_id') == conversion_id:
                reports.append(ValidationReport(**data))
        return sorted(reports, key=lambda r: r.generated_at, reverse=True)
    
    def get_latest_report(self, conversion_id: str) -> Optional[ValidationReport]:
        """Get the latest report for a conversion."""
        reports = self.get_reports_for_conversion(conversion_id)
        return reports[0] if reports else None


class ReportFormatter:
    """Formats reports into different output formats."""
    
    def to_json(self, report: ValidationReport) -> str:
        """Format report as JSON."""
        return json.dumps({
            'report_id': report.report_id,
            'conversion_id': report.conversion_id,
            'generated_at': report.generated_at,
            'validation_results': report.validation_results,
            'regression_results': report.regression_results,
            'coverage_metrics': report.coverage_metrics,
            'quality_score': report.quality_score,
            'recommendations': report.recommendations,
            'metadata': report.metadata
        }, indent=2, default=str)
    
    def to_html(self, report: ValidationReport) -> str:
        """Format report as HTML."""
        grade = report.quality_score.get('grade', 'N/A') if report.quality_score else 'N/A'
        grade_colors = {'A': '#28a745', 'B': '#17a2b8', 'C': '#ffc107', 'D': '#fd7e14', 'F': '#dc3545'}
        grade_color = grade_colors.get(grade, '#6c757d')
        
        # Build HTML
        html = [
            '<!DOCTYPE html>',
            '<html lang="en">',
            '<head>',
            '    <meta charset="UTF-8">',
            '    <meta name="viewport" content="width=device-width, initial-scale=1.0">',
            f'    <title>Validation Report - {report.conversion_id}</title>',
            '    <style>',
            '        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; line-height: 1.6; max-width: 1200px; margin: 0 auto; padding: 20px; }',
            '        h1 { color: #333; border-bottom: 2px solid #007bff; padding-bottom: 10px; }',
            '        h2 { color: #555; margin-top: 30px; }',
            '        .summary { background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0; }',
            f'        .grade {{ font-size: 48px; font-weight: bold; color: {grade_color}; }}',
            '        .score { font-size: 24px; color: #666; }',
            '        .metadata { color: #888; font-size: 14px; }',
            '        .recommendations { background: #fff3cd; padding: 15px; border-radius: 8px; }',
            '        .recommendations li { margin: 5px 0; }',
            '        .alert { background: #f8d7da; color: #721c24; }',
            '        .section { margin: 20px 0; }',
            '        table { width: 100%; border-collapse: collapse; }',
            '        th, td { padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }',
            '        th { background: #007bff; color: white; }',
            '    </style>',
            '</head>',
            '<body>',
            '    <h1>Validation Report</h1>',
            '    <div class="metadata">',
            f'        <p>Report ID: {report.report_id}</p>',
            f'        <p>Conversion ID: {report.conversion_id}</p>',
            f'        <p>Generated: {report.generated_at}</p>',
            '    </div>',
            '    <div class="summary">',
            '        <h2>Summary</h2>',
            f'        <p class="grade">Grade: {grade}</p>',
        ]
        
        if report.quality_score:
            score = report.quality_score.get('overall_score', 0)
            html.append(f'        <p class="score">Score: {score:.2f}</p>')
        
        html.append('    </div>')
        
        # Quality breakdown
        if report.quality_score and report.quality_score.get('breakdown'):
            html.append('    <div class="section">')
            html.append('        <h2>Quality Breakdown</h2>')
            html.append('        <table>')
            html.append('            <tr><th>Metric</th><th>Score</th></tr>')
            for k, v in report.quality_score.get('breakdown', {}).items():
                html.append(f'            <tr><td>{k}</td><td>{v:.2f}</td></tr>')
            html.append('        </table>')
            html.append('    </div>')
        
        # Coverage metrics
        if report.coverage_metrics:
            cov = report.coverage_metrics
            html.append('    <div class="section">')
            html.append('        <h2>Coverage Metrics</h2>')
            html.append(f'        <p>Overall Coverage: {cov.get("overall_coverage", 0):.2f}</p>')
            html.append(f'        <p>Java Coverage: {cov.get("java_coverage", 0):.2f}</p>')
            html.append(f'        <p>Bedrock Coverage: {cov.get("bedrock_coverage", 0):.2f}</p>')
            html.append('    </div>')
        
        # Regression status
        if report.regression_results:
            reg = report.regression_results
            html.append('    <div class="section">')
            html.append('        <h2>Regression Status</h2>')
            html.append(f'        <p>Regression Detected: {reg.get("regression_detected", False)}</p>')
            html.append(f'        <p>Severity: {reg.get("severity", "none")}</p>')
            html.append('    </div>')
        
        # Recommendations
        html.append('    <div class="section">')
        html.append('        <h2>Recommendations</h2>')
        html.append('        <ul class="recommendations">')
        for rec in report.recommendations:
            alert_class = 'alert' if 'REGRESSION' in rec or 'FAILED' in rec else ''
            html.append(f'            <li class="{alert_class}">{rec}</li>')
        html.append('        </ul>')
        html.append('    </div>')
        
        html.append('</body>')
        html.append('</html>')
        
        return '\n'.join(html)
    
    def to_markdown(self, report: ValidationReport) -> str:
        """Format report as Markdown."""
        grade = report.quality_score.get('grade', 'N/A') if report.quality_score else 'N/A'
        
        md = [
            f'# Validation Report',
            '',
            f'**Report ID:** {report.report_id}',
            f'**Conversion ID:** {report.conversion_id}',
            f'**Generated:** {report.generated_at}',
            '',
            '## Summary',
            '',
            f'- **Grade:** {grade}',
        ]
        
        if report.quality_score:
            score = report.quality_score.get('overall_score', 0)
            md.append(f'- **Score:** {score:.2f}')
        
        md.append('')
        
        if report.quality_score and report.quality_score.get('breakdown'):
            md.append('## Quality Breakdown')
            md.append('')
            for metric, score in report.quality_score['breakdown'].items():
                md.append(f'- {metric}: {score:.2f}')
            md.append('')
        
        if report.coverage_metrics:
            cov = report.coverage_metrics
            md.append('## Coverage Metrics')
            md.append('')
            md.append(f'- Overall Coverage: {cov.get("overall_coverage", 0):.2f}')
            md.append(f'- Java Coverage: {cov.get("java_coverage", 0):.2f}')
            md.append(f'- Bedrock Coverage: {cov.get("bedrock_coverage", 0):.2f}')
            md.append('')
        
        if report.regression_results:
            reg = report.regression_results
            md.append('## Regression Status')
            md.append('')
            md.append(f'- Regression Detected: {reg.get("regression_detected", False)}')
            md.append(f'- Severity: {reg.get("severity", "none")}')
            md.append('')
        
        if report.recommendations:
            md.append('## Recommendations')
            md.append('')
            for rec in report.recommendations:
                md.append(f'- {rec}')
        
        return '\n'.join(md)


class AlertSystem:
    """Manages alerts based on validation results."""
    
    def __init__(self):
        self.alert_thresholds = {
            'critical_regression': {'severity': 'critical', 'enabled': True},
            'low_quality': {'grade': 'D', 'enabled': True},
            'validation_failed': {'enabled': True},
            'coverage_low': {'threshold': 0.5, 'enabled': True}
        }
        self.alerts: List[Dict[str, Any]] = []
    
    def check_and_alert(self, report: ValidationReport) -> List[Dict[str, Any]]:
        """Check report and generate alerts if needed."""
        new_alerts = []
        
        # Check for critical regression
        if report.regression_results and report.regression_results.get('regression_detected'):
            if report.regression_results.get('severity') in ['critical', 'major']:
                alert = {
                    'type': 'critical_regression',
                    'severity': 'high',
                    'conversion_id': report.conversion_id,
                    'message': f"Critical regression detected: {report.regression_results.get('severity')}",
                    'timestamp': datetime.now().isoformat()
                }
                new_alerts.append(alert)
                self.alerts.append(alert)
        
        # Check for low quality
        if report.quality_score:
            grade = report.quality_score.get('grade', 'N/A')
            if grade in ['D', 'F']:
                alert = {
                    'type': 'low_quality',
                    'severity': 'medium',
                    'conversion_id': report.conversion_id,
                    'message': f"Low quality grade: {grade}",
                    'timestamp': datetime.now().isoformat()
                }
                new_alerts.append(alert)
                self.alerts.append(alert)
        
        # Check for validation failure
        if report.validation_results:
            if isinstance(report.validation_results, dict) and not report.validation_results.get('is_valid', True):
                alert = {
                    'type': 'validation_failed',
                    'severity': 'high',
                    'conversion_id': report.conversion_id,
                    'message': "Validation failed",
                    'timestamp': datetime.now().isoformat()
                }
                new_alerts.append(alert)
                self.alerts.append(alert)
        
        # Check for low coverage
        if report.coverage_metrics:
            coverage = report.coverage_metrics.get('overall_coverage', 1.0)
            if coverage < self.alert_thresholds['coverage_low']['threshold']:
                alert = {
                    'type': 'coverage_low',
                    'severity': 'low',
                    'conversion_id': report.conversion_id,
                    'message': f"Low coverage: {coverage:.2f}",
                    'timestamp': datetime.now().isoformat()
                }
                new_alerts.append(alert)
                self.alerts.append(alert)
        
        return new_alerts
    
    def get_recent_alerts(self, count: int = 10) -> List[Dict[str, Any]]:
        """Get recent alerts."""
        return self.alerts[-count:]
    
    def clear_alerts(self):
        """Clear all alerts."""
        self.alerts = []


# Singleton instances
_report_generator: Optional[ReportGenerator] = None
_report_formatter: Optional[ReportFormatter] = None
_alert_system: Optional[AlertSystem] = None


def get_report_generator() -> ReportGenerator:
    """Get report generator singleton."""
    global _report_generator
    if _report_generator is None:
        _report_generator = ReportGenerator()
    return _report_generator


def get_report_formatter() -> ReportFormatter:
    """Get report formatter singleton."""
    global _report_formatter
    if _report_formatter is None:
        _report_formatter = ReportFormatter()
    return _report_formatter


def get_alert_system() -> AlertSystem:
    """Get alert system singleton."""
    global _alert_system
    if _alert_system is None:
        _alert_system = AlertSystem()
    return _alert_system
