#!/bin/bash

# Configuration
DATA_DIR="/home/alex/Projects/portkit/ai_engine/mmsd/data"
BACKUP_DIR="$DATA_DIR/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

mkdir -p "$BACKUP_DIR"

echo "[$(date)] Starting backup..."

# Identify the old backup if it exists
OLD_BACKUP=$(ls "$BACKUP_DIR"/mmsd_backup_*.tar.gz 2>/dev/null)

# Create new backup
tar -czf "$BACKUP_DIR/mmsd_backup_$TIMESTAMP.tar.gz" -C "$DATA_DIR" processed/synthesis_pairs.jsonl raw/instructions.jsonl health_check.log

if [ $? -eq 0 ]; then
    echo "[$(date)] Backup successful: mmsd_backup_$TIMESTAMP.tar.gz"
    
    # Delete old backup if new one is successful
    if [ ! -z "$OLD_BACKUP" ]; then
        echo "[$(date)] Removing old backup: $(basename "$OLD_BACKUP")"
        rm "$OLD_BACKUP"
    fi
else
    echo "[$(date)] ERROR: Backup failed!"
    exit 1
fi
