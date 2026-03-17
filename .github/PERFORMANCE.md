# Build Performance Dashboard

## Overview
This dashboard tracks CI build performance to identify regressions and improvements over time.

## Live Dashboard

### GitHub Actions Insights
- Navigate to your repository on GitHub
- Go to **Insights** → **Actions**
- View build times, success rates, and trends

### Performance Metrics Artifacts
Each CI run uploads performance artifacts:
- `ci-performance-summary` - Contains `summary.json`, `history.json`, and markdown reports

## Performance Reports

### PR Reports
On pull requests, the CI generates a performance report showing:
- Total build duration
- Time spent in each major step
- Comparison with baseline
- Slow steps (>5 minutes)

### Trend Reports
The `trend-report.md` shows:
- Last 10 build runs with durations
- Average step times
- Trend analysis (improving/stable/regressing)

## Historical Data

Performance history is stored in:
- `.github/perf-metrics/history.json` - JSON array of past runs

## Alerts

The CI monitors for performance regressions:
- **>60 seconds slower** than baseline triggers a warning
- **>5 minutes slower** triggers an error

## Adding Performance Tracking to New Jobs

To add timing to a new job:

```yaml
jobs:
  my-new-job:
    steps:
    - name: Initialize performance tracking
      run: |
        ./scripts/ci-performance-tracker.sh init
        echo "STEP_START=$(date +%s)" >> $GITHUB_ENV

    # ... your job steps ...

    - name: Record job timing
      if: always()
      run: |
        STEP_END=$(date +%s)
        ./scripts/ci-performance-tracker.sh record "My Job Name" $STEP_START $STEP_END
      env:
        STEP_START: ${{ env.STEP_START }}

    - name: Upload performance metrics
      if: always()
      uses: actions/upload-artifact@v7
      with:
        name: perf-metrics-my-job
        path: .github/perf-metrics/*.json
        retention-days: 30
```

## Key Metrics Tracked

| Metric | Description |
|--------|-------------|
| Changes Detection | Time to detect changed files |
| Prepare Base Images | Docker image building |
| Prepare Node Base | Node.js environment setup |
| Format Check | Code formatting validation |
| Vulnerability Scan | Security scanning |
| Integration Tests | Backend tests |
| Frontend Tests | Frontend unit/build/lint tests |
| Mutation Testing | Code mutation tests |

## Accessing via API

```bash
# Get latest performance data
curl -s https://api.github.com/repos/OWNER/REPO/actions/artifacts | jq '.artifacts[] | select(.name=="ci-performance-summary")'
```
