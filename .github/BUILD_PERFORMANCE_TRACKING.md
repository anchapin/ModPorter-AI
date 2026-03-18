# Build Performance Tracking

This document explains how build performance is tracked and analyzed in ModPorter-AI's CI pipeline.

## Overview

Build performance tracking automatically records the duration of CI pipeline steps and tracks performance trends over time. This helps identify performance regressions early and optimize the build process.

## Key Features

### 1. **Automatic Step Timing**
- Each major CI step duration is automatically recorded
- Timestamps captured with high precision
- Stored as JSON for easy parsing and analysis

### 2. **Performance Metrics**
Collected metrics include:
- Total workflow duration
- Individual step durations
- Average step time
- Number of steps
- Branch and commit information
- Workflow run ID and number

### 3. **Baseline Comparison**
- First run establishes a baseline
- Subsequent runs compared against baseline
- Automatic detection of regressions (>60s slower) and improvements (>60s faster)
- Percentage change calculation

### 4. **Slow Step Detection**
- Steps exceeding 5 minutes are flagged
- Listed in performance reports
- Helps identify optimization opportunities

### 5. **PR Performance Reports**
- Automatic generation of performance summaries for PRs
- Shows total duration, step count, and averages
- Includes comparison with baseline
- Lists any slow steps found

## Tools and Scripts

### Python Module: `scripts/ci_performance_tracker.py`

Command-line interface for performance tracking operations.

**Usage:**
```bash
python3 scripts/ci_performance_tracker.py <command> [options]
```

**Commands:**
- `record <step> <start> <end>` - Record a step timing
- `aggregate` - Aggregate all metrics into summary
- `compare` - Compare with baseline
- `report` - Generate markdown report for PR comment
- `slow-steps` - List steps exceeding threshold
- `export` - Export all metrics as JSON

**Examples:**
```bash
# Record a step
python3 scripts/ci_performance_tracker.py record "checkout" 1000 1010

# Aggregate metrics
python3 scripts/ci_performance_tracker.py aggregate

# Compare with baseline
python3 scripts/ci_performance_tracker.py compare

# Generate PR report
python3 scripts/ci_performance_tracker.py report

# Find slow steps (> 10 minutes)
python3 scripts/ci_performance_tracker.py slow-steps --threshold 600

# Export as JSON
python3 scripts/ci_performance_tracker.py export --output metrics.json
```

### Bash Script: `scripts/ci-performance-tracker.sh`

Shell-based interface for performance tracking.

**Usage:**
```bash
./scripts/ci-performance-tracker.sh <command> [options]
```

**Commands:**
- `init` - Initialize tracking directory
- `record <name> <start> <end>` - Record step timing
- `aggregate` - Aggregate metrics
- `compare` - Compare with baseline
- `report` - Generate report
- `upload` - Create metrics archive

## Integration with GitHub Actions

The CI workflow automatically:

1. **Records Metrics**: During the performance-monitoring job
2. **Aggregates Data**: Combines all step timings
3. **Compares Baseline**: Shows performance vs. baseline
4. **Generates Reports**: Creates markdown for PR comments
5. **Uploads Artifacts**: Stores metrics for historical analysis

### Workflow Steps

```yaml
- name: Set up Python for performance tracking
  uses: actions/setup-python@v6

- name: Record workflow metrics
  run: |
    python3 scripts/ci_performance_tracker.py aggregate
    python3 scripts/ci_performance_tracker.py compare

- name: Generate performance report
  if: github.event_name == 'pull_request'
  run: |
    python3 scripts/ci_performance_tracker.py report

- name: Upload performance metrics artifact
  uses: actions/upload-artifact@v4
  with:
    name: ci-performance-metrics
    path: .github/perf-metrics/
    retention-days: 30
```

## Metrics Storage

Performance metrics are stored in `.github/perf-metrics/`:

### Files

- **`step-<name>.json`** - Individual step metric files
  ```json
  {
    "step": "step-name",
    "duration_seconds": 10.5,
    "start": 1678000000,
    "end": 1678000010.5,
    "recorded_at": "2026-03-10T12:00:00Z",
    "run_id": "123456",
    "run_number": 45,
    "branch": "main"
  }
  ```

- **`summary.json`** - Aggregated metrics
  ```json
  {
    "workflow": "CI",
    "run_id": "123456",
    "run_number": 45,
    "branch": "main",
    "commit": "abc123def456",
    "timestamp": "2026-03-10T12:00:00Z",
    "total_duration_seconds": 360.0,
    "steps_count": 3,
    "average_step_duration": 120.0,
    "steps": [...]
  }
  ```

- **`baseline.json`** - Performance baseline for comparison
  ```json
  {
    "workflow": "CI",
    "total_duration_seconds": 320.0,
    ...
  }
  ```

- **`pr-report.md`** - Markdown report for PR comments

## Performance Report Example

```markdown
## 📊 Build Performance Report

### Build Summary
- **Total Duration:** 360.0s
- **Steps:** 3
- **Average Step Time:** 120.0s
- **Branch:** main

### Performance Comparison
🟢 IMPROVEMENT: -50.0s (-12.5%)

### Slow Steps (> 5 minutes)
- **run-tests:** 350.0s
```

## Interpreting Results

### Status Indicators

- 🟢 **Improvement** - Performance improved >60 seconds
- 🔴 **Regression** - Performance regressed >60 seconds  
- 🟡 **Normal** - Within tolerance range
- 🆕 **Baseline Created** - First baseline established

### Performance Goals

| Metric | Target | Status |
|--------|--------|--------|
| Total CI Time | < 25 minutes | ✅ |
| Setup Overhead | < 25% | ✅ |
| Cache Hit Rate | > 90% | ✅ |
| No Regressions | > 60s | ✅ |

## Analyzing Trends

### Historical Metrics

Performance metrics are retained as artifacts for 30 days:

1. Navigate to Actions tab in GitHub
2. Select the workflow run
3. Download `ci-performance-metrics` artifact
4. View trend data in `summary.json` files

### Identifying Bottlenecks

To find slow steps:

```bash
python3 scripts/ci_performance_tracker.py slow-steps --threshold 300
```

### Comparing Baselines

View historical changes:

```bash
# Export current metrics
python3 scripts/ci_performance_tracker.py export > current.json

# Compare with previous baseline
jq '.total_duration_seconds' current.json
jq '.total_duration_seconds' .github/perf-metrics/baseline.json
```

## Optimization Opportunities

### Quick Wins

1. **Cache Optimization** - Improve cache hit rates
2. **Parallelization** - Run independent steps in parallel
3. **Dependency Cleanup** - Remove unnecessary dependencies
4. **Image Pre-warming** - Pre-build base images

### Long-term Improvements

1. **Step Restructuring** - Optimize step order
2. **Resource Allocation** - Increase runner resources
3. **Tool Updates** - Use faster tools/versions
4. **Architecture Changes** - Simplify pipeline

## Troubleshooting

### No Metrics Generated

**Problem**: `.github/perf-metrics/` is empty

**Solutions**:
1. Check that `python3 scripts/ci_performance_tracker.py aggregate` runs
2. Verify metrics are being recorded before aggregation
3. Check for Python errors in workflow logs

### Baseline Not Updating

**Problem**: Comparison always shows "baseline_created"

**Solutions**:
1. Manually copy `summary.json` to `baseline.json`
2. Run comparison on next workflow execution
3. Check file permissions in `.github/perf-metrics/`

### Large Performance Variance

**Problem**: Metrics vary wildly between runs

**Solutions**:
1. Check GitHub runner load
2. Review for new dependencies slowing things down
3. Check for resource contention
4. Look for external service delays

## Development Guide

### Running Tests

```bash
python3 -m pytest tests/test_ci_performance_tracker.py -v
```

### Adding Custom Metrics

In GitHub Actions workflow:

```yaml
- name: Custom metric
  run: |
    START=$(date +%s.%N)
    # ... your step ...
    END=$(date +%s.%N)
    python3 scripts/ci_performance_tracker.py record "my-step" $START $END
```

### Programmatic Usage

```python
from scripts.ci_performance_tracker import PerformanceTracker

tracker = PerformanceTracker()
tracker.record_metric("my-step", 1000.0, 1010.5)
tracker.aggregate_metrics()

summary = tracker.get_summary()
slow_steps = tracker.get_slow_steps(threshold_seconds=300)
comparison = tracker.compare_with_baseline()

print(tracker.generate_pr_comment())
```

## Related Documentation

- [CI Workflow Configuration](.github/workflows/ci.yml)
- [Performance Optimization Guide](../docs/performance-optimization.md)
- [CI Architecture](../docs/ci-architecture.md)

## Support

For issues or questions about build performance tracking:

1. Check the [Troubleshooting](#troubleshooting) section
2. Review workflow logs in GitHub Actions
3. Check `ci-performance-metrics` artifacts
4. Open an issue with performance data attached
