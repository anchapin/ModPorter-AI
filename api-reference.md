# API Reference

This document provides detailed documentation for the ModPorter AI REST API.

## Base URL

```
http://localhost:8080/api/v1
```

## Authentication

The API uses JWT tokens for authentication. Include the token in the `Authorization` header:

```
Authorization: Bearer <access_token>
```

---

## Authentication Endpoints

### Register User

Create a new user account.

**Endpoint:** `POST /api/v1/auth/register`

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

**Password Requirements:**
- At least 8 characters
- At least one number
- Both uppercase and lowercase letters
- At least one special character (!@#$%^&*()_+-=[]{}|;:,.<>?)

**Response (201):**
```json
{
  "message": "User registered. Please check email for verification link.",
  "user_id": "uuid-string"
}
```

**Errors:**
- `400`: Email already registered
- `422`: Invalid password requirements

---

### Login

Authenticate and receive access tokens.

**Endpoint:** `POST /api/v1/auth/login`

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

**Response (200):**
```json
{
  "access_token": "eyJhbGc...",
  "refresh_token": "eyJhbGc...",
  "token_type": "bearer"
}
```

**Errors:**
- `401`: Invalid email or password
- `403`: Email not verified

---

### Refresh Token

Refresh an expired access token.

**Endpoint:** `POST /api/v1/auth/refresh`

**Request Body:**
```json
{
  "refresh_token": "eyJhbGc..."
}
```

**Response (200):**
```json
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer"
}
```

**Errors:**
- `401`: Invalid or expired refresh token

---

### Verify Email

Verify user's email address.

**Endpoint:** `GET /api/v1/auth/verify-email/{token}`

**Path Parameters:**
- `token`: Verification token from email

**Response (200):**
```json
{
  "message": "Email verified successfully"
}
```

---

### Forgot Password

Request a password reset email.

**Endpoint:** `POST /api/v1/auth/forgot-password`

**Request Body:**
```json
{
  "email": "user@example.com"
}
```

**Response (200):**
```json
{
  "message": "If the email is registered, a password reset link has been sent."
}
```

---

### Reset Password

Reset password using reset token.

**Endpoint:** `POST /api/v1/auth/reset-password/{token}`

**Path Parameters:**
- `token`: Reset token from email

**Request Body:**
```json
{
  "password": "NewSecurePass123!"
}
```

**Response (200):**
```json
{
  "message": "Password reset successfully"
}
```

---

### Get Current User

Get profile of authenticated user.

**Endpoint:** `GET /api/v1/auth/me`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response (200):**
```json
{
  "id": "uuid-string",
  "email": "user@example.com",
  "is_verified": true,
  "created_at": "2024-01-01T00:00:00+00:00",
  "conversion_count": 5
}
```

---

### Logout

Invalidate current token.

**Endpoint:** `POST /api/v1/auth/logout`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response (200):**
```json
{
  "message": "Successfully logged out"
}
```

---

## Upload Endpoints

### Upload File

Upload a JAR/ZIP file for conversion.

**Endpoint:** `POST /api/v1/upload`

**Content-Type:** `multipart/form-data`

**Request:**
- `file`: JAR or ZIP file (max 100MB)

**Response (201):**
```json
{
  "job_id": "uuid-string",
  "original_filename": "my-mod.jar",
  "file_size": 1048576,
  "content_type": "application/java-archive",
  "message": "File 'my-mod.jar' uploaded successfully"
}
```

**Errors:**
- `400`: Invalid file type
- `413`: File too large
- `500`: Upload failed

---

### Initialize Chunked Upload

Start a chunked upload for large files.

**Endpoint:** `POST /api/v1/upload/chunked/init`

**Query Parameters:**
- `filename`: Original filename
- `total_size`: Total file size in bytes
- `content_type`: Content type (optional)

**Response (200):**
```json
{
  "upload_id": "uuid-string",
  "chunk_size": 5242880,
  "total_size": 52428800,
  "message": "Chunked upload initialized. Upload chunks using /chunked/{upload_id}"
}
```

---

### Upload Chunk

Upload a file chunk.

**Endpoint:** `POST /api/v1/upload/chunked/{upload_id}`

**Path Parameters:**
- `upload_id`: Upload session ID from init

**Query Parameters:**
- `chunk_index`: Zero-based chunk index

**Content-Type:** `multipart/form-data`
- `chunk`: Binary chunk data

**Response (200):**
```json
{
  "upload_id": "uuid-string",
  "chunk_index": 0,
  "chunks_received": 1,
  "message": "Chunk 0 received"
}
```

---

### Complete Chunked Upload

Finish chunked upload and process file.

**Endpoint:** `POST /api/v1/upload/chunked/{upload_id}/complete`

**Path Parameters:**
- `upload_id`: Upload session ID

**Response (201):**
```json
{
  "job_id": "uuid-string",
  "original_filename": "my-mod.jar",
  "file_size": 10485760,
  "content_type": "application/java-archive",
  "message": "File 'my-mod.jar' uploaded and assembled successfully"
}
```

---

### Get Upload Status

Check status of an uploaded file.

**Endpoint:** `GET /api/v1/upload/{job_id}`

**Path Parameters:**
- `job_id`: Job ID from upload response

**Response (200):**
```json
{
  "job_id": "uuid-string",
  "status": "completed",
  "progress": 100,
  "message": "File processed successfully"
}
```

**Status values:** `pending`, `uploading`, `completed`, `failed`

---

### Cancel Upload

Cancel an in-progress upload.

**Endpoint:** `DELETE /api/v1/upload/{job_id}`

**Path Parameters:**
- `job_id`: Job ID to cancel

**Response (200):**
```json
{
  "message": "Upload job 'uuid-string' cancelled and files cleaned up"
}
```

---

## Jobs Endpoints

### Create Job

Start a new conversion job.

**Endpoint:** `POST /api/v1/jobs`

**Request Body:**
```json
{
  "file_path": "/path/to/uploaded/file.jar",
  "original_filename": "my-mod.jar",
  "options": {
    "conversion_mode": "standard",
    "target_version": "1.20",
    "output_format": "mcaddon",
    "webhook_url": "https://your-server.com/webhook"
  }
}
```

**Options:**
- `conversion_mode`: `simple`, `standard`, or `complex`
- `target_version`: `1.19`, `1.20`, or `1.21`
- `output_format`: `mcaddon` or `zip`
- `webhook_url`: URL for completion notification (optional)

**Response (201):**
```json
{
  "job_id": "uuid-string",
  "message": "Job created successfully. Use GET /api/v1/jobs/{job_id} to track progress."
}
```

---

### List Jobs

Get paginated list of user's jobs.

**Endpoint:** `GET /api/v1/jobs`

**Query Parameters:**
- `limit`: Max jobs to return (1-100, default: 50)
- `offset`: Jobs to skip (default: 0)

**Response (200):**
```json
{
  "jobs": [
    {
      "job_id": "uuid-string",
      "user_id": "user-uuid",
      "original_filename": "my-mod.jar",
      "status": "completed",
      "progress": 100,
      "current_step": "packaging",
      "result_url": "https://...",
      "error_message": null,
      "created_at": "2024-01-01T00:00:00",
      "updated_at": "2024-01-01T00:10:00",
      "completed_at": "2024-01-01T00:10:00"
    }
  ],
  "total": 1,
  "limit": 50,
  "offset": 0
}
```

---

### Get Job Status

Get detailed status of a conversion job.

**Endpoint:** `GET /api/v1/jobs/{job_id}`

**Path Parameters:**
- `job_id`: Job UUID

**Response (200):**
```json
{
  "job_id": "uuid-string",
  "user_id": "user-uuid",
  "original_filename": "my-mod.jar",
  "status": "completed",
  "progress": 100,
  "current_step": "packaging",
  "result_url": "https://...",
  "error_message": null,
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:10:00",
  "completed_at": "2024-01-01T00:10:00"
}
```

**Status values:** `pending`, `processing`, `completed`, `failed`, `cancelled`

**Errors:**
- `404`: Job not found
- `403`: Not authorized to access this job

---

### Cancel Job

Cancel a pending or processing job.

**Endpoint:** `DELETE /api/v1/jobs/{job_id}`

**Path Parameters:**
- `job_id`: Job UUID

**Response (200):**
```json
{
  "job_id": "uuid-string",
  "message": "Job 'uuid-string' cancelled successfully"
}
```

**Errors:**
- `400`: Cannot cancel completed or failed job
- `404`: Job not found

---

## API Keys

### Create API Key

Create a new API key for programmatic access.

**Endpoint:** `POST /api/v1/auth/api-keys`

**Request Body:**
```json
{
  "name": "My API Key"
}
```

**Response (201):**
```json
{
  "id": "uuid-string",
  "name": "My API Key",
  "prefix": "mpk_abc123",
  "api_key": "mpk_abc123xyz789...",
  "created_at": "2024-01-01T00:00:00+00:00"
}
```

**Note:** The full API key is only shown once - store it securely.

---

### List API Keys

List all API keys for your account.

**Endpoint:** `GET /api/v1/auth/api-keys`

**Response (200):**
```json
[
  {
    "id": "uuid-string",
    "name": "My API Key",
    "prefix": "mpk_abc123",
    "created_at": "2024-01-01T00:00:00+00:00",
    "last_used": "2024-01-02T00:00:00+00:00",
    "is_active": true
  }
]
```

---

### Revoke API Key

Delete an API key.

**Endpoint:** `DELETE /api/v1/auth/api-keys/{key_id}`

**Path Parameters:**
- `key_id`: API key ID

**Response (200):**
```json
{
  "message": "API key revoked"
}
```

---

## Webhooks

Configure webhooks to receive notifications when conversions complete.

### Webhook Payload

When a job completes, a POST request is sent to your configured webhook URL:

```json
{
  "job_id": "uuid-string",
  "status": "completed",
  "result_url": "https://...",
  "original_filename": "my-mod.jar",
  "completed_at": "2024-01-01T00:10:00"
}
```

### Setting Up Webhooks

Include `webhook_url` in the job options when creating a job:

```json
{
  "file_path": "/path/to/file.jar",
  "original_filename": "my-mod.jar",
  "options": {
    "webhook_url": "https://your-server.com/webhook"
  }
}
```

---

## Error Responses

All endpoints may return error responses in the following format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

**Common HTTP Status Codes:**

| Code | Description |
|------|-------------|
| 400 | Bad Request - Invalid input |
| 401 | Unauthorized - Invalid or missing token |
| 403 | Forbidden - Not authorized |
| 404 | Not Found - Resource doesn't exist |
| 413 | Payload Too Large - File too big |
| 422 | Unprocessable Entity - Validation failed |
| 500 | Internal Server Error |

---

## Rate Limits

API requests are rate-limited to ensure fair usage:

- **Authenticated requests**: 1000 requests per hour
- **Upload requests**: 100 per hour
- **Job creation**: 50 per hour

Rate limit headers are included in responses:
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1640995200
```

---

## SDKs and Libraries

### Python

```python
import requests

BASE_URL = "http://localhost:8080/api/v1"

# Login
response = requests.post(f"{BASE_URL}/auth/login", json={
    "email": "user@example.com",
    "password": "SecurePass123!"
})
tokens = response.json()
headers = {"Authorization": f"Bearer {tokens['access_token']}"}

# Upload
with open("mod.jar", "rb") as f:
    response = requests.post(
        f"{BASE_URL}/upload",
        files={"file": f},
        headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
```

### JavaScript/TypeScript

```typescript
const BASE_URL = "http://localhost:8080/api/v1";

async function login(email: string, password: string) {
  const response = await fetch(`${BASE_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  return response.json();
}

async function uploadFile(file: File, token: string) {
  const formData = new FormData();
  formData.append("file", file);
  
  const response = await fetch(`${BASE_URL}/upload`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: formData,
  });
  return response.json();
}
```

---

## Support

- **Documentation**: [docs.portkit.cloud](https://docs.portkit.cloud)
- **Discord**: [discord.gg/modporter](https://discord.gg/modporter)
- **GitHub Issues**: [github.com/anchapin/portkit/issues](https://github.com/anchapin/portkit/issues)