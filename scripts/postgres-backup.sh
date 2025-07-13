#!/bin/bash
# PostgreSQL Backup Script for ModPorter AI
# Day 6: Production database backup strategy

set -e

# Configuration
DB_NAME="modporter"
DB_USER="postgres"
BACKUP_DIR="/backups"
RETENTION_DAYS=30
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/modporter_backup_${TIMESTAMP}.sql"

# Create backup directory if it doesn't exist
mkdir -p ${BACKUP_DIR}

echo "Starting backup of database: ${DB_NAME}"
echo "Backup file: ${BACKUP_FILE}"

# Create backup
pg_dump -h localhost -U ${DB_USER} -d ${DB_NAME} --verbose --format=custom --no-owner --no-privileges > ${BACKUP_FILE}

# Compress backup
gzip ${BACKUP_FILE}
BACKUP_FILE="${BACKUP_FILE}.gz"

echo "Backup completed: ${BACKUP_FILE}"

# Check backup file size
BACKUP_SIZE=$(du -h ${BACKUP_FILE} | cut -f1)
echo "Backup size: ${BACKUP_SIZE}"

# Remove old backups
echo "Cleaning up old backups (older than ${RETENTION_DAYS} days)..."
find ${BACKUP_DIR} -name "modporter_backup_*.sql.gz" -type f -mtime +${RETENTION_DAYS} -delete

echo "Backup process completed successfully"

# Verify backup integrity
echo "Verifying backup integrity..."
gunzip -t ${BACKUP_FILE}
if [ $? -eq 0 ]; then
    echo "Backup integrity check passed"
else
    echo "ERROR: Backup integrity check failed!"
    exit 1
fi

# Upload to S3 if configured
if [ ! -z "${S3_BACKUP_BUCKET}" ] && [ ! -z "${AWS_ACCESS_KEY_ID}" ]; then
    echo "Uploading backup to S3..."
    aws s3 cp ${BACKUP_FILE} s3://${S3_BACKUP_BUCKET}/postgres/ --storage-class STANDARD_IA
    echo "S3 upload completed"
fi

echo "Database backup completed successfully!"