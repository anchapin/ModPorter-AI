# Disaster Recovery Plan

**Issue**: [#1206](https://github.com/anchapin/portkit/issues/1206)
**Milestone**: M5: Beta Launch
**Status**: Pre-beta blocker

---

## Overview

PortKit uses PostgreSQL 15 with pgvector extension as its primary database, storing:
- User accounts and authentication
- Stripe subscription associations
- Conversion job history and state
- Document embeddings for RAG
- Session state

This document defines the disaster recovery plan, backup procedures, and point-in-time recovery capabilities.

---

## Recovery Objectives

| Objective | Target | Description |
|-----------|--------|-------------|
| **RPO** | 24 hours | Maximum acceptable data loss |
| **RTO** | 4 hours | Maximum acceptable downtime |
| **PITR Window** | 7 days | Can restore to any point in last 7 days |
| **Backup Frequency** | Daily | Full backups at minimum |

---

## Backup Architecture

### Backup Types

1. **Daily Full Backups**
   - Complete database dump in custom format (pg_dump)
   - Compressed with gzip
   - Local storage: `/backups/postgres/daily/`
   - S3 storage: `s3://{bucket}/postgres/daily/`

2. **WAL Archival** (for PITR)
   - Write-Ahead Log shipping enabled
   - Archived to `/backups/postgres/wal/`
   - S3 WAL archival for offsite redundancy

3. **Offsite Replication**
   - S3 bucket with Standard_IA storage
   - Cross-region replication for DR
   - Backblaze B2 as secondary backup location

### Retention Policy

| Tier | Retention | Storage Location |
|------|------------|------------------|
| Daily | 7 days | Local + S3 |
| Weekly | 4 weeks | S3 |
| Monthly | 12 months | S3/Glacier |
| Yearly | 7 years | S3/Glacier |

---

## Automated Backup System

### Primary Backup Script

The backup system is automated via `scripts/portkit-backup.sh`:

```bash
# Daily backup (default - full + verification)
./scripts/portkit-backup.sh daily

# Weekly backup (full)
./scripts/portkit-backup.sh weekly

# Monthly backup (full)
./scripts/portkit-backup.sh monthly

# List available backups
./scripts/portkit-backup.sh list

# Verify a specific backup
./scripts/portkit-backup.sh verify /path/to/backup.dump.gz
```

### Environment Variables

```bash
# Database connection
export PGHOST=localhost
export PGPORT=5432
export PGDATABASE=portkit
export PGUSER=postgres
export PGPASSWORD=your_password

# Backup configuration
export BACKUP_ROOT=/backups/postgres
export RETENTION_DAILY=7
export RETENTION_WEEKLY=4
export RETENTION_MONTHLY=12

# S3 configuration
export S3_BACKUP_BUCKET=your-bucket-name
export AWS_ACCESS_KEY_ID=your-key
export AWS_SECRET_ACCESS_KEY=your-secret

# Notifications
export SLACK_WEBHOOK_URL=https://hooks.slack.com/...
export BACKUP_LOG_FILE=/var/log/portkit/backup.log
```

### Cron Schedule

```bash
# Edit crontab
crontab -e

# Daily backup at midnight UTC
0 0 * * * /home/alex/Projects/portkit/scripts/portkit-backup.sh daily >> /var/log/portkit/backup.log 2>&1

# Weekly backup on Sunday at 1 AM UTC
0 1 * * 0 /home/alex/Projects/portkit/scripts/portkit-backup.sh weekly >> /var/log/portkit/backup.log 2>&1

# Monthly backup on 1st of month at 2 AM UTC
0 2 1 * * /home/alex/Projects/portkit/scripts/portkit-backup.sh monthly >> /var/log/portkit/backup.log 2>&1
```

---

## Point-in-Time Recovery (PITR)

### Prerequisites

1. WAL archiving must be enabled
2. Sufficient backup storage for WAL segments
3. Understanding of the target recovery point

### PITR Recovery Process

#### Step 1: Identify Recovery Point

```bash
# List available WAL segments
ls -la /backups/postgres/wal/

# Check backup timestamps
./scripts/portkit-backup.sh list

# Determine target recovery time (format: YYYY-MM-DD HH:MM:SS)
```

#### Step 2: Prepare Recovery Environment

```bash
# Stop application services
docker compose -f docker-compose.prod.yml stop backend celery-worker

# Keep postgres running for recovery
docker compose -f docker-compose.prod.yml stop -t postgres  # NOT this
# Instead, just stop write traffic
```

#### Step 3: Restore Base Backup

```bash
# Create new database for recovery
createdb -h localhost -U postgres -d portkit portkit_recovered

# Extract and restore full backup
gunzip -c /backups/postgres/daily/full_20260401_120000.dump.gz | \
    pg_restore -h localhost -U postgres -d portkit_recovered --no-owner --verbose
```

#### Step 4: Configure Recovery

Create recovery configuration:

```bash
# Create recovery.conf (PostgreSQL 12 and later uses recovery.target)
cat > /var/lib/postgresql/data/postgresql.conf.recovery << EOF
restore_command = 'gunzip -c /backups/postgres/wal/%f > %p'
recovery_target_time = '2026-04-15 14:30:00 UTC'
recovery_target_action = 'promote'
EOF
```

#### Step 5: Apply WAL and Verify

```bash
# Start PostgreSQL in recovery mode
pg_ctl start -D /var/lib/postgresql/data

# Monitor recovery progress
psql -h localhost -U postgres -d portkit_recovered -c "SELECT pg_is_in_recovery();"

# Verify data at recovery point
psql -h localhost -U postgres -d portkit_recovered -c "SELECT count(*) FROM users;"
psql -h localhost -U postgres -d portkit_recovered -c "SELECT count(*) FROM conversion_jobs;"
```

---

## Disaster Recovery Scenarios

### Scenario 1: Database Corruption

**Symptoms:**
- Database reports corruption errors
- Query failures with I/O errors
- Inconsistent data integrity

**Recovery Steps:**
1. Stop writes to the database immediately
2. Create a final backup of current state (if possible)
3. Identify the last known good backup
4. Restore from the most recent clean backup
5. Verify data integrity
6. Resume operations

**Estimated RTO:** 1-2 hours

### Scenario 2: Complete Data Loss

**Symptoms:**
- Database volume destroyed
- Hardware failure
- Natural disaster

**Recovery Steps:**
1. Provision new database server
2. Restore from most recent S3 backup
3. Verify application connectivity
4. Resume operations
5. Document lessons learned

**Estimated RTO:** 2-4 hours

### Scenario 3: Ransomware Attack

**Symptoms:**
- Database encrypted
- Backup files encrypted
- Ransom note received

**Recovery Steps:**
1. Isolate affected systems immediately
2. Do NOT pay the ransom
3. Restore from offline S3 backups (not connected to network)
4. Verify no malware in restored system
5. Resume operations
6. Report to authorities

**Estimated RTO:** 4-8 hours

---

## DR Runbook

### Quick Reference

```
INCIDENT: Database failure
SEVERITY: P0 (Critical)
RESPONSE TIME: 15 minutes

IMMEDIATE ACTIONS:
1. Stop write traffic to database
2. Assess extent of damage
3. Identify last good backup
4. Initiate restore procedure
5. Verify data integrity
6. Resume operations

CONTACT:
- Primary: @alex (GitHub: anchapin)
- Backup: None configured yet
```

### Step-by-Step Recovery

#### Phase 1: Assessment (0-15 minutes)

```bash
# Check database status
pg_isready -h localhost -p 5432 -U postgres

# Check recent backups
./scripts/portkit-backup.sh list

# Check backup age
ls -la /backups/postgres/daily/

# Identify last good backup timestamp
```

#### Phase 2: Decision (15-30 minutes)

Based on assessment, choose one:
- **Restore to point-in-time**: If recent transactions must be recovered
- **Restore to last backup**: If data loss is acceptable
- **Rebuild from scratch**: If no viable backup exists (last resort)

#### Phase 3: Restore (30 minutes - 2 hours)

```bash
# Option A: Full restore from latest backup
docker compose -f docker-compose.prod.yml stop backend
gunzip -c /backups/postgres/daily/latest.dump.gz | \
    pg_restore -h localhost -U postgres -d portkit --clean --no-owner
docker compose -f docker-compose.prod.yml start backend

# Option B: Restore to new database for verification
createdb -h localhost -U postgres portkit_test
gunzip -c /backups/postgres/daily/latest.dump.gz | \
    pg_restore -h localhost -U postgres -d portkit_test --no-owner
# Verify, then swap
```

#### Phase 4: Verification (2-4 hours)

```bash
# Verify database integrity
psql -h localhost -U postgres -d portkit -c "SELECT count(*) FROM users;"
psql -h localhost -U postgres -d portkit -c "SELECT count(*) FROM conversion_jobs;"
psql -h localhost -U postgres -d portkit -c "SELECT count(*) FROM subscriptions;"

# Verify pgvector extension
psql -h localhost -U postgres -d portkit -c \
    "SELECT * FROM pg_extension WHERE extname='vector';"

# Check application connectivity
curl -f http://localhost:8000/api/v1/health
```

---

## Backup Monitoring and Alerts

### Prometheus Alert Rules

The following alerts are configured in `monitoring/alert_rules.yml`:

| Alert | Condition | Severity |
|-------|-----------|----------|
| `BackupTooOld` | No backup in 25 hours | critical |
| `BackupVerificationFailed` | Backup verification fails | critical |
| `BackupUploadFailed` | S3 upload fails | warning |
| `PostgreSQLDown` | Database unavailable | critical |

### Manual Verification Commands

```bash
# Check backup file exists and age
ls -la /backups/postgres/daily/

# Verify backup integrity
./scripts/portkit-backup.sh verify /backups/postgres/daily/full_latest.dump.gz

# List backup contents
pg_restore -l /backups/postgres/daily/full_latest.dump.gz | head -20

# Test restore to temporary database
createdb -h localhost -U postgres portkit_test
pg_restore -h localhost -U postgres -d portkit_test /backups/postgres/daily/full_latest.dump.gz
psql -h localhost -U postgres -d portkit_test -c "\dt"
dropdb -h localhost -U postgres portkit_test
```

### Health Check Endpoint

The `/api/v1/health` endpoint includes backup status information:

```json
{
  "status": "healthy",
  "backup": {
    "last_success": "2026-05-03T00:00:00Z",
    "age_hours": 12,
    "verified": true
  }
}
```

---

## Testing the DR Plan

### Monthly Testing Procedure

1. **First week of month**: Schedule DR test
2. **Day before**: Notify team of upcoming test
3. **Test day**:
   - Create isolated test environment
   - Restore latest backup to test DB
   - Verify data integrity (row counts, checksums)
   - Test application connectivity
   - Document results
4. **Post-test**: Clean up test environment

### Test Checklist

- [ ] Backup completed successfully in last 24 hours
- [ ] Backup file size is reasonable (not empty, not suspiciously small)
- [ ] Backup verification passed
- [ ] S3 upload completed (if configured)
- [ ] Restore to test database works
- [ ] Row counts match expected values
- [ ] pgvector extension loaded correctly
- [ ] Application can connect to restored database
- [ ] Document test results in post-mortem directory

---

## Fly.io Specific Instructions

For deployments on Fly.io:

### Enable Automated Backups

```bash
# Check current backup configuration
flyctl postgres status -a portkit-db

# Configure automated backups (paid plan required)
flyctl postgres update -a portkit-db --backup-retention 30
```

### Fly.io WAL and PITR

```bash
# Create manual snapshot
flyctl postgres snapshot create -a portkit-db

# List snapshots
flyctl postgres snapshot list -a portkit-db

# Restore from snapshot
flyctl postgres restore -a portkit-db --snapshot <snapshot-id>
```

### Fly.io Environment Variables

```bash
# Set backup-related secrets
flyctl secrets set BACKUP_ROOT=/backups/postgres
flyctl secrets set S3_BACKUP_BUCKET=portkit-backups
flyctl secrets set WAL_ARCHIVE_PATH=/backups/postgres/wal

# Set S3 credentials
flyctl secrets set AWS_ACCESS_KEY_ID=<key>
flyctl secrets set AWS_SECRET_ACCESS_KEY=<secret>
```

---

## Offsite Backup Configuration

### S3 Configuration

```bash
# Create S3 bucket with versioning
aws s3 mb s3://portkit-backups --region us-east-1

# Enable versioning
aws s3api put-bucket-versioning --bucket portkit-backups --versioning-configuration Status=Enabled

# Enable cross-region replication
aws s3api put-bucket-replication --bucket portkit-backups --replication-configuration file://replication.json
```

### Backblaze B2 Configuration

```bash
# Install b2 CLI
pip install b2

# Configure b2
b2 authorize-account

# Create bucket for backups
b2 create-bucket portkit-dr-backups allPublic

# Upload script for offsite copy
./scripts/offsite-backup.sh
```

---

## Related Documentation

- [DATABASE_BACKUP.md](./DATABASE_BACKUP.md) - Detailed backup procedures
- [runbook.md](./runbook.md) - Incident response procedures
- [HIGH-AVAILABILITY.md](./HIGH-AVAILABILITY.md) - HA configuration
- [scripts/portkit-backup.sh](../scripts/portkit-backup.sh) - Backup script
- [monitoring/alert_rules.yml](../monitoring/alert_rules.yml) - Alert configuration

---

## Change Log

| Date | Version | Changes |
|------|---------|---------|
| 2026-05-03 | 1.0 | Initial document creation for issue #1206 |

---

*Document Version: 1.0*
*Last Updated: 2026-05-03*
*Maintained by: anchapin*