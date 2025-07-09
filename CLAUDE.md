# CLAUDE.md

-This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

-## Development Commands

-### Core Development Workflow
-```bash
-# Install all dependencies across all services
-npm run install-all

-# Start all services in development mode
-npm run dev

-# Start individual services
-npm run dev:frontend    # React dev server (port 3000)
-npm run dev:backend     # FastAPI with uvicorn (port 8000)
-npm run dev:ai-engine   # AI engine service (port 8001)
-```

-### Testing
-```bash
-# Run all tests
-npm run test

-# Service-specific testing
-npm run test:frontend   # Vitest + React Testing Library
-npm run test:backend    # pytest with async support
-cd backend && pytest tests/test_main.py  # Single test file
-cd frontend && npm test -- ConversionUpload.test.tsx  # Single component test
-```

-### Code Quality & Build
-```bash
-# Linting and formatting
-npm run lint           # ESLint + Ruff across all services
-npm run format         # Prettier + Black formatting

-# Build for production
-npm run build          # Frontend production build
-```

-### Development Tools
-```bash
-# Component development
-cd frontend && npm run storybook

-# Docker deployment
-docker-compose up -d              # Full stack
-docker-compose -f docker-compose.dev.yml up  # Development mode
-```

-## Architecture Overview

-### Multi-Agent AI System
-ModPorter AI uses a **CrewAI-based multi-agent architecture** for intelligent mod conversion:

-- **Java Analyzer Agent**: Parses .jar files, identifies assets, code logic, and dependencies
-- **Bedrock Architect Agent**: Maps Java features to Bedrock equivalents using "Smart Assumptions"
-- **Logic Translator Agent**: Converts Java OOP code to Bedrock's event-driven JavaScript
-- **Asset Converter Agent**: Transforms textures, models, and sounds to Bedrock formats
-- **Packaging Agent**: Assembles final .mcaddon files with proper manifests
-- **QA Validator Agent**: Validates output and generates conversion reports

-### Smart Assumptions Engine
-The core innovation is the Smart Assumptions system that handles incompatible features:

-- **Custom Dimensions** → Large structures within existing dimensions
-- **Complex Machinery** → Simplified blocks with preserved aesthetics
-- **Custom GUI/HUD** → Book or sign-based interfaces
-- **Client-Side Rendering** → Explicitly excluded with user notification
-- **Mod Dependencies** → Bundled (simple) or flagged for failure (complex)

-### Service Architecture
-```
-Frontend (React/TypeScript) ↔ Backend (FastAPI) ↔ AI Engine (CrewAI)
-                                    ↓
-                            Database (PostgreSQL)
-                                    ↓
-                              Cache (Redis)
-```

-### Key File Locations
-- **Agent Definitions**: `ai-engine/src/crew/conversion_crew.py`
-- **Smart Assumptions Logic**: `ai-engine/src/models/smart_assumptions.py`
-- **API Endpoints**: `backend/src/main.py`
-- **React Components**: `frontend/src/components/`
-- **Mermaid Diagrams**: `frontend/src/components/MermaidDiagram/`
-- **Documentation**: `docs/` (DIAGRAMS.md, API.md, ARCHITECTURE.md)

-## Technology Stack Specifics

-### Frontend (Vite + React)
-- **Build System**: Vite 5.0+ for fast HMR and builds
-- **Routing**: React Router for multi-page navigation
-- **File Uploads**: react-dropzone for drag-and-drop mod ingestion
-- **API Communication**: Axios with TypeScript interfaces
-- **Visual Documentation**: Mermaid.js for interactive architectural diagrams
-- **Testing**: Vitest (not Jest) - use `vi.mock()` instead of `jest.mock()`

-### Backend (FastAPI)
-- **Async Framework**: FastAPI with uvicorn ASGI server
-- **File Processing**: python-multipart for mod file uploads
-- **Type Safety**: Pydantic models for request/response validation
-- **Testing**: pytest with async support and httpx for API testing

-### AI Engine (CrewAI + LangChain)
-- **Multi-Agent Framework**: CrewAI for orchestrating specialized agents
-- **Java Processing**: javalang library for parsing Java mod source code
-- **Asset Processing**: Pillow (PIL) for textures, pydub for audio conversion
-- **Queue Management**: Celery with Redis for background processing

-## Development Patterns

-### Component Structure
-React components follow a consistent pattern:
-```
-components/
-├── ComponentName/
-│   ├── ComponentName.tsx      # Main component
-│   ├── ComponentName.stories.tsx  # Storybook stories
-│   ├── ComponentName.test.tsx     # Vitest tests
-│   └── ComponentName.css          # Component styles
-```

-### API Integration
-- All API calls use TypeScript interfaces defined in `frontend/src/types/api.ts`
-- Backend endpoints follow RESTful conventions with OpenAPI documentation
-- File uploads use multipart form data with progress tracking

-### Agent Task Flow
-CrewAI agents work sequentially with shared context:
-1. **Analysis** → Feature identification and dependency mapping
-2. **Planning** → Smart assumption selection and conversion strategy
-3. **Translation** → Code and asset conversion
-4. **Packaging** → .mcaddon assembly with validation
-5. **Reporting** → Detailed conversion results and user guidance

-## Testing Strategy

-### Frontend Testing
-- **Unit Tests**: Component logic with React Testing Library
-- **Integration Tests**: API communication and file upload flows
-- **Visual Testing**: Storybook for component documentation and manual testing

-### Backend Testing
-- **API Tests**: FastAPI endpoints with pytest and httpx
-- **AI Agent Tests**: Mock LLM responses for agent behavior validation
-- **File Processing Tests**: Mod parsing and conversion logic verification

-## Key Configuration Files

-### Environment Management
-- Root `.env.example`: Database, Redis, and API key configuration
-- Service-specific environment files in each subdirectory
-- Docker environment variables for containerized deployment

-### Build Configuration
-- `frontend/vite.config.ts`: Vite build settings with TypeScript support
-- `backend/requirements.txt`: Python dependencies with version pinning
-- `ai-engine/requirements.txt`: AI/ML dependencies including CrewAI and LangChain

-## Documentation Integration

-The project includes comprehensive visual documentation:
-- **Interactive Diagrams**: Mermaid.js components for system architecture
-- **GitHub Actions**: Automated documentation generation workflow
-- **Storybook**: Component documentation with usage examples
-- **API Documentation**: OpenAPI/Swagger integration with FastAPI

-## Smart Assumptions Implementation

-When working with the Smart Assumptions system:
-- Logic is centralized in `ai-engine/src/models/smart_assumptions.py`
-- Each assumption type has dedicated handling methods
-- User notifications about applied assumptions are generated automatically
-- The system prioritizes user transparency over perfect conversion

-## Vision: AI-Powered Mod Conversion

-The project implements a "conditionally feasible" approach to Java→Bedrock conversion, focusing on delivering the "best possible approximation" rather than perfect 1:1 conversion. The multi-agent AI system intelligently handles the fundamental platform differences through smart assumptions while maintaining full transparency with users about any compromises made during conversion.
