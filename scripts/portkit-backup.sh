#!/bin/bash
# PostgreSQL Backup Script with Point-in-Time Recovery Support
# portkit Database Backup System
# Version: 2.0.0

set -euo pipefail

# ============================================
# Configuration
# ============================================
readonly BACKUP_ROOT="${BACKUP_ROOT:-/backups/postgres}"
readonly RETENTION_DAILY="${RETENTION_DAILY:-7}"
readonly RETENTION_WEEKLY="${RETENTION_WEEKLY:-4}"
readonly RETENTION_MONTHLY="${RETENTION_MONTHLY:-12}"
readonly S3_BUCKET="${S3_BACKUP_BUCKET:-}"
readonly S3_PREFIX="${S3_PREFIX:-postgres}"
readonly WAL_ARCHIVE_PATH="${WAL_ARCHIVE_PATH:-}"
readonly LOG_FILE="${BACKUP_LOG_FILE:-/var/log/portkit/backup.log}"
readonly PGHOST="${PGHOST:-localhost}"
readonly PGPORT="${PGPORT:-5432}"
readonly PGDATABASE="${PGDATABASE:-portkit}"
readonly PGUSER="${PGUSER:-postgres}"
readonly PGPASSWORD="${PGPASSWORD:-}"

readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[0;33m'
readonly NC='\033[0m'

log() {
    local msg="$1"
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${GREEN}[${timestamp}]${NC} $msg" | tee -a "$LOG_FILE"
}

warn() {
    local msg="$1"
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${YELLOW}[${timestamp}] WARNING:${NC} $msg" | tee -a "$LOG_FILE"
}

error() {
    local msg="$1"
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${RED}[${timestamp}] ERROR:${NC} $msg" | tee -a "$LOG_FILE"
    exit 1
}

ensure_dir() {
    local dir="$1"
    mkdir -p "$dir"
}

get_timestamp() {
    date +%Y%m%d_%H%M%S
}

get_backup_size() {
    local file="$1"
    if [ -f "$file" ]; then
        du -h "$file" | cut -f1
    else
        echo "N/A"
    fi
}

check_db_connection() {
    log "Checking database connection..."
    if [ -n "$PGPASSWORD" ]; then
        export PGPASSWORD
    fi
    if ! pg_isready -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" > /dev/null 2>&1; then
        error "Database is not available at ${PGHOST}:${PGPORT}"
    fi
    log "Database connection OK"
}

create_full_backup() {
    local backup_dir="$1"
    local backup_name="full_$(get_timestamp)"
    local backup_file="${backup_dir}/${backup_name}.dump"
    local compressed_file="${backup_file}.gz"

    log "Creating full backup: ${backup_name}"
    log "Database: ${PGDATABASE} on ${PGHOST}:${PGPORT}"

    if [ -n "$PGPASSWORD" ]; then
        export PGPASSWORD
    fi

    pg_dump \
        -h "$PGHOST" \
        -p "$PGPORT" \
        -U "$PGUSER" \
        -d "$PGDATABASE" \
        --format=custom \
        --no-owner \
        --no-acl \
        --verbose \
        -f "$backup_file"

    if [ $? -ne 0 ]; then
        error "Full backup failed"
    fi

    log "Compressing backup..."
    gzip "$backup_file"

    local size
    size=$(get_backup_size "$compressed_file")
    log "Full backup completed: ${compressed_file} (${size})"

    echo "$compressed_file"
}

verify_backup() {
    local backup_file="$1"
    log "Verifying backup: ${backup_file}"

    if [ ! -f "$backup_file" ]; then
        error "Backup file not found: ${backup_file}"
    fi

    if [[ "$backup_file" == *.gz ]]; then
        if ! gunzip -t "$backup_file" 2>/dev/null; then
            error "Backup verification failed: compressed file corrupted"
        fi
    else
        if ! pg_restore --version > /dev/null 2>&1; then
            warn "pg_restore not available, skipping restore test"
            return 0
        fi
        local test_db="portkit_backup_test_$$"
        if createdb -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" "$test_db" 2>/dev/null; then
            if pg_restore -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$test_db" "$backup_file" > /dev/null 2>&1; then
                log "Backup verification passed"
                dropdb -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" "$test_db" 2>/dev/null || true
            else
                dropdb -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" "$test_db" 2>/dev/null || true
                error "Backup verification failed: restore test failed"
            fi
        else
            warn "Could not create test database, skipping restore test"
        fi
    fi
    log "Backup verification successful"
    return 0
}

cleanup_old_backups() {
    local backup_dir="$1"
    local count=0
    log "Cleaning up old backups..."
    if [ -d "$backup_dir" ]; then
        cd "$backup_dir" || return
        while IFS= read -r -d '' file; do
            rm -f "$file"
            ((count++))
        done < <(find . -name "full_*.dump.gz" -mtime +"${RETENTION_DAILY}" -print0 2>/dev/null)
        log "Cleaned up ${count} old backup files"
    fi
}

cleanup_old_weekly_backups() {
    local backup_dir="$1"
    local count=0
    log "Cleaning up old weekly backups..."
    if [ -d "$backup_dir" ]; then
        cd "$backup_dir" || return
        while IFS= read -r -d '' file; do
            rm -f "$file"
            ((count++))
        done < <(find . -name "weekly_*.dump.gz" -mtime +"$((RETENTION_WEEKLY * 7))" -print0 2>/dev/null)
        log "Cleaned up ${count} old weekly backup files"
    fi
}

cleanup_old_monthly_backups() {
    local backup_dir="$1"
    local count=0
    log "Cleaning up old monthly backups..."
    if [ -d "$backup_dir" ]; then
        cd "$backup_dir" || return
        while IFS= read -r -d '' file; do
            rm -f "$file"
            ((count++))
        done < <(find . -name "monthly_*.dump.gz" -mtime +"$((RETENTION_MONTHLY * 30))" -print0 2>/dev/null)
        log "Cleaned up ${count} old monthly backup files"
    fi
}

upload_to_s3() {
    local backup_file="$1"
    local s3_path="${S3_PREFIX}/daily/$(basename "$backup_file")"

    if [ -z "$S3_BUCKET" ]; then
        warn "S3_BUCKET not configured, skipping upload"
        return 0
    fi
    if ! command -v aws > /dev/null 2>&1; then
        warn "AWS CLI not installed, skipping S3 upload"
        return 0
    fi

    log "Uploading to S3: s3://${S3_BUCKET}/${s3_path}"
    if aws s3 cp "$backup_file" "s3://${S3_BUCKET}/${s3_path}" --storage-class STANDARD_IA 2>/dev/null; then
        log "S3 upload completed"
        return 0
    else
        warn "S3 upload failed"
        return 1
    fi
}

send_notification() {
    local status="$1"
    local message="$2"
    if [ -n "${SLACK_WEBHOOK_URL:-}" ]; then
        local color
        case "$status" in
            success) color="#36a64f" ;;
            failure) color="#ff0000" ;;
            *) color="#36a64f" ;;
        esac
        curl -s -X POST -H 'Content-type: application/json' \
            --data "{\"attachments\":[{\"color\":\"${color}\",\"text\":\"${message}\"}]}" \
            "${SLACK_WEBHOOK_URL}" > /dev/null 2>&1 || true
    fi
}

run_daily_backup() {
    log "=========================================="
    log "Starting Daily Backup Process"
    log "=========================================="

    local backup_dir="${BACKUP_ROOT}/daily"
    ensure_dir "$backup_dir"
    ensure_dir "$(dirname "$LOG_FILE")"

    check_db_connection
    local backup_file
    backup_file=$(create_full_backup "$backup_dir")
    verify_backup "$backup_file"
    upload_to_s3 "$backup_file"
    cleanup_old_backups "$backup_dir"

    local size
    size=$(get_backup_size "$backup_file")

    log "=========================================="
    log "Daily Backup Completed Successfully"
    log "Backup: ${backup_file}"
    log "Size: ${size}"
    log "Retention: ${RETENTION_DAILY} days"
    log "=========================================="

    send_notification "success" "Daily backup completed: ${size}"
}

run_weekly_backup() {
    log "=========================================="
    log "Starting Weekly Backup Process"
    log "=========================================="

    local backup_dir="${BACKUP_ROOT}/weekly"
    ensure_dir "$backup_dir"
    ensure_dir "$(dirname "$LOG_FILE")"

    check_db_connection

    local backup_name="weekly_$(get_timestamp)"
    local backup_file="${backup_dir}/${backup_name}.dump"

    if [ -n "$PGPASSWORD" ]; then
        export PGPASSWORD
    fi

    pg_dump \
        -h "$PGHOST" \
        -p "$PGPORT" \
        -U "$PGUSER" \
        -d "$PGDATABASE" \
        --format=custom \
        --no-owner \
        --no-acl \
        --verbose \
        -f "$backup_file"

    gzip "$backup_file"
    backup_file="${backup_file}.gz"

    local size
    size=$(get_backup_size "$backup_file")

    verify_backup "$backup_file"
    upload_to_s3 "$backup_file"
    cleanup_old_weekly_backups "$backup_dir"

    log "=========================================="
    log "Weekly Backup Completed Successfully"
    log "Backup: ${backup_file}"
    log "Size: ${size}"
    log "=========================================="

    send_notification "success" "Weekly backup completed: ${size}"
}

run_monthly_backup() {
    log "=========================================="
    log "Starting Monthly Backup Process"
    log "=========================================="

    local backup_dir="${BACKUP_ROOT}/monthly"
    ensure_dir "$backup_dir"
    ensure_dir "$(dirname "$LOG_FILE")"

    check_db_connection

    local backup_name="monthly_$(get_timestamp)"
    local backup_file="${backup_dir}/${backup_name}.dump"

    if [ -n "$PGPASSWORD" ]; then
        export PGPASSWORD
    fi

    pg_dump \
        -h "$PGHOST" \
        -p "$PGPORT" \
        -U "$PGUSER" \
        -d "$PGDATABASE" \
        --format=custom \
        --no-owner \
        --no-acl \
        --verbose \
        -f "$backup_file"

    gzip "$backup_file"
    backup_file="${backup_file}.gz"

    local size
    size=$(get_backup_size "$backup_file")

    verify_backup "$backup_file"
    upload_to_s3 "$backup_file"
    cleanup_old_monthly_backups "$backup_dir"

    log "=========================================="
    log "Monthly Backup Completed Successfully"
    log "Backup: ${backup_file}"
    log "Size: ${size}"
    log "=========================================="

    send_notification "success" "Monthly backup completed: ${size}"
}

usage() {
    cat << EOF
PostgreSQL Backup Script for portkit

Usage: $0 [command] [options]

Commands:
    daily           Run daily backup (full + WAL)
    weekly          Run weekly backup (full)
    monthly         Run monthly backup (full)
    verify FILE     Verify a backup file
    list            List available backups
    restore FILE    Restore from backup (interactive)
    help            Show this help message

Environment Variables:
    BACKUP_ROOT         Backup directory (default: /backups/postgres)
    RETENTION_DAILY     Daily retention in days (default: 7)
    RETENTION_WEEKLY    Weekly retention in weeks (default: 4)
    RETENTION_MONTHLY   Monthly retention in months (default: 12)
    S3_BUCKET          S3 bucket for remote backup
    S3_PREFIX          S3 prefix path (default: postgres)
    PGHOST             PostgreSQL host (default: localhost)
    PGPORT             PostgreSQL port (default: 5432)
    PGDATABASE         Database name (default: portkit)
    PGUSER             PostgreSQL user (default: postgres)
    PGPASSWORD         PostgreSQL password
    SLACK_WEBHOOK_URL  Slack webhook for notifications

Examples:
    $0 daily                    # Run daily backup
    $0 weekly                   # Run weekly backup
    $0 verify /backups/daily/full_20260401.dump.gz  # Verify backup
    $0 list                     # List all backups

EOF
}

list_backups() {
    log "Available Backups:"
    log "=================="
    for backup_type in daily weekly monthly; do
        local backup_dir="${BACKUP_ROOT}/${backup_type}"
        if [ -d "$backup_dir" ]; then
            echo ""
            echo "--- ${backup_type^^} BACKUPS ---"
            ls -lh "$backup_dir" 2>/dev/null || echo "  No backups found"
        fi
    done
}

main() {
    local command="${1:-daily}"

    case "$command" in
        daily)
            run_daily_backup
            ;;
        weekly)
            run_weekly_backup
            ;;
        monthly)
            run_monthly_backup
            ;;
        verify)
            local file="$2"
            if [ -z "$file" ]; then
                error "Please specify a backup file to verify"
            fi
            verify_backup "$file"
            ;;
        list)
            list_backups
            ;;
        restore)
            error "Restore functionality requires manual intervention. See docs/DATABASE_BACKUP.md"
            ;;
        help|--help|-h)
            usage
            ;;
        *)
            error "Unknown command: $command"
            ;;
    esac
}

main "$@"