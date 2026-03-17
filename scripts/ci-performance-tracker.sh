#!/bin/bash
# CI Performance Tracker
# Tracks and reports build performance metrics

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
WORKFLOW_NAME="${WORKFLOW_NAME:-ci}"
ARTIFACT_NAME="performance-metrics"
OUTPUT_DIR="${OUTPUT_DIR:-.performance}"

# Initialize performance data
PERFORMANCE_DATA="${OUTPUT_DIR}/metrics.json"
HISTORICAL_DATA="${OUTPUT_DIR}/history.json"

# Function to log with timestamp
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] ✓${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] ⚠${NC} $1"
}

log_error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ✗${NC} $1"
}

# Create output directory
mkdir -p "${OUTPUT_DIR}"

# Initialize metrics file
init_metrics() {
    cat > "${PERFORMANCE_DATA}" << EOF
{
  "workflow": "${WORKFLOW_NAME}",
  "run_id": "${RUN_ID:-unknown}",
  "run_number": "${RUN_NUMBER:-unknown}",
  "branch": "${BRANCH:-unknown}",
  "commit": "${COMMIT:-unknown}",
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "steps": [],
  "total_duration_seconds": 0
}
EOF
}

# Record a step start time
step_start() {
    local step_name="$1"
    local step_id="${step_name// /-}"
    echo "{\"step\": \"${step_name}\", \"start\": $(date +%s), \"status\": \"running\"}" >> "${OUTPUT_DIR}/steps_${step_id}.tmp"
}

# Record a step end time
step_end() {
    local step_name="$1"
    local step_id="${step_name// /-}"
    local temp_file="${OUTPUT_DIR}/steps_${step_id}.tmp"
    
    if [[ -f "${temp_file}" ]]; then
        local start_time
        start_time=$(grep -o '"start": [0-9]*' "${temp_file}" | grep -o '[0-9]*')
        local end_time
        end_time=$(date +%s)
        local duration=$((end_time - start_time))
        
        # Remove temp file
        rm -f "${temp_file}"
        
        # Add step to metrics
        local step_json
        step_json=$(cat << EOF
{
  "name": "${step_name}",
  "start_time": ${start_time},
  "end_time": ${end_time},
  "duration_seconds": ${duration}
}
EOF
)
        
        # Append to steps array
        local steps_json
        steps_json=$(cat "${PERFORMANCE_DATA}")
        echo "${steps_json}" | jq --argjson step "${step_json}" '.steps += [$step]' > "${PERFORMANCE_DATA}.tmp"
        mv "${PERFORMANCE_DATA}.tmp" "${PERFORMANCE_DATA}"
        
        log_success "${step_name}: ${duration}s"
    else
        log_warning "No start time found for step: ${step_name}"
    fi
}

# Calculate total duration
calculate_total() {
    local first_step
    first_step=$(cat "${PERFORMANCE_DATA}" | jq -r '.steps[0].start_time // 0')
    local last_step
    last_step=$(cat "${PERFORMANCE_DATA}" | jq -r '.steps[-1].end_time // 0')
    local total=$((last_step - first_step))
    
    # Update total duration
    cat "${PERFORMANCE_DATA}" | jq ".total_duration_seconds = ${total}" > "${PERFORMANCE_DATA}.tmp"
    mv "${PERFORMANCE_DATA}.tmp" "${PERFORMANCE_DATA}"
    
    log "Total build time: ${total}s"
}

# Generate performance report
generate_report() {
    local previous_duration="${1:-0}"
    
    # Calculate metrics
    local total_duration
    total_duration=$(cat "${PERFORMANCE_DATA}" | jq -r '.total_duration_seconds')
    
    # Build report
    cat > "${OUTPUT_DIR}/report.md" << EOF
# Build Performance Report

## Summary
- **Workflow**: ${WORKFLOW_NAME}
- **Run**: ${RUN_NUMBER:-unknown}
- **Branch**: ${BRANCH:-unknown}
- **Total Duration**: ${total_duration}s

## Step Breakdown

EOF

    # Add step details
    cat "${PERFORMANCE_DATA}" | jq -r '.steps[] | "- **\(.name)**: \(.duration_seconds)s"' >> "${OUTPUT_DIR}/report.md"
    
    # Add comparison if historical data available
    if [[ "${previous_duration}" -gt 0 ]]; then
        local diff=$((total_duration - previous_duration))
        local percent_change
        percent_change=$(echo "scale=2; (${diff} / ${previous_duration}) * 100" | bc)
        
        cat >> "${OUTPUT_DIR}/report.md" << EOF

## Comparison with Previous Run
- **Previous Duration**: ${previous_duration}s
- **Difference**: ${diff}s (${percent_change}%)
EOF
        
        if [[ ${diff} -gt 0 ]]; then
            log_warning "Build is ${diff}s slower than previous run"
        else
            log_success "Build is $((-diff))s faster than previous run"
        fi
    fi
    
    log "Report generated: ${OUTPUT_DIR}/report.md"
}

# Upload metrics as artifact (for GitHub Actions)
upload_metrics() {
    if [[ -n "${GITHUB_TOKEN:-}" ]]; then
        log "Uploading performance metrics..."
        # Metrics will be uploaded via actions/upload-artifact in the workflow
    fi
}

# Main functions
show_help() {
    cat << EOF
CI Performance Tracker

Usage: $0 <command> [options]

Commands:
    init                    Initialize performance tracking
    start <step_name>       Mark step as started
    end <step_name>         Mark step as completed
    report [prev_duration]  Generate performance report
    upload                  Upload metrics as artifact
    help                    Show this help message

Environment Variables:
    WORKFLOW_NAME     Name of the workflow (default: ci)
    RUN_ID            GitHub Actions run ID
    RUN_NUMBER        GitHub Actions run number
    BRANCH            Branch name
    COMMIT            Commit SHA
    OUTPUT_DIR        Output directory (default: .performance)

Examples:
    $0 init
    $0 start "Install dependencies"
    $0 end "Install dependencies"
    $0 report
EOF
}

# Parse command
case "${1:-help}" in
    init)
        init_metrics
        log_success "Performance tracking initialized"
        ;;
    start)
        if [[ -z "${2:-}" ]]; then
            log_error "Step name required"
            exit 1
        fi
        step_start "$2"
        log "Started: $2"
        ;;
    end)
        if [[ -z "${2:-}" ]]; then
            log_error "Step name required"
            exit 1
        fi
        step_end "$2"
        ;;
    report)
        calculate_total
        generate_report "${2:-0}"
        ;;
    upload)
        upload_metrics
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        log_error "Unknown command: $1"
        show_help
        exit 1
        ;;
esac
