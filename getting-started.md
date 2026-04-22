# Getting Started with Portkit

Welcome to Portkit - the first AI-powered tool that converts Minecraft Java Edition mods to Bedrock Edition add-ons.

## What is Portkit?

Portkit automates 60-80% of the work required to convert Java mods to Bedrock add-ons, saving you months of manual rewriting. Our multi-agent AI system:

- Analyzes Java code structure and dependencies
- Translates Java logic to JavaScript (Bedrock Script API)
- Converts textures, models, and sounds
- Validates the conversion for errors
- Packages everything into a ready-to-use .mcaddon file

## Prerequisites

### For Local Development

Before setting up locally, ensure you have:

- **Docker & Docker Compose** (recommended) - handles all dependencies automatically
- **OR** for manual setup:
  - Node.js 22.12+ LTS (for frontend with Vite 7.2.2+)
  - Python 3.9+ (for backend)
  - PostgreSQL 15+ (database)
  - Redis 7+ (caching)

### For Using the Web App

- **A Java mod file** (.jar or .zip) that you want to convert
- **Basic understanding** of Minecraft modding (helpful but not required)
- **A Bedrock testing environment** (Minecraft Bedrock Edition on any platform)

## Installation

### Option 1: Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/anchapin/portkit.git
cd portkit

# Copy environment variables
cp .env.example .env
```

Edit `.env` and add your API keys:

```bash
# AI API Keys (required)
OPENAI_API_KEY=your-openai-api-key
ANTHROPIC_API_KEY=your-anthropic-api-key
```

### Option 2: Manual Local Setup

```bash
# Install all dependencies
pnpm run install-all
```

## Quick Start

### Running Locally with Docker

```bash
# Start all services
docker compose up -d

# Check service status
docker compose ps
```

**Service URLs:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8080
- AI Engine: http://localhost:8001
- PostgreSQL: localhost:5433
- Redis: localhost:6379

### First Conversion

1. **Open the web interface**: Go to http://localhost:3000
2. **Upload your mod**: Click "Upload Mod" and select a .jar or .zip file
3. **Review analysis**: See detected components and complexity level
4. **Start conversion**: Click "Start Conversion" and wait for completion
5. **Download**: Get your .mcaddon file and install in Bedrock Edition

### Using the API

```bash
# Register a new user
curl -X POST http://localhost:8080/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "SecurePass123!"}'

# Login
curl -X POST http://localhost:8080/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "SecurePass123!"}'

# Upload a mod file
curl -X POST http://localhost:8080/api/v1/upload \
  -F "file=@my-mod.jar"

# Check job status
curl http://localhost:8080/api/v1/jobs/{job_id}
```

## Configuration

### Environment Variables

Key environment variables for `.env`:

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENAI_API_KEY` | OpenAI API key for AI processing | Yes |
| `ANTHROPIC_API_KEY` | Anthropic API key for AI processing | Yes |
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `REDIS_URL` | Redis connection string | Yes |
| `LOG_LEVEL` | Logging level (DEBUG, INFO, WARNING, ERROR) | No |
| `DEBUG` | Enable debug mode (true/false) | No |

### Docker Compose Options

```bash
# Production deployment (uses pre-built images)
docker compose -f docker-compose.prod.yml up -d

# Development with hot reload
docker compose -f docker-compose.dev.yml up -d
```

### Health Checks

Verify all services are running:

```bash
# Check frontend
curl http://localhost:3000/health

# Check backend
curl http://localhost:8080/health

# Check AI engine
curl http://localhost:8001/api/v1/health

# Check all services
docker compose ps
```

## Troubleshooting

### Service Won't Start

**Problem**: Docker containers fail to start

**Solutions**:
- Check if ports are already in use: `docker compose ps`
- Verify .env file has required API keys
- Check logs: `docker compose logs [service-name]`

### Conversion Failed

**Problem**: Conversion stopped with an error

**Solutions**:
- Check the error message in the conversion report
- Make sure your mod file is not corrupted
- Verify the mod uses standard Minecraft Forge/Fabric APIs
- Try again - some errors are transient

### Missing Features

**Problem**: Some features didn't convert

**Solutions**:
- Check the "Component Inventory" section of the report
- Look for "Manual Steps Required" notes
- Some Java features don't have Bedrock equivalents

### Add-on Won't Install

**Problem**: .mcaddon file won't install

**Solutions**:
- Make sure you're using Bedrock Edition (not Java)
- Check file size (max 100MB for Marketplace)
- Verify file extension is .mcaddon (not .zip)

## Next Steps

- Read the [API Reference](api-reference.md) for programmatic access
- Check the [Conversion Guide](conversion-guide.md) for advanced options
- Read the [Step-by-Step Tutorial](tutorial.md) for detailed walkthrough
- Check the [FAQ](faq.md) for common questions

## Getting Help

- **Documentation**: [docs.portkit.cloud](https://docs.portkit.cloud)
- **Discord**: [discord.gg/modporter](https://discord.gg/modporter)
- **Email**: support@portkit.cloud
- **GitHub Issues**: [github.com/anchapin/portkit/issues](https://github.com/anchapin/portkit/issues)

Happy converting!
