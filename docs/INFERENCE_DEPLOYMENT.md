# Self-Hosted LLM Inference Deployment

**Issue**: [#1203](https://github.com/anchapin/portkit/issues/1203) — Self-hosted LLM inference deployment: RunPod Flash + vLLM → SGLang

**Dependencies**:
- [#997](https://github.com/anchapin/portkit/issues/997) — Fine-tuning infrastructure (produces model weights before Phase 2)
- [#990](https://github.com/anchapin/portkit/issues/990) — LLM-powered AST→Bedrock translation (Phase 2 replaces hosted API call)
- [#1201](https://github.com/anchapin/portkit/issues/1201) — LangGraph migration (orchestration layer calling inference endpoint)

## Phases Overview

| Phase | Approach | Status | Notes |
|-------|----------|--------|-------|
| 1 | OpenRouter API → Claude Sonnet / Qwen3-Coder | **Current** | Zero infra, pay-per-token |
| 2 | RunPod Flash + vLLM | **Pending #997** | After fine-tuned model weights exist |
| 3 | SGLang vs vLLM benchmark | **Post-beta** | If SGLang wins, drop-in swap |

## Phase 1: OpenRouter API (Current Baseline)

Currently in production. No changes required.

**Providers**: OpenRouter with Claude Sonnet or Qwen3-Coder

**Configuration**:
```bash
LLM_PROVIDER=openrouter
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_API_KEY=your_openrouter_key
LLM_MODEL=anthropic/claude-3.5-sonnet
```

## Phase 2: RunPod Flash + vLLM

**Prerequisite**: #997 produces fine-tuned model weights (~500+ conversion pairs)

### Why RunPod Flash?

- **Python-native**: Works directly with existing Celery/Python stack (no TypeScript bridge)
- **Scale-to-zero**: Pay only during active conversions — critical before sustained traffic
- **FlashBoot cold starts**: ~10-15s after first load (~52s initial). Acceptable for async batch conversion jobs
- **Auto-scale 0→N**: Handles burst submissions without manual capacity management

### Why vLLM?

- **PagedAttention**: Handles long-context Java→Bedrock conversion prompts efficiently
- **14-24x throughput** over raw HuggingFace Transformers
- **OpenAI-compatible API**: Minimal changes to existing LLM call layer
- **Battle-tested**: Large community, active development

### Target Hardware

QLoRA-merged Qwen3-Coder-7B or DeepSeek-Coder-7B runs on a single RTX 4090 (24GB VRAM).

- RunPod RTX 4090 Flex: ~$0.007/min ($0.42/hr)
- Typical mod section conversion: 10-30s of inference
- With scale-to-zero: near-zero cost during idle

### Deployment Steps

#### 1. Set Up RunPod Account and Endpoint

```python
# Using RunPod Flash SDK
from runpod import Endpoint, GpuType

@Endpoint(
    name="portkit-inference",
    gpu=GpuType.NVIDIA_GEFORCE_RTX_4090,
    workers_min=0,
    workers_max=5,
    dependencies=["vllm"]
)
async def convert(prompt: str) -> dict:
    # vLLM handles inference — Flash manages worker lifecycle
    from vllm import LLM, SamplingParams

    llm = LLM(model="你的-model-name")
    sampling_params = SamplingParams(temperature=0.1, max_tokens=4096)
    outputs = llm.generate(prompt, sampling_params)
    return {"output": outputs[0].outputs[0].text}
```

#### 2. Store Model Weights

Store fine-tuned weights in private HuggingFace Hub repo:
```bash
# Push after QLoRA merge
from transformers import AutoModelForCausalLM
model.push_to_hub("your-org/portkit-coder-7B", private=True)
```

#### 3. Configure Environment Variables

```bash
# Mode: cloud | self_hosted | hybrid (self-hosted with cloud fallback)
INFERENCE_MODE=hybrid
INFERENCE_PROVIDER=runpod_flash

# RunPod configuration
RUNPOD_ENDPOINT_ID=your_endpoint_id
RUNPOD_API_KEY=your_runpod_api_key

# Model (stored in private HF Hub)
SELF_HOSTED_MODEL=your-org/portkit-coder-7B
```

#### 4. Celery Task Integration

The inference task runs via Celery for async processing:

```python
# In backend/src/services/celery_tasks.py
@shared_task(name="services.celery_tasks.llm_inference_task")
def llm_inference_task(
    messages: List[Dict[str, str]],
    model: str = None,
    temperature: float = 0.1,
    max_tokens: int = 4096,
) -> Dict[str, Any]:
    """
    Self-hosted LLM inference via RunPod Flash.

    Architecture:
    - Celery worker picks up task from Redis queue
    - Calls RunPod Flash endpoint (vLLM + fine-tuned model)
    - Result stored in Redis, returned to client
    """
    from utils.self_hosted_inference import SelfHostedInferenceClient, InferenceConfig

    config = InferenceConfig(
        provider=InferenceProvider.RUNPOD_FLASH,
        mode=InferenceMode.SELF_HOSTED,
        model_name=model,
    )
    client = SelfHostedInferenceClient(config)

    result = asyncio.run(
        client.complete(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    )

    return {
        "success": result.success,
        "content": result.content,
        "model": result.model,
        "provider": result.provider,
        "duration": result.duration,
        "cost": result.cost,
        "error": result.error,
    }
```

**Usage**:
```python
# Enqueue inference task
result = llm_inference_task.delay(
    messages=[{"role": "user", "content": "Convert this Java..."}],
    model="portkit-coder-7B",
    temperature=0.1,
)
# Non-blocking get
response = result.get(timeout=300)
```

### Cold Start Optimization

Target: <15s after first load

```python
# Warmup configuration
config = InferenceConfig(
    warmup_requests=1,
    keep_alive=300,  # seconds
    scale_to_zero=True,
)
```

## Phase 3: SGLang Benchmark

**When**: Post-beta, after Phase 2 is stable

### Why SGLang?

- **RadixAttention**: 85-95% KV cache hit rate on shared context prefixes
- **~29% faster** than vLLM on H100 batch workloads
- **PortKit's prompts**: Share long system-prompt prefixes (Bedrock docs, conversion patterns) — RadixAttention likely wins here

### Benchmark Plan

1. Deploy both vLLM and SGLang with same model weights
2. Run conversion batch through each with PortKit's actual prompt shapes
3. Measure:
   - Tokens/second throughput
   - KV cache hit rate
   - Cold start latency
   - Cost per conversion

### Drop-In Swap

Both SGLang and vLLM expose OpenAI-compatible APIs:
```bash
# If SGLang wins
INFERENCE_PROVIDER=sglang
SGLANG_URL=https://your-sglang-endpoint
```

## Cost Comparison

| Approach | Per-Conversion Cost | Quality | Latency |
|----------|-------------------|---------|---------|
| GPT-4o API | ~$0.10–0.50 | High | 5–15s |
| Claude API | ~$0.15–0.75 | High | 5–20s |
| Self-hosted Qwen3-7B (fine-tuned) | ~$0.01–0.03 | Medium→High | 2–5s |
| Self-hosted Qwen3-32B (fine-tuned) | ~$0.03–0.08 | High | 5–10s |

## Also Worth Evaluating: Modal

Modal runs GPU functions with GPU Memory Snapshots that reduce cold start overhead, potentially cheaper per-request (~$0.004) than RunPod. Worth a side-by-side benchmark once model weights exist.

## Acceptance Criteria

- [ ] Phase 1 (OpenRouter): documented as current baseline in README / architecture docs
- [ ] Phase 2 spike: benchmark vLLM on RTX 4090 with QLoRA-merged 7B model once #997 produces weights
- [ ] Phase 2 deploy: RunPod Flash endpoint serving the fine-tuned model, called via Celery task queue
- [ ] Celery task queue integration confirmed (not direct API-to-inference call)
- [ ] Model weights stored in private HuggingFace Hub repo with access controls
- [ ] Phase 3 benchmark: SGLang vs vLLM on PortKit conversion prompt shapes (batch, shared system prefixes)
- [ ] Cold start latency measured and documented (target: <15s after first load)
- [ ] Cost per conversion estimated and tracked at each phase

## References

- [RunPod Flash](https://github.com/runpod/flash)
- [vLLM](https://github.com/vllm-project/vllm)
- [SGLang](https://github.com/sgl-project/sglang)
- [vLLM vs SGLang Comparison](https://docs.endpointscale.com/sglang)
- [RunPod Documentation](https://docs.runpod.io/)