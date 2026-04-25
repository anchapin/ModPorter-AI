#!/bin/bash
# Fly.io startup script for Portkit

echo "🚀 Starting Portkit on Fly.io..."

# Start PostgreSQL if needed (or connect to external)
if [ "$DATABASE_URL" = "" ]; then
    echo "⚠️  No DATABASE_URL set, using local SQLite"
    export DATABASE_URL="sqlite+aiosqlite:///data/db/portkit.db"
    mkdir -p /data/db
else
    # Convert postgresql:// or postgres:// to postgresql+asyncpg:// for async SQLAlchemy
    echo "📊 Using PostgreSQL database"
    case "$DATABASE_URL" in
        postgres://*)
            echo "Converting postgres:// to postgresql+asyncpg://"
            export DATABASE_URL="postgresql+asyncpg://${DATABASE_URL#postgres://}"
            ;;
        postgresql://*)
            echo "Converting postgresql:// to postgresql+asyncpg://"
            export DATABASE_URL="postgresql+asyncpg://${DATABASE_URL#postgresql://}"
            ;;
        *)
            echo "DATABASE_URL already in correct format"
            ;;
    esac
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
export PYTHONPATH=/usr/local/lib/python3.11/dist-packages:/app/backend:/app/backend/src
echo "PYTHONPATH=$PYTHONPATH"
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 1 2>&1 | sed 's/^/[BACKEND] /' &
BACKEND_PID=$!
echo "Backend PID: $BACKEND_PID"

# Start AI Engine
echo "🤖 Starting AI Engine..."
cd /app/ai-engine
export PYTHONPATH=/usr/local/lib/python3.11/dist-packages:/app/ai-engine
echo "PYTHONPATH=$PYTHONPATH"
python -m uvicorn main:app --host 0.0.0.0 --port 8001 --workers 1 2>&1 | sed 's/^/[AI-ENGINE] /' &
AI_PID=$!
echo "AI Engine PID: $AI_PID"

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 10

# Check if services are healthy
echo "🏥 Health checking services..."
for i in 1 2 3 4 5 6 7 8 9 10; do
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        echo "✅ Backend API is healthy"
        break
    fi
    echo "⏳ Waiting for backend... attempt $i/10"
    sleep 5
done

for i in 1 2 3 4 5 6 7 8 9 10; do
    if curl -f http://localhost:8001/health > /dev/null 2>&1; then
        echo "✅ AI Engine is healthy"
        break
    fi
    echo "⏳ Waiting for AI engine... attempt $i/10"
    sleep 5
done

# Start Nginx
echo "🌐 Starting Nginx..."
nginx -g "daemon off;" &
NGINX_PID=$!

echo "🎉 Portkit is running!"
echo "Frontend: http://localhost"
echo "Backend: http://localhost:8000"
echo "AI Engine: http://localhost:8001"

# Keep the script running and handle signals
trap "echo 'Stopping services...'; kill $BACKEND_PID $AI_PID $NGINX_PID 2>/dev/null; exit 0" TERM INT

# Wait for any process to exit
wait $BACKEND_PID $AI_PID $NGINX_PID