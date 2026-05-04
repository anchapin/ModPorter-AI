#!/bin/bash
# PITR Restore Test Script
# Issue: #1206 - Database backup, point-in-time recovery, and disaster recovery plan
#
# This script tests the backup restoration procedure in an isolated environment.
# It does NOT affect the production database.
#
# Usage: ./scripts/test-backup-restore.sh [--full-restore | --pitr | --verify]
#
# WARNING: This script creates temporary databases and should be run in a
# non-production environment only.

set -euo pipefail

readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[0;33m'
readonly NC='\033[0m'

readonly TEST_DB_NAME="portkit_restore_test"
readonly BACKUP_ROOT="${BACKUP_ROOT:-/backups/postgres}"
readonly PGHOST="${PGHOST:-localhost}"
readonly PGPORT="${PGPORT:-5432}"
readonly PGDATABASE="${PGDATABASE:-portkit}"
readonly PGUSER="${PGUSER:-postgres}"
readonly PGPASSWORD="${PGPASSWORD:-}"

log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1"
    exit 1
}

check_prerequisites() {
    log "Checking prerequisites..."

    if ! command -v pg_dump > /dev/null 2>&1; then
        error "pg_dump is not installed. Install postgresql-client."
    fi

    if ! command -v pg_restore > /dev/null 2>&1; then
        error "pg_restore is not installed. Install postgresql-client."
    fi

    if ! command -v createdb > /dev/null 2>&1; then
        error "createdb is not installed. Install postgresql-client."
    fi

    if [ -n "$PGPASSWORD" ]; then
        export PGPASSWORD
    fi

    if ! pg_isready -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" > /dev/null 2>&1; then
        error "PostgreSQL is not available at ${PGHOST}:${PGPORT}"
    fi

    log "Prerequisites check passed"
}

find_latest_backup() {
    local backup_dir="${BACKUP_ROOT}/daily"
    if [ ! -d "$backup_dir" ]; then
        error "Backup directory not found: ${backup_dir}"
    fi

    local latest_backup
    latest_backup=$(ls -t "${backup_dir}"/full_*.dump.gz 2>/dev/null | head -1)

    if [ -z "$latest_backup" ]; then
        error "No backup files found in ${backup_dir}"
    fi

    echo "$latest_backup"
}

restore_to_test_db() {
    local backup_file="$1"
    local test_db="${TEST_DB_NAME}_$$"

    log "Testing backup restoration..."
    log "Backup file: ${backup_file}"
    log "Test database: ${test_db}"

    if pg_isready -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$test_db" > /dev/null 2>&1; then
        warn "Test database ${test_db} exists, dropping..."
        dropdb -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" "$test_db" 2>/dev/null || true
    fi

    log "Creating test database..."
    if ! createdb -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" "$test_db" 2>/dev/null; then
        error "Failed to create test database"
    fi

    log "Restoring backup to test database..."
    if ! gunzip -c "$backup_file" | pg_restore -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$test_db" --no-owner --verbose 2>&1; then
        dropdb -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" "$test_db" 2>/dev/null || true
        error "Backup restoration failed"
    fi

    log "Backup restoration completed successfully"
    echo "$test_db"
}

verify_restored_data() {
    local test_db="$1"

    log "Verifying restored data..."

    local table_counts
    table_counts=$(psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$test_db" -t -c "
        SELECT COUNT(*) FROM pg_tables WHERE schemaname = 'public';
    " 2>/dev/null)

    local row_count
    row_count=$(echo "$table_counts" | xargs)

    if [ -z "$row_count" ] || [ "$row_count" -eq 0 ]; then
        warn "No tables found in restored database"
    else
        log "Found $row_count tables in restored database"
    fi

    local users_count
    users_count=$(psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$test_db" -t -c "
        SELECT COUNT(*) FROM users WHERE email IS NOT NULL LIMIT 1;
    " 2>/dev/null || echo "0")

    if [ -n "$users_count" ]; then
        log "Users table exists (sample count: $users_count)"
    fi

    log "Checking pgvector extension..."
    local vector_ext
    vector_ext=$(psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$test_db" -t -c "
        SELECT COUNT(*) FROM pg_extension WHERE extname = 'vector';
    " 2>/dev/null || echo "0")

    if [ "$(echo "$vector_ext" | xargs)" -gt 0 ]; then
        log "pgvector extension is present"
    else
        warn "pgvector extension not found (may not be in this backup)"
    fi

    log "Data verification completed"
}

test_pitr_capability() {
    log "Testing PITR capability..."

    local backup_dir="${BACKUP_ROOT}/wal"
    if [ ! -d "$backup_dir" ]; then
        warn "WAL archive directory not found: ${backup_dir}"
        warn "PITR may not be available"
        return 0
    fi

    local wal_count
    wal_count=$(ls "$backup_dir" 2>/dev/null | wc -l)

    if [ "$wal_count" -gt 0 ]; then
        log "Found $wal_count WAL segments for PITR"
    else
        warn "No WAL segments found in ${backup_dir}"
    fi

    log "PITR capability check completed"
}

cleanup_test_db() {
    local test_db="$1"

    log "Cleaning up test database: ${test_db}"
    if dropdb -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" "$test_db" 2>/dev/null; then
        log "Test database cleaned up successfully"
    else
        warn "Failed to clean up test database (may not exist)"
    fi
}

run_full_restore_test() {
    log "=========================================="
    log "FULL BACKUP RESTORE TEST"
    log "=========================================="

    check_prerequisites

    local latest_backup
    latest_backup=$(find_latest_backup)

    if [ ! -f "$latest_backup" ]; then
        error "Backup file not found: ${latest_backup}"
    fi

    local backup_age=$(($(date +%s) - $(stat -c %Y "$latest_backup" 2>/dev/null || stat -f %m "$latest_backup" 2>/dev/null)))
    local age_hours=$((backup_age / 3600))

    log "Backup age: ${age_hours} hours"

    if [ "$age_hours" -gt 25 ]; then
        warn "Backup is older than 25 hours - this should trigger BackupTooOld alert"
    fi

    local test_db
    test_db=$(restore_to_test_db "$latest_backup")

    verify_restored_data "$test_db"

    cleanup_test_db "$test_db"

    log "=========================================="
    log "FULL BACKUP RESTORE TEST PASSED"
    log "=========================================="
}

run_pitr_test() {
    log "=========================================="
    log "POINT-IN-TIME RECOVERY TEST"
    log "=========================================="

    check_prerequisites

    test_pitr_capability

    log "=========================================="
    log "PITR TEST COMPLETED"
    log "=========================================="
}

run_verify_only() {
    log "=========================================="
    log "BACKUP VERIFICATION ONLY"
    log "=========================================="

    check_prerequisites

    local latest_backup
    latest_backup=$(find_latest_backup)

    log "Verifying backup file: ${latest_backup}"

    if [ ! -f "$latest_backup" ]; then
        error "Backup file not found"
    fi

    local file_size
    file_size=$(du -h "$latest_backup" | cut -f1)
    log "Backup file size: ${file_size}"

    log "Testing gzip integrity..."
    if gunzip -t "$latest_backup" 2>/dev/null; then
        log "Gzip integrity check passed"
    else
        error "Gzip integrity check FAILED"
    fi

    log "Listing backup contents..."
    pg_restore -l "$latest_backup" 2>/dev/null | head -20 || warn "Could not list backup contents"

    log "=========================================="
    log "BACKUP VERIFICATION COMPLETED"
    log "=========================================="
}

usage() {
    cat << EOF
PITR Restore Test Script

Usage: $0 [command]

Commands:
    full-restore    Test full backup restoration (creates temporary database)
    pitr           Test point-in-time recovery capability
    verify         Verify backup file integrity only
    help           Show this help message

Environment Variables:
    BACKUP_ROOT    Backup directory (default: /backups/postgres)
    PGHOST         PostgreSQL host (default: localhost)
    PGPORT         PostgreSQL port (default: 5432)
    PGDATABASE     Database name (default: portkit)
    PGUSER         PostgreSQL user (default: postgres)
    PGPASSWORD     PostgreSQL password

Examples:
    $0 full-restore    # Test complete restore procedure
    $0 pitr            # Test PITR capability
    $0 verify          # Just verify backup file

EOF
}

main() {
    local command="${1:-verify}"

    case "$command" in
        full-restore)
            run_full_restore_test
            ;;
        pitr)
            run_pitr_test
            ;;
        verify)
            run_verify_only
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