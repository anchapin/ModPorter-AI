#!/bin/bash

# Test script to verify the SmartAssumptionEngine serialization fix
echo "Testing conversion process after SmartAssumptionEngine fix..."

# Test the health endpoint first
echo "1. Testing backend health..."
health_response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/api/v1/health)
if [ "$health_response" != "200" ]; then
    echo "Backend health check failed: $health_response"
    exit 1
fi
echo "Backend is healthy ✓"

# Upload a file first
echo "2. Uploading test file..."
upload_response=$(curl -s -F "file=@temp_uploads/065a2a1c-9cba-47b1-9f6f-9e0c33195c74.jar" http://localhost:8080/api/v1/upload)
file_id=$(echo "$upload_response" | grep -o '"file_id":"[^"]*"' | cut -d'"' -f4)

if [ -z "$file_id" ]; then
    echo "File upload failed: $upload_response"
    exit 1
fi
echo "File uploaded successfully, file_id: $file_id ✓"

# Start conversion with the uploaded file
echo "3. Starting conversion..."
convert_request='{
    "file_id": "'$file_id'",
    "original_filename": "test.jar",
    "target_version": "1.20.0",
    "options": {
        "smart_assumptions": true,
        "include_dependencies": true
    }
}'

convert_response=$(curl -s -X POST \
    -H "Content-Type: application/json" \
    -d "$convert_request" \
    http://localhost:8080/api/v1/convert)

job_id=$(echo "$convert_response" | grep -o '"job_id":"[^"]*"' | cut -d'"' -f4)

if [ -z "$job_id" ]; then
    echo "Conversion start failed: $convert_response"
    exit 1
fi
echo "Conversion started successfully, job_id: $job_id ✓"

# Wait a few seconds and check status to see if the SmartAssumptionEngine error occurs
echo "4. Waiting 10 seconds for processing..."
sleep 10

# Check conversion status
echo "5. Checking conversion status..."
status_response=$(curl -s http://localhost:8080/api/v1/convert/$job_id/status)
status=$(echo "$status_response" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
message=$(echo "$status_response" | grep -o '"message":"[^"]*"' | cut -d'"' -f4)

echo "Conversion status: $status"
if [ -n "$message" ]; then
    echo "Message: $message"
fi

# Check if we still get the SmartAssumptionEngine serialization error
if echo "$status_response" | grep -q "SmartAssumptionEngine"; then
    echo "❌ FAILED: SmartAssumptionEngine serialization error still present"
    echo "Response: $status_response"
    exit 1
elif [ "$status" = "failed" ] && echo "$message" | grep -q "SmartAssumptionEngine"; then
    echo "❌ FAILED: SmartAssumptionEngine error in failure message"
    exit 1
else
    echo "✅ PASSED: No SmartAssumptionEngine serialization error detected"
    echo "The fix appears to be working correctly!"
fi
