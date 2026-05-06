# PortKit Plugin API Contract

Version: 1.0.0
Last Updated: 2026-05-06

## Overview

The PortKit Plugin API enables IDE plugins (bridge., VS Code, Blockbench) to trigger Java-to-Bedrock conversions through the centralized PortKit cloud API. All conversion logic, AI processing, and billing remain centralized.

## Base URL

```
Production: https://api.portkit.com/api/v1/plugins
Staging: https://staging-api.portkit.com/api/v1/plugins
Local: http://localhost:8080/api/v1/plugins
```

## Authentication

All API requests should include an API key for authentication:

```
Authorization: Bearer <API_KEY>
```

API keys are managed through the PortKit dashboard.

## Endpoints

### Start Conversion

Initiates a new conversion job from an IDE plugin.

**POST** `/convert`

#### Request Headers

| Header | Type | Required | Description |
|--------|------|----------|-------------|
| Content-Type | string | Yes | Must be `application/json` |
| Authorization | string | No | Bearer token if API key configured |

#### Request Body

```json
{
  "plugin_type": "bridge" | "vscode" | "blockbench",
  "file_data": "<base64_encoded_file>",
  "file_name": "example-mod.jar",
  "target_version": "1.20.0",
  "options": {}
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| plugin_type | string | Yes | IDE plugin identifier |
| file_data | string | Yes | Base64-encoded .jar or .zip file |
| file_name | string | Yes | Original filename |
| target_version | string | No | Target Bedrock version (default: "1.20.0") |
| options | object | No | Conversion options |

#### Response (202 Accepted)

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "preprocessing",
  "message": "Conversion started from bridge plugin",
  "estimated_time": 35
}
```

### Get Conversion Status

Retrieves the current status of a conversion job.

**GET** `/convert/{job_id}/status`

#### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| job_id | string (UUID) | The conversion job ID |

#### Response (200 OK)

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "progress": 100,
  "message": "Conversion completed successfully.",
  "result_url": "/api/v1/plugins/convert/550e8400-e29b-41d4-a716-446655440000/download",
  "error": null,
  "created_at": "2026-05-06T10:30:00Z"
}
```

#### Status Values

| Status | Description |
|--------|-------------|
| queued | Job is waiting to start |
| preprocessing | Preprocessing uploaded file |
| processing | AI conversion in progress |
| postprocessing | Finalizing conversion results |
| completed | Conversion finished successfully |
| failed | Conversion encountered an error |
| cancelled | Job was cancelled by user |

### Download Converted File

Downloads the converted Bedrock add-on.

**GET** `/convert/{job_id}/download`

#### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| job_id | string (UUID) | The conversion job ID |

#### Response (200 OK)

- Content-Type: `application/octet-stream`
- Content-Disposition: `attachment; filename="modname_converted.mcaddon"`

The response body contains the binary `.mcaddon` file.

#### Error Responses

| Status | Description |
|--------|-------------|
| 400 | Job not yet completed |
| 404 | Job or result file not found |

## Error Handling

All error responses follow this format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

## Rate Limits

Plugin API requests are subject to the same rate limits as regular API requests:
- 100 requests per minute per API key
- File size limit: 100MB

## Plugin Identifiers

| Plugin | Identifier |
|--------|------------|
| bridge. | `bridge` |
| VS Code Extension | `vscode` |
| Blockbench Plugin | `blockbench` |

## Example Usage

### cURL

```bash
# Start conversion
curl -X POST https://api.portkit.com/api/v1/plugins/convert \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "plugin_type": "bridge",
    "file_data": "$(base64 -w0 mod.jar)",
    "file_name": "mod.jar",
    "target_version": "1.20.0"
  }'

# Check status
curl https://api.portkit.com/api/v1/plugins/convert/{job_id}/status \
  -H "Authorization: Bearer YOUR_API_KEY"

# Download result
curl -O https://api.portkit.com/api/v1/plugins/convert/{job_id}/download \
  -H "Authorization: Bearer YOUR_API_KEY"
```

### JavaScript (from bridge. plugin)

```typescript
const result = await fetch(`${API_ENDPOINT}/convert`, {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    "Authorization": `Bearer ${apiKey}`,
  },
  body: JSON.stringify({
    plugin_type: "bridge",
    file_data: base64EncodedFile,
    file_name: "mod.jar",
    target_version: "1.20.0",
  }),
});

const { job_id } = await result.json();
```

## Webhook Notifications (Optional)

For real-time UI updates, plugins can poll `/convert/{job_id}/status` every 2-3 seconds during active conversion. The conversion typically takes 30-60 seconds.