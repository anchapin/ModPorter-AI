# ModPorter AI API Documentation

## Base URL
- Development: `http://localhost:8000/api/v1`
- Production: `https://api.modporter.ai/v1`

## Authentication
Currently, the API is open for public use. Authentication will be added in future versions for rate limiting and user management.

## Endpoints

### Health Check
```http
GET /api/v1/health
```

**Response**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2025-07-02T12:00:00Z"
}
```

### Start Conversion
```http
POST /convert
```

Implements PRD Feature 1: One-Click Modpack Ingestion

**Request Body (multipart/form-data)**
```
mod_file: File (optional) - .jar or .zip file
mod_url: string (optional) - CurseForge or Modrinth URL
smart_assumptions: boolean (default: true)
include_dependencies: boolean (default: true)
```

**Timeout**: Conversions have a maximum timeout of 10 minutes. If a conversion takes longer than this, it will be marked as failed.

**Response**
```json
{
  "conversion_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "overall_success_rate": 0.0,
  "converted_mods": [],
  "failed_mods": [],
  "smart_assumptions_applied": [],
  "download_url": null,
  "detailed_report": {
    "stage": "initialization",
    "progress": 0,
    "logs": [],
    "technical_details": {}
  }
}
```

### Get Conversion Status
```http
GET /convert/{conversion_id}/status
```

**Response**
```json
{
  "conversion_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "overall_success_rate": 85.5,
  "converted_mods": [
    {
      "name": "Iron Chests",
      "version": "1.19.2-14.4.4",
      "status": "success", 
      "features": [
        {
          "name": "Iron Chest Block",
          "type": "block",
          "converted": true,
          "changes": "Converted to custom block with container functionality"
        }
      ],
      "warnings": []
    }
  ],
  "failed_mods": [],
  "smart_assumptions_applied": [
    {
      "original_feature": "Custom GUI",
      "assumption_applied": "Converted to book interface",
      "impact": "medium",
      "description": "Chest GUI converted to book-based interface for inventory management"
    }
  ],
  "download_url": "https://api.modporter.ai/v1/convert/550e8400.../download",
  "detailed_report": {
    "stage": "completed",
    "progress": 100,
    "logs": ["Analysis completed", "Conversion successful", "Package created"],
    "technical_details": {
      "processing_time": 45.2,
      "agents_used": ["java_analyzer", "bedrock_architect", "logic_translator"]
    }
  }
}
```

### Download Converted Add-on
```http
GET /convert/{conversion_id}/download
```

**Response**
- Content-Type: `application/octet-stream`
- Content-Disposition: `attachment; filename="converted_modpack.mcaddon"`
- Binary .mcaddon file

### Validation Endpoints (PRD Feature 4)

#### Start Validation
```http
POST /validate/{conversion_id}
```

**Request Body**
```json
{
  "validation_type": "direct_comparison",
  "java_version": "1.19.2",
  "original_mod_url": "https://www.curseforge.com/minecraft/mc-mods/iron-chests"
}
```

#### Get Validation Results
```http
GET /validate/{conversion_id}/results
```

**Response**
```json
{
  "validation_id": "validation-123",
  "status": "completed",
  "comparison_score": 78.5,
  "visual_similarities": {
    "textures": 95.0,
    "models": 87.3,
    "ui_elements": 45.2
  },
  "functional_similarities": {
    "crafting_recipes": 100.0,
    "block_behavior": 82.1,
    "item_properties": 91.7
  },
  "differences": [
    {
      "category": "gui",
      "description": "Original mod has custom GUI, converted version uses book interface",
      "impact": "medium"
    }
  ],
  "screenshots": {
    "java_version": "https://api.modporter.ai/screenshots/java_123.png",
    "bedrock_version": "https://api.modporter.ai/screenshots/bedrock_123.png"
  }
}
```

## Error Responses

All endpoints return consistent error format:

```json
{
  "error": "Human-readable error message",
  "code": "ERROR_CODE",
  "details": {
    "field": "specific_field_with_error",
    "reason": "detailed_reason"
  },
  "timestamp": "2025-07-02T12:00:00Z"
}
```

### Common Error Codes
- `INVALID_FILE_TYPE`: Unsupported file format
- `FILE_TOO_LARGE`: File exceeds size limit
- `INVALID_URL`: Malformed or unsupported repository URL
- `CONVERSION_FAILED`: AI conversion process failed
- `RATE_LIMIT_EXCEEDED`: Too many requests
- `CONVERSION_NOT_FOUND`: Invalid conversion ID

## Rate Limits
- **File Uploads**: 10 per hour per IP
- **Status Checks**: 60 per minute per IP
- **Downloads**: 20 per hour per IP

Rate limit headers:
```
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 7
X-RateLimit-Reset: 1625155200
```

## WebSocket Events (Real-time Updates)

Connect to `ws://localhost:8000/ws/{conversion_id}` for real-time progress updates.

**Event Types**:
```json
{
  "type": "progress_update",
  "data": {
    "stage": "analysis",
    "progress": 25,
    "message": "Analyzing mod structure..."
  }
}

{
  "type": "agent_update", 
  "data": {
    "agent": "java_analyzer",
    "status": "completed",
    "findings": "Found 15 blocks, 8 items, 2 entities"
  }
}

{
  "type": "assumption_applied",
  "data": {
    "feature": "Custom Dimension: Twilight Forest",
    "assumption": "Converting to large structure in Overworld",
    "impact": "high"
  }
}
```