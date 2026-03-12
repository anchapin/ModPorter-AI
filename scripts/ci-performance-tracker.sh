#!/bin/bash
# CI Build Performance Tracker
# Tracks timing metrics from GitHub Actions CI pipeline and outputs JSON
# Usage: ci-performance-tracker.sh [job-name] [start-timestamp] [end-timestamp]

set -e

# Configuration
PERF_DATA_DIR=".github/perf-metrics"
ARTIFACT_NAME="ci-performance-metrics"

# Helper functions
log_info() {
    echo "ℹ️  $1" >&2
}

log_success() {
    echo "✅ $1" >&2
}

log_error() {
    echo "❌ $1" >&2
}

# Initialize performance tracking
init_tracking() {
    mkdir -p "$PERF_DATA_DIR"
    log_info "Performance tracking directory initialized: $PERF_DATA_DIR"
}

# Record step timing (called from within GitHub Actions steps)
record_step() {
    local step_name="$1"
    local step_start="$2"
    local step_end="$3"
    
    if [ -z "$step_name" ] || [ -z "$step_start" ] || [ -z "$step_end" ]; then
        log_error "Usage: record_step <step-name> <start-timestamp> <end-timestamp>"
        return 1
    fi
    
    local duration=$((step_end - step_start))
    local timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    
    local step_file="$PERF_DATA_DIR/step-${step_name//\//-}.json"
    
    cat > "$step_file" << EOF
{
  "step": "$step_name",
  "duration_seconds": $duration,
  "start": $step_start,
  "end": $step_end,
  "recorded_at": "$timestamp",
  "run_id": "$GITHUB_RUN_ID",
  "run_number": "$GITHUB_RUN_NUMBER",
  "branch": "$GITHUB_REF_NAME"
}
EOF
    
    log_success "Recorded: $step_name ($duration seconds)"
}

# Aggregate all performance metrics into a summary
aggregate_metrics() {
    local summary_file="$PERF_DATA_DIR/summary.json"
    local total_duration=0
    local job_count=0
    
    log_info "Aggregating performance metrics..."
    
    # Ensure the directory exists
    mkdir -p "$PERF_DATA_DIR"
    
    # Check if any step files exist
    local step_files=("$PERF_DATA_DIR"/step-*.json)
    if [ ! -f "${step_files[0]}" ]; then
        log_info "No performance metrics found to aggregate"
        # Create empty summary file
        cat > "$summary_file" << EOF
{
  "workflow": "${GITHUB_WORKFLOW:-CI}",
  "run_id": "${GITHUB_RUN_ID:-0}",
  "run_number": "${GITHUB_RUN_NUMBER:-0}",
  "branch": "${GITHUB_REF_NAME:-unknown}",
  "commit": "${GITHUB_SHA:-unknown}",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "total_duration_seconds": 0,
  "steps_count": 0,
  "average_step_duration": 0,
  "steps": []
}
EOF
        log_success "Created empty metrics summary (no step data found)"
        cat "$summary_file"
        return 0
    fi
    
    # Collect all step metrics
    local steps_json="["
    local first=true
    
    for step_file in "$PERF_DATA_DIR"/step-*.json; do
        if [ -f "$step_file" ]; then
            if [ "$first" = true ]; then
                first=false
            else
                steps_json+=","
            fi
            steps_json+=$(cat "$step_file")
            
            # Add to total duration
            local duration=$(jq .duration_seconds "$step_file")
            total_duration=$((total_duration + duration))
            job_count=$((job_count + 1))
        fi
    done
    steps_json+="]"
    
    local timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    local workflow_name="${GITHUB_WORKFLOW:-CI}"
    
    # Create summary
    cat > "$summary_file" << EOF
{
  "workflow": "$workflow_name",
  "run_id": "$GITHUB_RUN_ID",
  "run_number": "$GITHUB_RUN_NUMBER",
  "branch": "$GITHUB_REF_NAME",
  "commit": "$GITHUB_SHA",
  "timestamp": "$timestamp",
  "total_duration_seconds": $total_duration,
  "steps_count": $job_count,
  "average_step_duration": $((job_count > 0 ? total_duration / job_count : 0)),
  "steps": $steps_json
}
EOF
    
    log_success "Metrics summary created: $summary_file"
    cat "$summary_file"
}

# Upload metrics to artifact storage
upload_metrics() {
    local artifact_dir="$PERF_DATA_DIR"
    
    if [ ! -d "$artifact_dir" ]; then
        log_error "No metrics directory found: $artifact_dir"
        return 1
    fi
    
    # Create a timestamped archive
    local timestamp=$(date -u +%Y%m%d-%H%M%S)
    local archive_name="ci-perf-${timestamp}.tar.gz"
    
    tar -czf "$archive_name" -C "$(dirname $artifact_dir)" "$(basename $artifact_dir)"
    log_success "Metrics archive created: $archive_name"
}

# Compare with baseline (if previous metrics exist)
compare_metrics() {
    local summary_file="$PERF_DATA_DIR/summary.json"
    local baseline_file=".github/perf-metrics/baseline.json"
    
    if [ ! -f "$summary_file" ]; then
        log_error "No metrics summary found"
        return 1
    fi
    
    if [ ! -f "$baseline_file" ]; then
        log_info "No baseline found - creating first baseline"
        cp "$summary_file" "$baseline_file"
        return 0
    fi
    
    local current_duration=$(jq .total_duration_seconds "$summary_file")
    local baseline_duration=$(jq .total_duration_seconds "$baseline_file")
    local diff=$((current_duration - baseline_duration))
    local percent=$((diff * 100 / baseline_duration))
    
    log_info "Performance Comparison:"
    echo "  Baseline: ${baseline_duration}s"
    echo "  Current:  ${current_duration}s"
    echo "  Diff:     ${diff}s (${percent}%)"
    
    if [ $diff -gt 60 ]; then
        log_error "Performance regression detected! ($diff seconds slower)"
    elif [ $diff -lt -60 ]; then
        log_success "Performance improvement! ($((diff * -1)) seconds faster)"
    else
        log_info "Performance within tolerance range"
    fi
}

# Generate performance report for PR comment
generate_pr_report() {
    local summary_file="$PERF_DATA_DIR/summary.json"
    local report_file="$PERF_DATA_DIR/pr-report.md"
    
    if [ ! -f "$summary_file" ]; then
        return 1
    fi
    
    local total_duration=$(jq -r .total_duration_seconds "$summary_file")
    local steps_count=$(jq -r .steps_count "$summary_file")
    local average=$(jq -r .average_step_duration "$summary_file")
    
    cat > "$report_file" << 'EOF'
## 📊 Build Performance Report

### Metrics Summary
```
EOF
    
    jq '.' "$summary_file" >> "$report_file"
    
    cat >> "$report_file" << EOF

\`\`\`

### Key Metrics
- **Total Duration:** ${total_duration}s
- **Steps:** $steps_count
- **Average Step Time:** ${average}s

### Slow Steps (> 5 minutes)
EOF
    
    jq -r '.steps[] | select(.duration_seconds > 300) | "- \(.step): \(.duration_seconds)s"' "$summary_file" >> "$report_file" || true
    
    log_success "Generated PR report: $report_file"
}

# Update history for trend tracking
update_history() {
    local summary_file="$PERF_DATA_DIR/summary.json"
    local history_file="$PERF_DATA_DIR/history.json"
    
    if [ ! -f "$summary_file" ]; then
        log_error "No metrics summary found to add to history"
        return 1
    fi
    
    # Initialize history file if it doesn't exist
    if [ ! -f "$history_file" ]; then
        echo "[]" > "$history_file"
    fi
    
    # Append current summary to history (limit to last 50 runs)
    local temp_history=$(mktemp)
    jq ". += [$(cat "$summary_file")] | .[-50:]" "$history_file" > "$temp_history"
    mv "$temp_history" "$history_file"
    
    log_success "History updated: $history_file"
    
    # Commit history to repo if on main branch
    if [ "$GITHUB_REF_NAME" = "main" ] && [ -n "$GITHUB_TOKEN" ]; then
        commit_history_to_repo
    fi
    
    # Generate trend report
    local trend_report="$PERF_DATA_DIR/trend-report.md"
    cat > "$trend_report" << 'EOF'
## 📈 Build Performance Trends (Last 10 runs)

| Run # | Date | Duration | Steps | Avg Step |
|-------|------|----------|-------|----------|
EOF
    
    jq -r '.[] | "| \(.run_number) | \(.timestamp | split("T")[0]) | \(.total_duration_seconds)s | \(.steps_count) | \(.average_step_duration)s |"' "$history_file" | tail -n 10 >> "$trend_report"
    
    # Add trend analysis
    cat >> "$trend_report" << 'EOF'

### Trend Analysis
EOF
    
    # Calculate trend for total duration
    local count=$(jq 'length' "$history_file")
    if [ "$count" -ge 2 ]; then
        local recent_avg=$(jq -s 'map(.total_duration_seconds) | add / length' "$history_file")
        local older_runs=$(jq ".[0:$count/2 | length] | map(.total_duration_seconds) | add / length" "$history_file")
        local trend_pct=$(( (recent_avg - older_runs) * 100 / older_runs ))
        
        if [ "$trend_pct" -gt 5 ]; then
            echo "⚠️ **Performance trending upward** (+${trend_pct}%)" >> "$trend_report"
        elif [ "$trend_pct" -lt -5 ]; then
            echo "✅ **Performance trending downward** (${trend_pct}%)" >> "$trend_report"
        else
            echo "➡️ **Performance stable**" >> "$trend_report"
        fi
    fi
    
    log_success "Trend report generated: $trend_report"
}

# Commit history to repository
commit_history_to_repo() {
    local history_file="$PERF_DATA_DIR/history.json"
    local commit_msg="ci: Update build performance history"
    
    git config --local user.email "github-actions[bot]@users.noreply.github.com"
    git config --local user.name "github-actions[bot]"
    
    git add "$history_file"
    
    if git diff --cached --quiet; then
        log_info "No changes to history file"
        return 0
    fi
    
    if git commit -m "$commit_msg"; then
        local branch="${GITHUB_REF_NAME:-main}"
        if git push "https://x-access-token:${GITHUB_TOKEN}@github.com/${GITHUB_REPOSITORY}.git" "HEAD:$branch" 2>/dev/null; then
            log_success "Performance history committed and pushed"
        else
            log_info "Could not push history (may need write permissions)"
        fi
    fi
}

# Display help
show_help() {
    cat << 'EOF'
CI Performance Tracker

Usage:
  ci-performance-tracker.sh [command] [options]

Commands:
  init              Initialize tracking directory
  record <name> <start> <end>  Record a step timing
  aggregate         Aggregate all metrics
  compare           Compare with baseline
  history           Update history and generate trend report
  report            Generate PR report
  upload            Upload metrics artifact
  help              Show this message

Examples:
  ci-performance-tracker.sh init
  ci-performance-tracker.sh record "Install Dependencies" 1678000000 1678000060
  ci-performance-tracker.sh aggregate
  ci-performance-tracker.sh compare
  ci-performance-tracker.sh history
  ci-performance-tracker.sh report

EOF
}

# Main
main() {
    local cmd="${1:-help}"
    
    case "$cmd" in
        init)
            init_tracking
            ;;
        record)
            init_tracking
            record_step "$2" "$3" "$4"
            ;;
        aggregate)
            aggregate_metrics
            ;;
        compare)
            compare_metrics
            ;;
        history)
            update_history
            ;;
        report)
            generate_pr_report
            ;;
        upload)
            upload_metrics
            ;;
        *)
            show_help
            ;;
    esac
}

main "$@"
