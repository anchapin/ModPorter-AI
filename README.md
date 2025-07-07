# ModPorter AI

An AI-powered tool for converting Minecraft Java Edition mods to Bedrock Edition add-ons.

## 🎯 Vision
Empower Minecraft players and creators with a "one-click" AI-powered tool that intelligently converts Java Edition mods into functional Bedrock Edition add-ons using smart assumptions to bridge technical gaps.

## 🚀 Features
- **One-Click Conversion**: Upload Java mods and get Bedrock add-ons automatically
- **AI-Powered Analysis**: Multi-agent system using CrewAI for intelligent conversion
- **Smart Assumptions**: Handles incompatible features with logical workarounds
- **Detailed Reporting**: Transparent conversion reports showing all changes
- **Validation System**: AI-powered comparison between original and converted mods

## 🛠️ Tech Stack
- **Frontend**: React + TypeScript
- **Backend**: Python + FastAPI
- **AI Engine**: CrewAI + LangChain
- **Local Agent**: Node.js for Minecraft integration

## 📦 Quick Start

This project offers two main ways to get started:

### Prerequisites
- Docker and Docker Compose (for Option 1)
- Node.js 18+ (for Option 2)
- Python 3.9+ (for Option 2)

### Option 1: Production Deployment (Docker Hub)

This option uses pre-built Docker images from Docker Hub for a production-like environment. Ensure you have Docker and Docker Compose installed.

1.  **Create a `.env` file** in the root directory of the project by copying the `.env.example` file:
    ```bash
    cp .env.example .env
    ```
2.  **Edit the `.env` file** and provide the necessary API keys (e.g., `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`) and any other production-specific configurations. **Important:** Change default passwords like `POSTGRES_PASSWORD` for actual production use.
3.  **Pull and run the containers** using `docker-compose.prod.yml`:
    ```bash
    docker-compose -f docker-compose.prod.yml pull
    docker-compose -f docker-compose.prod.yml up -d
    ```
    This will download the latest images from Docker Hub (anchapin/modporter-ai-frontend, anchapin/modporter-ai-backend, anchapin/modporter-ai-ai-engine) and start the services.

    The services will be available at:
    - Frontend: [http://localhost:3000](http://localhost:3000)
    - Backend API: [http://localhost:8000/api/v1/](http://localhost:8000/api/v1/)
    - AI Engine API: [http://localhost:8001/api/v1/](http://localhost:8001/api/v1/) (if it has an API)

4.  **To stop the services**:
    ```bash
    docker-compose -f docker-compose.prod.yml down
    ```

#### Environment Variables for Production Containers

The Docker Hub containers can be configured using environment variables defined in your `.env` file and passed through the `docker-compose.prod.yml` file. Refer to the `environment` section of each service in `docker-compose.prod.yml` for available variables.

**Key variables to configure:**
- `OPENAI_API_KEY`: Your OpenAI API key (for AI Engine).
- `ANTHROPIC_API_KEY`: Your Anthropic API key (for AI Engine).
- `DATABASE_URL`: The connection string for the PostgreSQL database.
- `REDIS_URL`: The connection string for Redis.
- `LOG_LEVEL`: Set to `INFO` for production, or `DEBUG` for more detailed logs.
- `POSTGRES_PASSWORD`: Change the default PostgreSQL password.

Ensure that any secrets or sensitive information are managed securely and not hardcoded into the `docker-compose.prod.yml` file directly. Use the `.env` file for this purpose.

### Option 2: Local Development Setup
1. Clone the repository
2. Create and configure your `.env` file by copying `.env.example`:
   ```bash
   cp .env.example .env
   ```
   Update the `.env` file with your API keys and development settings.
3. Install dependencies: `npm run install-all`
4. Start development servers: `npm run dev` (This uses `docker-compose.dev.yml` for services like Postgres and Redis, and runs frontend, backend, and ai-engine locally)
5. Open http://localhost:3000

## Testing

### Run all tests
npm run test

### Backend tests
cd backend && pytest

### Frontend tests
cd frontend && npm test

## 📖 Documentation

- [Product Requirements Document](docs/PRD.md)
- [API Documentation](docs/API.md)
- [Contributing Guidelines](CONTRIBUTING.md)

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Legal Notice

Users are responsible for ensuring they have the right to convert mods. Respect original mod licenses and Minecraft's terms of service.