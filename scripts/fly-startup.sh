#!/bin/sh
# Fly.io startup script for ModPorter AI

set -e

echo "🚀 Starting ModPorter AI on Fly.io..."

# Start PostgreSQL if needed (or connect to external)
if [ "$DATABASE_URL" = "" ]; then
    echo "⚠️  No DATABASE_URL set, using local SQLite"
    export DATABASE_URL="sqlite:///app/data/modporter.db"
    mkdir -p /app/data
fi

# Start Redis if needed (or connect to external)
if [ "$REDIS_URL" = "" ]; then
    echo "📦 Starting local Redis..."
    redis-server --daemonize yes --port 6379
    export REDIS_URL="redis://localhost:6379"
fi

# Start Backend API
echo "🔧 Starting Backend API..."
cd /app/backend
export PYTHONPATH=/app/backend
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 1 &
BACKEND_PID=$!

# Start AI Engine
echo "🤖 Starting AI Engine..."
cd /app/ai-engine
export PYTHONPATH=/app/ai-engine
python -m uvicorn src.main:app --host 0.0.0.0 --port 8001 --workers 1 &
AI_PID=$!

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 10

# Check if services are healthy
echo "🏥 Health checking services..."
for i in 1 2 3 4 5; do
    if curl -f http://localhost:8000/api/v1/health > /dev/null 2>&1; then
        echo "✅ Backend API is healthy"
        break
    fi
    echo "⏳ Waiting for backend... attempt $i/5"
    sleep 5
done

for i in 1 2 3 4 5; do
    if curl -f http://localhost:8001/api/v1/health > /dev/null 2>&1; then
        echo "✅ AI Engine is healthy"
        break
    fi
    echo "⏳ Waiting for AI engine... attempt $i/5"
    sleep 5
done

# Start Nginx
echo "🌐 Starting Nginx..."
nginx -g "daemon off;" &
NGINX_PID=$!

echo "🎉 ModPorter AI is running!"
echo "Frontend: http://localhost"
echo "Backend: http://localhost:8000"
echo "AI Engine: http://localhost:8001"

# Keep the script running and handle signals
trap "echo 'Stopping services...'; kill $BACKEND_PID $AI_PID $NGINX_PID; exit 0" TERM INT

# Wait for any process to exit
wait