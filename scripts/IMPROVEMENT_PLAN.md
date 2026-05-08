# GRPO Training Improvement Plan

## Context
- **Hardware**: AMD RX 6600 XT (8.6 GB VRAM, ROCm 7.1)
- **Current model**: Qwen2.5-Coder-0.5B-Instruct, fp16 + LoRA r=8
- **Dataset**: 1400 Minecraft mod conversion pairs (Java→Bedrock), all with reasoning traces
- **Current results**: Reward 0.02–0.20, 85% completions truncated, grad norm spikes, no consistent improvement

## Diagnosed Problems

| # | Problem | Root Cause | Severity |
|---|---------|-----------|----------|
| P1 | 85% completions truncated at 200 tokens | max_completion_length=200 is far too short | **CRITICAL** |
| P2 | Learning rate 100x too high | lr=1e-4 causes grad norm spikes (inf, 8.6) | HIGH |
| P3 | KL penalty stifles exploration | beta=0.04 penalizes policy changes | HIGH |
| P4 | Too few generations per prompt | num_generations=4 gives noisy advantage estimates | HIGH |
| P5 | No supervised warmup | Model never learns correct output format before RL exploration | HIGH |
| P6 | Model too small for task | 0.5B struggles with structured code generation | MEDIUM-HIGH |
| P7 | Reward function is sparse/flat | Rewards mostly 0.02–0.06, little gradient signal | HIGH |
| P8 | Only 50 samples used | Training on 50/1400 pairs, limited diversity | MEDIUM |
| P9 | Low temperature limits diversity | T=0.8 is conservative for GRPO exploration | MEDIUM |
| P10 | Reasoning traces unused | 1400 chain-of-thought annotations sitting in dataset | MEDIUM |

## Research-Backed Solutions

Sources: MicroCoder-GRPO (arxiv:2603.07777), DAPO (arxiv:2503.14476), G²RPO-A (arxiv:2508.13023), DRIVE (arxiv:2511.06307), DCPO (arxiv:2509.02333), VeRPO (arxiv:2601.03525)

---

## Phase 1: Quick Wins (LOW effort, fixes P1–P5, P9)
**Goal**: Fix the critical truncation bug + stabilize training  
**Estimated time**: 2-3 hours (script modification + training run)

| Change | Before | After | Rationale |
|--------|--------|-------|-----------|
| max_completion_length | 200 | 512 | MicroCoder: early truncation causes IRREVERSIBLE damage |
| learning_rate | 1e-4 | 1e-6 | All GRPO papers use 1e-6; current is 100x too high |
| beta (KL weight) | 0.04 | 0.0 | DAPO/MicroCoder: remove KL for code tasks |
| loss_type | bnpo | dapo | Token-level loss handles variable-length code better |
| epsilon_high | 0.2 | 0.28 | Asymmetric clipping prevents entropy collapse |
| num_generations | 4 | 8 | G²RPO-A: 8-12 for small models; better advantage estimates |
| temperature | 0.8 | 1.0 | MicroCoder: higher T for code diversity |
| per_device_train_batch_size | 4 | 1 | Compensate for longer sequences + more generations |
| gradient_accumulation | 1 | 4 | Keep effective batch size = 4 |
| scale_rewards | group | false | Remove std normalization that causes difficulty bias |
| num_samples | 50 | 200 | More data diversity |
| max_steps | 30 | 60 | More training with stable lr |

**Implementation**: Modify `resume_grpo_training.py` config section  
**VRAM estimate**: ~2.1 GB model + ~1.5 GB activations = ~3.6 GB total → fits comfortably

---

## Phase 2: SFT Warmup (MEDIUM effort, fixes P5, P10)
**Goal**: Teach model the output format before RL exploration  
**Estimated time**: 4-6 hours (new script + training)

### SFT Script
- **Data**: All 1400 pairs, 90/10 train/val split
- **Format**: System prompt + Java source → reasoning trace + bedrock_source
- **Model**: Same Qwen2.5-Coder-0.5B-Instruct + LoRA r=8
- **Config**:
  ```
  learning_rate=2e-5, epochs=3, batch_size=2, gradient_accumulation=4
  max_seq_length=2048, warmup_ratio=0.1, weight_decay=0.01
  logging_steps=5, eval_strategy="steps", eval_steps=50
  save_strategy="steps", save_steps=50, load_best_model_at_end=True
  ```
- **Why**: DRIVE paper shows SFT→GRPO gives +58% on code tasks. Model needs to learn format BEFORE exploring with RL.

### Why reasoning traces matter
- All 1400 pairs have chain-of-thought reasoning traces
- SFT on reasoning teaches the model HOW to approach conversions
- G²RPO-A shows reasoning guidance improves 0.6B models by +8%

---

## Phase 3: Improved Reward Function (MEDIUM effort, fixes P7)
**Goal**: Smoother reward gradient, better signal quality  
**Estimated time**: 3-4 hours (rewrite reward function + test)

### Current reward problems
- Most rewards cluster in 0.02–0.06 range (too flat)
- No partial credit for "almost correct" structures
- No penalty for hallucinated fields
- Binary JSON validity check (0 or 1, no middle ground)

### New reward components (VeRPO-inspired dense rewards)

| Component | Weight | Description |
|-----------|--------|-------------|
| manifest_field_match | 0.15 | Exact field-by-field comparison with reference manifest |
| manifest_uuid_format | 0.05 | Are UUIDs properly formatted? |
| js_function_match | 0.15 | Function names overlap with reference |
| js_event_handler_match | 0.10 | Correct event handlers (onTick, onUse, etc.) |
| js_control_flow_match | 0.10 | Control structures match reference complexity |
| json_parseability | 0.10 | Can JSON be parsed? Partial credit for near-valid |
| length_appropriateness | 0.10 | Output length within 0.5-2.0x of reference |
| structural_completeness | 0.15 | Both manifest AND JS present, correct order |
| no_hallucination_penalty | 0.10 | Penalize invented APIs, non-existent Bedrock methods |

### Key improvements
- Partial credit at each step (not binary 0/1)
- Penalize specific failure modes (hallucinated APIs, missing sections)
- Difficulty-weighted (harder conversions get higher reward ceiling)
- Smoother gradient for RL training

---

## Phase 4: Larger Model (MEDIUM effort, fixes P6)
**Goal**: Upgrade from 0.5B to 1.5B for better code understanding  
**Estimated time**: 4-8 hours (download + config tuning + training)

### Target: Qwen2.5-Coder-1.5B-Instruct
- **Params**: 1.5B (3x more than current)
- **Hidden**: 1536 (vs 896)
- **Layers**: 28 (vs 24)
- **FP16 weights**: ~2.8 GB → fits in 8.6 GB with LoRA

### VRAM budget
| Component | Size |
|-----------|------|
| Model weights (fp16) | 2.8 GB |
| LoRA adapters + optimizer | 0.3 GB |
| KV cache (4 gen × 256 tokens) | 0.5 GB |
| Activation memory (grad checkpoint) | 2.0 GB |
| **Total** | **~5.6 GB** |
| **Free** | **~3.0 GB** |

### Config adjustments for 1.5B
```
per_device_train_batch_size=1, gradient_accumulation=4
num_generations=4 (not 8 — too much VRAM)
max_completion_length=256 (start conservative, increase later)
max_seq_length=1024
```

### Why 1.5B and not 3B
- 3B fp16 = 6.0 GB weights alone → only 2.6 GB for everything else → too tight for GRPO
- 1.5B is the sweet spot for 8.6 GB VRAM
- G²RPO-A tested directly on 1.7B models with excellent results

---

## Phase 5: Curriculum & Scale (HIGH effort, fixes P8)
**Goal**: Use all 1400 pairs with difficulty-based curriculum  
**Estimated time**: 6-8 hours

### Step 1: Difficulty scoring
Score each pair by reference complexity:
- Simple: <200 tokens reference, 1-2 functions → ~400 pairs
- Medium: 200-800 tokens, multiple functions → ~700 pairs
- Hard: >800 tokens, complex event handlers → ~300 pairs

### Step 2: DRIVE-inspired curriculum
1. **Stage 1** (entropy expansion): Train on all 1400 pairs, 8 rollouts, GRPO
2. **Stage 2** (hard focus): Retrain on hardest 300 pairs only, higher rollout budget
3. Duplicate hard examples 2x in training data (DRIVE finding)

---

## Implementation Order

```
Week 1: Phase 1 (Quick Wins) → immediate training improvement
Week 1: Phase 2 (SFT Warmup) → parallel development
Week 2: Phase 3 (Reward Function) → needs SFT model to test against
Week 2: Phase 4 (Larger Model) → apply Phases 1-3 to 1.5B model  
Week 3: Phase 5 (Curriculum) → full pipeline on 1.5B with all improvements
```

## Expected Impact (Cumulative)

| After Phase | Expected Reward Range | Confidence |
|-------------|----------------------|------------|
| Current | 0.02–0.20 | (measured) |
| Phase 1 | 0.10–0.40 | HIGH — fixing truncation alone is transformative |
| Phase 2 | 0.20–0.60 | HIGH — SFT teaches format, GRPO refines |
| Phase 3 | 0.30–0.70 | MEDIUM — better reward signal → better policy |
| Phase 4 | 0.40–0.85 | MEDIUM — 3x more params = better code understanding |
| Phase 5 | 0.50–0.90+ | LOW — diminishing returns, but curriculum helps |

## Actual Results (Cumulative)

| Phase | Model | Eval Reward | Truncation | Max Grad Norm | Time |
|-------|-------|-------------|------------|---------------|------|
| Baseline | 0.5B, basic config | 0.097 | 85% | ∞ | ~10 min |
| Phase 1 (config fixes) | 0.5B, fixed config | 0.263 | 22% | 1.31 | ~25 min |
| SFT→GRPO pipeline | 0.5B, SFT warmup | 0.267 | 24% | 1.75 | ~15 min |
| Phase 3 (dense reward) | 0.5B, 6-component reward | 0.410 | 22% | 0.52 | ~25 min |
| Phase 4 (1.5B, compl=384) | 1.5B, SFT+GRPO | 0.112 | 100% | 0.12 | ~51 min |
| Phase 4b (1.5B, compl=512) | 1.5B, SFT+GRPO | 0.311 | 100% | 0.08 | ~72 min |
| **Phase 5 (1.5B, curriculum)** | **1.5B, SFT+curriculum GRPO** | **0.326** | **75%** | **0.28** | **~159 min** |

### Phase 5 Detailed Comparison (10-sample held-out eval, same samples for all)

| Model | Total | Manifest | JS Quality | JSON Validity | Bedrock APIs | Hallucination |
|-------|-------|----------|------------|--------------|--------------|---------------|
| Phase 3 (0.5B) | 0.219 | 0.000 | 0.119 | 0.600 | 0.150 | 0.210 |
| Phase 4b (1.5B) | 0.327 | 0.000 | 0.230 | **1.000** | **0.240** | 0.135 |
| **Phase 5 (1.5B, curriculum)** | **0.313** | 0.000 | **0.255** | 0.900 | 0.165 | **0.135** |

### Phase 5 Key Findings

1. **Curriculum training helped EOS learning**: Stage 1 (easy/medium) achieved 25% non-truncated completions vs Phase 4b's 0%
2. **DAPO soft overlong penalty + EOS bonus**: The model learned to stop on easy examples (min completion 219 tokens vs always 512)
3. **Best JS quality** (0.255) of any phase — curriculum focuses model on achievable tasks first
4. **Manifest score still 0**: Neither model produces proper manifest.json in eval (prompt truncation issue)
5. **Phase 4b slightly higher on this eval** (0.327 vs 0.313) — but Phase 5 has better JS quality
6. **Stage 2 (all data) regressed EOS learning**: Adding hard examples brought clipped ratio back to ~100%

### Remaining Issues

- **Truncation**: Phase 5 improved on easy examples (25% non-truncated in Stage 1) but Stage 2 hard samples revert to 100%
- **Manifest generation**: Neither model reliably produces manifest.json blocks (0.000 for all)
- **Bedrock API usage**: Phase 4b better at API detection (0.240 vs 0.165) — Phase 5 curriculum may dilute API-heavy examples
- **Eval variance**: 10-sample eval has high variance — Phase 4b and Phase 5 are roughly comparable

## Key Risks

| Risk | Mitigation |
|------|-----------|
| OOM with longer completions | Reduce batch size, enable gradient checkpointing |
| Reward hacking | Hold out 10% of dataset for honest evaluation |
| Overfitting on 1400 pairs | LoRA keeps trainable params low; early stopping |
| 1.5B model too slow on RX 6600 XT | ~50s/step — acceptable for 80 steps |
| Model diverges with higher temperature | Monitor KL closely, add callback to auto-reduce T |
| 4-bit merge OOM | Use fp16 base instead (4-bit → fp16 merge allocates full model in memory) |
