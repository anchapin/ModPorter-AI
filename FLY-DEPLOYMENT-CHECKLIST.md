# Fly.io Deployment Checklist for ModPorter AI

## ✅ Prerequisites Completed in PR #184
- [x] Multi-stage Dockerfile optimized for Fly.io (`Dockerfile.fly`)
- [x] Fly.io configuration file (`deploy-fly.toml`)
- [x] Nginx configuration for production (`nginx-fly.conf`)
- [x] Startup script for coordinating services (`scripts/fly-startup.sh`)
- [x] Fixed CI/CD issues:
  - [x] Added missing `ai-engine/setup.py` and `ai-engine/requirements.txt`
  - [x] Added missing `backend/setup.py` and `backend/requirements.txt`
  - [x] Created `backend/tests/` directory with basic health test

## 🚀 Manual Steps Required Before Deployment

### 1. Install Fly.io CLI
```bash
# Install flyctl
curl -L https://fly.io/install.sh | sh

# Add to PATH (add to ~/.bashrc or ~/.zshrc)
export PATH="$HOME/.fly/bin:$PATH"

# Verify installation
flyctl version
```

### 2. Authenticate with Fly.io
```bash
# Sign up/login to Fly.io
flyctl auth signup
# OR
flyctl auth login
```

### 3. Create Fly.io App
```bash
# Navigate to project root
cd /path/to/ModPorter-AI

# Create the app (will use settings from deploy-fly.toml)
flyctl apps create modporter-ai --generate-name=false

# Or let Fly.io generate a unique name
flyctl apps create --generate-name
```

### 4. Set Required Secrets
```bash
# Essential secrets for production
flyctl secrets set OPENAI_API_KEY="your-openai-api-key"
flyctl secrets set SECRET_KEY="your-secret-key-for-jwt"
flyctl secrets set DATABASE_URL="postgresql://postgres:password@modporter-postgres.internal:5432/modporter"
flyctl secrets set REDIS_URL="redis://modporter-redis.internal:6379"

# Optional: Environment-specific secrets
flyctl secrets set ANTHROPIC_API_KEY="your-anthropic-key"
flyctl secrets set GEMINI_API_KEY="your-gemini-key"
```

### 5. Create Persistent Volume
```bash
# Create volume for persistent data
flyctl volumes create modporter_data --region iad --size 10
```

### 6. Setup External Database (Recommended)
```bash
# Create PostgreSQL database
flyctl postgres create --name modporter-postgres --region iad

# Get connection string
flyctl postgres connect -a modporter-postgres

# Create Redis instance
flyctl redis create --name modporter-redis --region iad
```

### 7. Deploy Application
```bash
# Deploy using our custom config
flyctl deploy --config deploy-fly.toml

# Monitor deployment
flyctl logs
```

### 8. Verify Deployment
```bash
# Check app status
flyctl status

# Check logs
flyctl logs

# Open in browser
flyctl open

# Test health endpoints
curl https://your-app.fly.dev/health
curl https://your-app.fly.dev/api/v1/health
```

## 🔧 Configuration Details

### Environment Variables Set in `deploy-fly.toml`:
- `ENVIRONMENT=production`
- `LOG_LEVEL=INFO`
- `DOMAIN=modporter.ai` (update as needed)
- `API_URL=https://modporter.ai/api/v1`
- `API_BASE_URL=https://modporter.ai`
- `FRONTEND_URL=https://modporter.ai`

### Services Configuration:
- **Frontend**: Nginx serving React build on port 80/443
- **Backend API**: FastAPI on port 8000 (internal)
- **AI Engine**: FastAPI on port 8001 (internal)
- **Health Check**: `/health` endpoint every 30s

### Resource Allocation:
- **Memory**: 2GB
- **CPU**: 2 shared cores
- **Storage**: 10GB persistent volume
- **Scaling**: 1-10 machines based on load

## 🚨 Pre-Deployment Testing

Before deploying to production, test locally:

```bash
# Build the Fly.io Docker image locally
docker build -f Dockerfile.fly -t modporter-ai:fly .

# Test the startup script
docker run --rm -p 80:80 -p 8000:8000 -p 8001:8001 \
  -e DATABASE_URL="sqlite:///app/data/test.db" \
  -e REDIS_URL="redis://localhost:6379" \
  modporter-ai:fly

# Test health endpoints
curl http://localhost/health
curl http://localhost:8000/api/v1/health
curl http://localhost:8001/api/v1/health
```

## 🔐 Security Considerations

1. **Secrets Management**: All sensitive data stored in Fly.io secrets
2. **HTTPS**: Force HTTPS enabled in configuration
3. **Security Headers**: CSP, HSTS, XSS protection in nginx config
4. **Rate Limiting**: API rate limiting configured in nginx
5. **Health Checks**: Automated health monitoring

## 📊 Monitoring

After deployment, monitor:
- Application logs: `flyctl logs`
- Metrics: `flyctl dashboard`
- Resource usage: `flyctl status`
- Health checks: Built-in to Fly.io platform

## 🔄 CI/CD Integration

To enable automatic deployments:
1. Add Fly.io API token to GitHub secrets
2. Add deploy step to `.github/workflows/` after tests pass
3. Configure automatic deployments on main branch

## 📝 Post-Deployment

1. **Custom Domain**: Point `modporter.ai` to Fly.io
2. **SSL Certificate**: Automatic with Fly.io for custom domains
3. **Monitoring**: Set up alerts for health check failures
4. **Backup Strategy**: Regular database backups
5. **Scale Configuration**: Adjust based on usage patterns

---

**Note**: This deployment uses a single-container approach for simplicity. For high-scale production, consider:
- Separate apps for frontend, backend, and AI engine
- Managed PostgreSQL and Redis services
- CDN for static assets
- Load balancing across multiple regions