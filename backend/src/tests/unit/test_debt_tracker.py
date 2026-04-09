"""
Unit tests for Technical Debt Tracking System.
"""

import pytest
import os
from pathlib import Path
from utils.debt_tracker import DebtTracker, DebtSeverity, DebtCategory, DebtItem


class TestDebtTracker:
    @pytest.fixture
    def tracker(self, tmp_path):
        # Create a temporary directory structure with some dummy files
        d = tmp_path / "src"
        d.mkdir()

        f1 = d / "file1.py"
        f1.write_text(
            """
# TODO(#123): Fix this bug [critical/reliability]
print("hello")
# DEBT(#456): Refactor this [low/maintainability]
""",
            encoding="utf-8",
        )

        f2 = d / "file2.py"
        f2.write_text(
            """
# FIXME(#123): Another bug [high]
# Just a comment
""",
            encoding="utf-8",
        )

        return DebtTracker(root_path=tmp_path)

    def test_scan_file(self, tracker, tmp_path):
        file_path = tmp_path / "src" / "file1.py"
        items = tracker.scan_file(file_path)

        assert len(items) == 2
        assert items[0].issue_number == 123
        assert items[0].severity == DebtSeverity.CRITICAL
        assert items[0].category == DebtCategory.RELIABILITY
        assert items[0].item_type == "TODO"

        assert items[1].issue_number == 456
        assert items[1].severity == DebtSeverity.LOW
        assert items[1].category == DebtCategory.MAINTAINABILITY

    def test_scan_directory(self, tracker):
        items = tracker.scan_directory()
        assert len(items) == 3

        # Verify debt_items is updated
        assert len(tracker.debt_items) == 3

    def test_get_summary(self, tracker):
        tracker.scan_directory()
        summary = tracker.get_summary()

        assert summary["total"] == 3
        assert summary["by_severity"]["critical"] == 1
        assert summary["by_severity"]["high"] == 1
        assert summary["by_severity"]["low"] == 1
        assert summary["by_issue"]["#123"]["count"] == 2

    def test_get_critical_items(self, tracker):
        tracker.scan_directory()
        critical = tracker.get_critical_items()
        assert len(critical) == 1
        assert critical[0].issue_number == 123

    def test_filter_by_issue(self, tracker):
        tracker.scan_directory()
        items = tracker.filter_by_issue(456)
        assert len(items) == 1
        assert items[0].item_type == "DEBT"

    def test_export_markdown(self, tracker, tmp_path):
        tracker.scan_directory()
        report_path = tmp_path / "report.md"
        report = tracker.export_markdown(str(report_path))

        assert "# Technical Debt Report" in report
        assert "## Summary" in report
        assert report_path.exists()

    def test_scan_non_existent_file(self, tracker):
        items = tracker.scan_file("non_existent.py")
        assert items == []

    def test_scan_directory_with_exclusions(self, tmp_path):
        d = tmp_path / "excluded"
        d.mkdir()
        f = d / "file.py"
        f.write_text("# TODO(#1): hidden")

        tracker = DebtTracker(root_path=tmp_path)
        items = tracker.scan_directory(exclude_patterns=["**/excluded/**"])
        assert len(items) == 0

    def test_get_summary_empty(self):
        tracker = DebtTracker()
        summary = tracker.get_summary()
        assert summary["total"] == 0

    def test_parse_severity_default(self):
        assert DebtTracker._parse_severity("unknown") == DebtSeverity.MEDIUM

    def test_to_dict_and_str(self):
        item = DebtItem(
            issue_number=1,
            description="desc",
            file_path="f.py",
            line_number=10,
            category=DebtCategory.OTHER,
            severity=DebtSeverity.MEDIUM,
        )
        d = item.to_dict()
        assert d["issue_number"] == 1

        s = str(item)
        assert "TODO(#1): desc" in s
        assert "f.py:10" in s

    def test_github_issue_link(self):
        item = DebtItem(
            issue_number=999,
            description="desc",
            file_path="f.py",
            line_number=1,
            category=DebtCategory.OTHER,
            severity=DebtSeverity.MEDIUM,
        )
        link = item.github_issue_link()
        assert "issues/999" in link

        custom_link = item.github_issue_link(repo="user/repo")
        assert "github.com/user/repo/issues/999" in custom_link
