#!/bin/bash
# Backup Script for ModPorter AI Production
# Usage: ./scripts/backup.sh [daily|weekly|manual]

set -e

# Configuration
BACKUP_TYPE=${1:-daily}
BACKUP_DIR="/backups"
S3_BUCKET=${S3_BACKUP_BUCKET:-modporter-backups}
RETENTION_DAYS=${BACKUP_RETENTION_DAYS:-30}
DATE=$(date +%Y%m%d_%H%M%S)
LOG_FILE="/var/log/modporter/backup.log"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a $LOG_FILE
}

error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" | tee -a $LOG_FILE
    exit 1
}

# Create directories
mkdir -p $BACKUP_DIR
mkdir -p /var/log/modporter

log "Starting ${BACKUP_TYPE} backup..."

# ============================================
# Database Backup
# ============================================
log "Backing up PostgreSQL database..."

DB_BACKUP_FILE="${BACKUP_DIR}/db_${DATE}.sql"

if docker ps | grep -q postgres; then
    docker-compose exec -T postgres pg_dump -U modporter modporter > $DB_BACKUP_FILE
    
    if [ $? -eq 0 ]; then
        log "Database dump created: $DB_BACKUP_FILE"
        
        # Compress backup
        gzip $DB_BACKUP_FILE
        log "Database backup compressed: ${DB_BACKUP_FILE}.gz"
        
        # Get backup size
        BACKUP_SIZE=$(du -h "${DB_BACKUP_FILE}.gz" | cut -f1)
        log "Backup size: $BACKUP_SIZE"
    else
        error "Database backup failed!"
    fi
else
    error "PostgreSQL container not running!"
fi

# ============================================
# Upload to S3
# ============================================
log "Uploading backup to S3..."

if command -v aws &> /dev/null; then
    aws s3 cp "${DB_BACKUP_FILE}.gz" "s3://${S3_BUCKET}/daily/db_${DATE}.sql.gz"
    
    if [ $? -eq 0 ]; then
        log "Backup uploaded to S3 successfully"
    else
        error "S3 upload failed!"
    fi
else
    log "AWS CLI not installed. Skipping S3 upload."
fi

# ============================================
# Cleanup Old Backups
# ============================================
log "Cleaning up old backups..."

# Local cleanup (keep RETENTION_DAYS)
find $BACKUP_DIR -name "db_*.sql.gz" -mtime +${RETENTION_DAYS} -delete
log "Local old backups cleaned up"

# S3 cleanup (keep RETENTION_DAYS)
if command -v aws &> /dev/null; then
    aws s3 ls "s3://${S3_BUCKET}/daily/" | while read -r line; do
        file_date=$(echo $line | awk '{print $1}')
        file_name=$(echo $line | awk '{print $4}')
        
        if [ -n "$file_date" ]; then
            file_timestamp=$(date -d "$file_date" +%s 2>/dev/null || echo 0)
            current_timestamp=$(date +%s)
            age_days=$(( (current_timestamp - file_timestamp) / 86400 ))
            
            if [ $age_days -gt $RETENTION_DAYS ]; then
                aws s3 rm "s3://${S3_BUCKET}/daily/${file_name}"
                log "Deleted old S3 backup: ${file_name}"
            fi
        fi
    done
fi

# ============================================
# Backup Summary
# ============================================
log "============================================"
log "Backup completed successfully!"
log "============================================"
log "Backup file: ${DB_BACKUP_FILE}.gz"
log "Backup size: $BACKUP_SIZE"
log "Retention: ${RETENTION_DAYS} days"
log "S3 bucket: ${S3_BUCKET}"
log "============================================"

# ============================================
# Send Notification (Optional)
# ============================================
if [ -n "$SLACK_WEBHOOK_URL" ]; then
    curl -X POST -H 'Content-type: application/json' \
        --data "{\"text\":\"✅ Backup completed successfully!\\nType: ${BACKUP_TYPE}\\nSize: ${BACKUP_SIZE}\\nRetention: ${RETENTION_DAYS} days\"}" \
        $SLACK_WEBHOOK_URL || true
fi
