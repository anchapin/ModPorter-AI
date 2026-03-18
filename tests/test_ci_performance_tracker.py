"""Tests for CI Performance Tracker"""

import json
import os
import tempfile
import time
from pathlib import Path
from unittest import mock

import pytest

# Add scripts directory to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from ci_performance_tracker import PerformanceTracker, PerformanceMetric


class TestPerformanceMetric:
    """Test PerformanceMetric dataclass"""

    def test_create_metric(self):
        metric = PerformanceMetric(
            step="test-step",
            duration_seconds=10.5,
            start_timestamp=1000.0,
            end_timestamp=1010.5,
            recorded_at="2026-03-10T12:00:00Z"
        )
        assert metric.step == "test-step"
        assert metric.duration_seconds == 10.5

    def test_metric_to_dict(self):
        metric = PerformanceMetric(
            step="test-step",
            duration_seconds=10.5,
            start_timestamp=1000.0,
            end_timestamp=1010.5,
            recorded_at="2026-03-10T12:00:00Z"
        )
        d = metric.to_dict()
        assert d['step'] == "test-step"
        assert d['duration_seconds'] == 10.5


class TestPerformanceTracker:
    """Test PerformanceTracker class"""

    @pytest.fixture
    def tracker(self):
        """Create tracker with temporary directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = PerformanceTracker(tmpdir)
            yield tracker

    def test_init_creates_directory(self):
        """Test that initialization creates the data directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = PerformanceTracker(tmpdir)
            assert tracker.data_dir.exists()

    def test_record_metric(self, tracker):
        """Test recording a single metric"""
        result = tracker.record_metric("test-step", 1000.0, 1010.5)
        assert result['step'] == "test-step"
        assert result['duration_seconds'] == 10.5

    def test_record_multiple_metrics(self, tracker):
        """Test recording multiple metrics"""
        tracker.record_metric("step-1", 1000.0, 1005.0)
        tracker.record_metric("step-2", 1005.0, 1020.0)

        metric_files = list(tracker.data_dir.glob("step-*.json"))
        assert len(metric_files) == 2

    def test_aggregate_metrics(self, tracker):
        """Test aggregating metrics"""
        tracker.record_metric("step-1", 1000.0, 1005.0)
        tracker.record_metric("step-2", 1005.0, 1025.0)

        summary = tracker.aggregate_metrics()

        assert summary['steps_count'] == 2
        assert summary['total_duration_seconds'] == 25.0
        assert summary['average_step_duration'] == 12.5

    def test_aggregate_empty(self, tracker):
        """Test aggregating when no metrics exist"""
        summary = tracker.aggregate_metrics()
        assert summary['steps_count'] == 0

    def test_get_summary(self, tracker):
        """Test retrieving summary"""
        tracker.record_metric("step-1", 1000.0, 1010.0)
        tracker.aggregate_metrics()

        summary = tracker.get_summary()
        assert summary is not None
        assert summary['steps_count'] == 1

    def test_get_summary_no_file(self, tracker):
        """Test retrieving summary when file doesn't exist"""
        summary = tracker.get_summary()
        assert summary is None

    def test_get_slow_steps(self, tracker):
        """Test identifying slow steps"""
        tracker.record_metric("fast-step", 1000.0, 1010.0)
        tracker.record_metric("slow-step", 1010.0, 1320.0)  # 310 seconds
        tracker.aggregate_metrics()

        slow = tracker.get_slow_steps(threshold_seconds=300)
        assert len(slow) == 1
        assert slow[0]['step'] == "slow-step"

    def test_compare_with_baseline_no_metrics(self, tracker):
        """Test comparison when no metrics exist"""
        result = tracker.compare_with_baseline()
        assert result == {}

    def test_compare_with_baseline_creates_baseline(self, tracker):
        """Test that comparison creates baseline on first run"""
        tracker.record_metric("step-1", 1000.0, 1010.0)
        tracker.aggregate_metrics()

        result = tracker.compare_with_baseline()
        assert result['status'] == 'baseline_created'

        # Verify baseline file exists
        baseline_file = tracker.data_dir / "baseline.json"
        assert baseline_file.exists()

    def test_compare_metrics_regression(self, tracker):
        """Test detecting performance regression"""
        # Create baseline
        tracker.record_metric("step-1", 1000.0, 1010.0)
        tracker.aggregate_metrics()
        tracker.compare_with_baseline()

        # Clear metrics
        for f in tracker.data_dir.glob("step-*.json"):
            f.unlink()

        # New slower metrics
        tracker.record_metric("step-1", 2000.0, 2100.0)  # 100 seconds vs 10
        tracker.aggregate_metrics()

        result = tracker.compare_with_baseline()
        assert result['status'] == 'regression'
        assert result['diff_seconds'] > 60

    def test_compare_metrics_improvement(self, tracker):
        """Test detecting performance improvement"""
        # Create baseline
        tracker.record_metric("step-1", 1000.0, 1100.0)  # 100 seconds
        tracker.aggregate_metrics()
        tracker.compare_with_baseline()

        # Clear metrics
        for f in tracker.data_dir.glob("step-*.json"):
            f.unlink()

        # Faster metrics
        tracker.record_metric("step-1", 2000.0, 2010.0)  # 10 seconds
        tracker.aggregate_metrics()

        result = tracker.compare_with_baseline()
        assert result['status'] == 'improvement'
        assert result['diff_seconds'] < -60

    def test_generate_pr_comment_no_metrics(self, tracker):
        """Test PR comment generation with no metrics"""
        comment = tracker.generate_pr_comment()
        assert "No performance metrics" in comment

    def test_generate_pr_comment_with_metrics(self, tracker):
        """Test PR comment generation with metrics"""
        tracker.record_metric("step-1", 1000.0, 1010.0)
        tracker.record_metric("step-2", 1010.0, 1360.0)  # 350 seconds
        tracker.aggregate_metrics()

        comment = tracker.generate_pr_comment()
        assert "Build Performance Report" in comment
        assert "Total Duration" in comment
        assert "step-2" in comment  # Should include slow step

    def test_to_json(self, tracker):
        """Test JSON export"""
        tracker.record_metric("step-1", 1000.0, 1010.0)
        tracker.aggregate_metrics()

        json_str = tracker.to_json()
        data = json.loads(json_str)

        assert data['steps_count'] == 1
        assert len(data['steps']) == 1

    @mock.patch.dict(os.environ, {
        'GITHUB_RUN_ID': '123',
        'GITHUB_RUN_NUMBER': '45',
        'GITHUB_REF_NAME': 'main',
        'GITHUB_SHA': 'abc123',
        'GITHUB_WORKFLOW': 'CI'
    })
    def test_tracker_with_github_env(self):
        """Test tracker with GitHub environment variables"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = PerformanceTracker(tmpdir)
            tracker.record_metric("step-1", 1000.0, 1010.0)
            tracker.aggregate_metrics()

            summary = tracker.get_summary()
            assert summary['run_id'] == '123'
            assert summary['run_number'] == 45
            assert summary['branch'] == 'main'
            assert summary['commit'] == 'abc123'
            assert summary['workflow'] == 'CI'


class TestIntegration:
    """Integration tests"""

    def test_full_workflow(self):
        """Test complete tracking workflow"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = PerformanceTracker(tmpdir)

            # Record metrics
            tracker.record_metric("checkout", 1000.0, 1010.0)
            tracker.record_metric("install-deps", 1010.0, 1040.0)
            tracker.record_metric("run-tests", 1040.0, 1080.0)

            # Aggregate
            summary = tracker.aggregate_metrics()
            assert summary['steps_count'] == 3
            assert summary['total_duration_seconds'] == 80.0

            # Compare (baseline creation)
            result = tracker.compare_with_baseline()
            assert result['status'] == 'baseline_created'

            # Generate report
            comment = tracker.generate_pr_comment()
            assert "Build Performance Report" in comment
            assert "80.0s" in comment

    def test_metric_step_name_sanitization(self, tmp_path):
        """Test that special characters in step names are handled"""
        tracker = PerformanceTracker(str(tmp_path))
        tracker.record_metric("step/with/slashes", 1000.0, 1010.0)

        metric_files = list(tracker.data_dir.glob("step-*.json"))
        assert len(metric_files) == 1

        with open(metric_files[0]) as f:
            data = json.load(f)
            assert data['step'] == "step/with/slashes"
