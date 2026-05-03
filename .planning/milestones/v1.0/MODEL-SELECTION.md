# AI Model Selection & Evaluation

**Date**: 2026-03-14  
**Phase**: 1.1 - AI Model Deployment  
**Task**: 1.1.1 - Model Selection & Evaluation  

---

## Evaluation Criteria

| Criterion | Weight | Description |
|-----------|--------|-------------|
| **Code Translation Quality** | 30% | HumanEval score, code-specific benchmarks |
| **Context Length** | 15% | Maximum tokens for input (Java code + context) |
| **Cost** | 20% | Cost per conversion (target: <$0.50) |
| **Latency** | 15% | Response time (target: <30 seconds) |
| **Availability** | 10% | Uptime, reliability |
| **Ease of Integration** | 10% | API quality, documentation, SDK support |

---

## Model Comparison Matrix

### Primary Candidates

| Model | HumanEval | Context | Cost/1M tokens | Cost/Conversion* | Latency | Deployment |
|-------|-----------|---------|----------------|------------------|---------|------------|
| **CodeT5+ 16B** | ~75% | 512 tokens | $0 (self-hosted) | $0.05 (GPU time) | 5-15s | Modal GPU |
| **DeepSeek-Coder-V2** | 82.1% | 128K tokens | $0.14 (input) | $0.10-0.20 | 3-10s | API |
| **CodeLlama-34B** | 72.5% | 16K tokens | $0.80 | $0.50-0.80 | 5-15s | API/GPU |
| **StarCoder2-15B** | 70.3% | 16K tokens | $0.40 | $0.30-0.50 | 3-10s | API/GPU |

*Cost per conversion estimated at ~50K tokens (10K input Java + 40K output Bedrock + context)

### Backup Candidates

| Model | HumanEval | Context | Cost/1M tokens | Cost/Conversion | Latency | Deployment |
|-------|-----------|---------|----------------|-----------------|---------|------------|
| **GPT-4 Turbo** | 87.1% | 128K tokens | $10.00 | $0.50-1.00 | 2-8s | API |
| **Claude 3.5 Sonnet** | 84.9% | 200K tokens | $3.00 | $0.15-0.30 | 2-8s | API |
| **Ollama (local)** | 65-75% | 8K tokens | $0 | $0 (electricity) | 10-30s | Local |

---

## Detailed Analysis

### CodeT5+ 16B (Salesforce)

**Pros:**
- Encoder-decoder architecture (optimal for translation tasks)
- Specifically trained for code-to-code translation
- Open source, self-hostable
- Cost-effective at scale (~$0.05/conversion)
- Good HumanEval score (~75%)

**Cons:**
- Requires GPU for inference
- 512 token context limit (may need chunking for large files)
- Self-hosting complexity
- May need fine-tuning for Java→Bedrock specifically

**Deployment Options:**
1. **Modal** (Recommended): A10G GPU, ~$0.70/hour, pay-per-second
2. **RunPod**: Similar pricing, more configuration options
3. **Hugging Face Inference Endpoints**: Easier setup, higher cost

**Recommendation**: ✅ **PRIMARY MODEL**
- Deploy on Modal for cost-effective GPU inference
- Use for 80%+ of conversions
- Expected cost: $0.05/conversion

---

### DeepSeek-Coder-V2 (DeepSeek AI)

**Pros:**
- Highest HumanEval score among open models (82.1%)
- Massive context window (128K tokens)
- Very cost-effective API ($0.14/1M input tokens)
- OpenAI-compatible API (easy integration)
- Good for complex, multi-file conversions

**Cons:**
- Newer model (less battle-tested)
- API dependency (no self-hosting option currently)
- China-based company (potential data sovereignty concerns)

**Deployment Options:**
1. **Official API**: api.deepseek.com
2. **Together AI**: Alternative provider
3. **Sambanova**: Enterprise deployment

**Recommendation**: ✅ **FALLBACK MODEL**
- Use when Modal is unavailable or for complex conversions
- Expected cost: $0.10-0.20/conversion

---

### Ollama (Local Development)

**Pros:**
- Free (no API costs)
- Private (runs locally)
- Easy to set up
- Good for development and testing
- Multiple model options (deepseek-coder, codellama, starcoder)

**Cons:**
- Requires local GPU for good performance
- Slower than API (10-30s vs 2-10s)
- Lower accuracy than best models
- Not suitable for production scale

**Deployment Options:**
1. **Local**: Developer machines
2. **Docker**: Containerized deployment
3. **Remote Ollama**: Self-hosted server

**Recommendation**: ✅ **DEVELOPMENT/BACKUP**
- Use for local development
- Fallback when APIs are unavailable
- Expected cost: $0 (free)

---

### GPT-4 Turbo (OpenAI)

**Pros:**
- Highest overall code understanding
- Excellent documentation and examples
- Very reliable (99.9%+ uptime)
- Easy integration

**Cons:**
- Expensive ($10/1M input tokens)
- Not code-specific (general LLM)
- Rate limits for free tier

**Recommendation**: ⚠️ **EMERGENCY BACKUP ONLY**
- Use only when all other models fail
- Expected cost: $0.50-1.00/conversion

---

## Final Selection

### Model Hierarchy

```
┌─────────────────────────────────────────┐
│  PRIMARY: CodeT5+ 16B (Modal GPU)       │
│  - 80%+ of conversions                  │
│  - Cost: ~$0.05/conversion              │
│  - Latency: 5-15 seconds                │
└─────────────────────────────────────────┘
              │
              ▼ (if unavailable)
┌─────────────────────────────────────────┐
│  FALLBACK: DeepSeek-Coder-V2 (API)      │
│  - 15-19% of conversions                │
│  - Cost: ~$0.10-0.20/conversion         │
│  - Latency: 3-10 seconds                │
└─────────────────────────────────────────┘
              │
              ▼ (if unavailable)
┌─────────────────────────────────────────┐
│  BACKUP: Ollama (Local)                 │
│  - <1% of conversions                   │
│  - Cost: $0                             │
│  - Latency: 10-30 seconds               │
└─────────────────────────────────────────┘
              │
              ▼ (if unavailable)
┌─────────────────────────────────────────┐
│  EMERGENCY: GPT-4 Turbo (API)           │
│  - Only when all else fails             │
│  - Cost: $0.50-1.00/conversion          │
│  - Latency: 2-8 seconds                 │
└─────────────────────────────────────────┘
```

### Expected Cost Breakdown

| Scenario | Model Mix | Avg Cost/Conversion | Monthly (1000 conversions) |
|----------|-----------|---------------------|----------------------------|
| **Normal** | 80% Modal, 19% DeepSeek, 1% Ollama | $0.06 | $60 |
| **Modal Down** | 50% DeepSeek, 49% Ollama, 1% GPT-4 | $0.15 | $150 |
| **All API** | 90% DeepSeek, 9% Ollama, 1% GPT-4 | $0.14 | $140 |
| **Worst Case** | 100% GPT-4 | $1.00 | $1,000 |

**Target Average**: <$0.10/conversion  
**Budget**: $500/month (allows 5,000+ conversions at target cost)

---

## Implementation Plan

### Phase 1: Modal Deployment (Days 1-3)
1. Create Modal account
2. Write deployment script for CodeT5+ 16B
3. Deploy to A10G GPU instance
4. Test endpoint accessibility
5. Configure health checks

### Phase 2: DeepSeek Integration (Days 3-4)
1. Create DeepSeek API account
2. Implement API client
3. Test translation quality
4. Configure rate limiting
5. Set up cost tracking

### Phase 3: Ollama Setup (Days 4-5)
1. Install Ollama locally
2. Pull deepseek-coder model
3. Implement local client
4. Test fallback chain
5. Document setup process

### Phase 4: Model Router (Days 5-7)
1. Implement router with fallback logic
2. Add health check before each request
3. Configure retry with exponential backoff
4. Implement cost tracking
5. Add logging and monitoring

---

## Success Criteria

- [ ] Model comparison matrix completed ✅
- [ ] Primary model selected (CodeT5+ via Modal) ✅
- [ ] Fallback model selected (DeepSeek-Coder API) ✅
- [ ] Backup model selected (Ollama local) ✅
- [ ] Emergency backup selected (GPT-4) ✅
- [ ] Cost analysis completed ✅
- [ ] Implementation plan defined ✅

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-03-14 | CodeT5+ 16B as primary | Best cost/quality ratio, encoder-decoder optimal for translation |
| 2026-03-14 | DeepSeek-Coder-V2 as fallback | High quality (82% HumanEval), cost-effective API |
| 2026-03-14 | Ollama for development | Free, private, good for testing |
| 2026-03-14 | GPT-4 as emergency backup | Most reliable, but expensive |

---

## Next Steps

1. **Begin Task 1.1.2**: Modal GPU Deployment
2. Create Modal account and configure billing
3. Write CodeT5+ deployment script
4. Test endpoint health and latency

---

*Model selection complete. Ready to proceed with deployment.*
