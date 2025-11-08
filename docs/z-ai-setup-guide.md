# Z.AI Integration Setup Guide

## Overview

This guide explains how to set up and configure Z.AI as the primary LLM backend for ModPorter-AI's AI engine. Z.AI provides high-quality GLM models with no additional cost for existing Pro plan subscribers.

## Prerequisites

- Active Z.AI Pro plan subscription
- Z.AI API key (available from your Z.AI dashboard)

## Configuration

### 1. Repository Variables

Add the following repository variables (Settings → Secrets and variables → Actions → Variables):

```
Z_AI_MODEL=glm-4-plus
Z_AI_BASE_URL=https://api.z.ai/v1
Z_AI_MAX_RETRIES=3
Z_AI_TIMEOUT=300
Z_AI_TEMPERATURE=0.1
Z_AI_MAX_TOKENS=4000
```

### 2. Repository Secrets

Add the following repository secret (Settings → Secrets and variables → Actions → New repository secret):

```
Z_AI_API_KEY=your_z_ai_api_key_here
```

**Important**: The secret should be named exactly `Z_AI_API_KEY` for the CI/CD pipeline to detect and configure it properly.

### 3. Local Development

For local development, set these environment variables:

```bash
# Enable Z.AI as primary backend
export USE_Z_AI=true

# Z.AI Configuration
export Z_AI_API_KEY=your_api_key_here
export Z_AI_MODEL=glm-4-plus
export Z_AI_BASE_URL=https://api.z.ai/v1

# Optional configuration
export Z_AI_MAX_RETRIES=3
export Z_AI_TIMEOUT=300
export Z_AI_TEMPERATURE=0.1
export Z_AI_MAX_TOKENS=4000

# Disable Ollama fallback (optional)
export USE_OLLAMA=false
```

Or create a `.env` file:

```env
USE_Z_AI=true
Z_AI_API_KEY=your_api_key_here
Z_AI_MODEL=glm-4-plus
Z_AI_BASE_URL=https://api.z.ai/v1
USE_OLLAMA=false
```

## Supported Models

Z.AI supports several GLM models. Recommended models for ModPorter-AI:

- **glm-4-plus** (default): Best balance of performance and quality
- **glm-4**: High-quality model for complex analysis
- **glm-3-turbo**: Fast responses for simple tasks

## Backend Priority System

The AI engine automatically selects the best available backend in this order:

1. **Z.AI** (if `USE_Z_AI=true` and `Z_AI_API_KEY` is set)
2. **Ollama** (if `USE_OLLAMA=true` and service is available)
3. **OpenAI** (if `OPENAI_API_KEY` is set)

## Testing the Integration

### 1. Run the Z.AI integration tests:

```bash
cd ai-engine
python -m pytest tests/integration/test_z_ai_integration.py -v
```

### 2. Test with the AI engine:

```python
from ai_engine.utils.rate_limiter import get_llm_backend

# This will automatically use Z.AI if configured
llm = get_llm_backend()
response = llm.invoke("Analyze this Java code for mod compatibility")
print(response.content)
```

### 3. Test with CrewAI workflows:

```python
from crewai import Agent, Task, Crew
from ai_engine.utils.rate_limiter import get_llm_backend

# Z.AI LLM will be automatically selected
llm = get_llm_backend()

analyzer = Agent(
    role='Java Code Analyzer',
    goal='Analyze Minecraft mod compatibility',
    backstory='Expert in Java mod development and compatibility issues',
    llm=llm
)

task = Task(
    description='Analyze the provided Java code for mod compatibility',
    agent=analyzer,
    expected_output='Compatibility analysis report'
)

crew = Crew(agents=[analyzer], tasks=[task])
result = crew.kickoff()
```

## Performance Characteristics

### Expected Performance

- **Response Time**: 2-5 seconds for typical analysis tasks
- **Quality**: Comparable to GPT-4 for code analysis tasks
- **Rate Limits**: 50 requests per minute, 40,000 tokens per minute
- **Reliability**: 99.9% uptime according to Z.AI SLA

### Cost Benefits

- **Zero Additional Cost**: Included in Z.AI Pro plan
- **No Setup Fees**: Immediate activation
- **High Quality**: Enterprise-grade GLM models

## Troubleshooting

### Common Issues

#### 1. "Z.AI API key is required" error

**Cause**: Missing or empty `Z_AI_API_KEY` environment variable.

**Solution**: Ensure the secret is properly configured in GitHub repository settings.

#### 2. "Failed to initialize Z.AI backend" error

**Cause**: Network issues or incorrect API base URL.

**Solution**: Check internet connectivity and verify `Z_AI_BASE_URL` setting.

#### 3. Rate limiting errors

**Cause**: Exceeding Z.AI rate limits.

**Solution**: The rate limiter handles this automatically, but consider reducing concurrent requests if issues persist.

#### 4. Model not found error

**Cause**: Invalid model name specified.

**Solution**: Use one of the supported models: `glm-4-plus`, `glm-4`, or `glm-3-turbo`.

### Debug Mode

Enable debug logging to troubleshoot issues:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Test Z.AI directly
from ai_engine.utils.rate_limiter import create_z_ai_llm
llm = create_z_ai_llm()
response = llm.invoke("Test message")
```

### Fallback Behavior

If Z.AI fails, the system automatically falls back to:

1. **Ollama** (if enabled and available)
2. **OpenAI** (if API key is configured)

This ensures continued operation even if Z.AI is temporarily unavailable.

## Monitoring and Metrics

### Key Metrics to Monitor

- **Success Rate**: Percentage of successful Z.AI API calls
- **Response Time**: Average time per request
- **Token Usage**: Total tokens consumed
- **Error Rate**: Percentage of failed requests

### CI/CD Integration

The CI pipeline automatically:

- Detects Z.AI API key availability
- Configures Z.AI as primary backend when available
- Falls back to Ollama when Z.AI is not configured
- Reports LLM backend status in test results

## Migration from Other Backends

### From OpenAI

1. Add `Z_AI_API_KEY` secret to repository
2. Set `USE_Z_AI=true` in environment
3. Set `USE_OLLAMA=false` (optional)
4. Run tests to verify functionality

### From Ollama

1. Add `Z_AI_API_KEY` secret to repository
2. Set `USE_Z_AI=true` in environment
3. Z.AI will automatically become primary backend
4. Ollama remains as fallback

## API Reference

### ZAIConfig Class

```python
@dataclass
class ZAIConfig:
    api_key: str = ""
    model: str = "glm-4-plus"
    base_url: str = "https://api.z.ai/v1"
    max_retries: int = 3
    timeout: int = 300
    temperature: float = 0.1
    max_tokens: int = 4000
```

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `USE_Z_AI` | No | `false` | Enable Z.AI backend |
| `Z_AI_API_KEY` | Yes | - | Your Z.AI API key |
| `Z_AI_MODEL` | No | `glm-4-plus` | Model to use |
| `Z_AI_BASE_URL` | No | `https://api.z.ai/v1` | API base URL |
| `Z_AI_MAX_RETRIES` | No | `3` | Max retry attempts |
| `Z_AI_TIMEOUT` | No | `300` | Request timeout (seconds) |
| `Z_AI_TEMPERATURE` | No | `0.1` | Sampling temperature |
| `Z_AI_MAX_TOKENS` | No | `4000` | Max tokens per response |

## Support

For Z.AI related issues:

- Check the [Z.AI Documentation](https://docs.z.ai)
- Review the [Z.AI API Reference](https://api.z.ai/docs)
- Contact Z.AI support for API-specific issues

For ModPorter-AI integration issues:

- Create an issue in the [GitHub repository](https://github.com/anchapin/ModPorter-AI)
- Check existing issues for similar problems
- Review CI/CD logs for detailed error information
