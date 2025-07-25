# ModPorter AI

An AI-powered tool for converting Minecraft Java Edition mods to Bedrock Edition add-ons.

[![codecov](https://codecov.io/gh/anchapin/ModPorter-AI/branch/main/graph/badge.svg)](https://codecov.io/gh/anchapin/ModPorter-AI)

## 🎯 Vision
Empower Minecraft players and creators with a "one-click" AI-powered tool that intelligently converts Java Edition mods into functional Bedrock Edition add-ons using smart assumptions to bridge technical gaps.

## 🚀 Features

### MVP Focus: Simple Block Conversion
The current development priority is the Minimum Viable Product (MVP), which focuses on the core functionality of converting a simple Java block mod into a functional Bedrock add-on.

-   **Java Block to Bedrock JSON**: Convert a `.jar` file containing a single block into a `.mcaddon` package.
-   **Texture Preservation**: Ensure the block's appearance is correctly transferred.
-   **Basic Functionality**: The converted block can be placed and destroyed in-game.

### Future (Post-MVP) Features
-   **Complex Conversions**: Support for items, entities, and complex logic.
-   **AI-Powered Analysis**: A multi-agent system for advanced conversion strategies.
-   **Detailed Reporting**: Transparent reports detailing the conversion process.
-   **Validation System**: AI-powered comparison between the original and converted mods.

## 🛠️ Tech Stack
- **Frontend**: React + TypeScript + Vite (served by Nginx in production)
- **Backend**: Python + FastAPI + SQLAlchemy + AsyncPG
- **AI Engine**: CrewAI + LangChain + FastAPI
- **RAG System**: Vector database (pgvector) + Embedding generation + Knowledge retrieval
- **Database**: PostgreSQL 15 with async support
- **Cache**: Redis 7 for sessions and caching
- **Infrastructure**: Docker + Docker Compose
- **Local Agent**: Node.js for Minecraft integration

## 📦 Quick Start

This project offers multiple deployment options:

### Prerequisites
- **Docker & Docker Compose** (recommended - handles all dependencies)
- OR for local development:
  - Node.js 18+
  - Python 3.9+
  - PostgreSQL 15+
  - Redis 7+

### Option 1: Production Deployment (Docker Hub)

This option uses pre-built Docker images from Docker Hub for a production-like environment.

```bash
# Clone the repository
git clone https://github.com/anchapin/ModPorter-AI.git
cd ModPorter-AI

# Copy environment variables
cp .env.example .env
# Edit .env and add your API keys (OPENAI_API_KEY, ANTHROPIC_API_KEY)

# Start all services using Docker Hub images
docker compose -f docker compose.prod.yml up -d

# Check service status
docker compose ps
```

**Service URLs:**
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8080 (or `/api/` when using frontend proxy)
- **PostgreSQL**: localhost:5433
- **Redis**: localhost:6379

**Note**: The frontend uses Nginx to proxy API requests to the backend, so you can access the API through either `http://localhost:3000/api/` or directly at `http://localhost:8080/api/`.

### Option 2: Local Development Setup (Docker)

#### Production Environment
```bash
# Clone the repository
git clone https://github.com/anchapin/ModPorter-AI.git
cd ModPorter-AI

# Copy environment variables
cp .env.example .env
# Edit .env and add your API keys (OPENAI_API_KEY, ANTHROPIC_API_KEY)

# Start all services
docker compose up -d

# Check service status
docker compose ps
```

#### Development Environment
```bash
# Use development configuration with hot reload
docker compose -f docker compose.dev.yml up -d
```

#### Service URLs
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8080
- **AI Engine**: http://localhost:8001
- **PostgreSQL**: localhost:5433
- **Redis**: localhost:6379

#### Docker Management
```bash
# View logs
docker compose logs [service-name]

# Restart a service
docker compose restart [service-name]

# Stop all services
docker compose down

# Rebuild and restart
docker compose up -d --build

# View real-time logs
docker compose logs -f
```

### Option 3: Manual Local Setup (Advanced)

If you prefer to run services locally without Docker:

1. Clone the repository
2. Install dependencies: `pnpm run install-all`
3. Start development servers: `pnpm run dev`
4. Open http://localhost:3000

## 🐳 Docker Architecture

### Services Overview
ModPorter AI uses a microservices architecture with the following containers:

| Service | Technology | Port | Purpose |
|---------|------------|------|---------|
| **Frontend** | React + Nginx | 3000 | User interface |
| **Backend** | FastAPI + Python | 8080 | Main API server |
| **AI Engine** | FastAPI + CrewAI | 8001 | AI conversion engine |
| **PostgreSQL** | PostgreSQL 15 | 5433 | Primary database |
| **Redis** | Redis 7 | 6379 | Caching & sessions |

### Environment Variables
Required environment variables (add to `.env`):
```bash
# AI API Keys (required)
OPENAI_API_KEY=your-openai-api-key
ANTHROPIC_API_KEY=your-anthropic-api-key

# Database Configuration
# For local development (auto-configured for Docker):
DATABASE_URL=postgresql+asyncpg://postgres:password@postgres:5432/modporter
POSTGRES_DB=modporter
POSTGRES_USER=postgres
POSTGRES_PASSWORD=password

# For Supabase (production):
DATABASE_URL=postgresql://supabase_user:supabase_password@db.your_project_id.supabase.co:5432/postgres

# Redis (auto-configured for Docker)
REDIS_URL=redis://redis:6379

# Application
LOG_LEVEL=INFO
DEBUG=false
VITE_API_URL=http://localhost:8080/api/v1
```

**Note**: Frontend environment variables (`VITE_API_URL`, `VITE_API_BASE_URL`) are set as build arguments in Docker Compose and are embedded into the built JavaScript bundle at build time.

### Health Checks
All services include health checks for monitoring:
```bash
# Check frontend health
curl http://localhost:3000/health

# Check backend health
curl http://localhost:8080/api/v1/health

# Check AI engine health
curl http://localhost:8001/api/v1/health

# Check all service status
docker compose ps
```

### Troubleshooting

#### Common Issues
1. **Port conflicts**: If ports 3000, 8080, 8001, 5433, or 6379 are in use, modify `docker compose.yml`
2. **Missing API keys**: Ensure `.env` file contains valid `OPENAI_API_KEY` and `ANTHROPIC_API_KEY`
3. **Database connection**: Check PostgreSQL container logs if backend fails to start
4. **WebSocket connection errors**: Ensure frontend environment variables are correctly set during Docker build
5. **CSP font errors**: Updated nginx configuration allows embedded fonts via `font-src 'self' data:`

#### Debugging Commands
```bash
# View service logs
docker compose logs backend
docker compose logs ai-engine
docker compose logs frontend

# Access container shell
docker compose exec backend bash
docker compose exec ai-engine bash

# Reset everything
docker compose down -v
docker compose up -d --build
```

## Testing

### Prerequisites for Testing
- Docker and Docker Compose (for test database)

### Setup Test Database
```bash
# Start the test PostgreSQL database
./scripts/test-db.sh start

# Or manually with docker-compose
docker-compose -f docker-compose.test.yml up -d test-postgres
```

### Run Tests
```bash
# Run all tests
pnpm run test

# Backend tests
cd backend && pytest

# Frontend tests
cd frontend && pnpm test

# AI Engine and RAG tests
cd ai-engine && pytest
```

### Test Database Management
```bash
# Start test database
./scripts/test-db.sh start

# Stop test database
./scripts/test-db.sh stop

# Reset test database (clears all data)
./scripts/test-db.sh reset

# View database logs
./scripts/test-db.sh logs
```

### MVP Conversion Test
To run the end-to-end MVP test case, which validates the complete pipeline from a Java block to Bedrock files, use the following command:

```bash
pytest tests/test_mvp_conversion.py
```

### Docker Tests
```bash
# Run tests in Docker containers
docker compose exec backend pytest
docker compose exec frontend pnpm test
docker compose exec ai-engine pytest

# Run tests with coverage
docker compose exec backend pytest --cov=src
docker compose exec ai-engine pytest --cov=src
```

## 🔧 Development Workflows

### Docker Development Best Practices

#### Hot Reload Development
Use the development Docker Compose configuration for active development:
```bash
# Start with hot reload enabled
docker compose -f docker compose.dev.yml up -d

# This enables:
# - Frontend: Vite dev server with hot reload
# - Backend: uvicorn with auto-reload
# - AI Engine: uvicorn with auto-reload and debug mode
```

#### Making Changes
```bash
# After code changes, rebuild specific service
docker compose build backend
docker compose up -d backend

# Or rebuild all services
docker compose up -d --build
```

#### Database Management
```bash
# Access PostgreSQL directly
docker compose exec postgres psql -U postgres -d modporter

# Run database migrations
docker compose exec backend alembic upgrade head

# Reset database (⚠️ destroys data)
docker compose down -v
docker compose up -d
```

#### Performance Monitoring
```bash
# Monitor resource usage
docker stats

# View container resource limits
docker compose config

# Check service dependencies
docker compose ps --services
```

## 📖 Documentation

- [Product Requirements Document](docs/PRD.md)
- [API Documentation](docs/API.md)
- [Contributing Guidelines](CONTRIBUTING.md)

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/anchapin/ModPorter-AI/issues)
- **Discussions**: [GitHub Discussions](https://github.com/anchapin/ModPorter-AI/discussions)
- **Documentation**: [Project Wiki](https://github.com/anchapin/ModPorter-AI/wiki)

## 🏆 Acknowledgments

- **CrewAI**: For the multi-agent AI framework
- **FastAPI**: For the high-performance API framework
- **React**: For the frontend framework
- **Docker**: For containerization
- **Minecraft Community**: For inspiration and support

---

Made with ❤️ by the ModPorter AI team

