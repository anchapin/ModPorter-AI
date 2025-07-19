#!/bin/bash

echo "🔧 Fixing Docker networking issues for ModPorter AI"
echo "================================================="

# Check if we're using the dev compose file
if [ -f "docker-compose.dev.yml" ]; then
    echo "✅ Found docker-compose.dev.yml"
    COMPOSE_FILE="docker-compose.dev.yml"
else
    echo "❌ docker-compose.dev.yml not found"
    exit 1
fi

# Stop containers if running
echo "🛑 Stopping existing containers..."
docker-compose -f $COMPOSE_FILE down

# Pull the latest Ollama image
echo "📥 Pulling latest Ollama image..."
docker pull ollama/ollama

# Check if llama3.2 model exists in Ollama
echo "🔍 Checking Ollama model availability..."
if docker volume inspect modporter-ai_ollama-data >/dev/null 2>&1; then
    echo "✅ Ollama data volume exists"
else
    echo "📦 Creating Ollama data volume..."
    docker volume create modporter-ai_ollama-data
fi

# Start services in correct order
echo "🚀 Starting services..."
docker-compose -f $COMPOSE_FILE up -d postgres redis

# Wait for postgres and redis to be ready
echo "⏳ Waiting for postgres and redis to be ready..."
sleep 10

# Start Ollama service
echo "🤖 Starting Ollama service..."
docker-compose -f $COMPOSE_FILE up -d ollama

# Wait for Ollama to be ready with proper health check
echo "⏳ Waiting for Ollama to be ready..."
echo "Checking Ollama health..."
for i in {1..12}; do
    if docker-compose -f $COMPOSE_FILE exec ollama curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
        echo "✅ Ollama is ready after $((i*5)) seconds"
        break
    fi
    echo "🔄 Ollama not ready yet, waiting 5 more seconds... (attempt $i/12)"
    sleep 5
done

# Pull the llama3.2 model in Ollama
echo "📥 Pulling llama3.2 model in Ollama..."
docker-compose -f $COMPOSE_FILE exec ollama ollama pull llama3.2

# Test Ollama connection and model availability
echo "🧪 Testing Ollama connection and model availability..."
docker-compose -f $COMPOSE_FILE exec ollama ollama list

# Additional test: verify external API connectivity
echo "🔗 Testing API connectivity from outside the container..."
if docker-compose -f $COMPOSE_FILE exec ollama curl -s http://localhost:11434/api/tags | grep -q "llama3.2"; then
    echo "✅ Ollama API is accessible and llama3.2 model is available"
else
    echo "❌ Ollama API test failed"
fi

# Start the AI engine and backend
echo "🚀 Starting AI engine and backend..."
docker-compose -f $COMPOSE_FILE up -d ai-engine backend

# Wait for services to be ready with proper health checks
echo "⏳ Waiting for services to be ready..."
echo "Checking AI engine health..."
for i in {1..18}; do
    if docker-compose -f $COMPOSE_FILE exec ai-engine curl -s http://localhost:8001/api/v1/health >/dev/null 2>&1; then
        echo "✅ AI engine is ready after $((i*10)) seconds"
        break
    fi
    echo "🔄 AI engine not ready yet, waiting 10 more seconds... (attempt $i/18)"
    sleep 10
done

echo "Checking backend health..."
for i in {1..6}; do
    if docker-compose -f $COMPOSE_FILE exec backend curl -s http://localhost:8000/api/v1/health >/dev/null 2>&1; then
        echo "✅ Backend is ready after $((i*5)) seconds"
        break
    fi
    echo "🔄 Backend not ready yet, waiting 5 more seconds... (attempt $i/6)"
    sleep 5
done

# Start frontend
echo "🌐 Starting frontend..."
docker-compose -f $COMPOSE_FILE up -d frontend

# Show status
echo "📊 Service status:"
docker-compose -f $COMPOSE_FILE ps

echo ""
echo "🎉 Setup complete!"
echo "💻 Frontend: http://localhost:3002"
echo "🔧 Backend API: http://localhost:8080"
echo "🤖 AI Engine: http://localhost:8001"
echo "📚 Ollama: http://localhost:11434"
echo ""
echo "🔍 To check logs:"
echo "docker-compose -f $COMPOSE_FILE logs ai-engine"
echo "docker-compose -f $COMPOSE_FILE logs ollama"
echo ""
echo "✅ Status check:"
echo "curl -s http://localhost:8001/api/v1/health | python3 -m json.tool"
echo "curl -s http://localhost:8080/api/v1/health | python3 -m json.tool"