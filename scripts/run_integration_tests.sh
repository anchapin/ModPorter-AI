#!/bin/bash
# Convenience script to run integration tests with real services
# Usage: ./scripts/run_integration_tests.sh [pytest args...]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is required for real-service integration tests"
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "Error: docker-compose is required for real-service integration tests"
    exit 1
fi

# Start test services
echo "Starting test services..."
if command -v docker-compose &> /dev/null; then
    docker-compose -f docker-compose.test.yml up -d
else
    docker compose -f docker-compose.test.yml up -d
fi

# Wait for services to be healthy
echo "Waiting for services to be healthy..."
sleep 5

# Function to cleanup on exit
cleanup() {
    echo "Cleaning up..."
    if command -v docker-compose &> /dev/null; then
        docker-compose -f docker-compose.test.yml down
    else
        docker compose -f docker-compose.test.yml down
    fi
}
trap cleanup EXIT

# Run the tests
echo "Running integration tests with USE_REAL_SERVICES=1..."
export USE_REAL_SERVICES=1
export TEST_DATABASE_URL="postgresql://postgres:password@localhost:5433/modporter_test"
export TEST_REDIS_URL="redis://localhost:6379/0"
export TEST_AI_ENGINE_URL="http://localhost:8080"

cd backend
python3 -m pytest "$@" src/tests/integration/test_real_*.py -v --tb=short

echo ""
echo "Integration tests completed successfully!"
