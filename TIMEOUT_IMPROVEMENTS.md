# Backend Timeout Improvements for Rate Limiting

## Summary
Updated the backend timeout configurations to properly handle OpenAI API rate limiting scenarios where conversions can take 20+ minutes due to automatic retry delays.

## Changes Made

### 1. Extended AI Engine Timeout Configuration
```python
# Before: 5 minutes timeout
AI_ENGINE_TIMEOUT = httpx.Timeout(300.0)

# After: 30 minutes timeout (configurable)
AI_ENGINE_TIMEOUT = httpx.Timeout(float(os.getenv("AI_ENGINE_TIMEOUT", "1800.0")))
```

### 2. Separate Health Check Timeout
```python
# Added dedicated health check timeout
AI_ENGINE_HEALTH_TIMEOUT = httpx.Timeout(float(os.getenv("AI_ENGINE_HEALTH_TIMEOUT", "30.0")))
```

### 3. Extended Polling Configuration
```python
# Before: 120 polls * 5s = 10 minutes maximum
max_polls = 120

# After: Configurable based on MAX_CONVERSION_TIME
max_polls = MAX_CONVERSION_TIME // 5  # 360 polls * 5s = 30 minutes default
```

### 4. Enhanced Progress Logging
```python
# Added progress logging every 60 seconds
if poll_count % 12 == 0:  # Every 12 polls = 60 seconds
    elapsed_minutes = (poll_count * 5) / 60
    logger.info(f"Job {job_id} still processing after {elapsed_minutes:.1f} minutes, status: {status}")
```

### 5. Improved Error Messages
```python
# Before: Generic timeout message
"error": "Polling for job status timed out."

# After: Contextual timeout message
"error": f"Conversion timed out after {max_polls * 5 / 60:.1f} minutes. This may be due to OpenAI API rate limiting. Please try again later."
```

## Environment Variables Added

### .env.example Updates
```bash
# File Upload Limits
MAX_CONVERSION_TIME=1800  # Increased from 600 to 1800 seconds (30 minutes)

# AI Engine Timeouts (in seconds)
AI_ENGINE_TIMEOUT=1800           # 30 minutes for conversions
AI_ENGINE_HEALTH_TIMEOUT=30      # 30 seconds for health checks
```

## Rate Limiting Context

### Why These Changes Are Needed
1. **OpenAI API Rate Limiting**: The rate limiter automatically retries with exponential backoff
2. **Retry Delays**: Can add 1-60 seconds per retry, with up to 3 retries per request
3. **Multiple LLM Calls**: Each conversion makes 6+ LLM calls across different agents
4. **Cumulative Delays**: Total conversion time can exceed 20-30 minutes under rate limiting

### Rate Limiting Behavior Observed
```
2025-07-09 04:19:48,337 - httpx - INFO - HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 429 Too Many Requests"
2025-07-09 04:19:48,337 - openai._base_client - INFO - Retrying request to /chat/completions in 11.826000 seconds
```

## Testing Results

### Before Changes
- Conversions failed after 5-10 minutes with "AI engine not available"
- Health checks were timing out during rate limiting
- No visibility into long-running conversions

### After Changes
- Conversions can run for up to 30 minutes
- Health checks work properly with dedicated timeout
- Progress logging provides visibility every minute
- Clear error messages explain rate limiting context

## Benefits

1. **Reliability**: Conversions now complete successfully even with rate limiting
2. **Visibility**: Progress logging shows conversion is still active
3. **Configurability**: Timeouts can be adjusted via environment variables
4. **User Experience**: Clear error messages explain delays
5. **Robustness**: Separate health check timeout prevents false negatives

## Usage

The system now automatically handles rate limiting scenarios without user intervention. Users will see:
- Progress updates during long conversions
- Informative error messages if timeouts occur
- Successful completion even with significant OpenAI delays

## Configuration

To adjust timeouts, set environment variables:
```bash
# For very high rate limiting scenarios
export AI_ENGINE_TIMEOUT=3600          # 1 hour
export MAX_CONVERSION_TIME=3600         # 1 hour

# For faster environments
export AI_ENGINE_TIMEOUT=900           # 15 minutes
export MAX_CONVERSION_TIME=900          # 15 minutes
```