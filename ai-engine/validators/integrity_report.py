"""
Integrity Report Generator

Generates detailed integrity validation reports.
"""

import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from .integrity_pipeline import IntegrityValidationReport

logger = logging.getLogger(__name__)


class IntegrityReportGenerator:
    """
    Generates detailed integrity validation reports.
    
    Creates reports in various formats (JSON, HTML, Markdown).
    """
    
    def __init__(self):
        pass
    
    def generate_report(
        self,
        validation_result: IntegrityValidationReport,
        format: str = 'json'
    ) -> str:
        """
        Generate report in specified format.
        
        Args:
            validation_result: The validation report data
            format: Output format ('json', 'html', 'markdown')
            
        Returns:
            Formatted report string
        """
        format = format.lower()
        
        if format == 'json':
            return self._generate_json_report(validation_result)
        elif format == 'html':
            return self._generate_html_report(validation_result)
        elif format == 'markdown' or format == 'md':
            return self._generate_markdown_report(validation_result)
        else:
            logger.warning(f"Unknown format {format}, defaulting to JSON")
            return self._generate_json_report(validation_result)
    
    def _generate_json_report(self, report: IntegrityValidationReport) -> str:
        """Generate JSON report."""
        return json.dumps(report.to_dict(), indent=2)
    
    def _generate_html_report(self, report: IntegrityValidationReport) -> str:
        """Generate HTML report."""
        status_class = "valid" if report.overall_valid else "invalid"
        status_text = "VALID" if report.overall_valid else "INVALID"
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Integrity Report - {report.conversion_id}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
               margin: 40px; background: #f5f5f5; }}
        .container {{ max-width: 900px; margin: 0 auto; background: white; 
                     border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .header {{ padding: 20px; border-bottom: 1px solid #eee; }}
        .status {{ display: inline-block; padding: 8px 16px; border-radius: 4px; 
                   font-weight: bold; }}
        .status.valid {{ background: #d4edda; color: #155724; }}
        .status.invalid {{ background: #f8d7da; color: #721c24; }}
        .section {{ padding: 20px; border-bottom: 1px solid #eee; }}
        .section h3 {{ margin-top: 0; color: #333; }}
        .metric {{ display: flex; justify-content: space-between; padding: 8px 0; }}
        .metric-label {{ color: #666; }}
        .metric-value {{ font-weight: 500; }}
        .metric-value.pass {{ color: #28a745; }}
        .metric-value.fail {{ color: #dc3545; }}
        .errors {{ background: #fff5f5; border-left: 3px solid #dc3545; 
                   padding: 10px; margin: 10px 0; }}
        .error-item {{ color: #dc3545; margin: 4px 0; }}
        .grade {{ font-size: 48px; font-weight: bold; text-align: center; 
                 padding: 20px; }}
        .grade-A {{ color: #28a745; }}
        .grade-B {{ color: #17a2b8; }}
        .grade-C {{ color: #ffc107; }}
        .grade-D {{ color: #fd7e14; }}
        .grade-F {{ color: #dc3545; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Output Integrity Report</h1>
            <p>Conversion ID: <strong>{report.conversion_id}</strong></p>
            <p>Generated: {report.timestamp}</p>
            <div class="status {status_class}">{status_text}</div>
        </div>
        
        <div class="section">
            <h3>Quality Assessment</h3>
            <div class="grade grade-{report.quality_grade}">{report.quality_grade}</div>
            <div class="metric">
                <span class="metric-label">Score</span>
                <span class="metric-value">{report.quality_score:.1%}</span>
            </div>
            <div class="metric">
                <span class="metric-label">Recommendation</span>
                <span class="metric-value">{report.quality_recommendation}</span>
            </div>
        </div>
        
        <div class="section">
            <h3>Package Information</h3>
            <div class="metric">
                <span class="metric-label">File Count</span>
                <span class="metric-value">{report.file_count}</span>
            </div>
            <div class="metric">
                <span class="metric-label">Total Size</span>
                <span class="metric-value">{self._format_size(report.total_size)}</span>
            </div>
            <div class="metric">
                <span class="metric-label">Package Hash</span>
                <span class="metric-value" style="font-family: monospace; font-size: 12px;">{report.package_hash[:16]}...</span>
            </div>
        </div>
        
        <div class="section">
            <h3>Validation Results</h3>
            <div class="metric">
                <span class="metric-label">Package Valid</span>
                <span class="metric-value {'pass' if report.package_valid else 'fail'}">
                    {'✓' if report.package_valid else '✗'} {report.package_valid}
                </span>
            </div>
            <div class="metric">
                <span class="metric-label">Manifest Valid</span>
                <span class="metric-value {'pass' if report.manifest_valid else 'fail'}">
                    {'✓' if report.manifest_valid else '✗'} {report.manifest_valid}
                </span>
            </div>
            <div class="metric">
                <span class="metric-label">Integrity Valid</span>
                <span class="metric-value {'pass' if report.integrity_valid else 'fail'}">
                    {'✓' if report.integrity_valid else '✗'} {report.integrity_valid}
                </span>
            </div>
            <div class="metric">
                <span class="metric-label">Completeness</span>
                <span class="metric-value">{report.completeness_percentage:.1f}%</span>
            </div>
            <div class="metric">
                <span class="metric-label">Correlation</span>
                <span class="metric-value">{report.correlation_score:.1%}</span>
            </div>
            <div class="metric">
                <span class="metric-label">Schema Valid</span>
                <span class="metric-value">{report.schema_valid_ratio:.1%}</span>
            </div>
        </div>
"""
        
        # Add errors section if any
        all_errors = (report.package_errors + report.manifest_errors + 
                      report.integrity_errors + report.schema_errors)
        if all_errors:
            html += """
        <div class="section">
            <h3>Errors</h3>
"""
            for error in all_errors[:10]:  # Limit to first 10
                error_type = error.get('type', 'unknown')
                message = error.get('message', 'No message')
                html += f'            <div class="errors"><div class="error-item">[{error_type}] {message}</div></div>\n'
            
            if len(all_errors) > 10:
                html += f'            <div class="errors"><div class="error-item">... and {len(all_errors) - 10} more errors</div></div>\n'
            
            html += "        </div>\n"
        
        html += f"""
        <div class="section">
            <h3>Summary</h3>
            <p>{report.summary}</p>
        </div>
    </div>
</body>
</html>"""
        
        return html
    
    def _generate_markdown_report(self, report: IntegrityValidationReport) -> str:
        """Generate Markdown report."""
        status_emoji = "✅" if report.overall_valid else "❌"
        
        md = f"""# Output Integrity Report

**Conversion ID:** `{report.conversion_id}`  
**Generated:** {report.timestamp}  
**Status:** {status_emoji} **{"VALID" if report.overall_valid else "INVALID"}**

---

## Quality Assessment

| Metric | Value |
|--------|-------|
| Grade | **{report.quality_grade}** |
| Score | {report.quality_score:.1%} |
| Recommendation | {report.quality_recommendation} |

---

## Package Information

| Metric | Value |
|--------|-------|
| File Count | {report.file_count} |
| Total Size | {self._format_size(report.total_size)} |
| Package Hash | `{report.package_hash[:32]}...` |

---

## Validation Results

| Check | Status |
|-------|--------|
| Package Valid | {'✅' if report.package_valid else '❌'} |
| Manifest Valid | {'✅' if report.manifest_valid else '❌'} |
| Integrity Valid | {'✅' if report.integrity_valid else '❌'} |
| Completeness | {report.completeness_percentage:.1f}% |
| Correlation | {report.correlation_score:.1%} |
| Schema Valid | {report.schema_valid_ratio:.1%} |
"""
        
        # Add errors section
        all_errors = (report.package_errors + report.manifest_errors + 
                      report.integrity_errors + report.schema_errors)
        if all_errors:
            md += "\n## Errors\n\n"
            for error in all_errors[:10]:
                error_type = error.get('type', 'unknown')
                message = error.get('message', 'No message')
                md += f"- `[{error_type}]` {message}\n"
            
            if len(all_errors) > 10:
                md += f"\n*... and {len(all_errors) - 10} more errors*\n"
        
        md += f"""

---

## Summary

{report.summary}
"""
        
        return md
    
    def _format_size(self, size: int) -> str:
        """Format file size in human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"


# Convenience function
def generate_integrity_report(
    validation_result: IntegrityValidationReport,
    format: str = 'json'
) -> str:
    """Generate integrity report in specified format."""
    generator = IntegrityReportGenerator()
    return generator.generate_report(validation_result, format)
