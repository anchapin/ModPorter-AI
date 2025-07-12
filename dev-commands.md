# Development Commands

## For Development Environment

When working with the development environment, always use the dev-specific commands:

### Build Services
```bash
# Build all services for development
docker-compose -f docker-compose.dev.yml build

# Build specific service for development
docker-compose -f docker-compose.dev.yml build frontend
docker-compose -f docker-compose.dev.yml build backend
docker-compose -f docker-compose.dev.yml build ai-engine
```

### Start/Stop Services
```bash
# Start all development services
docker-compose -f docker-compose.dev.yml up -d

# Start specific service
docker-compose -f docker-compose.dev.yml up -d frontend

# Stop all services
docker-compose -f docker-compose.dev.yml down

# Restart specific service
docker-compose -f docker-compose.dev.yml restart frontend
```

### Rebuild and Restart
```bash
# Full rebuild and restart (recommended when Dockerfile changes)
docker-compose -f docker-compose.dev.yml down
docker-compose -f docker-compose.dev.yml build --no-cache
docker-compose -f docker-compose.dev.yml up -d
```

### Troubleshooting
```bash
# Check logs for specific service
docker-compose -f docker-compose.dev.yml logs frontend
docker-compose -f docker-compose.dev.yml logs backend
docker-compose -f docker-compose.dev.yml logs ai-engine

# Check container status
docker-compose -f docker-compose.dev.yml ps
```

## Important Notes

1. **Always use `-f docker-compose.dev.yml`** for development
2. **Never use just `docker compose build`** - it uses the production configuration
3. **Frontend uses Node.js in dev, nginx in production**
4. **Development ports:**
   - Frontend: http://localhost:3002
   - Backend: http://localhost:8080
   - AI Engine: http://localhost:8001
   - Database: localhost:5433