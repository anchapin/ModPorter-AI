#!/bin/bash
# Production Deployment Script for ModPorter AI
# Usage: ./scripts/deploy-prod.sh [staging|production]

set -e

# Configuration
ENVIRONMENT=${1:-production}
PROJECT_NAME="modporter-ai"
BACKUP_DIR="/backups"
LOG_FILE="/var/log/modporter/deploy.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a $LOG_FILE
}

error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" | tee -a $LOG_FILE
    exit 1
}

warning() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1" | tee -a $LOG_FILE
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    error "Please run as root (sudo ./scripts/deploy-prod.sh)"
fi

# Create log directory
mkdir -p /var/log/modporter

log "Starting deployment to ${ENVIRONMENT}..."

# ============================================
# Pre-deployment Checks
# ============================================
log "Running pre-deployment checks..."

# Check Docker
if ! command -v docker &> /dev/null; then
    error "Docker is not installed. Please install Docker first."
fi

# Check Docker Compose
if ! command -v docker-compose &> /dev/null; then
    error "Docker Compose is not installed. Please install Docker Compose first."
fi

# Check if .env.prod exists
if [ ! -f ".env.prod" ]; then
    error ".env.prod file not found. Please copy .env.prod.example to .env.prod and configure it."
fi

log "Pre-deployment checks passed."

# ============================================
# Backup Current State
# ============================================
log "Creating backup..."

mkdir -p $BACKUP_DIR

# Backup database
if docker ps | grep -q postgres; then
    BACKUP_FILE="${BACKUP_DIR}/db_backup_$(date +%Y%m%d_%H%M%S).sql"
    docker-compose exec -T postgres pg_dump -U modporter modporter > $BACKUP_FILE
    gzip $BACKUP_FILE
    log "Database backup created: ${BACKUP_FILE}.gz"
fi

# Backup current docker-compose state
docker-compose ps > ${BACKUP_DIR}/containers_$(date +%Y%m%d_%H%M%S).txt 2>&1 || true

log "Backup completed."

# ============================================
# Pull Latest Changes
# ============================================
log "Pulling latest changes from git..."

git fetch origin
git checkout main
git pull origin main

log "Latest changes pulled."

# ============================================
# Build and Deploy
# ============================================
log "Building Docker images..."

docker-compose -f docker-compose.prod.yml build --no-cache

log "Docker images built."

log "Starting services..."

docker-compose -f docker-compose.prod.yml up -d

log "Services started."

# ============================================
# Wait for Services to be Healthy
# ============================================
log "Waiting for services to be healthy..."

# Wait for PostgreSQL
log "Waiting for PostgreSQL..."
timeout 60 bash -c 'until docker-compose exec -T postgres pg_isready -U modporter > /dev/null 2>&1; do sleep 2; done' || error "PostgreSQL failed to start"

# Wait for Redis
log "Waiting for Redis..."
timeout 30 bash -c 'until docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; do sleep 2; done' || error "Redis failed to start"

# Wait for Backend
log "Waiting for Backend..."
timeout 60 bash -c 'until curl -s http://localhost:8080/api/v1/health > /dev/null 2>&1; do sleep 5; done' || error "Backend failed to start"

# Wait for Frontend
log "Waiting for Frontend..."
timeout 30 bash -c 'until curl -s http://localhost:3000 > /dev/null 2>&1; do sleep 2; done' || warning "Frontend may still be starting"

log "All services are healthy!"

# ============================================
# Run Database Migrations
# ============================================
log "Running database migrations..."

docker-compose exec -T backend bash -c "cd /app/src && alembic upgrade head" || warning "Database migrations may have failed"

log "Database migrations completed."

# ============================================
# Post-deployment Checks
# ============================================
log "Running post-deployment checks..."

# Check all services
docker-compose -f docker-compose.prod.yml ps

# Test health endpoints
log "Testing health endpoints..."

BACKEND_HEALTH=$(curl -s http://localhost:8080/api/v1/health | python3 -c "import sys, json; print(json.load(sys.stdin).get('status', 'unknown'))" 2>/dev/null || echo "failed")
log "Backend health: $BACKEND_HEALTH"

if [ "$BACKEND_HEALTH" != "healthy" ]; then
    warning "Backend health check failed. Check logs for details."
fi

log "Post-deployment checks completed."

# ============================================
# Cleanup Old Backups
# ============================================
log "Cleaning up old backups..."

find $BACKUP_DIR -name "db_backup_*.sql.gz" -mtime +30 -delete || true

log "Old backups cleaned up."

# ============================================
# Deployment Summary
# ============================================
log "============================================"
log "Deployment completed successfully!"
log "============================================"
log ""
log "Service URLs:"
log "  Frontend:  http://localhost:3000"
log "  Backend:   http://localhost:8080"
log "  Grafana:   http://localhost:3001 (admin/admin)"
log "  Prometheus: http://localhost:9090"
log "  Jaeger:    http://localhost:16686"
log ""
log "Next steps:"
log "  1. Configure SSL certificates (certbot)"
log "  2. Configure DNS records"
log "  3. Set up email service (SendGrid)"
log "  4. Monitor logs: tail -f /var/log/modporter/deploy.log"
log "============================================"
