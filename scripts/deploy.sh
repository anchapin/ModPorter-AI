#!/bin/bash
# Production Deployment Script for ModPorter AI
# Day 6: CI/CD deployment automation

set -e

# Configuration
ENVIRONMENT=${1:-production}
COMPOSE_FILE="docker-compose.prod.yml"
ENV_FILE=".env.prod"

echo "🚀 Starting ModPorter AI deployment for environment: ${ENVIRONMENT}"

# Check prerequisites
echo "✅ Checking prerequisites..."
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed"
    exit 1
fi

if [ ! -f "${ENV_FILE}" ]; then
    echo "❌ Environment file ${ENV_FILE} not found"
    exit 1
fi

# Load environment variables
source ${ENV_FILE}

# Validate required environment variables
REQUIRED_VARS=("DB_PASSWORD" "SECRET_KEY" "JWT_SECRET_KEY")
for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        echo "❌ Required environment variable ${var} is not set"
        exit 1
    fi
done

echo "✅ Prerequisites check passed"

# Create necessary directories
echo "📁 Creating required directories..."
mkdir -p logs ssl monitoring/grafana/dashboards monitoring/grafana/provisioning scripts

# Set permissions for backup script
chmod +x scripts/postgres-backup.sh

# Pull latest images
echo "📥 Pulling latest Docker images..."
docker-compose -f ${COMPOSE_FILE} pull

# Build application images
echo "🔨 Building application images..."
docker-compose -f ${COMPOSE_FILE} build --no-cache

# Stop existing services gracefully
echo "🛑 Stopping existing services..."
docker-compose -f ${COMPOSE_FILE} down --remove-orphans

# Start services
echo "🚀 Starting services..."
docker-compose -f ${COMPOSE_FILE} up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to be healthy..."
sleep 30

# Check service health
echo "🏥 Checking service health..."
services=("backend" "ai-engine" "redis" "postgres")
for service in "${services[@]}"; do
    echo "Checking ${service}..."
    if docker-compose -f ${COMPOSE_FILE} ps ${service} | grep -q "healthy\|Up"; then
        echo "✅ ${service} is healthy"
    else
        echo "❌ ${service} is not healthy"
        docker-compose -f ${COMPOSE_FILE} logs ${service}
        exit 1
    fi
done

# Run database migrations if needed
echo "🗄️ Running database migrations..."
docker-compose -f ${COMPOSE_FILE} exec -T backend python -m alembic upgrade head

# Verify deployment
echo "✅ Verifying deployment..."
if curl -f http://localhost:${BACKEND_PORT:-8080}/api/v1/health > /dev/null 2>&1; then
    echo "✅ Backend health check passed"
else
    echo "❌ Backend health check failed"
    exit 1
fi

if curl -f http://localhost:${AI_ENGINE_PORT:-8001}/api/v1/health > /dev/null 2>&1; then
    echo "✅ AI Engine health check passed"
else
    echo "❌ AI Engine health check failed"
    exit 1
fi

if curl -f http://localhost:${FRONTEND_PORT:-80}/health > /dev/null 2>&1; then
    echo "✅ Frontend health check passed"
else
    echo "❌ Frontend health check failed"
    exit 1
fi

# Setup monitoring
echo "📊 Setting up monitoring..."
if [ "${PROMETHEUS_ENABLED}" = "true" ]; then
    echo "✅ Prometheus monitoring enabled"
    echo "📊 Grafana dashboard available at: http://localhost:${GRAFANA_PORT:-3001}"
    echo "📈 Prometheus available at: http://localhost:${PROMETHEUS_PORT:-9090}"
fi

# Setup log rotation
echo "📝 Setting up log rotation..."
cat > /etc/logrotate.d/modporter << EOF
/var/lib/docker/volumes/modporter_*_logs/_data/*.log {
    daily
    missingok
    rotate 52
    compress
    notifempty
    create 644 root root
    postrotate
        docker-compose -f ${COMPOSE_FILE} restart
    endscript
}
EOF

# Setup backup cron job
echo "💾 Setting up backup cron job..."
(crontab -l 2>/dev/null; echo "0 2 * * * docker-compose -f ${PWD}/${COMPOSE_FILE} exec -T postgres /usr/local/bin/backup.sh") | crontab -

# Print deployment summary
echo ""
echo "🎉 ModPorter AI deployment completed successfully!"
echo ""
echo "📋 Deployment Summary:"
echo "  🌐 Frontend: http://localhost:${FRONTEND_PORT:-80}"
echo "  🔗 Backend API: http://localhost:${BACKEND_PORT:-8080}/api/v1"
echo "  🤖 AI Engine: http://localhost:${AI_ENGINE_PORT:-8001}/api/v1"
echo "  📊 Grafana: http://localhost:${GRAFANA_PORT:-3001}"
echo "  📈 Prometheus: http://localhost:${PROMETHEUS_PORT:-9090}"
echo ""
echo "📚 Useful Commands:"
echo "  View logs: docker-compose -f ${COMPOSE_FILE} logs -f [service]"
echo "  Scale service: docker-compose -f ${COMPOSE_FILE} up -d --scale [service]=[count]"
echo "  Stop services: docker-compose -f ${COMPOSE_FILE} down"
echo "  Backup database: docker-compose -f ${COMPOSE_FILE} exec postgres /usr/local/bin/backup.sh"
echo ""
echo "✅ All services are running and healthy!"