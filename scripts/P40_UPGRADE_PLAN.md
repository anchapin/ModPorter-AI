# P40 Upgrade Plan: Multi-GPU Training Strategy

## The Opportunity

Adding a **NVIDIA Tesla P40 (24GB VRAM)** to the system alongside the **AMD RX 6600 XT (8.6 GB VRAM)** transforms what's possible:

| Spec | RX 6600 XT (current) | Tesla P40 (new) |
|------|---------------------|-----------------|
| VRAM | 8.6 GB | **24 GB** |
| Compute | ROCm 7.1, FP16 | CUDA, FP16 |
| Backend | ROCm PyTorch | CUDA PyTorch |
| Flash Attention | ❌ | ❌ (Pascal) |
| BF16 | ✅ | ❌ (FP16 only) |
| Tensor Cores | ❌ | ❌ |
| Bandwidth | 256 GB/s | **346 GB/s** |
| Max power | 160W | 250W |

### Why this matters

The 8.6 GB VRAM was the binding constraint on everything:
- Could only run **1.5B model** (3 GB weights)
- Only **4 GRPO generations** (noisy advantages)
- Max **512-token completions** (references didn't fit)
- **100% clipped ratio** — model could never finish generating
- No room for reward model, evaluation, or data preprocessing during training

With 24 GB, we can run **MoE code models with 30B total / 3B active params**, or **4B dense models** with generous generation budgets.

---

## Model Selection (2026 Models)

### Why NOT Qwen2.5-Coder

Qwen2.5-Coder was released **September 2024** — ancient by LLM standards. The Qwen3 generation (April 2025) and Qwen3-Coder series (late 2025) dramatically outperform it on code benchmarks.

### The killer option: Qwen3-Coder MoE models

The Qwen3-Coder series uses **Mixture-of-Experts (MoE)** architecture — 30B total parameters but only **3B active per token**. This means:
- **Code quality of a 30B model** (it has 128–512 specialized code experts)
- **Training cost of a 3B model** (only 3B params active per forward pass)
- Fits in 24GB with **QLoRA** (4-bit quantization = ~15 GB for weights)

### Model Candidates for 24GB P40

| Model | Total Params | Active/Token | FP16 Size | QLoRA Size | Architecture | Release |
|-------|-------------|--------------|-----------|------------|--------------|---------|
| **Qwen3-Coder-Next** | **30B** | **3B** | 60 GB ❌ | **15 GB** ⚠️ | MoE 512 experts, qwen3_next | **Mar 2026** |
| **Qwen3-Coder-30B-A3B** | **30.5B** | **3B** | 61 GB ❌ | **15.2 GB** ⚠️ | MoE 128 experts, qwen3_moe | **Dec 2025** |
| Qwen3-4B | 4B | 4B | 8 GB ✅ | 2 GB ✅ | Dense, qwen3 | Jul 2025 |
| Qwen3-1.7B | 2B | 2B | 4 GB ✅ | 1 GB ✅ | Dense, qwen3 | Jul 2025 |
| Qwen2.5-Coder-7B | 7B | 7B | 14 GB ⚠️ | 3.5 GB ✅ | Dense, qwen2 | Sep 2024 |

### Recommendation: **Qwen3-Coder-30B-A3B-Instruct**

The Qwen3-Coder-Next is the newest but uses an untested architecture (qwen3_next with 512 experts). **Qwen3-Coder-30B-A3B** is the safer pick:
- Proven architecture (qwen3_moe), 8.9M downloads, 1049 likes
- 128 experts, 8 active per token → 3B active params
- **Purpose-built for code** — not a general model fine-tuned on code
- Apache 2.0 license

**Fallback if MoE is too unstable**: Qwen3-4B (dense, fp16, comfortable fit).

### MoE VRAM budget on P40

```
Qwen3-Coder-30B-A3B with QLoRA (4-bit):
┌─────────────────────────────────┐
│ Model weights (4-bit NF4)  15.2 GB │
│ LoRA adapter (r=16)         0.2 GB │
│ Optimizer (8-bit AdamW)     0.5 GB │
│ Activations (grad ckpt)     1.5 GB │
│ Generation buffer (4×512)   2.5 GB │
│ Working memory              1.0 GB │
│─────────────────────────────────│
│ TOTAL                      ~20.9 GB │ ⚠️ tight but fits in 24 GB
│ Headroom                    ~3.1 GB │
└─────────────────────────────────┘
```

### MoE-specific considerations

| Concern | Impact | Mitigation |
|---------|--------|------------|
| MoE + LoRA compatibility | PEFT supports MoE LoRA since v0.6 | Target `q_proj, k_proj, v_proj, o_proj` only (not experts) |
| MoE + GRPO (generations) | 4 generations × forward pass = 4× expert routing | Use `generation_batch_size=1` (sequential generation) |
| MoE + 4-bit on Pascal | BitsAndBytes works on compute 6.1 | Use `bnb_4bit_compute_dtype=torch.float16` |
| MoE gradient checkpointing | Standard gradient ckpt works with MoE | Essential — keeps activation memory low |
| Qwen3 support in TRL | TRL 1.3.0 supports qwen3_moe | Use `trust_remote_code=True` |

## Can Both GPUs Be Used Together?

### In a single PyTorch process: **NO** ❌

PyTorch is compiled as either a CUDA build OR a ROCm build — never both. A single `import torch` binary can only talk to one GPU backend.

### In separate processes: **YES** ✅

```
┌─────────────────────────────────┐     ┌─────────────────────────────────┐
│    P40 (24GB, CUDA)             │     │    RX 6600 XT (8.6GB, ROCm)     │
│    Python Process #1            │     │    Python Process #2            │
│                                 │     │                                 │
│    • 3B/7B GRPO training        │     │    • Reward model inference     │
│    • SFT warmup                 │     │    • Data preprocessing         │
│    • Generation & evaluation    │     │    • Test-time evaluation       │
│                                 │     │    • 1.5B model experiments     │
│    CUDA_VISIBLE_DEVICES=0       │     │    HIP_VISIBLE_DEVICES=0        │
│    (CUDA PyTorch venv)          │     │    (ROCm PyTorch venv)          │
└─────────────────────────────────┘     └─────────────────────────────────┘
         │                                        │
         └──────── shared CPU memory ─────────────┘
              (no direct GPU↔GPU transfer)
```

### Practical dual-GPU workflow:

1. **P40**: Main training (GRPO/SFT) — the heavy lifter
2. **RX 6600 XT**: Run a reward model server (separate process) that the P40 training calls into
   - Or: run data preprocessing, tokenization, dataset augmentation
   - Or: run the 1.5B model in parallel for A/B comparison during evaluation

**What NOT to try:**
- ❌ DeepSpeed/FSDP across both GPUs
- ❌ `torch.nn.DataParallel` across vendors
- ❌ Both CUDA and ROCm PyTorch in the same venv

---

## Hardware Setup Checklist

### Before installing the P40

| Item | Requirement | Notes |
|------|-------------|-------|
| **PSU wattage** | ≥650W recommended | P40=250W + RX6600XT=160W + CPU=65W + other=50W = ~525W peak |
| **8-pin PCIe power** | 1 available 8-pin connector | P40 needs one 8-pin PCIe power cable |
| **PCIe slot** | Available x16 slot (x4 electrical OK) | The x4 slot will reduce P40 bandwidth by ~30% but still works |
| **Cooling** | Server blower or active cooling | P40 has no fans — needs airflow (rack mount or PCIe fan) |
| **Driver conflict** | Install NVIDIA driver alongside AMD | Both drivers coexist on Linux — use `nvidia` + `amdgpu` |

### Software setup (separate venvs)

```bash
# P40 venv — CUDA PyTorch
python3.12 -m venv ~/.venv_cuda
~/.venv_cuda/bin/pip install torch torchvision torchaudio --index-url https://download.pyt.org/whl/cu124
~/.venv_cuda/bin/pip install transformers trl peft datasets bitsandbytes accelerate

# RX 6600 XT venv — ROCm PyTorch (already exists)
# scripts/.venv_grpo — keep as-is
```

### Critical: P40 is Pascal (compute 6.1) — Limitations

| Feature | P40 Support | Impact |
|---------|-------------|--------|
| **BF16** | ❌ NOT supported | Must use `fp16=True, bf16=False` |
| **Flash Attention** | ❌ NOT supported | Use `attn_implementation="sdpa"` or `"eager"` |
| **Unsloth** | ❌ NOT supported | Use standard TRL + PEFT (no Unsloth patches) |
| **Tensor Cores** | ❌ None | FP16 matmul ~2× slower than Ampere |
| **8-bit optimizer** | ✅ Works | Use `bitsandbytes` AdamW 8-bit |
| **4-bit quantization** | ✅ Works | QLoRA via BitsAndBytes |
| **Gradient checkpointing** | ✅ Works | Essential for memory |

---

## Training Strategy: 2-Phase Plan

### Phase A: Qwen3-Coder-30B-A3B with QLoRA on P40 (Primary)

**Target**: `Qwen/Qwen3-Coder-30B-A3B-Instruct` (30.5B total, 3B active, MoE)

This is the best code model that fits the P40 — 10× more total knowledge than Qwen2.5-Coder-1.5B, with code-specialized expert routing.

```
VRAM budget (30B MoE QLoRA + LoRA r=16):
┌─────────────────────────────────┐
│ Model weights (4-bit NF4)  15.2 GB │
│ LoRA adapter (r=16)         0.2 GB │
│ Optimizer (8-bit AdamW)     0.5 GB │
│ Activations (grad ckpt)     1.5 GB │
│ Generation buffer           2.5 GB │ (4 gen × 512 tokens, sequential)
│ Working memory              1.0 GB │
│─────────────────────────────────│
│ TOTAL                      ~20.9 GB │ ✅ fits in 24 GB
│ Headroom                    ~3.1 GB │
└─────────────────────────────────┘
```

**Config:**
```python
from transformers import BitsAndBytesConfig
from trl import GRPOConfig

bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.float16,  # P40: NO bf16
    bnb_4bit_use_double_quant=True,
)

GRPOConfig(
    # Model
    per_device_train_batch_size=1,
    gradient_accumulation_steps=8,    # Effective batch = 8
    num_generations=4,                # Conservative for MoE + 24GB
    max_completion_length=512,        # 2× longer than before
    max_seq_length=2048,              # 2× context

    # Training
    learning_rate=2e-6,
    warmup_steps=20,
    max_steps=200,

    # Hardware
    fp16=True,
    bf16=False,                       # P40 doesn't have BF16!
    gradient_checkpointing=True,
    optim="adamw_8bit",
    attn_implementation="sdpa",       # No Flash Attention on Pascal

    # GRPO
    loss_type="dapo",
    beta=0.0,
    epsilon=0.2,
    epsilon_high=0.28,
    temperature=1.0,
    mask_truncated_completions=True,
    scale_rewards=False,
)
```

**Why this solves the Phase 4b/5 problems:**

| Problem | Before (8.6 GB, 1.5B) | After (24 GB, 30B MoE) |
|---------|----------------------|------------------------|
| 100% truncated completions | 512 tokens, always hit max | 512 tokens + MoE produces better structured output |
| Only 4 GRPO generations | Noisy advantages | 4 generations with much higher-quality base model |
| 1.5B model, general | Weak code understanding | **30B code-specialized MoE** — 10× total knowledge |
| Manifest always 0 | No room in context | 2048-token context → full prompts + room to generate |
| Flat training rewards | Weak reward signal | Better base model → reward signal has more contrast |
| Old Qwen2.5 architecture | Sep 2024 | **Dec 2025 MoE** — state-of-the-art code generation |

### Phase B: Qwen3-4B Dense Fallback

If the MoE model is too unstable or slow on the P40:

```python
# Qwen3-4B dense — comfortable fit, no QLoRA needed
GRPOConfig(
    num_generations=8,          # More generations — dense model is smaller
    max_completion_length=1024, # Even longer completions
    per_device_train_batch_size=2,
    fp16=True,
    bf16=False,
    gradient_checkpointing=True,
)
```

4B dense VRAM: ~12 GB total → 12 GB headroom. Most conservative option.

---

## Implementation Roadmap

### Step 1: Hardware Installation (30 min)

1. Power off, install P40 in available x16 slot
2. Connect 8-pin PCIe power cable
3. Boot, verify with `lspci | grep -i nvidia`
4. Install NVIDIA driver: `sudo apt install nvidia-driver-550` (or latest for Pascal)
5. Verify: `nvidia-smi` shows P40 with 24GB

### Step 2: CUDA venv Setup (15 min)

```bash
python3.12 -m venv ~/.venv_cuda
~/.venv_cuda/bin/pip install \
    torch==2.7.0 torchvision torchaudio \
    --index-url https://download.pyt.org/whl/cu124
~/.venv_cuda/bin/pip install \
    transformers==5.5.0 trl==1.3.0 peft==0.19.1 \
    datasets accelerate bitsandbytes scipy
# NOTE: NO unsloth — it doesn't support Pascal
```

### Step 3: Verify P40 Works (5 min)

```bash
CUDA_VISIBLE_DEVICES=0 ~/.venv_cuda/bin/python -c "
import torch
print(f'CUDA available: {torch.cuda.is_available()}')
print(f'Device: {torch.cuda.get_device_name(0)}')
print(f'VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB')
x = torch.randn(1000, 1000, device='cuda', dtype=torch.float16)
print(f'FP16 matmul: {(x @ x).sum().item():.0f}')
"
```

### Step 4: Load and Test Qwen3-Coder-30B-A3B (10 min)

```bash
CUDA_VISIBLE_DEVICES=0 ~/.venv_cuda/bin/python -c "
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

bnb = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type='nf4',
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_use_double_quant=True,
)

model = AutoModelForCausalLM.from_pretrained(
    'Qwen/Qwen3-Coder-30B-A3B-Instruct',
    quantization_config=bnb,
    device_map='auto',
    trust_remote_code=True,
)
tok = AutoTokenizer.from_pretrained('Qwen/Qwen3-Coder-30B-A3B-Instruct')

# Test generation
messages = [{'role': 'user', 'content': 'Write a hello world in JavaScript'}]
text = tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
inputs = tok(text, return_tensors='pt').to('cuda')
out = model.generate(**inputs, max_new_tokens=100)
print(tok.decode(out[0], skip_special_tokens=True))
print(f'VRAM: {torch.cuda.memory_allocated() / 1e9:.2f} GB')
"
```

### Step 5: SFT Warmup (30-60 min)

```bash
CUDA_VISIBLE_DEVICES=0 ~/.venv_cuda/bin/python phase6_sft_moe.py
```

SFT on all 1400 pairs with max_seq_length=2048, 2 epochs. Standard SFTTrainer (no Unsloth).

### Step 6: GRPO with Curriculum (2-3 hours)

```bash
CUDA_VISIBLE_DEVICES=0 ~/.venv_cuda/bin python phase6_grpo_moe.py
```

Stage 1: 676 easy/medium samples, 200 steps
Stage 2: All 1260 samples, 150 steps

### Step 7: Evaluate & Compare (15 min)

```bash
# P40: evaluate MoE model
CUDA_VISIBLE_DEVICES=0 ~/.venv_cuda/bin/python evaluate_phases.py

# AMD: evaluate 1.5B model (parallel, separate process)
HSA_OVERRIDE_GFX_VERSION=10.3.0 scripts/.venv_grpo/bin/python evaluate_phases.py
```

---

## Expected Impact

| Metric | Phase 5 (1.5B, 8.6GB) | Phase 6 MoE (30B/3B, 24GB) | Phase 6 Dense (4B, 24GB) |
|--------|----------------------|----------------------------|--------------------------|
| Model | Qwen2.5-Coder-1.5B | **Qwen3-Coder-30B-A3B** | Qwen3-4B |
| Model generation | Sep 2024 | **Dec 2025** | Jul 2025 |
| Total params | 1.5B | **30.5B** | 4B |
| Active params | 1.5B | **3B** | 4B |
| Max completion | 512 tokens | **512 tokens** | **1024 tokens** |
| num_generations | 4 | **4** | **8** |
| Truncation rate | 100% | **<30%** (est) | **<15%** (est) |
| Manifest generation | 0% | **40-60%** (est) | **30-50%** (est) |
| JS quality (prev) | 0.255 | **0.5+** (est) | **0.4+** (est) |
| Eval reward | 0.326 | **0.6+** (est) | **0.5+** (est) |
| Code-specific experts | None | **128 MoE experts** | No (general) |

The 3× VRAM increase is the single biggest improvement because:
1. **Longer completions** → model can actually finish generating
2. **More generations** → GRPO gets cleaner advantage estimates
3. **Bigger model** → better code understanding and generation
4. **Longer context** → more Java source visible → better conversions

---

## Risks & Mitigations

| Risk | Probability | Mitigation |
|------|-------------|------------|
| PSU insufficient (535W peak) | Medium | Monitor with `nvidia-smi -q -d POWER`; underclock P40: `sudo nvidia-smi -pl 200` |
| PCIe x4 slot bottleneck | Low | ~30% bandwidth reduction — training still works |
| P40 overheating (blower fan) | Medium | Monitor `nvidia-smi -q -d TEMPERATURE`; add PCI fan bracket if >85°C |
| MoE + QLoRA instability on Pascal | Medium | Fallback to Qwen3-4B dense (fp16, proven architecture) |
| MoE slow generation on Pascal | Medium | No tensor cores; MoE routing adds overhead. Expect ~2× slower than dense 3B |
| BitsAndBytes 4-bit on Pascal | Low | Works via DP4A instructions; well-tested |
| Driver conflict (NVIDIA + AMD) | Low | Both coexist on Linux; isolate with `CUDA_VISIBLE_DEVICES` / `HIP_VISIBLE_DEVICES` |
| PEFT LoRA on MoE model | Low | Supported since PEFT v0.6; target attention layers only (not experts) |
| Qwen3-Coder-Next too new | Medium | Start with Qwen3-Coder-30B-A3B (more proven); try Next if it works |

---

## Files to Create (after P40 is installed)

1. `scripts/phase6_sft_moe.py` — SFT warmup on Qwen3-Coder-30B-A3B (CUDA, QLoRA)
2. `scripts/phase6_grpo_moe.py` — GRPO curriculum training on MoE model (CUDA)
3. `scripts/phase6_fallback_4b.py` — Fallback with Qwen3-4B dense (CUDA, fp16)
4. `scripts/reward_server.py` — Reward computation server for AMD GPU
5. `scripts/evaluate_p40.py` — Evaluation script for P40 models
6. Updated `scripts/IMPROVEMENT_PLAN.md`
