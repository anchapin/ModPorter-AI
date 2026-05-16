# AI Model Configuration Guide

This document describes the AI models used for Java to Bedrock Minecraft mod conversion, configuration options, and reproducibility settings.

## Overview

PortKit uses frontier AI models via [OpenRouter](https://openrouter.ai) for conversion. The system supports multiple models with automatic fallback to ensure reliable conversions.

## Supported Models

### Premium Tier Models

| Model Key | Provider Model ID | Provider | Max Tokens | Temperature |
|-----------|------------------|----------|-------------|-------------|
| `deepseek-v4-pro` | `deepseek/deepseek-chat-v3.1` | OpenRouter | 8192 | 0.1 |
| `deepseek-v4-flash` | `deepseek/deepseek-chat-v3-0324` | OpenRouter | 8192 | 0.1 |
| `kimi-k2` | `moonshotai/kimi-k2` | OpenRouter | 8192 | 0.1 |
| `glm-5` | `thudm/glm-4-32b` | OpenRouter | 8192 | 0.1 |

### Default Fallback Order

When a model fails or is unavailable, the system tries models in this order:

1. `deepseek-v4-pro` (default, highest quality)
2. `kimi-k2` (alternative high quality)
3. `deepseek-v4-flash` (faster, lower cost)
4. `glm-5` (budget option)

## Environment Variables

### Required

| Variable | Description |
|----------|-------------|
| `OPENROUTER_API_KEY` | API key from [OpenRouter](https://openrouter.ai/keys) |

### Optional

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENROUTER_API_KEY` | Required | Primary API key for premium conversion |

## Reproducibility Settings

### Temperature

All models use `temperature: 0.1` for reproducible outputs. This low temperature setting ensures consistent conversion results across multiple runs.

### Max Tokens

All models are configured with `max_tokens: 8192`, providing sufficient context for complex mod conversions.

### Why Low Temperature?

The conversion task requires precise, deterministic outputs. High temperature can cause:
- Inconsistent block state mappings
- Variable item registry naming
- Different script generation approaches

## Version Pinning

### Pinning to a Specific Model

To use a specific model instead of the fallback chain:

```python
from mmsd.premium_client import PortKitPremium

client = PortKitPremium(model="deepseek-v4-pro")
result = client.convert(instruction="My mod", java_source=java_code)
```

### Pinning to a Specific Provider Model

For absolute reproducibility, pin to both the model key and the provider model ID:

```python
MODEL_CONFIGS = {
    "deepseek-v4-pro": {
        "model_id": "deepseek/deepseek-chat-v3.1",
        "provider": "openrouter",
        "max_tokens": 8192,
        "temperature": 0.1,
    },
}
```

### Freezing Model Configuration

To lock your environment to specific versions:

1. Create a `model-config.json` in your project:

```json
{
  "model": "deepseek-v4-pro",
  "fallback_models": ["kimi-k2", "deepseek-v4-flash"],
  "temperature": 0.1,
  "max_tokens": 8192
}
```

2. Load this configuration at startup:

```python
import json

with open("model-config.json") as f:
    config = json.load(f)

client = PortKitPremium(
    model=config["model"],
    fallback_models=config.get("fallback_models")
)
```

## Cost Estimation

Approximate pricing per 1M tokens via OpenRouter:

| Model | Input Cost | Output Cost |
|-------|------------|-------------|
| `deepseek-v4-pro` | $0.55 | $2.19 |
| `deepseek-v4-flash` | $0.27 | $1.10 |
| `kimi-k2` | $0.60 | $2.50 |
| `glm-5` | $0.50 | $1.50 |

Note: Prices are approximate. Check [OpenRouter pricing](https://openrouter.ai/pricing) for current rates.

## Troubleshooting

### Model Unavailable

If you see `Unknown model: <model_name>`:
- Verify the model key is spelled correctly
- Check that `OPENROUTER_API_KEY` is set and valid
- Ensure your OpenRouter account has access to the model

### Inconsistent Results

For consistent results:
1. Set `temperature=0.1` explicitly
2. Pin to a specific model instead of using fallback
3. Ensure Java source code is identical between runs
4. Check that instruction text is exactly the same

### Rate Limiting

OpenRouter applies rate limits. The system automatically retries with exponential backoff (`max_retries: 3`). For higher limits, upgrade your OpenRouter plan.

## Related Documentation

- [ARCHITECTURE.md](./ARCHITECTURE.md) - System architecture
- [AI-AGENT-BEST-PRACTICES.md](./AI-AGENT-BEST-PRACTICES.md) - AI agent guidelines
- [migrate-to-z-ai.md](./migrate-to-z-ai.md) - Migration guide