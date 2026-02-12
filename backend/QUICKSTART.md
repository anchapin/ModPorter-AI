# Quick Start Guide: WebSocket & Conversion API

This guide helps you quickly test the new WebSocket and Conversion API implementation.

## Prerequisites

- Python 3.9+
- Docker and Docker Compose (recommended)
- OR local PostgreSQL and Redis

## 1. Start the Backend

### Using Docker (Recommended)

```bash
cd /home/alexc/Projects/ModPorter-AI

# Start with hot reload
docker compose -f docker compose.dev.yml up -d backend

# View logs
docker compose logs -f backend

# Backend will be available at: http://localhost:8080
```

### Using Local Environment

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your DATABASE_URL and REDIS_URL

# Start the server
python src/main.py
```

## 2. Verify the Server is Running

```bash
# Health check
curl http://localhost:8080/api/v1/health

# Expected response:
# {
#   "status": "healthy",
#   "version": "1.0.0",
#   "timestamp": "2025-02-12T10:30:00.123456"
# }
```

## 3. Test REST API Endpoints

### Create a Conversion

```bash
# Prepare a test JAR file (or use an existing mod)
# For testing, we can create a simple file
echo "fake jar content" > test_mod.jar

# Create conversion
curl -X POST http://localhost:8080/api/v1/conversions \
  -F "file=@test_mod.jar" \
  -F 'options={"assumptions":"conservative","target_version":"1.20.0"}'

# Save the conversion_id from the response, e.g.:
# {"conversion_id":"550e8400-e29b-41d4-a716-446655440000",...}

CONVERSION_ID="550e8400-e29b-41d4-a716-446655440000"
```

### Get Conversion Status

```bash
curl http://localhost:8080/api/v1/conversions/$CONVERSION_ID

# Example response:
# {
#   "conversion_id": "550e8400-e29b-41d4-a716-446655440000",
#   "status": "processing",
#   "progress": 45,
#   "message": "JavaAnalyzerAgent is analyzing mod structure...",
#   "created_at": "2025-02-12T10:30:00Z",
#   "updated_at": "2025-02-12T10:35:00Z",
#   "result_url": null,
#   "error": null,
#   "original_filename": "test_mod.jar"
# }
```

### List All Conversions

```bash
curl "http://localhost:8080/api/v1/conversions?page=1&page_size=10"

# Example response:
# {
#   "conversions": [...],
#   "total": 42,
#   "page": 1,
#   "page_size": 10
# }
```

### Download Result (When Complete)

```bash
# After conversion completes (status: "completed")
curl http://localhost:8080/api/v1/conversions/$CONVERSION_ID/download \
  --output converted.mcaddon
```

### Delete Conversion

```bash
curl -X DELETE http://localhost:8080/api/v1/conversions/$CONVERSION_ID

# Response: 204 No Content
```

## 4. Test WebSocket Connection

### Using Python

```bash
# Install websockets
pip install websockets

# Create a test script
cat > test_ws.py << 'EOF'
import asyncio
import websockets
import json

async def test_websocket():
    conversion_id = "YOUR_CONVERSION_ID"  # Replace with actual ID
    uri = f"ws://localhost:8080/api/v1/conversions/{conversion_id}/ws"

    print(f"Connecting to {uri}...")
    async with websockets.connect(uri) as websocket:
        print("Connected!")

        while True:
            message = await websocket.recv()
            data = json.loads(message)
            msg_type = data.get("type")
            payload = data.get("data", {})

            if msg_type == "agent_progress":
                print(f"[{payload.get('progress')}%] {payload.get('agent')}: {payload.get('message')}")
            elif msg_type == "conversion_complete":
                print("✓ Conversion complete!")
                download_url = payload.get("details", {}).get("download_url")
                if download_url:
                    print(f"  Download: http://localhost:8080{download_url}")
                break
            elif msg_type == "conversion_failed":
                print(f"✗ Conversion failed: {payload.get('message')}")
                break

asyncio.run(test_websocket())
EOF

# Run the test
python test_ws.py
```

### Using websocat (Easiest for testing)

```bash
# Install websocat
cargo install websocat
# or on macOS: brew install websocat

# Connect to WebSocket
websocat ws://localhost:8080/api/v1/conversions/$CONVERSION_ID/ws

# You'll see messages like:
# {"type":"connection_established","data":{"conversion_id":"...","message":"Connected to conversion progress stream","timestamp":"..."}}
# {"type":"agent_progress","data":{"agent":"JavaAnalyzerAgent","status":"in_progress","progress":10,"message":"Parsing Java AST...","timestamp":"..."}}
# {"type":"agent_progress","data":{"agent":"JavaAnalyzerAgent","status":"completed","progress":100,"message":"Java analysis complete","timestamp":"..."}}
```

## 5. Run Unit Tests

```bash
cd backend

# Run all WebSocket tests
pytest tests/test_websocket_integration.py -v

# Run specific test
pytest tests/test_websocket_integration.py::test_websocket_connection -v

# Run with coverage
pytest tests/test_websocket_integration.py --cov=websocket --cov=api/conversions -v
```

## 6. OpenAPI Documentation

The API documentation is automatically generated by FastAPI:

- **Swagger UI**: http://localhost:8080/docs
- **ReDoc**: http://localhost:8080/redoc

Open these URLs in your browser to explore all endpoints with interactive examples.

## 7. Complete Workflow Example

```bash
# 1. Start backend (see step 1)

# 2. Create conversion
RESPONSE=$(curl -s -X POST http://localhost:8080/api/v1/conversions \
  -F "file=@test_mod.jar" \
  -F 'options={"assumptions":"conservative"}')

# 3. Extract conversion ID
CONVERSION_ID=$(echo $RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['conversion_id'])")
echo "Conversion ID: $CONVERSION_ID"

# 4. Monitor status via polling (alternative to WebSocket)
while true; do
  STATUS=$(curl -s http://localhost:8080/api/v1/conversions/$CONVERSION_ID | python3 -c "import sys, json; print(json.load(sys.stdin)['status'])")
  PROGRESS=$(curl -s http://localhost:8080/api/v1/conversions/$CONVERSION_ID | python3 -c "import sys, json; print(json.load(sys.stdin)['progress'])")

  echo "Status: $STATUS, Progress: $PROGRESS%"

  if [ "$STATUS" = "completed" ] || [ "$STATUS" = "failed" ]; then
    break
  fi

  sleep 2
done

# 5. Download result if completed
if [ "$STATUS" = "completed" ]; then
  curl http://localhost:8080/api/v1/conversions/$CONVERSION_ID/download \
    --output result.mcaddon
  echo "Downloaded result.mcaddon"
else
  echo "Conversion failed"
fi
```

## 8. Test with Multiple WebSocket Clients

The WebSocket implementation supports multiple clients connecting to the same conversion. Open multiple terminal windows and run:

```bash
# Terminal 1
websocat ws://localhost:8080/api/v1/conversions/$CONVERSION_ID/ws

# Terminal 2
websocat ws://localhost:8080/api/v1/conversions/$CONVERSION_ID/ws

# Terminal 3 (create conversion)
curl -X POST http://localhost:8080/api/v1/conversions \
  -F "file=@test_mod.jar" \
  -F 'options={}'
```

Both Terminal 1 and Terminal 2 should receive identical progress updates.

## 9. Troubleshooting

### Connection Refused

```bash
# Check if backend is running
curl http://localhost:8080/api/v1/health

# If connection refused, start backend:
cd /home/alexc/Projects/ModPorter-AI
docker compose -f docker compose.dev.yml up -d backend
```

### WebSocket Connection Failed

- **Error**: "Connection failed" or "404 Not Found"
- **Solution**: Verify the conversion ID is correct and the conversion exists

### File Upload Rejected

```bash
# Check file type (must be .jar or .zip)
file test_mod.jar

# Check file size (must be < 100MB)
ls -lh test_mod.jar

# Ensure file exists
ls test_mod.jar
```

### Progress Not Updating

- **Cause**: Background task not running
- **Solution**: Check backend logs for errors
  ```bash
  docker compose logs backend | tail -50
  ```

## 10. Next Steps

After verifying the implementation works:

1. **Integrate with Frontend**
   - Use the React component examples in `WEBSOCKET_CLIENT_EXAMPLES.md`
   - Add WebSocket connection to your progress component
   - Implement reconnection logic

2. **Add Authentication**
   - Add JWT authentication to WebSocket connections
   - Ensure users can only access their own conversions

3. **Add Rate Limiting**
   - Implement rate limiting for conversion creation
   - Add per-user rate limits

4. **Monitor in Production**
   - Track WebSocket connection counts
   - Monitor conversion success rates
   - Alert on errors

## Documentation

- **Implementation Guide**: `WEBSOCKET_API_IMPLEMENTATION.md`
- **Client Examples**: `WEBSOCKET_CLIENT_EXAMPLES.md`
- **Summary**: `IMPLEMENTATION_SUMMARY.md`
- **API Documentation**: http://localhost:8080/docs

## Support

If you encounter issues:

1. Check the logs: `docker compose logs backend`
2. Verify all prerequisites are installed
3. Ensure PostgreSQL and Redis are running
4. Review the implementation guide for detailed information
