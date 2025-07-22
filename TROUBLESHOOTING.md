# Troubleshooting Guide

## Quick Status Check

```bash
# Check all services
docker compose -f docker compose.dev.yml ps

# Check logs for specific service
docker compose -f docker compose.dev.yml logs [service-name]

# Test service health
curl http://localhost:8080/api/v1/health  # Backend
curl http://localhost:8001/api/v1/health  # AI Engine
curl http://localhost:3002               # Frontend
```

## Common Issues and Solutions

### 1. Frontend Import Errors

**Problem**: `SyntaxError: The requested module does not provide an export named 'X'`

**Solution**: 
```bash
# Restart the frontend container to clear cache
docker compose -f docker compose.dev.yml restart frontend
```

### 2. AI Engine Not Starting

**Problem**: AI engine fails to initialize with LLM errors

**Solution**: The development environment uses mock LLM by default. Check configuration:
```bash
# Check environment variables
docker compose -f docker compose.dev.yml exec ai-engine env | grep -E "(USE_MOCK_LLM|USE_OLLAMA)"

# Should show:
# USE_MOCK_LLM=true
# USE_OLLAMA=false
```

### 3. Container Build Issues

**Problem**: Frontend shows nginx errors instead of Node.js

**Solution**: Always use the dev-specific commands:
```bash
# Wrong (uses production config)
docker compose build

# Correct (uses dev config)
docker compose -f docker compose.dev.yml build
```

### 4. Database Issues

**Problem**: PostgreSQL vector extension errors

**Solution**: The database will show warnings but continue working. This is normal in development.

### 5. Port Conflicts

**Problem**: Services can't bind to ports

**Solution**: Check for conflicting services:
```bash
# Check what's using the ports
netstat -tulpn | grep -E "(3002|8080|8001|5433|6379|11434)"

# Stop conflicting services or use different ports
```

## Service URLs

- **Frontend**: http://localhost:3002
- **Backend**: http://localhost:8080
- **AI Engine**: http://localhost:8001
- **Database**: localhost:5433
- **Redis**: localhost:6379
- **Ollama**: localhost:11434

## Development Commands

```bash
# Start all services
docker compose -f docker compose.dev.yml up -d

# Stop all services
docker compose -f docker compose.dev.yml down

# Rebuild and restart
docker compose -f docker compose.dev.yml down
docker compose -f docker compose.dev.yml build --no-cache
docker compose -f docker compose.dev.yml up -d

# Check logs
docker compose -f docker compose.dev.yml logs -f [service-name]
```

## Configuration

The development environment is configured for:
- ✅ Mock LLM (no API keys needed)
- ✅ Hot reloading for frontend
- ✅ Auto-reload for backend services
- ✅ Persistent volumes for data
- ✅ Proper networking between services

## Current Status

All services are healthy and running:
- Frontend: React + Vite dev server
- Backend: FastAPI with auto-reload
- AI Engine: FastAPI with mock LLM
- Database: PostgreSQL with pgvector
- Redis: In-memory data store
- Ollama: Local LLM server (available but not used in dev)