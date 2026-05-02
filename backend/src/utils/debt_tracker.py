"""
Technical Debt Tracking System

Provides utilities for identifying, categorizing, and tracking technical debt
in the codebase. Integrates with GitHub issues for prioritization.

Convention:
  TODO(#<issue-number>): <description>
  FIXME(#<issue-number>): <description>
  DEBT(#<issue-number>): <description>

Example:
  # TODO(#687): Refactor authentication logic for performance
  # FIXME(#695): Handle edge case in file processing
  # DEBT(#700): Replace legacy API calls with new SDK
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

import structlog

logger = structlog.get_logger()


class DebtSeverity(str, Enum):
    """Severity levels for technical debt."""

    CRITICAL = "critical"  # Blocks production use
    HIGH = "high"  # Significant impact on performance/reliability
    MEDIUM = "medium"  # Should be addressed in next sprint
    LOW = "low"  # Nice to have improvements


class DebtCategory(str, Enum):
    """Categories of technical debt."""

    PERFORMANCE = "performance"  # Performance optimizations needed
    RELIABILITY = "reliability"  # Reliability/error handling
    MAINTAINABILITY = "maintainability"  # Code quality/readability
    TESTING = "testing"  # Test coverage/quality
    SECURITY = "security"  # Security vulnerabilities/hardening
    REFACTORING = "refactoring"  # Code structure improvements
    DOCUMENTATION = "documentation"  # Missing/outdated docs
    DEPENDENCY = "dependency"  # Dependency updates/removal
    OTHER = "other"  # Misc improvements


@dataclass
class DebtItem:
    """Represents a single technical debt item."""

    issue_number: int
    description: str
    file_path: str
    line_number: int
    category: DebtCategory
    severity: DebtSeverity
    item_type: str = field(default="TODO")  # supported: TODO, FIXME, DEBT
    author: Optional[str] = None
    created_date: str = field(default_factory=lambda: datetime.now().isoformat())
    context: str = ""  # Code context around the debt item

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    def github_issue_link(self, repo: str = "anchapin/portkit") -> str:
        """Generate GitHub issue link."""
        return f"https://github.com/{repo}/issues/{self.issue_number}"

    def __str__(self) -> str:
        return (
            f"{self.item_type}(#{self.issue_number}): {self.description} "
            f"[{self.severity}/{self.category}] @ {self.file_path}:{self.line_number}"
        )


class DebtTracker:
    """Scans codebase for technical debt markers and aggregates findings."""

    # Pattern for matching debt markers: TODO/FIXME/DEBT(#123): description
    DEBT_PATTERN = re.compile(
        r"^\s*#\s*(TODO|FIXME|DEBT)\(#(\d+)\):\s*(.+?)(?:\s*\[([^\]]+)\])?\s*$",
        re.MULTILINE,
    )

    def __init__(self, root_path: str | Path = "."):
        """Initialize debt tracker.

        Args:
            root_path: Root directory to scan for debt markers.
        """
        self.root_path = Path(root_path)
        self.debt_items: list[DebtItem] = []

    def scan_file(self, file_path: str | Path) -> list[DebtItem]:
        """Scan a single file for technical debt markers.

        Args:
            file_path: Path to file to scan.

        Returns:
            List of debt items found in file.
        """
        file_path = Path(file_path)
        items = []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except (OSError, UnicodeDecodeError) as e:
            logger.warning(f"Could not read file {file_path}: {e}")
            return items

        for line_num, line in enumerate(lines, 1):
            match = self.DEBT_PATTERN.search(line)
            if not match:
                continue

            item_type, issue_num, description, category_str = match.groups()
            issue_number = int(issue_num)

            # Parse category from description or annotation
            category = self._parse_category(category_str or description)
            severity = self._parse_severity(category_str or description)

            item = DebtItem(
                issue_number=issue_number,
                description=description.strip(),
                file_path=str(file_path.relative_to(self.root_path)),
                line_number=line_num,
                category=category,
                severity=severity,
                item_type=item_type,
                context=self._get_context(lines, line_num),
            )
            items.append(item)

        return items

    def scan_directory(
        self,
        pattern: str = "**/*.py",
        exclude_patterns: Optional[list[str]] = None,
    ) -> list[DebtItem]:
        """Scan directory for technical debt markers.

        Args:
            pattern: Glob pattern for files to scan (default: Python files).
            exclude_patterns: List of patterns to exclude from scan.

        Returns:
            List of all debt items found.
        """
        exclude_patterns = exclude_patterns or [
            "**/.git/**",
            "**/venv/**",
            "**/__pycache__/**",
            "**/.pytest_cache/**",
            "**/node_modules/**",
        ]

        all_items = []
        for file_path in self.root_path.glob(pattern):
            # Check exclusions
            if any(file_path.match(exc) for exc in exclude_patterns):
                continue

            items = self.scan_file(file_path)
            all_items.extend(items)

        self.debt_items = all_items
        return all_items

    def get_summary(self) -> dict:
        """Get summary statistics of debt items.

        Returns:
            Dictionary with summary statistics.
        """
        if not self.debt_items:
            return {
                "total": 0,
                "by_severity": {},
                "by_category": {},
                "by_issue": {},
            }

        summary = {
            "total": len(self.debt_items),
            "by_severity": {},
            "by_category": {},
            "by_issue": {},
        }

        for item in self.debt_items:
            # By severity
            sev = item.severity.value
            summary["by_severity"][sev] = summary["by_severity"].get(sev, 0) + 1

            # By category
            cat = item.category.value
            summary["by_category"][cat] = summary["by_category"].get(cat, 0) + 1

            # By issue
            issue = f"#{item.issue_number}"
            if issue not in summary["by_issue"]:
                summary["by_issue"][issue] = {"count": 0, "items": []}
            summary["by_issue"][issue]["count"] += 1
            summary["by_issue"][issue]["items"].append(str(item))

        return summary

    def get_critical_items(self) -> list[DebtItem]:
        """Get all critical severity debt items.

        Returns:
            List of critical debt items.
        """
        return [item for item in self.debt_items if item.severity == DebtSeverity.CRITICAL]

    def filter_by_issue(self, issue_number: int) -> list[DebtItem]:
        """Get all debt items for a specific issue.

        Args:
            issue_number: GitHub issue number.

        Returns:
            List of debt items for the issue.
        """
        return [item for item in self.debt_items if item.issue_number == issue_number]

    @staticmethod
    def _parse_category(text: str) -> DebtCategory:
        """Parse category from text annotation or description.

        Args:
            text: Text to parse (e.g., "critical/performance").

        Returns:
            DebtCategory enum value.
        """
        text_lower = text.lower()

        for category in DebtCategory:
            if category.value in text_lower:
                return category

        # Default to other if no match
        return DebtCategory.OTHER

    @staticmethod
    def _parse_severity(text: str) -> DebtSeverity:
        """Parse severity from text annotation.

        Args:
            text: Text to parse (e.g., "critical/performance").

        Returns:
            DebtSeverity enum value.
        """
        text_lower = text.lower()

        for severity in DebtSeverity:
            if severity.value in text_lower:
                return severity

        # Default to medium if no match
        return DebtSeverity.MEDIUM

    @staticmethod
    def _get_context(lines: list[str], line_num: int, context_lines: int = 2) -> str:
        """Get surrounding context for a debt marker.

        Args:
            lines: All lines from the file.
            line_num: Line number (1-indexed).
            context_lines: Number of lines before/after to include.

        Returns:
            Context string with surrounding lines.
        """
        start = max(0, line_num - context_lines - 1)
        end = min(len(lines), line_num + context_lines)

        context = []
        for i in range(start, end):
            prefix = ">>>" if i == line_num - 1 else "   "
            context.append(f"{prefix} {i + 1}: {lines[i].rstrip()}")

        return "\n".join(context)

    def export_markdown(self, output_path: Optional[str] = None) -> str:
        """Export debt items as markdown report.

        Args:
            output_path: Optional path to write markdown report.

        Returns:
            Markdown formatted report.
        """
        lines = ["# Technical Debt Report\n"]
        lines.append(f"Generated: {datetime.now().isoformat()}\n")
        lines.append("## Summary\n")

        summary = self.get_summary()
        lines.append(f"- **Total Items**: {summary['total']}\n")

        if summary["by_severity"]:
            lines.append("- **By Severity**:\n")
            for severity in ["critical", "high", "medium", "low"]:
                count = summary["by_severity"].get(severity, 0)
                if count:
                    lines.append(f"  - {severity.capitalize()}: {count}\n")

        if summary["by_category"]:
            lines.append("- **By Category**:\n")
            for category, count in sorted(summary["by_category"].items(), key=lambda x: -x[1]):
                lines.append(f"  - {category.replace('_', ' ').title()}: {count}\n")

        lines.append("\n## Issues by GitHub Issue Number\n")

        if summary["by_issue"]:
            for issue, data in sorted(
                summary["by_issue"].items(),
                key=lambda x: int(x[0].lstrip("#")),
                reverse=True,
            ):
                lines.append(f"### {issue}\n")
                lines.append(f"- Count: {data['count']}\n")
                lines.append("- Items:\n")
                for item in data["items"]:
                    lines.append(f"  - {item}\n")

        lines.append("\n## Detailed View\n")

        # Group by severity
        for severity in [
            DebtSeverity.CRITICAL,
            DebtSeverity.HIGH,
            DebtSeverity.MEDIUM,
            DebtSeverity.LOW,
        ]:
            items = [i for i in self.debt_items if i.severity == severity]
            if not items:
                continue

            lines.append(f"### {severity.value.upper()}\n")

            for item in sorted(items, key=lambda x: (x.file_path, x.line_number)):
                lines.append(f"#### {item.item_type}(#{item.issue_number})\n")
                lines.append(f"- **Description**: {item.description}\n")
                lines.append(f"- **Location**: `{item.file_path}:{item.line_number}`\n")
                lines.append(f"- **Category**: {item.category.value}\n")
                lines.append(f"- **Severity**: {item.severity.value}\n")
                lines.append(f"- **GitHub Issue**: {item.github_issue_link()}\n")
                lines.append("- **Context**:\n```\n")
                lines.append(item.context)
                lines.append("\n```\n")

        report = "".join(lines)

        if output_path:
            Path(output_path).write_text(report, encoding="utf-8")
            logger.info(f"Debt report exported to {output_path}")

        return report
