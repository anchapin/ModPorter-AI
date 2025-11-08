# ModPorter AI - Comprehensive API Documentation

## 🚀 Overview

ModPorter AI provides a RESTful API for converting Minecraft Java Edition mods to Bedrock Edition add-ons. This document covers all available endpoints, authentication, best practices, and integration examples.

## 🌐 Base URLs

### Environments
- **Development**: `http://localhost:8000/api/v1`
- **Staging**: `https://staging-api.modporter.ai/v1`
- **Production**: `https://api.modporter.ai/v1`

### WebSocket Endpoints
- **Conversion Progress**: `ws://localhost:8000/ws/conversions/{conversion_id}`
- **Real-time Updates**: `wss://api.modporter.ai/ws/conversions/{conversion_id}`

## 🔐 Authentication & Security

### Current Status
- API is currently open for public use
- Authentication will be implemented in v2.0
- Rate limiting applies to all requests

### Rate Limiting
| Endpoint | Limit | Window |
|----------|-------|--------|
| Conversions | 10 per hour | per IP |
| File Uploads | 100MB per request | per request |
| General API | 1000 requests per hour | per IP |
| WebSocket Connections | 50 concurrent | per IP |

### Headers
```http
Content-Type: application/json
X-API-Version: 1.0 (optional)
User-Agent: YourApp/1.0 (recommended)
```

## 📊 Response Format

### Success Response
```json
{
  "success": true,
  "data": {
    // Response data
  },
  "message": "Operation completed successfully",
  "timestamp": "2025-01-01T12:00:00Z",
  "request_id": "req_550e8400-e29b-41d4-a716"
}
```

### Error Response
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input parameters",
    "details": {
      "field": "mod_file",
      "issue": "File size exceeds 100MB limit"
    }
  },
  "timestamp": "2025-01-01T12:00:00Z",
  "request_id": "req_550e8400-e29b-41d4-a716"
}
```

### HTTP Status Codes
| Code | Description |
|------|-------------|
| 200 | Success |
| 201 | Created |
| 202 | Accepted (async processing) |
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 429 | Rate Limited |
| 500 | Internal Server Error |
| 503 | Service Unavailable |

## 🔄 Conversion Endpoints

### Start New Conversion
```http
POST /api/v1/conversions
```

Initiate a new mod conversion process.

**Request (multipart/form-data)**
```
mod_file: File (optional) - .jar or .zip file, max 100MB
mod_url: string (optional) - CurseForge/Modrinth URL
smart_assumptions: boolean (default: true)
include_dependencies: boolean (default: true)
target_version: string (default: "latest")
performance_profile: string (default: "balanced") - "fast", "balanced", "quality"
conversion_options: JSON (optional) - Additional conversion settings
```

**Example cURL**
```bash
curl -X POST \
  http://localhost:8000/api/v1/conversions \
  -H 'Content-Type: multipart/form-data' \
  -F 'mod_file=@/path/to/mod.jar' \
  -F 'smart_assumptions=true' \
  -F 'performance_profile=quality'
```

**Example JSON Request**
```bash
curl -X POST \
  http://localhost:8000/api/v1/conversions \
  -H 'Content-Type: application/json' \
  -d '{
    "mod_url": "https://modrinth.com/mod/iron-chests/version/1.19.2-14.4.4",
    "smart_assumptions": true,
    "include_dependencies": true,
    "target_version": "1.20.0",
    "performance_profile": "balanced",
    "conversion_options": {
      "preserve_textures": true,
      "optimize_entities": true
    }
  }'
```

**Response**
```json
{
  "success": true,
  "data": {
    "conversion_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "queued",
    "estimated_duration_seconds": 300,
    "input_summary": {
      "file_count": 1,
      "total_size_mb": 45.2,
      "mod_count": 1,
      "dependency_count": 3
    },
    "progress_websocket_url": "ws://localhost:8000/ws/conversions/550e8400-e29b-41d4-a716-446655440000",
    "status_poll_url": "/api/v1/conversions/550e8400-e29b-41d4-a716-446655440000/status"
  },
  "message": "Conversion queued successfully",
  "timestamp": "2025-01-01T12:00:00Z"
}
```

### Get Conversion Status
```http
GET /api/v1/conversions/{conversion_id}/status
```

Retrieve current status and progress of a conversion.

**Response**
```json
{
  "success": true,
  "data": {
    "conversion_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "processing",
    "progress_percentage": 65,
    "current_stage": "entity_conversion",
    "stages": [
      {
        "name": "file_analysis",
        "status": "completed",
        "duration_seconds": 45
      },
      {
        "name": "dependency_resolution",
        "status": "completed", 
        "duration_seconds": 120
      },
      {
        "name": "entity_conversion",
        "status": "in_progress",
        "progress_percentage": 40,
        "estimated_remaining_seconds": 80
      }
    ],
    "overall_success_rate": 0,
    "converted_components": {
      "blocks": 12,
      "items": 8,
      "entities": 3,
      "recipes": 15
    },
    "started_at": "2025-01-01T12:00:00Z",
    "estimated_completion": "2025-01-01T12:05:00Z"
  },
  "timestamp": "2025-01-01T12:03:00Z"
}
```

### Get Conversion Results
```http
GET /api/v1/conversions/{conversion_id}
```

Retrieve full conversion results including download links and detailed report.

**Response**
```json
{
  "success": true,
  "data": {
    "conversion_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "completed",
    "overall_success_rate": 85.5,
    "conversion_summary": {
      "total_components": 40,
      "successful_conversions": 34,
      "failed_conversions": 6,
      "warnings": 8
    },
    "converted_mods": [
      {
        "name": "Iron Chests",
        "version": "1.19.2-14.4.4",
        "status": "success",
        "components": {
          "blocks": [
            {
              "name": "Iron Chest",
              "original_id": "ironchests:iron_chest",
              "bedrock_id": "custom:iron_chest",
              "converted": true,
              "changes": "Converted to custom block with container functionality"
            }
          ],
          "items": [
            {
              "name": "Iron Chest Upgrade",
              "converted": true,
              "changes": "Converted to custom upgrade item"
            }
          ],
          "entities": [],
          "recipes": [
            {
              "name": "Iron Chest Recipe",
              "converted": true,
              "changes": "Adapted for Bedrock crafting system"
            }
          ]
        },
        "performance_score": 92,
        "quality_assessment": "high"
      }
    ],
    "failed_components": [
      {
        "name": "Advanced GUI",
        "type": "gui",
        "reason": "Complex inventory management not supported in Bedrock",
        "workaround": "Simplified to book interface"
      }
    ],
    "smart_assumptions_applied": [
      {
        "original_feature": "Custom GUI",
        "assumption_applied": "Converted to book interface",
        "impact": "medium",
        "description": "Chest GUI converted to book-based interface for inventory management",
        "confidence": 85
      }
    ],
    "performance_metrics": {
      "conversion_time_seconds": 245,
      "memory_peak_mb": 512,
      "cpu_usage_percent": 45
    },
    "downloads": {
      "mcaddon": {
        "url": "/api/v1/conversions/550e8400-e29b-41d4-a716-446655440000/download/mcaddon",
        "size_mb": 12.5,
        "checksum": "sha256:abc123..."
      },
      "source_files": {
        "url": "/api/v1/conversions/550e8400-e29b-41d4-a716-446655440000/download/source",
        "size_mb": 8.2
      }
    },
    "detailed_report": {
      "summary": "Successfully converted Iron Chests mod with 85.5% success rate",
      "technical_details": {
        "java_version": "1.19.2",
        "target_bedrock_version": "1.20.0",
        "api_level": "59"
      },
      "recommendations": [
        "Test chest functionality in multiplayer",
        "Consider custom textures for better visual integration"
      ]
    }
  },
  "timestamp": "2025-01-01T12:04:00Z"
}
```

### Download Converted Files
```http
GET /api/v1/conversions/{conversion_id}/download/{format}
```

Download converted files in specified format.

**Parameters**
- `format`: `mcaddon`, `mcpack`, `source`, `report`

**Headers**
```http
Accept: application/zip (for source files)
Accept: application/octet-stream (for mcaddon)
```

### List Conversions
```http
GET /api/v1/conversions
```

List user's conversion history.

**Query Parameters**
- `limit`: Number of results (default: 20, max: 100)
- `offset`: Pagination offset (default: 0)
- `status`: Filter by status (`queued`, `processing`, `completed`, `failed`)
- `sort`: Sort by field (`created_at`, `status`, `success_rate`) default: `created_at`
- `order`: Sort order (`asc`, `desc`) default: `desc`

**Response**
```json
{
  "success": true,
  "data": {
    "conversions": [
      {
        "conversion_id": "550e8400-e29b-41d4-a716-446655440000",
        "status": "completed",
        "created_at": "2025-01-01T12:00:00Z",
        "completed_at": "2025-01-01T12:04:00Z",
        "success_rate": 85.5,
        "input_type": "file_upload",
        "mod_name": "Iron Chests",
        "file_size_mb": 45.2
      }
    ],
    "pagination": {
      "total": 45,
      "limit": 20,
      "offset": 0,
      "has_more": true
    }
  },
  "timestamp": "2025-01-01T13:00:00Z"
}
```

## 🎨 Behavior Editor Endpoints

### Get Behavior Templates
```http
GET /api/v1/behavior-templates
```

Retrieve available behavior templates for customization.

**Query Parameters**
- `category`: Filter by category (`blocks`, `items`, `entities`, `recipes`)
- `complexity`: Filter by complexity (`simple`, `medium`, `complex`)

**Response**
```json
{
  "success": true,
  "data": {
    "templates": [
      {
        "id": "container_block",
        "name": "Container Block",
        "category": "blocks",
        "complexity": "medium",
        "description": "Block with inventory functionality",
        "template": {
          "format_version": "1.20.0",
          "minecraft:block": {
            "description": {
              "identifier": "custom:container",
              "menu_category": {
                "category": "construction"
              }
            },
            "components": {
              "minecraft:inventory": {
                "container_type": "container",
                "size": 27
              }
            }
          }
        },
        "customizable_fields": [
          "identifier",
          "container_type",
          "size"
        ]
      }
    ]
  },
  "timestamp": "2025-01-01T12:00:00Z"
}
```

### Create Custom Behavior
```http
POST /api/v1/behaviors
```

Create or modify custom behavior JSON.

**Request Body**
```json
{
  "conversion_id": "550e8400-e29b-41d4-a716-446655440000",
  "component_type": "block",
  "component_id": "custom:iron_chest",
  "behavior_json": {
    "format_version": "1.20.0",
    "minecraft:block": {
      "description": {
        "identifier": "custom:iron_chest",
        "menu_category": {
          "category": "construction"
        }
      },
      "components": {
        "minecraft:inventory": {
          "container_type": "container",
          "size": 54
        }
      }
    }
  },
  "validation_options": {
    "strict_mode": true,
    "target_version": "1.20.0"
  }
}
```

### Validate Behavior
```http
POST /api/v1/behaviors/validate
```

Validate behavior JSON against Bedrock Edition standards.

**Request Body**
```json
{
  "behavior_json": {...},
  "target_version": "1.20.0",
  "strict_mode": false
}
```

**Response**
```json
{
  "success": true,
  "data": {
    "valid": false,
    "errors": [
      {
        "path": "$.minecraft:block.components",
        "message": "Missing required component: minecraft:material_instances",
        "severity": "error"
      }
    ],
    "warnings": [
      {
        "path": "$.minecraft:block.description",
        "message": "Consider adding more descriptive properties",
        "severity": "warning"
      }
    ],
    "suggestions": [
      "Add minecraft:material_instances component for proper rendering"
    ]
  },
  "timestamp": "2025-01-01T12:00:00Z"
}
```

## 📈 Performance Endpoints

### Get System Metrics
```http
GET /api/v1/metrics
```

Retrieve system performance metrics.

**Response**
```json
{
  "success": true,
  "data": {
    "system": {
      "cpu_usage_percent": 35.5,
      "memory_usage_percent": 67.2,
      "disk_usage_percent": 45.8,
      "uptime_seconds": 86400
    },
    "api": {
      "requests_per_minute": 45,
      "average_response_time_ms": 120,
      "active_conversions": 3,
      "queue_length": 1
    },
    "conversion_stats": {
      "total_conversions": 1250,
      "success_rate": 87.3,
      "average_conversion_time_seconds": 180,
      "popular_targets": ["blocks", "items", "entities"]
    }
  },
  "timestamp": "2025-01-01T12:00:00Z"
}
```

### Performance Benchmark
```http
POST /api/v1/performance/benchmark
```

Run performance benchmark on conversion system.

**Request Body**
```json
{
  "scenario": "moderate_load",
  "test_files": [
    "https://modrinth.com/mod/example-mod"
  ],
  "options": {
    "include_ai_analysis": true,
    "test_performance_profiles": ["fast", "balanced", "quality"]
  }
}
```

## 🔧 Advanced Endpoints

### Conversion Preview
```http
POST /api/v1/conversions/preview
```

Generate preview of conversion changes without full conversion.

**Request Body**
```json
{
  "mod_file": "File or URL",
  "analysis_depth": "deep", // "shallow", "medium", "deep"
  "include_estimate": true
}
```

**Response**
```json
{
  "success": true,
  "data": {
    "mod_analysis": {
      "name": "Example Mod",
      "version": "1.19.2",
      "components": {
        "blocks": 12,
        "items": 8,
        "entities": 3,
        "recipes": 15
      },
      "complexity_score": 7.5,
      "compatibility_assessment": {
        "overall_score": 85,
        "potential_issues": [
          "Custom rendering may require adaptation"
        ]
      }
    },
    "conversion_estimate": {
      "success_probability": 85,
      "estimated_time_seconds": 240,
      "resource_requirements": {
        "memory_mb": 512,
        "cpu_cores": 2
      },
      "potential_changes": [
        "GUI systems will be simplified",
        "Custom entities will use Bedrock behaviors"
      ]
    }
  },
  "timestamp": "2025-01-01T12:00:00Z"
}
```

### Batch Conversion
```http
POST /api/v1/conversions/batch
```

Initiate batch conversion of multiple mods.

**Request Body**
```json
{
  "mods": [
    {"url": "https://modrinth.com/mod/mod1"},
    {"file": "File object"}
  ],
  "options": {
    "global_settings": {
      "smart_assumptions": true,
      "performance_profile": "balanced"
    },
    "individual_settings": {
      "0": {"target_version": "1.19.0"},
      "1": {"include_dependencies": false}
    }
  }
}
```

## 🌐 WebSocket Integration

### Conversion Progress WebSocket

Connect to real-time conversion updates:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/conversions/{conversion_id}');

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    
    switch(data.type) {
        case 'progress_update':
            console.log(`Progress: ${data.progress_percentage}%`);
            console.log(`Stage: ${data.current_stage}`);
            break;
            
        case 'stage_completed':
            console.log(`Stage ${data.stage_name} completed in ${data.duration_seconds}s`);
            break;
            
        case 'conversion_completed':
            console.log('Conversion completed!');
            window.location.href = data.results_url;
            break;
            
        case 'error':
            console.error('Conversion error:', data.error);
            break;
    }
};

ws.onerror = function(error) {
    console.error('WebSocket error:', error);
};

ws.onclose = function() {
    console.log('WebSocket connection closed');
};
```

**WebSocket Message Types**

| Type | Description |
|------|-------------|
| `progress_update` | General progress update |
| `stage_completed` | Specific stage completed |
| `conversion_completed` | Full conversion finished |
| `error` | Error occurred during conversion |
| `queue_update` | Position in queue updated |

**Example WebSocket Message**
```json
{
  "type": "progress_update",
  "timestamp": "2025-01-01T12:02:00Z",
  "data": {
    "progress_percentage": 45,
    "current_stage": "entity_conversion",
    "stage_progress": 60,
    "estimated_remaining_seconds": 120,
    "components_completed": 18,
    "total_components": 40
  }
}
```

## 📚 Client Libraries

### JavaScript/TypeScript

```javascript
// npm install @modporter-ai/client
import { ModPorterClient } from '@modporter-ai/client';

const client = new ModPorterClient({
  baseURL: 'https://api.modporter.ai/v1',
  apiKey: 'your-api-key' // optional for now
});

// Start conversion
const conversion = await client.conversions.create({
  modUrl: 'https://modrinth.com/mod/example-mod',
  smartAssumptions: true,
  performanceProfile: 'quality'
});

// Monitor progress
client.conversions.onProgress(conversion.conversionId, (update) => {
  console.log(`Progress: ${update.progressPercentage}%`);
});

// Get results
const results = await client.conversions.get(conversion.conversionId);
```

### Python

```python
# pip install modporter-ai-client
from modporter_ai import ModPorterClient

client = ModPorterClient(base_url='https://api.modporter.ai/v1')

# Start conversion
conversion = client.conversions.create(
    mod_url='https://modrinth.com/mod/example-mod',
    smart_assumptions=True,
    performance_profile='quality'
)

# Monitor progress
for update in client.conversions.stream_progress(conversion.conversion_id):
    print(f"Progress: {update.progress_percentage}%")
    if update.status == 'completed':
        break

# Get results
results = client.conversions.get(conversion.conversion_id)
```

## 🛠️ Integration Examples

### React Component

```jsx
import React, { useState, useEffect } from 'react';
import { ModPorterClient } from '@modporter-ai/client';

function ConversionManager() {
  const [conversion, setConversion] = useState(null);
  const [progress, setProgress] = useState(0);
  const client = new ModPorterClient();

  const startConversion = async (file) => {
    const result = await client.conversions.create({
      file,
      smartAssumptions: true,
      performanceProfile: 'balanced'
    });
    
    setConversion(result.data);
  };

  useEffect(() => {
    if (conversion) {
      const ws = new WebSocket(
        `ws://localhost:8000/ws/conversions/${conversion.conversion_id}`
      );

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'progress_update') {
          setProgress(data.data.progress_percentage);
        }
      };

      return () => ws.close();
    }
  }, [conversion]);

  return (
    <div>
      <input type="file" onChange={(e) => startConversion(e.target.files[0])} />
      {conversion && (
        <div>
          <p>Conversion ID: {conversion.conversion_id}</p>
          <p>Progress: {progress}%</p>
        </div>
      )}
    </div>
  );
}
```

### Node.js Script

```javascript
const ModPorterClient = require('@modporter-ai/client');
const fs = require('fs');

async function batchConvert(modFiles) {
  const client = new ModPorterClient();
  
  for (const file of modFiles) {
    console.log(`Converting ${file}...`);
    
    try {
      const conversion = await client.conversions.create({
        file: fs.createReadStream(file),
        performanceProfile: 'quality'
      });
      
      // Wait for completion
      const result = await client.conversions.waitForCompletion(
        conversion.conversion_id,
        { timeout: 600000 } // 10 minutes
      );
      
      // Download result
      const downloadStream = await client.conversions.download(
        result.conversion_id,
        'mcaddon'
      );
      
      const outputPath = `${file}_converted.mcaddon`;
      const fileStream = fs.createWriteStream(outputPath);
      
      downloadStream.pipe(fileStream);
      
      console.log(`✅ ${file} -> ${outputPath}`);
      console.log(`Success rate: ${result.overall_success_rate}%`);
      
    } catch (error) {
      console.error(`❌ Failed to convert ${file}:`, error.message);
    }
  }
}

// Usage
batchConvert(['mod1.jar', 'mod2.jar']);
```

## 🐛 Error Handling

### Common Error Codes

| Code | Description | Resolution |
|------|-------------|------------|
| `INVALID_FILE_FORMAT` | Uploaded file is not valid .jar or .zip | Check file format and extension |
| `FILE_TOO_LARGE` | File exceeds 100MB limit | Compress file or contact support |
| `DEPENDENCY_NOT_FOUND` | Required dependency cannot be located | Provide dependency files or URLs |
| `CONVERSION_TIMEOUT` | Conversion exceeded 10-minute timeout | Try simplifying mod or using performance profile "fast" |
| `RATE_LIMIT_EXCEEDED` | Too many requests | Wait and retry, or upgrade plan |
| `AI_SERVICE_UNAVAILABLE` | AI conversion services temporarily down | Retry later or use basic conversion |

### Error Response Handling

```javascript
try {
  const result = await client.conversions.create(requestData);
} catch (error) {
  if (error.response) {
    // API responded with error
    const { code, message, details } = error.response.data.error;
    
    switch (code) {
      case 'INVALID_FILE_FORMAT':
        alert('Please upload a valid .jar or .zip file');
        break;
      case 'FILE_TOO_LARGE':
        alert('File is too large. Maximum size is 100MB');
        break;
      case 'RATE_LIMIT_EXCEEDED':
        alert('Too many requests. Please wait and try again');
        setTimeout(() => retryConversion(), 60000);
        break;
      default:
        alert(`Error: ${message}`);
    }
  } else if (error.request) {
    // Network error
    alert('Network error. Please check your connection');
  } else {
    // Unexpected error
    alert('An unexpected error occurred');
  }
}
```

## 📖 Best Practices

### Performance Optimization
1. **Use WebSocket** for real-time updates instead of polling
2. **Batch conversions** when processing multiple mods
3. **Choose appropriate performance profile** based on needs
4. **Compress large files** before uploading
5. **Cache conversion results** for repeated conversions

### Error Handling
1. **Implement retry logic** with exponential backoff
2. **Validate inputs** before sending to API
3. **Handle rate limits** gracefully
4. **Provide user feedback** for all operations
5. **Log errors** for debugging

### Security
1. **Validate file types** before upload
2. **Sanitize URLs** when using mod URLs
3. **Use HTTPS** for all API calls
4. **Never expose API keys** in client-side code
5. **Set appropriate timeouts** for requests

## 🔍 Testing & Debugging

### Test Environment
- Use `http://localhost:8000/api/v1` for development
- Mock server responses for unit testing
- Use WebSocket test tools for real-time features

### Debug Mode
Add `X-Debug: true` header to enable detailed error responses:
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input parameters",
    "details": {
      "debug_info": {
        "request_id": "req_123",
        "trace_id": "trace_456",
        "validation_errors": [...]
      }
    }
  }
}
```

### Monitoring
Monitor these metrics for optimal performance:
- API response times
- Conversion success rates
- WebSocket connection health
- Resource usage patterns

## 🆘 Support

### Getting Help
- **Documentation**: Check this comprehensive guide first
- **Status Page**: https://status.modporter.ai
- **GitHub Issues**: Report bugs and feature requests
- **Discord Community**: Real-time support and discussions
- **Email Support**: support@modporter.ai

### Reporting Issues
When reporting issues, include:
1. Request ID from response headers
2. Full error response
3. Steps to reproduce
4. Expected vs actual behavior
5. Environment details (browser, version, etc.)

---

## 📈 API Changelog

### v1.0 (Current)
- Initial release with core conversion functionality
- WebSocket support for real-time progress
- Behavior editor integration
- Performance optimization options

### Upcoming Features
- User authentication and management
- Conversion history and analytics
- Custom behavior marketplace
- Advanced batch processing
- Mobile API optimizations

For the latest updates and announcements, follow our [GitHub Repository](https://github.com/anchapin/ModPorter-AI) and [Discord Server](https://discord.gg/modporter).
