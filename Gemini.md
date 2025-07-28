# Project Overview

This project is a full-stack web application with a React frontend, a Python backend, and a machine learning component.

## Project Structure

The project is organized into the following directories:

-   `.github/`: Contains GitHub Actions workflows for CI/CD.
-   `ai-engine/`: Contains the Python-based AI processing logic.
-   `backend/`: Contains the Python FastAPI backend application.
-   `database/`: Contains database schema definitions and migration scripts.
-   `docs/`: Contains project documentation.
-   `frontend/`: Contains the React frontend application.
-   `tests/`: Contains integration and end-to-end tests.

## Getting Started

1.  **Prerequisites:**
    *   Docker
    *   Node.js (for frontend development)
    *   Python (for backend and AI development)

2.  **Installation:**
    *   Clone the repository: `git clone https://github.com/your-username/your-repo.git`
    *   Navigate to the project directory: `cd your-repo`
    *   Install frontend dependencies: `cd frontend && pnpm install`
    *   Install backend dependencies: `cd ../backend && pip install -r requirements.txt`

3.  **Running the Application:**
    *   Start the application with Docker Compose: `docker compose up --build`
    *   The frontend will be available at `http://localhost:5173`
    *   The backend will be available at `http://localhost:8000`

## Contribution Guidelines

To ensure code quality and consistency, please follow these guidelines when contributing to the project.

### Running Tests

Before submitting a pull request, please run the following tests to ensure that your changes do not break existing functionality.

*   **Frontend Tests:**
    ```bash
    cd frontend
    pnpm test
    ```

*   **Backend and AI Tests:**
    ```bash
    pytest
    ```

### Linting

Please ensure that your code adheres to the project's linting rules.

*   **Frontend Linting:**
    ```bash
    cd frontend
    pnpm lint
    ```

*   **Backend and AI Linting:**
    ```bash
    ruff check .
    ```

### Code Formatting

This project uses Prettier for code formatting. Please format your code before submitting a pull request.

```bash
pnpm format
```

This will format all files in the project according to the Prettier configuration.

### Coding Style Guide

*   **Variable Naming:**
    *   Use `snake_case` for all variable names in Python files.
    *   Use `camelCase` for all variable names in TypeScript/JavaScript files.
*   **Functions:**
    *   All new functions must include a JSDoc comment block explaining their purpose, parameters, and return value.
*   **React Components:**
    *   Use functional components with Hooks for all new React components.
