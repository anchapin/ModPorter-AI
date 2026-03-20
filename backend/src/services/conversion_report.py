"""
Conversion Report Generator

Generate comprehensive reports for conversion jobs.
"""

import logging
import json
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class ConversionReport:
    """Conversion report for a single job."""

    def __init__(
        self,
        job_id: str,
        java_code: str,
        bedrock_code: Optional[str] = None,
    ):
        self.job_id = job_id
        self.java_code = java_code
        self.bedrock_code = bedrock_code
        self.start_time = datetime.utcnow()
        self.end_time = None
        self.status = "pending"
        self.stages = []
        self.assumptions = []
        self.issues = []
        self.metrics = {}

    def add_stage(self, name: str, status: str, duration_ms: float, details: Optional[str] = None):
        """Add a processing stage."""
        self.stages.append(
            {
                "name": name,
                "status": status,
                "duration_ms": duration_ms,
                "details": details or "",
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

    def add_assumption(self, feature: str, assumption: str, confidence: float):
        """Add a smart assumption."""
        self.assumptions.append(
            {
                "feature": feature,
                "assumption": assumption,
                "confidence": confidence,
            }
        )

    def add_issue(self, issue: str, severity: str = "warning"):
        """Add an issue."""
        self.issues.append(
            {
                "issue": issue,
                "severity": severity,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

    def set_metrics(self, metrics: Dict[str, Any]):
        """Set conversion metrics."""
        self.metrics = metrics

    def complete(self, bedrock_code: str, success: bool = True):
        """Mark conversion as complete."""
        self.bedrock_code = bedrock_code
        self.end_time = datetime.utcnow()
        self.status = "completed" if success else "failed"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "job_id": self.job_id,
            "status": self.status,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "java_code": self.java_code,
            "bedrock_code": self.bedrock_code,
            "stages": self.stages,
            "assumptions": self.assumptions,
            "issues": self.issues,
            "metrics": self.metrics,
        }

    def to_markdown(self) -> str:
        """Convert to Markdown report."""
        lines = [
            f"# Conversion Report",
            f"",
            f"**Job ID**: {self.job_id}",
            f"**Status**: {self.status}",
            f"**Started**: {self.start_time.isoformat()}",
            f"**Completed**: {self.end_time.isoformat() if self.end_time else 'N/A'}",
            f"",
            f"## Processing Stages",
            f"",
        ]

        for stage in self.stages:
            status_icon = "✓" if stage["status"] == "success" else "✗"
            lines.append(f"- {status_icon} **{stage['name']}**: {stage['duration_ms']:.0f}ms")
            if stage.get("details"):
                lines.append(f"  - {stage['details']}")

        if self.assumptions:
            lines.extend(
                [
                    f"",
                    f"## Smart Assumptions",
                    f"",
                ]
            )
            for assumption in self.assumptions:
                lines.append(
                    f"- **{assumption['feature']}**: {assumption['assumption']} (confidence: {assumption['confidence']:.0%})"
                )

        if self.issues:
            lines.extend(
                [
                    f"",
                    f"## Issues",
                    f"",
                ]
            )
            for issue in self.issues:
                icon = "⚠️" if issue["severity"] == "warning" else "❌"
                lines.append(f"- {icon} {issue['issue']}")

        if self.metrics:
            lines.extend(
                [
                    f"",
                    f"## Metrics",
                    f"",
                ]
            )
            for key, value in self.metrics.items():
                lines.append(f"- **{key}**: {value}")

        return "\n".join(lines)


class ConversionReportGenerator:
    """Generate conversion reports."""

    def __init__(self, output_dir: str = "/app/conversion_reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Report generator initialized. Output dir: {self.output_dir}")

    def generate_report(
        self,
        job_id: str,
        java_code: str,
        bedrock_code: Optional[str] = None,
    ) -> ConversionReport:
        """
        Generate a conversion report.

        Args:
            job_id: Job ID
            java_code: Java source code
            bedrock_code: Bedrock code (optional)

        Returns:
            Conversion report
        """
        report = ConversionReport(job_id, java_code, bedrock_code)
        return report

    def save_report(self, report: ConversionReport, format: str = "json") -> str:
        """
        Save report to file.

        Args:
            report: Report to save
            format: Output format (json or markdown)

        Returns:
            File path
        """
        timestamp = report.start_time.strftime("%Y%m%d_%H%M%S")

        if format == "json":
            filename = f"report_{report.job_id}_{timestamp}.json"
            filepath = self.output_dir / filename

            with open(filepath, "w") as f:
                json.dump(report.to_dict(), f, indent=2)

            logger.info(f"Saved JSON report: {filepath}")

        elif format == "markdown":
            filename = f"report_{report.job_id}_{timestamp}.md"
            filepath = self.output_dir / filename

            with open(filepath, "w") as f:
                f.write(report.to_markdown())

            logger.info(f"Saved Markdown report: {filepath}")

        else:
            raise ValueError(f"Unknown format: {format}")

        return str(filepath)

    def get_report(self, job_id: str) -> Optional[ConversionReport]:
        """
        Load report from file.

        Args:
            job_id: Job ID

        Returns:
            Report or None
        """
        # Find report file
        for filepath in self.output_dir.glob(f"report_{job_id}_*.json"):
            with open(filepath, "r") as f:
                data = json.load(f)

            report = ConversionReport(
                job_id=data["job_id"],
                java_code=data["java_code"],
                bedrock_code=data.get("bedrock_code"),
            )
            report.start_time = datetime.fromisoformat(data["start_time"])
            report.end_time = (
                datetime.fromisoformat(data["end_time"]) if data.get("end_time") else None
            )
            report.status = data["status"]
            report.stages = data["stages"]
            report.assumptions = data["assumptions"]
            report.issues = data["issues"]
            report.metrics = data["metrics"]

            return report

        return None


# Singleton instance
_report_generator = None


def get_report_generator() -> ConversionReportGenerator:
    """Get or create report generator singleton."""
    global _report_generator
    if _report_generator is None:
        _report_generator = ConversionReportGenerator()
    return _report_generator
