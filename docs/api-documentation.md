# Portkit API Documentation

Complete REST API reference for Portkit conversion services.

## Base URL

```
Production: https://api.portkit.cloud/v1
Staging: https://api-staging.portkit.cloud/v1
Development: http://localhost:8080/api/v1
```

## Authentication

Most endpoints require API key authentication:

```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
  https://api.portkit.cloud/v1/conversions
```

**Get your API key**: [portkit.cloud/dashboard/settings](https://portkit.cloud/dashboard/settings)

## API Status

Check current API status and uptime:

```bash
curl https://status.portkit.cloud
```

---

## Endpoints

### Conversions

#### Start Conversion

Convert a Java mod to Bedrock add-on.

**Endpoint**: `POST /conversions`

**Authentication**: Required (API Key)

**Request**:

```bash
curl -X POST https://api.portkit.cloud/v1/conversions \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -F "file=@mod.jar" \
  -F "options={\"complexity\":\"high\",\"optimize_assets\":true}"
```

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| file | File | Yes | Java mod file (.jar or .zip, max 100MB) |
| options | JSON | No | Conversion options (see below) |

**Conversion Options**:

```json
{
  "complexity": "low|medium|high",  // Default: auto-detect
  "optimize_assets": true,          // Optimize textures/sounds
  "include_source": false,          // Include Java source in report
  "experimental_features": false,    // Enable experimental conversions
  "target_bedrock_version": "1.20.40" // Target Bedrock version
}
```

**Response**:

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "created_at": "2026-03-27T15:30:00Z",
  "estimated_completion": "2026-03-27T15:35:00Z",
  "mod_info": {
    "name": "Ruby Sword Mod",
    "version": "1.0.0",
    "loader": "forge",
    "complexity": "simple"
  }
}
```

**Status Codes**:
- `201 Created`: Conversion started successfully
- `400 Bad Request`: Invalid file or options
- `401 Unauthorized`: Invalid API key
- `413 Payload Too Large`: File exceeds size limit
- `429 Too Many Requests`: Rate limit exceeded

---

#### List Conversions

Get list of user's conversions with pagination.

**Endpoint**: `GET /conversions`

**Authentication**: Required (API Key)

**Request**:

```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
  "https://api.portkit.cloud/v1/conversions?page=1&limit=20&status=completed"
```

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| page | integer | No | Page number (default: 1) |
| limit | integer | No | Items per page (default: 20, max: 100) |
| status | string | No | Filter by status (processing, completed, failed) |
| sort | string | No | Sort by (created_at, updated_at) |

**Response**:

```json
{
  "total": 45,
  "page": 1,
  "limit": 20,
  "conversions": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "completed",
      "created_at": "2026-03-27T15:30:00Z",
      "updated_at": "2026-03-27T15:35:00Z",
      "mod_name": "Ruby Sword Mod",
      "success_rate": 95,
      "components_converted": 3
    }
  ]
}
```

---

#### Get Conversion Status

Get detailed status of a conversion.

**Endpoint**: `GET /conversions/{id}`

**Authentication**: Required (API Key)

**Request**:

```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
  https://api.portkit.cloud/v1/conversions/550e8400-e29b-41d4-a716-446655440000
```

**Response**:

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "created_at": "2026-03-27T15:30:00Z",
  "updated_at": "2026-03-27T15:35:00Z",
  "progress": {
    "current_step": "packaging",
    "percentage": 95,
    "eta_seconds": 30
  },
  "mod_info": {
    "name": "Ruby Sword Mod",
    "version": "1.0.0",
    "loader": "forge",
    "complexity": "simple"
  },
  "result": {
    "success_rate": 95,
    "components_converted": 3,
    "manual_steps_required": 0,
    "download_url": "/conversions/550e8400.../download"
  }
}
```

**Status Values**:
- `uploaded`: File uploaded, waiting to start
- `analyzing`: Analyzing Java code structure
- `converting`: Translating to Bedrock
- `validating`: Quality assurance checks
- `packaging`: Creating .mcaddon file
- `completed`: Conversion successful
- `failed`: Conversion failed (check error_message)

---

#### Download Conversion

Download the converted .mcaddon file.

**Endpoint**: `GET /conversions/{id}/download`

**Authentication**: Required (API Key)

**Request**:

```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
  -O https://api.portkit.cloud/v1/conversions/550e8400.../download
```

**Response**:
- `200 OK`: File download (binary .mcaddon)
- `404 Not Found`: Conversion not found or not completed

---

#### Delete Conversion

Cancel or delete a conversion.

**Endpoint**: `DELETE /conversions/{id}`

**Authentication**: Required (API Key)

**Request**:

```bash
curl -X DELETE \
  -H "Authorization: Bearer YOUR_API_KEY" \
  https://api.portkit.cloud/v1/conversions/550e8400...
```

**Response**:

```json
{
  "message": "Conversion deleted successfully"
}
```

---

### WebSocket Progress

#### Real-time Progress Updates

Connect to WebSocket for real-time conversion progress.

**Endpoint**: `WS /conversions/{id}/ws`

**Authentication**: Required (API Key in query param)

**Connection**:

```javascript
const ws = new WebSocket(
  `wss://api.portkit.cloud/v1/conversions/${id}/ws?api_key=YOUR_API_KEY`
);

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(`Progress: ${data.percentage}%`);
};
```

**Message Format**:

```json
{
  "type": "progress",
  "step": "converting",
  "percentage": 45,
  "message": "Translating Java to JavaScript...",
  "eta_seconds": 180
}
```

**Message Types**:
- `progress`: Progress update
- `step_change`: Conversion step changed
- `warning`: Non-fatal warning
- `error`: Error occurred
- `complete`: Conversion finished
- `cancelled`: Conversion was cancelled

---

### Conversion Report

#### Get Conversion Report

Get detailed conversion report with assumptions and manual steps.

**Endpoint**: `GET /conversions/{id}/report`

**Authentication**: Required (API Key)

**Request**:

```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
  https://api.portkit.cloud/v1/conversions/550e8400.../report
```

**Response**:

```json
{
  "conversion_id": "550e8400-e29b-41d4-a716-446655440000",
  "mod_info": {
    "name": "Ruby Sword Mod",
    "version": "1.0.0"
  },
  "success_rate": 95,
  "components": [
    {
      "type": "item",
      "name": "Ruby Sword",
      "status": "success",
      "file": "behavior_packs/rubysword/items/ruby_sword.json"
    }
  ],
  "assumptions": [
    {
      "feature": "attack_damage",
      "java_value": 10,
      "bedrock_value": 10,
      "confidence": "high"
    }
  ],
  "manual_steps": [],
  "validation_results": {
    "syntax_check": "passed",
    "schema_validation": "passed",
    "asset_integrity": "passed"
  }
}
```

---

### Batch Conversion

#### Start Batch Conversion

Convert multiple mods at once (Pro feature).

**Endpoint**: `POST /conversions/batch`

**Authentication**: Required (Pro/Studio API Key)

**Request**:

```bash
curl -X POST https://api.portkit.cloud/v1/conversions/batch \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -F "files=@mod1.jar" \
  -F "files=@mod2.jar" \
  -F "files=@mod3.jar" \
  -F "options={\"optimize_assets\":true}"
```

**Response**:

```json
{
  "batch_id": "batch-550e8400-e29b-41d4-a716",
  "conversion_ids": [
    "550e8400-e29b-41d4-a716-446655440000",
    "550e8400-e29b-41d4-a716-446655440001",
    "550e8400-e29b-41d4-a716-446655440002"
  ],
  "status": "processing",
  "total_conversions": 3
}
```

---

### Analytics

#### Get Usage Statistics

Get API usage statistics for current billing period.

**Endpoint**: `GET /analytics/usage`

**Authentication**: Required (API Key)

**Request**:

```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
  https://api.portkit.cloud/v1/analytics/usage
```

**Response**:

```json
{
  "period": {
    "start": "2026-03-01T00:00:00Z",
    "end": "2026-03-31T23:59:59Z"
  },
  "usage": {
    "conversions_total": 45,
    "conversions_completed": 42,
    "conversions_failed": 3,
    "api_calls": 150,
    "storage_used_mb": 450
  },
  "limits": {
    "conversions_limit": "unlimited",
    "api_calls_limit": 1000,
    "storage_limit_mb": 10240
  }
}
```

---

### Health

#### Health Check

Check API health status.

**Endpoint**: `GET /health`

**Authentication**: Not required

**Request**:

```bash
curl https://api.portkit.cloud/v1/health
```

**Response**:

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2026-03-27T15:30:00Z",
  "services": {
    "database": "healthy",
    "redis": "healthy",
    "ai_engine": "healthy"
  }
}
```

---

## Error Handling

### Error Response Format

All errors follow this format:

```json
{
  "error": {
    "code": "INVALID_FILE_TYPE",
    "message": "Only .jar and .zip files are supported",
    "details": {
      "received_type": "exe",
      "allowed_types": [".jar", ".zip"]
    },
    "documentation_url": "https://docs.portkit.cloud/errors/invalid-file-type"
  }
}
```

### Common Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `INVALID_API_KEY` | 401 | API key is invalid or expired |
| `INSUFFICIENT_CREDITS` | 402 | Not enough conversion credits |
| `INVALID_FILE_TYPE` | 400 | File type not supported |
| `FILE_TOO_LARGE` | 413 | File exceeds size limit |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `CONVERSION_FAILED` | 422 | Conversion failed (check details) |
| `NOT_FOUND` | 404 | Resource not found |

### Rate Limiting

**Rate limits** per API key:

| Plan | Requests/Hour | Conversions/Day |
|------|---------------|-----------------|
| Free | 10 | 5 |
| Pro | 100 | Unlimited |
| Studio | 1000 | Unlimited |
| Enterprise | Custom | Unlimited |

**Rate limit headers**:

```http
HTTP/1.1 200 OK
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1648380000
```

---

## Code Examples

### Python

```python
import requests

API_KEY = "your_api_key"
BASE_URL = "https://api.portkit.cloud/v1"

# Start conversion
with open("mod.jar", "rb") as f:
    response = requests.post(
        f"{BASE_URL}/conversions",
        headers={"Authorization": f"Bearer {API_KEY}"},
        files={"file": f},
        data={"options": '{"complexity":"high"}'}
    )

conversion_id = response.json()["id"]
print(f"Conversion started: {conversion_id}")

# Check status
status = requests.get(
    f"{BASE_URL}/conversions/{conversion_id}",
    headers={"Authorization": f"Bearer {API_KEY}"}
).json()

print(f"Status: {status['status']}")

# Download when complete
if status["status"] == "completed":
    download = requests.get(
        f"{BASE_URL}/conversions/{conversion_id}/download",
        headers={"Authorization": f"Bearer {API_KEY}"}
    )

    with open("mod.mcaddon", "wb") as f:
        f.write(download.content)
```

### JavaScript (Node.js)

```javascript
const axios = require('axios');
const fs = require('fs');

const API_KEY = 'your_api_key';
const BASE_URL = 'https://api.portkit.cloud/v1';

// Start conversion
const form = new FormData();
form.append('file', fs.createReadStream('mod.jar'));
form.append('options', JSON.stringify({ complexity: 'high' }));

const { data } = await axios.post(
  `${BASE_URL}/conversions`,
  form,
  {
    headers: {
      'Authorization': `Bearer ${API_KEY}`,
      ...form.getHeaders()
    }
  }
);

const conversionId = data.id;
console.log(`Conversion started: ${conversionId}`);

// Poll for completion
while (true) {
  const status = await axios.get(
    `${BASE_URL}/conversions/${conversionId}`,
    { headers: { 'Authorization': `Bearer ${API_KEY}` } }
  );

  console.log(`Status: ${status.data.status}`);

  if (status.data.status === 'completed') {
    // Download
    const download = await axios.get(
      `${BASE_URL}/conversions/${conversionId}/download`,
      {
        headers: { 'Authorization': `Bearer ${API_KEY}` },
        responseType: 'arraybuffer'
      }
    );

    fs.writeFileSync('mod.mcaddon', download.data);
    break;
  }

  await new Promise(resolve => setTimeout(resolve, 5000));
}
```

### cURL

```bash
# Start conversion
curl -X POST https://api.portkit.cloud/v1/conversions \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -F "file=@mod.jar" \
  -F 'options={"optimize_assets":true}'

# Check status
curl https://api.portkit.cloud/v1/conversions/CONVERSION_ID \
  -H "Authorization: Bearer YOUR_API_KEY"

# Download
curl -O https://api.portkit.cloud/v1/conversions/CONVERSION_ID/download \
  -H "Authorization: Bearer YOUR_API_KEY"
```

---

## SDKs and Libraries

### Official SDKs

- **Python**: `pip install portkit`
- **JavaScript**: `npm install @modporter/sdk`
- **Go**: `go get github.com/modporter/go-sdk`
- **Rust**: `cargo add modporter-rs`

### Community Libraries

- **Java**: [modporter-java](https://github.com/modporter-community/java-sdk)
- **C#**: [Modporter.NET](https://github.com/modporter-community/dotnet-sdk)
- **PHP**: [modporter-php](https://github.com/modporter-community/php-sdk)

---

## Testing

### Sandbox Environment

Test your integration without using production credits:

```bash
# Use sandbox URL
SANDBOX_URL="https://api-sandbox.portkit.cloud/v1"

# Sandbox API key (free testing)
SANDBOX_KEY="sandbox_test_key"

curl -X POST $SANDBOX_URL/conversions \
  -H "Authorization: Bearer $SANDBOX_KEY" \
  -F "file=@test_mod.jar"
```

**Sandbox limits**:
- 10 test conversions/day
- Files max 10MB
- Results expire in 1 hour

---

## Changelog

### Version 1.0.0 (2026-03-27)

**Added**:
- Initial API release
- Conversion endpoints
- WebSocket progress updates
- Batch conversion (Pro)
- Analytics and usage stats

---

## Support

- **Documentation**: [docs.portkit.cloud](https://docs.portkit.cloud)
- **API Reference**: [api.portkit.cloud/docs](https://api.portkit.cloud/docs) (Swagger UI)
- **Support Email**: api-support@portkit.cloud
- **GitHub Issues**: [github.com/portkit/issues](https://github.com/portkit/issues)
- **Discord**: [discord.gg/modporter](https://discord.gg/modporter)

---

**Need help?** Join our API Discord channel or contact api-support@portkit.cloud
