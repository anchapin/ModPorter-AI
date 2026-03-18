"""Tests for technical debt tracking system."""

import json
import sys
import tempfile
from pathlib import Path

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.debt_tracker import (
    DebtCategory,
    DebtSeverity,
    DebtTracker,
    DebtItem,
)


class TestDebtItem:
    """Tests for DebtItem dataclass."""

    def test_debt_item_creation(self):
        """Test creating a debt item."""
        item = DebtItem(
            issue_number=687,
            description="Optimize authentication",
            file_path="backend/src/security/auth.py",
            line_number=145,
            category=DebtCategory.PERFORMANCE,
            severity=DebtSeverity.CRITICAL,
        )

        assert item.issue_number == 687
        assert item.description == "Optimize authentication"
        assert item.category == DebtCategory.PERFORMANCE
        assert item.severity == DebtSeverity.CRITICAL
        assert item.item_type == "TODO"

    def test_debt_item_to_dict(self):
        """Test converting debt item to dictionary."""
        item = DebtItem(
            issue_number=687,
            description="Test",
            file_path="test.py",
            line_number=1,
            category=DebtCategory.OTHER,
            severity=DebtSeverity.LOW,
        )

        data = item.to_dict()
        assert data["issue_number"] == 687
        assert data["description"] == "Test"
        assert data["category"] == DebtCategory.OTHER.value
        assert data["severity"] == DebtSeverity.LOW.value

    def test_github_issue_link(self):
        """Test generating GitHub issue link."""
        item = DebtItem(
            issue_number=687,
            description="Test",
            file_path="test.py",
            line_number=1,
            category=DebtCategory.OTHER,
            severity=DebtSeverity.LOW,
        )

        link = item.github_issue_link()
        assert "687" in link
        assert "github.com" in link


class TestDebtTracker:
    """Tests for DebtTracker scanner."""

    @pytest.fixture
    def temp_py_file(self):
        """Create a temporary Python file with debt markers."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False
        ) as f:
            f.write('''"""Test module."""

# TODO(#687): Optimize authentication [critical/performance]
def authenticate():
    """Authenticate user."""
    pass

# FIXME(#695): Handle timeout [high/reliability]
def fetch_data():
    """Fetch data from API."""
    pass

# DEBT(#700): Replace legacy API [medium/refactoring]
def old_method():
    """Using deprecated API."""
    pass
''')
            f.flush()
            yield Path(f.name)
        Path(f.name).unlink()

    def test_scan_file(self, temp_py_file):
        """Test scanning a single file."""
        tracker = DebtTracker(root_path=temp_py_file.parent)
        items = tracker.scan_file(temp_py_file)

        assert len(items) == 3

        # Check first item
        todo_item = next(i for i in items if i.item_type == "TODO")
        assert todo_item.issue_number == 687
        assert todo_item.description == "Optimize authentication"
        assert todo_item.category == DebtCategory.PERFORMANCE
        assert todo_item.severity == DebtSeverity.CRITICAL

        # Check FIXME item
        fixme_item = next(i for i in items if i.item_type == "FIXME")
        assert fixme_item.issue_number == 695
        assert fixme_item.severity == DebtSeverity.HIGH

        # Check DEBT item
        debt_item = next(i for i in items if i.item_type == "DEBT")
        assert debt_item.issue_number == 700
        assert debt_item.category == DebtCategory.REFACTORING

    def test_scan_directory(self, temp_py_file):
        """Test scanning a directory."""
        tracker = DebtTracker(root_path=temp_py_file.parent)
        items = tracker.scan_directory(pattern="*.py")

        assert len(items) >= 3

    def test_get_summary(self, temp_py_file):
        """Test generating summary statistics."""
        tracker = DebtTracker(root_path=temp_py_file.parent)
        items = tracker.scan_file(temp_py_file)
        tracker.debt_items = items  # Manually set items

        summary = tracker.get_summary()

        assert summary["total"] == 3
        assert summary["by_severity"]["critical"] == 1
        assert summary["by_severity"]["high"] == 1
        assert summary["by_severity"]["medium"] == 1
        assert "#687" in summary["by_issue"]
        assert summary["by_issue"]["#687"]["count"] == 1

    def test_get_critical_items(self, temp_py_file):
        """Test filtering critical items."""
        tracker = DebtTracker(root_path=temp_py_file.parent)
        items = tracker.scan_file(temp_py_file)
        tracker.debt_items = items  # Manually set items

        critical = tracker.get_critical_items()

        assert len(critical) == 1
        assert critical[0].issue_number == 687

    def test_filter_by_issue(self, temp_py_file):
        """Test filtering by issue number."""
        tracker = DebtTracker(root_path=temp_py_file.parent)
        items = tracker.scan_file(temp_py_file)
        tracker.debt_items = items  # Manually set items

        items_687 = tracker.filter_by_issue(687)
        assert len(items_687) == 1
        assert items_687[0].issue_number == 687

        items_999 = tracker.filter_by_issue(999)
        assert len(items_999) == 0

    def test_parse_category(self):
        """Test category parsing."""
        # Explicit category
        cat = DebtTracker._parse_category("critical/performance")
        assert cat == DebtCategory.PERFORMANCE

        # Category in description
        cat = DebtTracker._parse_category("handle security issues")
        assert cat == DebtCategory.SECURITY

        # Default category
        cat = DebtTracker._parse_category("random text")
        assert cat == DebtCategory.OTHER

    def test_parse_severity(self):
        """Test severity parsing."""
        # Explicit severity
        sev = DebtTracker._parse_severity("critical/performance")
        assert sev == DebtSeverity.CRITICAL

        # All severity levels
        assert DebtTracker._parse_severity("critical") == DebtSeverity.CRITICAL
        assert DebtTracker._parse_severity("high") == DebtSeverity.HIGH
        assert DebtTracker._parse_severity("medium") == DebtSeverity.MEDIUM
        assert DebtTracker._parse_severity("low") == DebtSeverity.LOW

        # Default severity
        sev = DebtTracker._parse_severity("random text")
        assert sev == DebtSeverity.MEDIUM

    def test_export_markdown(self, temp_py_file):
        """Test exporting markdown report."""
        tracker = DebtTracker(root_path=temp_py_file.parent)
        items = tracker.scan_file(temp_py_file)
        tracker.debt_items = items  # Manually set items

        markdown = tracker.export_markdown()

        assert "Technical Debt Report" in markdown
        assert "Summary" in markdown
        assert "#687" in markdown
        assert "CRITICAL" in markdown

    def test_export_markdown_to_file(self, temp_py_file):
        """Test exporting markdown to file."""
        tracker = DebtTracker(root_path=temp_py_file.parent)
        items = tracker.scan_file(temp_py_file)
        tracker.debt_items = items  # Manually set items

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as f:
            output_path = f.name

        try:
            tracker.export_markdown(output_path)

            # Verify file was created
            assert Path(output_path).exists()

            # Verify content
            content = Path(output_path).read_text()
            assert "Technical Debt Report" in content
            assert "#687" in content
        finally:
            Path(output_path).unlink()

    def test_context_extraction(self, temp_py_file):
        """Test context line extraction around debt marker."""
        tracker = DebtTracker(root_path=temp_py_file.parent)
        items = tracker.scan_file(temp_py_file)

        # Find the TODO item
        todo_item = next(i for i in items if i.item_type == "TODO")

        # Verify context includes surrounding lines
        assert "def authenticate" in todo_item.context
        assert ">>>" in todo_item.context  # Indicates the marked line

    def test_empty_directory(self):
        """Test scanning empty directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = DebtTracker(root_path=tmpdir)
            items = tracker.scan_directory()

            assert len(items) == 0
            assert tracker.get_summary()["total"] == 0

    def test_malformed_markers(self):
        """Test that malformed markers are partially matched."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False
        ) as f:
            f.write('''# TODO 687: Missing parentheses
# FIXME(687: Missing closing paren
# TODO(#689): Valid marker
''')
            f.flush()

            tracker = DebtTracker(root_path=Path(f.name).parent)
            items = tracker.scan_file(f.name)

            # Valid marker should be found
            assert len(items) == 1
            assert items[0].issue_number == 689

        Path(f.name).unlink()

    def test_json_serializable(self, temp_py_file):
        """Test that debt items can be serialized to JSON."""
        tracker = DebtTracker(root_path=temp_py_file.parent)
        items = tracker.scan_file(temp_py_file)
        tracker.debt_items = items  # Manually set items

        # Convert to dicts
        items_dict = [item.to_dict() for item in tracker.debt_items]

        # Should be JSON serializable
        json_str = json.dumps(items_dict, default=str)
        assert len(json_str) > 0

        # Parse back
        parsed = json.loads(json_str)
        assert len(parsed) == 3
        assert parsed[0]["issue_number"] == 687
