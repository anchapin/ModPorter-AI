#!/usr/bin/env python3
"""
CI Performance Tracking Module
Records and analyzes build performance metrics from GitHub Actions
"""

import json
import os
import sys
import time
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import argparse


@dataclass
class PerformanceMetric:
    """Single performance metric"""

    step: str
    duration_seconds: float
    start_timestamp: float
    end_timestamp: float
    recorded_at: str
    run_id: Optional[str] = None
    run_number: Optional[int] = None
    branch: Optional[str] = None

    def to_dict(self) -> Dict:
        return asdict(self)


class PerformanceTracker:
    """Tracks and manages CI performance metrics"""

    def __init__(self, data_dir: str = ".github/perf-metrics"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.run_id = os.getenv("GITHUB_RUN_ID")
        self.run_number = os.getenv("GITHUB_RUN_NUMBER")
        self.branch = os.getenv("GITHUB_REF_NAME", "unknown")
        self.commit = os.getenv("GITHUB_SHA", "unknown")

    def record_metric(self, step: str, start: float, end: float) -> Dict:
        """Record a performance metric for a step"""
        metric = PerformanceMetric(
            step=step,
            duration_seconds=end - start,
            start_timestamp=start,
            end_timestamp=end,
            recorded_at=datetime.now(timezone.utc).isoformat(),
            run_id=self.run_id,
            run_number=int(self.run_number) if self.run_number else None,
            branch=self.branch,
        )

        metric_file = self.data_dir / f"step-{step.replace('/', '-')}.json"
        with open(metric_file, "w") as f:
            json.dump(metric.to_dict(), f, indent=2)

        print(f"✅ Recorded: {step} ({metric.duration_seconds:.1f}s)")
        return metric.to_dict()

    def aggregate_metrics(self) -> Dict:
        """Aggregate all recorded metrics"""
        metrics_files = list(self.data_dir.glob("step-*.json"))

        steps = []
        total_duration = 0

        for metric_file in sorted(metrics_files):
            with open(metric_file, "r") as f:
                metric = json.load(f)
                steps.append(metric)
                total_duration += metric["duration_seconds"]

        summary = {
            "workflow": os.getenv("GITHUB_WORKFLOW", "CI"),
            "run_id": self.run_id,
            "run_number": int(self.run_number) if self.run_number else None,
            "branch": self.branch,
            "commit": self.commit,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_duration_seconds": total_duration,
            "steps_count": len(steps),
            "average_step_duration": total_duration / len(steps) if steps else 0,
            "steps": steps,
        }

        summary_file = self.data_dir / "summary.json"
        with open(summary_file, "w") as f:
            json.dump(summary, f, indent=2)

        if metrics_files:
            print(f"✅ Metrics aggregated ({len(steps)} steps, {total_duration:.1f}s total)")
        else:
            print("⚠️  No metrics found")
        return summary

    def get_summary(self) -> Optional[Dict]:
        """Get current summary"""
        summary_file = self.data_dir / "summary.json"
        if not summary_file.exists():
            return None

        with open(summary_file, "r") as f:
            return json.load(f)

    def compare_with_baseline(self) -> Dict:
        """Compare current metrics with baseline"""
        summary_file = self.data_dir / "summary.json"
        baseline_file = self.data_dir / "baseline.json"

        if not summary_file.exists():
            print("❌ No metrics summary found")
            return {}

        with open(summary_file, "r") as f:
            current = json.load(f)

        if not baseline_file.exists():
            print("ℹ️  No baseline found - creating first baseline")
            with open(baseline_file, "w") as f:
                json.dump(current, f, indent=2)
            return {"status": "baseline_created"}

        with open(baseline_file, "r") as f:
            baseline = json.load(f)

        current_dur = current["total_duration_seconds"]
        baseline_dur = baseline["total_duration_seconds"]
        diff = current_dur - baseline_dur
        percent = (diff / baseline_dur * 100) if baseline_dur else 0

        result = {
            "baseline_seconds": baseline_dur,
            "current_seconds": current_dur,
            "diff_seconds": diff,
            "diff_percent": round(percent, 2),
            "status": "improvement" if diff < -60 else ("regression" if diff > 60 else "normal"),
        }

        print(f"📊 Performance Report:")
        print(f"  Baseline: {baseline_dur:.1f}s")
        print(f"  Current:  {current_dur:.1f}s")
        print(f"  Diff:     {diff:+.1f}s ({result['diff_percent']:+.1f}%)")
        print(f"  Status:   {result['status'].upper()}")

        return result

    def get_slow_steps(self, threshold_seconds: float = 300) -> List[Dict]:
        """Get steps that exceed threshold"""
        summary = self.get_summary()
        if not summary:
            return []

        return [s for s in summary.get("steps", []) if s["duration_seconds"] > threshold_seconds]

    def generate_pr_comment(self) -> str:
        """Generate markdown report for PR comment"""
        summary = self.get_summary()
        comparison = self.compare_with_baseline()

        if not summary:
            return "No performance metrics available"

        total_dur = summary["total_duration_seconds"]
        steps_count = summary["steps_count"]
        slow_steps = self.get_slow_steps()

        comment = f"""## 📊 Build Performance Report

### Build Summary
- **Total Duration:** {total_dur:.1f}s
- **Steps:** {steps_count}
- **Average Step Time:** {summary["average_step_duration"]:.1f}s
- **Branch:** {summary["branch"]}

### Performance Comparison
"""

        if comparison and "status" in comparison:
            status_emoji = (
                "🟢"
                if comparison["status"] == "improvement"
                else ("🔴" if comparison["status"] == "regression" else "🟡")
            )
            if comparison["status"] == "baseline_created":
                comment += f"🆕 Baseline created\n"
            else:
                comment += f"{status_emoji} {comparison['status'].upper()}: {comparison['diff_seconds']:+.1f}s ({comparison['diff_percent']:+.1f}%)\n"

        if slow_steps:
            comment += "\n### Slow Steps (> 5 minutes)\n"
            for step in slow_steps:
                comment += f"- **{step['step']}:** {step['duration_seconds']:.1f}s\n"

        return comment

    def to_json(self) -> str:
        """Export all metrics as JSON"""
        summary = self.get_summary() or {}
        return json.dumps(summary, indent=2)


def main():
    parser = argparse.ArgumentParser(description="CI Performance Tracker")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Record command
    record_parser = subparsers.add_parser("record", help="Record a performance metric")
    record_parser.add_argument("step", help="Step name")
    record_parser.add_argument("start", type=float, help="Start timestamp")
    record_parser.add_argument("end", type=float, help="End timestamp")
    record_parser.add_argument("--dir", default=".github/perf-metrics", help="Data directory")

    # Aggregate command
    agg_parser = subparsers.add_parser("aggregate", help="Aggregate metrics")
    agg_parser.add_argument("--dir", default=".github/perf-metrics", help="Data directory")

    # Compare command
    cmp_parser = subparsers.add_parser("compare", help="Compare with baseline")
    cmp_parser.add_argument("--dir", default=".github/perf-metrics", help="Data directory")

    # Report command
    rep_parser = subparsers.add_parser("report", help="Generate PR report")
    rep_parser.add_argument("--dir", default=".github/perf-metrics", help="Data directory")
    rep_parser.add_argument("--output", help="Output file")

    # Slow-steps command
    slow_parser = subparsers.add_parser("slow-steps", help="Get slow steps")
    slow_parser.add_argument("--threshold", type=float, default=300, help="Threshold in seconds")
    slow_parser.add_argument("--dir", default=".github/perf-metrics", help="Data directory")

    # Export command
    exp_parser = subparsers.add_parser("export", help="Export metrics as JSON")
    exp_parser.add_argument("--dir", default=".github/perf-metrics", help="Data directory")
    exp_parser.add_argument("--output", help="Output file")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    tracker = PerformanceTracker(args.dir if hasattr(args, "dir") else ".github/perf-metrics")

    if args.command == "record":
        tracker.record_metric(args.step, args.start, args.end)
    elif args.command == "aggregate":
        tracker.aggregate_metrics()
    elif args.command == "compare":
        tracker.compare_with_baseline()
    elif args.command == "report":
        comment = tracker.generate_pr_comment()
        if args.output:
            with open(args.output, "w") as f:
                f.write(comment)
            print(f"✅ Report written to {args.output}")
        else:
            print(comment)
    elif args.command == "slow-steps":
        slow = tracker.get_slow_steps(args.threshold)
        for step in slow:
            print(f"- {step['step']}: {step['duration_seconds']:.1f}s")
    elif args.command == "export":
        json_output = tracker.to_json()
        if args.output:
            with open(args.output, "w") as f:
                f.write(json_output)
            print(f"✅ Exported to {args.output}")
        else:
            print(json_output)


if __name__ == "__main__":
    main()
