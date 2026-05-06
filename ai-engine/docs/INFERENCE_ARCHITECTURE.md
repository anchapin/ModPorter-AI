# Self-Hosted LLM Inference Architecture

**Issue:** #1203 - Self-hosted LLM inference deployment: RunPod Flash + vLLM → SGLang
**Milestone:** M6: Beta Iteration (due 2026-05-15)
**Dependencies:** #997 (Fine-tuning), #990 (LLM pipeline)

## Overview

PortKit's AI engine transitions from hosted API inference (OpenRouter) to self-hosted inference after the fine-tuned model from #997 is ready. This document outlines the phased inference strategy and deployment architecture.

## Phased Inference Strategy

### Phase 1 — Now (Baseline)
**OpenRouter API → Claude Sonnet or Qwen3-Coder**
- Zero infrastructure setup
- Pay per token — cost scales with usage
- Iterate fast on prompts and output schemas
- **Status:** Documented as current baseline

### Phase 2 — After #997 (~500+ conversion pairs)
**RunPod Flash + vLLM → QLoRA-merged fine-tuned model**

```
API request
    ↓
Redis job queue (Celery already wired)
    ↓
Celery worker
    ↓
RunPod Flash endpoint (vLLM + QLoRA-merged fine-tuned model)
    ↓
Result stored in Tigris/Redis
    ↓
API returns result to client
```

**Why RunPod Flash:**
- Python-native — works directly with existing Celery/Python stack
- Scale-to-zero — pay only during active conversions
- FlashBoot cold starts — ~10-15s after first load
- Auto-scale 0→N — handles burst submissions

**Target hardware:** QLoRA-merged Qwen3-Coder-7B on single RTX 4090 (24GB VRAM)
- RunPod RTX 4090 Flex: ~$0.007/min ($0.42/hr)
- Typical mod section conversion: 10-30s of inference

### Phase 3 — Post-beta (Optimization)
**Benchmark SGLang vs vLLM on PortKit's actual prompt shapes**

SGLang advantages for PortKit:
- RadixAttention: 85-95% KV cache hit rate on shared context prefixes
- PortKit's conversion prompts share long system-prompt prefixes (Bedrock docs, conversion patterns)
- ~29% faster than vLLM on H100 batch workloads

## Inference Server Comparison

| Server | Best for | Notes |
|--------|----------|-------|
| **vLLM** | High-concurrency API, first deployment | PagedAttention, 14-24x over raw HF Transformers, OpenAI-compatible |
| **SGLang** | Agent pipelines, multi-turn, batch jobs | RadixAttention = 85-95% KV cache hit rate on shared prefixes |
| **TGI** | — | Entered maintenance mode Dec 2025 — do not start new projects |
| **Triton+TensorRT** | NVIDIA-only enterprise | Overkill for PortKit's current stage |

## Configuration

### Environment Variables

```bash
# Inference mode: cloud (default) | self_hosted | hybrid
INFERENCE_MODE=cloud

# Provider: openrouter | runpod_flash | sglang | vllm | ollama
INFERENCE_PROVIDER=openrouter

# Self-hosted endpoint (SGLang/vLLM)
SELF_HOSTED_ENDPOINT=https://your-sglang-endpoint.com/v1
SELF_HOSTED_API_KEY=your-api-key
SELF_HOSTED_MODEL=Qwen3-Coder-7B

# RunPod Flash (Phase 2)
RUNPOD_ENDPOINT_ID=your-endpoint-id
RUNPOD_API_KEY=your-runpod-key
RUNPOD_ENDPOINT=https://api.runpod.io/v2/your-endpoint-id

# SGLang (Phase 3)
SGLANG_URL=http://localhost:30000
VLLM_URL=http://localhost:8000

# Performance tuning
INFERENCE_TIMEOUT=120
SCALE_TO_ZERO=true
INFERENCE_WARMUP_REQUESTS=1
INFERENCE_KEEP_ALIVE=300
```

### Usage in Code

```python
from utils.self_hosted_inference import SelfHostedInferenceClient, InferenceRouter

# Direct client
client = SelfHostedInferenceClient()
result = asyncio.run(client.complete(
    messages=[{"role": "user", "content": "Convert this Java mod..."}],
    model="Qwen3-Coder-7B"
))

# Router with automatic fallback
router = get_inference_router()
result = asyncio.run(router.complete(messages=[...]))
```

## Celery Task Integration

```python
from utils.self_hosted_inference import create_inference_celery_task

inference_task = create_inference_celery_task()

# Async call from conversion pipeline
result = inference_task.delay(
    messages=[{"role": "user", "content": prompt}],
    model="Qwen3-Coder-7B"
)
output = result.get(timeout=300)
```

## Cost Estimation

### Phase 1 (Cloud)
- Claude 3.5 Sonnet: ~$0.003/1K input + $0.015/1K output
- Typical conversion: ~$0.10-0.50 per mod

### Phase 2 (Self-hosted)
- RunPod RTX 4090 Flex: $0.42/hr
- ~14 tokens/sec throughput
- Scale-to-zero: near-zero cost during idle
- Estimated: ~$0.01-0.03 per conversion

### Phase 3 (SGLang optimization)
- 29% faster throughput
- Better KV cache utilization
- Further cost reduction expected

## Acceptance Criteria

- [x] Phase 1 (OpenRouter): documented as current baseline
- [ ] Phase 2 spike: benchmark vLLM on RTX 4090 with QLoRA-merged 7B model (blocked on #997)
- [ ] Phase 2 deploy: RunPod Flash endpoint serving fine-tuned model
- [ ] Celery task queue integration confirmed
- [ ] Model weights in private HuggingFace Hub repo
- [ ] Phase 3 benchmark: SGLang vs vLLM on PortKit prompt shapes
- [ ] Cold start latency measured (target: <15s after first load)
- [ ] Cost per conversion estimated and tracked

## References

- [RunPod Flash](https://github.com/runpod/flash)
- [vLLM](https://github.com/vllm-project/vllm)
- [SGLang](https://github.com/sgl-project/sglang)