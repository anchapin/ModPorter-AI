# Project Overview

This project, "ModPorter-AI", is a multi-component application designed for AI-driven tasks, likely related to code conversion or analysis, given the "ai-engine" and "backend" components. It includes a React-based frontend, a Python backend, and a separate Python AI engine, all containerized with Docker.

## Key Technologies

*   **Frontend:** React, TypeScript, Vite, pnpm, ESLint, Prettier, Storybook.
*   **Backend:** Python, FastAPI, SQLAlchemy, Alembic.
*   **AI Engine:** Python (likely with various AI/ML libraries).
*   **Database:** SQL (e.g., PostgreSQL).
*   **Containerization:** Docker, Docker Compose.
*   **Testing:** Pytest.
*   **Linting/Formatting:** Ruff (Python), ESLint, Prettier (Frontend).
*   **CI/CD:** GitHub Actions.

## Project Structure

*   `.github/workflows/`: GitHub Actions for CI/CD.
*   `ai-engine/`: Contains the Python-based AI processing logic.
*   `backend/`: Houses the Python FastAPI application, database interactions, and business logic.
*   `frontend/`: The React/TypeScript web application.
*   `database/`: SQL schema definitions.
*   `docs/`: Project documentation.
*   `tests/`: Integration and unit tests for various components.
*   `docker-compose*.yml`: Docker Compose configurations for development and production environments.

## How to Interact with the Project

### General Commands

*   **List files:** `ls -F` or `find . -maxdepth 2`
*   **Read file content:** `cat <file_path>` or `read_file <file_path>`
*   **Search file content:** `grep -r "pattern" .` or `search_file_content "pattern"`

### Docker Compose

The project uses Docker Compose for managing its services. You can use the following commands:

*   **Build and start services (development):** `docker-compose -f docker-compose.dev.yml up --build`
*   **Build and start services (production):** `docker-compose -f docker-compose.prod.yml up --build`
*   **Stop services:** `docker-compose down`
*   **View logs:** `docker-compose logs -f <service_name>`

### Testing

*   **Run all Python tests:** `pytest` (from the project root or within `ai-engine/` or `backend/`)
*   **Run specific Python tests:** `pytest <path_to_test_file>`
*   **Run frontend tests:** Refer to `frontend/package.json` for specific test commands (e.g., `pnpm test`).

### Linting/Formatting

*   **Python (Ruff):** `ruff check .` (from project root or component directories)
*   **Frontend (ESLint/Prettier):** Refer to `frontend/package.json` for specific commands (e.g., `pnpm lint`, `pnpm format`).

### Building

*   **Frontend:** `pnpm install` then `pnpm build` in `frontend/` directory.
*   **Docker Images:** `docker-compose build` or `docker build` within specific component directories (`ai-engine/`, `backend/`, `frontend/`).

## Important Notes

*   Always refer to the specific `Dockerfile` and `requirements.txt`/`package.json` files within each component directory for precise dependency and build information.
*   Database migrations are handled via Alembic in the `backend/`.
*   The `.env.example` files provide templates for environment variables.