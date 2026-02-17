"""
Report Export Service for ModPorter AI
Provides export functionality for conversion reports in multiple formats.
"""

import json
import base64
import html
from typing import Dict, Any, Optional
from datetime import datetime
from ..schemas.report_types import InteractiveReport


class ReportExporter:
    """Service for exporting conversion reports in various formats."""

    def __init__(self):
        self.supported_formats = ["json", "html", "csv"]

    def export_to_json(self, report: InteractiveReport, pretty: bool = True) -> str:
        """Export report to JSON format."""
        report_dict = report.to_dict()

        if pretty:
            return json.dumps(report_dict, indent=2, default=str)
        else:
            return json.dumps(report_dict, default=str)

    def export_to_html(self, report: InteractiveReport) -> str:
        """Export report to HTML format."""
        html_template = self._get_html_template()

        # Prepare data for template with proper HTML escaping
        context = {
            "report": self._escape_report_data(report.to_dict()),
            "generation_date": html.escape(datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            "title": html.escape(f"Conversion Report - {report.metadata.job_id}")
        }

        # Template substitution with escaped data
        html_content = html_template.format(**context)
        return html_content

    def _escape_report_data(self, data: Any) -> Any:
        """Recursively escape HTML in report data."""
        if isinstance(data, str):
            return html.escape(data)
        elif isinstance(data, dict):
            return {key: self._escape_report_data(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self._escape_report_data(item) for item in data]
        else:
            return data

    def export_to_csv(self, report: InteractiveReport) -> str:
        """Export report summary to CSV format."""
        csv_content = []

        # Header
        csv_content.append("Section,Metric,Value")

        # Summary data
        summary = report.summary
        csv_content.append(f"Summary,Overall Success Rate,{summary.overall_success_rate}%")
        csv_content.append(f"Summary,Total Features,{summary.total_features}")
        csv_content.append(f"Summary,Converted Features,{summary.converted_features}")
        csv_content.append(f"Summary,Partially Converted,{summary.partially_converted_features}")
        csv_content.append(f"Summary,Failed Features,{summary.failed_features}")
        csv_content.append(f"Summary,Assumptions Applied,{summary.assumptions_applied_count}")
        csv_content.append(f"Summary,Processing Time (s),{summary.processing_time_seconds}")
        csv_content.append(f"Summary,Quality Score,{summary.conversion_quality_score}")

        # Feature analysis
        for feature in report.feature_analysis.features:
            csv_content.append(f"Features,{feature.name},{feature.status}")
            csv_content.append(f"Features,{feature.name} Compatibility,{feature.compatibility_score}%")

        # Assumptions
        for assumption in report.assumptions_report.assumptions:
            csv_content.append(f"Assumptions,{assumption.original_feature},{assumption.impact_level}")

        return "\n".join(csv_content)

    def create_shareable_link(self, report_id: str, base_url: str = "") -> str:
        """Create a shareable link for the report."""
        if not base_url:
            base_url = "https://modporter.ai"  # Default base URL

        return f"{base_url}/reports/{report_id}"

    def generate_download_package(self, report: InteractiveReport) -> Dict[str, str]:
        """Generate a complete download package with all formats."""
        package = {}

        # JSON export
        package["report.json"] = self.export_to_json(report)

        # HTML export
        package["report.html"] = self.export_to_html(report)

        # CSV export
        package["summary.csv"] = self.export_to_csv(report)

        # Metadata file
        metadata = {
            "report_id": report.metadata.report_id,
            "job_id": report.metadata.job_id,
            "generated_at": report.metadata.generation_timestamp.isoformat(),
            "version": report.metadata.version,
            "export_formats": list(package.keys())
        }
        package["metadata.json"] = json.dumps(metadata, indent=2)

        return package

    def _get_html_template(self) -> str:
        """Get HTML template for report export."""
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            line-height: 1.6;
            color: #333;
        }}
        .header {{
            border-bottom: 2px solid #007bff;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        .title {{
            color: #007bff;
            margin: 0;
        }}
        .subtitle {{
            color: #666;
            margin: 5px 0 0 0;
        }}
        .section {{
            margin: 30px 0;
            padding: 20px;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
        }}
        .section-title {{
            color: #007bff;
            margin-top: 0;
            border-bottom: 1px solid #e0e0e0;
            padding-bottom: 10px;
        }}
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }}
        .summary-item {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 6px;
            text-align: center;
        }}
        .summary-value {{
            font-size: 1.5em;
            font-weight: bold;
            color: #007bff;
        }}
        .feature-item {{
            background: #f8f9fa;
            margin: 10px 0;
            padding: 15px;
            border-radius: 6px;
            border-left: 4px solid #007bff;
        }}
        .assumption-item {{
            background: #fff3cd;
            margin: 10px 0;
            padding: 15px;
            border-radius: 6px;
            border-left: 4px solid #ffc107;
        }}
        .status-success {{ color: #28a745; }}
        .status-partial {{ color: #ffc107; }}
        .status-failed {{ color: #dc3545; }}
        .technical-log {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 6px;
            font-family: monospace;
            font-size: 0.9em;
            overflow-x: auto;
        }}
        @media print {{
            body {{ margin: 0; padding: 15px; }}
            .section {{ page-break-inside: avoid; }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1 class="title">ModPorter AI Conversion Report</h1>
        <p class="subtitle">Job ID: {report[metadata][job_id]} | Generated: {generation_date}</p>
    </div>

    <div class="section">
        <h2 class="section-title">Summary</h2>
        <div class="summary-grid">
            <div class="summary-item">
                <div class="summary-value">{report[summary][overall_success_rate]}%</div>
                <div>Success Rate</div>
            </div>
            <div class="summary-item">
                <div class="summary-value">{report[summary][total_features]}</div>
                <div>Total Features</div>
            </div>
            <div class="summary-item">
                <div class="summary-value">{report[summary][converted_features]}</div>
                <div>Converted</div>
            </div>
            <div class="summary-item">
                <div class="summary-value">{report[summary][assumptions_applied_count]}</div>
                <div>Assumptions Applied</div>
            </div>
            <div class="summary-item">
                <div class="summary-value">{report[summary][processing_time_seconds]}s</div>
                <div>Processing Time</div>
            </div>
            <div class="summary-item">
                <div class="summary-value">{report[summary][conversion_quality_score]}</div>
                <div>Quality Score</div>
            </div>
        </div>
    </div>

    <div class="section">
        <h2 class="section-title">Feature Analysis</h2>
        <p><strong>Compatibility Summary:</strong> {report[feature_analysis][compatibility_mapping_summary]}</p>
        <p><strong>Impact Assessment:</strong> {report[feature_analysis][impact_assessment_summary]}</p>

        <h3>Features by Category</h3>
        <div id="features-content">
            <!-- Features would be dynamically populated here -->
        </div>
    </div>

    <div class="section">
        <h2 class="section-title">Smart Assumptions</h2>
        <p><strong>Total Assumptions:</strong> {report[assumptions_report][total_assumptions_count]}</p>
        <div id="assumptions-content">
            <!-- Assumptions would be dynamically populated here -->
        </div>
    </div>

    <div class="section">
        <h2 class="section-title">Technical Information</h2>
        <h3>Performance Metrics</h3>
        <div class="technical-log">
            <!-- Performance metrics would be shown here -->
        </div>

        <h3>Optimization Opportunities</h3>
        <ul id="optimizations-list">
            <!-- Optimization suggestions would be listed here -->
        </ul>
    </div>

    <div class="section">
        <p><em>Report generated by ModPorter AI v{report[metadata][version]} on {generation_date}</em></p>
    </div>
</body>
</html>
        """


class PDFExporter:
    """PDF export functionality (requires additional dependencies)."""

    def __init__(self):
        self.available = self._check_dependencies()

    def _check_dependencies(self) -> bool:
        """Check if PDF export dependencies are available."""
        try:
            import importlib.util
            spec = importlib.util.find_spec("weasyprint")  # or reportlab
            return spec is not None
        except ImportError:
            return False

    def export_to_pdf(self, report: InteractiveReport) -> Optional[bytes]:
        """Export report to PDF format."""
        if not self.available:
            return None

        try:
            import weasyprint

            # Get HTML content
            exporter = ReportExporter()
            html_content = exporter.export_to_html(report)

            # Convert to PDF
            pdf_document = weasyprint.HTML(string=html_content)
            pdf_bytes = pdf_document.write_pdf()

            return pdf_bytes

        except Exception as e:
            print(f"PDF export failed: {e}")
            return None

    def export_to_pdf_base64(self, report: InteractiveReport) -> Optional[str]:
        """Export report to PDF and return as base64 string."""
        pdf_bytes = self.export_to_pdf(report)
        if pdf_bytes:
            return base64.b64encode(pdf_bytes).decode('utf-8')
        return None
