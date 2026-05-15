#!/bin/bash
# Fly.io startup script for Portkit
# Supports two modes:
#   MONOLITH: AI Engine runs in the same container (AI_ENGINE_EXTRACTED unset or 0)
#   EXTRACTED: AI Engine runs as a separate Fly.io app (AI_ENGINE_EXTRACTED=1)

echo "🚀 Starting Portkit on Fly.io..."

# Default AI Engine upstream for monolith mode
export AI_ENGINE_UPSTREAM="${AI_ENGINE_UPSTREAM:-localhost:8001}"

# Render nginx config from template (envsubst only replaces ${AI_ENGINE_UPSTREAM})
echo "📝 Rendering nginx config (AI_ENGINE_UPSTREAM=${AI_ENGINE_UPSTREAM})..."
envsubst '${AI_ENGINE_UPSTREAM}' < /etc/nginx/nginx.conf.template > /etc/nginx/nginx.conf

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

# Start AI Engine locally only in monolith mode
if [ "$AI_ENGINE_EXTRACTED" = "1" ]; then
    echo "🤖 AI Engine runs as a separate Fly.io app (portkit-ai-engine) — skipping local startup"
else
    echo "🤖 Starting AI Engine (monolith mode)..."
    cd /app/ai-engine
    export PYTHONPATH=/usr/local/lib/python3.11/dist-packages:/app/ai-engine
    echo "PYTHONPATH=$PYTHONPATH"
    python -m uvicorn main:app --host 0.0.0.0 --port 8001 --workers 1 2>&1 | sed 's/^/[AI-ENGINE] /' &
    AI_PID=$!
    echo "AI Engine PID: $AI_PID"
fi

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 10

# Check if backend is healthy
echo "🏥 Health checking backend..."
for i in 1 2 3 4 5 6 7 8 9 10; do
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        echo "✅ Backend API is healthy"
        break
    fi
    echo "⏳ Waiting for backend... attempt $i/10"
    sleep 5
done

# Check AI Engine health (local or remote)
if [ "$AI_ENGINE_EXTRACTED" = "1" ]; then
    echo "🤖 Checking remote AI Engine health at ${AI_ENGINE_UPSTREAM}..."
    for i in 1 2 3 4 5; do
        if curl -f "http://${AI_ENGINE_UPSTREAM}/health/liveness" > /dev/null 2>&1; then
            echo "✅ Remote AI Engine is healthy"
            break
        fi
        echo "⏳ Waiting for remote AI engine... attempt $i/5"
        sleep 5
    done
else
    for i in 1 2 3 4 5 6 7 8 9 10; do
        if curl -f http://localhost:8001/health > /dev/null 2>&1; then
            echo "✅ AI Engine is healthy"
            break
        fi
        echo "⏳ Waiting for AI engine... attempt $i/10"
        sleep 5
    done
fi

# Start Nginx
echo "🌐 Starting Nginx..."
nginx -g "daemon off;" &
NGINX_PID=$!

echo "🎉 Portkit is running!"
echo "Frontend: http://localhost"
echo "Backend: http://localhost:8000"
if [ "$AI_ENGINE_EXTRACTED" = "1" ]; then
    echo "AI Engine: http://${AI_ENGINE_UPSTREAM} (separate app)"
else
    echo "AI Engine: http://localhost:8001"
fi

# Keep the script running and handle signals
if [ -n "${AI_PID:-}" ]; then
    trap "echo 'Stopping services...'; kill $BACKEND_PID $AI_PID $NGINX_PID 2>/dev/null; exit 0" TERM INT
    wait $BACKEND_PID $AI_PID $NGINX_PID
else
    trap "echo 'Stopping services...'; kill $BACKEND_PID $NGINX_PID 2>/dev/null; exit 0" TERM INT
    wait $BACKEND_PID $NGINX_PID
fi
