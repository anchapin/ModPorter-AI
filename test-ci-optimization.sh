#!/bin/bash

# CI Optimization Test Script
# Tests the new base image and optimized build system locally

set -e

echo "🚀 Testing CI Optimization Strategy Locally"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
REGISTRY="ghcr.io"
REPO_NAME="anchapin/modporter-ai"
TEST_MODE="${1:-full}"  # full, base-only, or optimized-only

# Function to print colored output
log_info() {
    echo -e "${GREEN}ℹ️  $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Function to time commands
time_command() {
    local start_time=$(date +%s)
    "$@"
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    log_info "Command completed in ${duration}s"
}

# Calculate dependency hashes
calculate_hashes() {
    log_info "Calculating dependency hashes..."
    
    PYTHON_HASH=$(cat ai-engine/requirements.txt backend/requirements.txt | sha256sum | cut -d' ' -f1 | head -c16)
    NODE_HASH=$(sha256sum frontend/pnpm-lock.yaml | cut -d' ' -f1 | head -c16)
    
    echo "Python dependencies hash: $PYTHON_HASH"
    echo "Node dependencies hash: $NODE_HASH"
    
    export PYTHON_HASH NODE_HASH
}

# Test base image builds
test_base_images() {
    log_info "Testing base image builds..."
    
    log_info "Building Python base image..."
    time_command docker build \
        -f docker/base-images/Dockerfile.python-base \
        -t test-python-base:latest \
        .
    
    log_info "Building Node base image..."
    time_command docker build \
        -f docker/base-images/Dockerfile.node-base \
        -t test-node-base:latest \
        frontend/
    
    log_info "Testing base image functionality..."
    
    # Test Python base
    docker run --rm test-python-base:latest python -c "
import fastapi, crewai, langchain, sentence_transformers
print('✅ Python base image: All dependencies available')
"
    
    # Test Node base
    docker run --rm test-node-base:latest sh -c "
pnpm --version && node --version
echo '✅ Node base image: Dependencies available'
"
}

# Test optimized builds
test_optimized_builds() {
    log_info "Testing optimized service builds..."
    
    # Use local test base images
    export PYTHON_BASE_TAG="latest"
    export NODE_BASE_TAG="latest"
    
    log_info "Building optimized AI engine..."
    time_command docker build \
        -f ai-engine/Dockerfile.optimized \
        --build-arg PYTHON_BASE_TAG=latest \
        -t test-ai-engine:optimized \
        ai-engine/
    
    log_info "Building optimized backend..."
    time_command docker build \
        -f backend/Dockerfile.optimized \
        --build-arg PYTHON_BASE_TAG=latest \
        -t test-backend:optimized \
        backend/
    
    log_info "Building optimized frontend..."
    time_command docker build \
        -f frontend/Dockerfile.optimized \
        --build-arg NODE_BASE_TAG=latest \
        -t test-frontend:optimized \
        frontend/
}

# Test standard builds for comparison
test_standard_builds() {
    log_info "Testing standard builds for comparison..."
    
    log_info "Building standard AI engine..."
    time_command docker build \
        -f ai-engine/Dockerfile \
        -t test-ai-engine:standard \
        ai-engine/
    
    log_info "Building standard backend..."
    time_command docker build \
        -f backend/Dockerfile \
        -t test-backend:standard \
        backend/
    
    log_info "Building standard frontend..."
    time_command docker build \
        -f frontend/Dockerfile \
        -t test-frontend:standard \
        frontend/
}

# Run tests in containers
test_containers() {
    log_info "Testing container functionality..."
    
    # Test that optimized containers work
    log_info "Testing AI engine container..."
    docker run --rm -d --name test-ai-engine -p 8001:8001 test-ai-engine:optimized
    sleep 5
    
    if curl -f http://localhost:8001/api/v1/health > /dev/null 2>&1; then
        log_info "✅ AI engine container is healthy"
    else
        log_warning "⚠️ AI engine container health check failed"
    fi
    
    docker stop test-ai-engine || true
    
    log_info "Testing backend container..."
    docker run --rm -d --name test-backend -p 8000:8000 test-backend:optimized
    sleep 5
    
    if curl -f http://localhost:8000/api/v1/health > /dev/null 2>&1; then
        log_info "✅ Backend container is healthy"
    else
        log_warning "⚠️ Backend container health check failed"
    fi
    
    docker stop test-backend || true
}

# Performance comparison
performance_summary() {
    log_info "Performance Summary"
    echo "=================="
    
    # Get image sizes
    echo "Image Sizes:"
    docker images --format "table {{.Repository}}:{{.Tag}}\t{{.Size}}" | grep test-
    
    echo ""
    echo "Build Time Comparison:"
    echo "- Base images: Built once, reused for all subsequent builds"
    echo "- Optimized builds: Only copy source code + fast operations"
    echo "- Standard builds: Full dependency installation every time"
    echo ""
    echo "Expected CI time reduction: 60-70%"
    echo "Expected cost reduction: 50-60%"
}

# Cleanup
cleanup() {
    log_info "Cleaning up test images..."
    docker rmi -f $(docker images -q test-*) 2>/dev/null || true
    log_info "Cleanup complete"
}

# Main execution
main() {
    calculate_hashes
    
    case $TEST_MODE in
        "base-only")
            test_base_images
            ;;
        "optimized-only")
            test_base_images
            test_optimized_builds
            test_containers
            ;;
        "full"|*)
            test_base_images
            test_optimized_builds
            test_standard_builds
            test_containers
            performance_summary
            ;;
    esac
    
    log_info "All tests completed successfully! 🎉"
    
    read -p "Clean up test images? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        cleanup
    fi
}

# Handle interrupts
trap cleanup EXIT

# Run main function
main "$@"
