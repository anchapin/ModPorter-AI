# PortKit Coder Training Report

**Date:** 2026-05-05  
**Task:** Fine-tune Qwen2.5-Coder-7B-Instruct for Minecraft Java→Bedrock mod conversion  
**Stage:** A (Reasoning + Code Generation)  

---

## 1. Dataset Statistics

| Metric | Value |
|--------|-------|
| Source file | `ai_engine/mmsd/synthesis_pairs.jsonl` |
| Total raw pairs | 1,400 |
| Pairs passing validation | 1,400 (100%) |
| Pairs with reasoning_trace < 100 chars | 0 |
| Validated output | `ai_engine/mmsd/data/processed/validated_pairs.jsonl` |
| Train split (first 90%) | 1,260 examples |
| Eval split (last 10%) | 140 examples |

### Token Length Distribution (estimated ~4 chars/token)

| Range | Count | Percentage |
|-------|-------|------------|
| 0–2k tokens | 939 | 67.1% |
| 2k–4k tokens | 431 | 30.8% |
| 4k–8k tokens | 21 | 1.5% |
| 8k–16k tokens | 8 | 0.6% |
| 16k+ tokens | 1 | 0.1% |

- **97.9%** of examples fit within `max_length=4096` tokens
- **99.4%** fit within 8192 tokens

### Data Fields

Each training example contains:
- `instruction` — Brief Minecraft mod concept description (2–4 sentences)
- `reasoning_trace` — Step-by-step platform mapping explanation (Java Forge ↔ Bedrock)
- `java_source` — Complete Java Forge 1.21 mod code
- `bedrock_source` — Bedrock Add-on output (manifest.json + scripting .js)

---

## 2. Training Configuration

### Base Model
- **Model:** `Qwen/Qwen2.5-Coder-7B-Instruct`
- **Parameters:** 7,615M (7.6B)
- **Architecture:** Qwen2
- **License:** Apache 2.0

### QLoRA Configuration

| Parameter | Value |
|-----------|-------|
| LoRA rank (r) | 64 |
| LoRA alpha | 128 |
| LoRA dropout | 0.1 |
| Target modules | q_proj, k_proj, v_proj, o_proj, gate_proj, up_proj, down_proj |
| Task type | CAUSAL_LM |
| Bias | none |

### Quantization (BitsAndBytes)

| Parameter | Value |
|-----------|-------|
| Load in 4-bit | True |
| Quant type | NF4 |
| Compute dtype | bfloat16 |
| Double quantization | True |

### Training Hyperparameters

| Parameter | Value |
|-----------|-------|
| Epochs | 3 |
| Per-device batch size | 2 |
| Gradient accumulation steps | 8 |
| **Effective batch size** | **16** |
| Learning rate | 2×10⁻⁴ |
| LR scheduler | Cosine |
| Warmup ratio | 0.05 |
| Max sequence length | 4,096 |
| Optimizer | paged_adamw_8bit |
| Gradient checkpointing | True |
| BF16 | True |
| Seed | 42 |

### Prompt Template (Stage A)

```
<|im_start|>system
You are PortKit, an expert at converting Minecraft Java Edition mods (Forge) to Bedrock Edition Add-ons. Given a mod description and Java source code, first reason through the platform mapping, then produce the Bedrock Add-on implementation.<|im_end|>
<|im_start|>user
Mod Description: {instruction}

Java Source:
{java_source}

Convert this to a Bedrock Add-on. First explain your conversion approach, then provide the files.<|im_end|>
<|im_start|>assistant
## Conversion Plan
{reasoning_trace}

## Bedrock Add-on Output
{bedrock_source}<|im_end|>
```

---

## 3. Training Results

> **Note:** Training requires a GPU (A10G 24GB recommended). Results will be filled in after the training run completes.

### To Run Training

**Option A: HF Jobs (recommended)**
```bash
# Ensure you have HF credits: https://huggingface.co/settings/billing
# Then submit via the HF Jobs API or CLI
```

**Option B: Local GPU**
```bash
cd /home/alex/Projects/portkit
python3 ai_engine/mmsd/train_portkit_coder.py
```

**Option C: Any GPU machine with Python**
```bash
pip install transformers trl peft bitsandbytes torch datasets accelerate
python3 ai_engine/mmsd/train_portkit_coder.py
```

### Expected Results

| Metric | Baseline (raw Qwen2.5-Coder-7B) | Fine-tuned (PortKit Coder) |
|--------|----------------------------------|---------------------------|
| Train loss | ~3.5–4.0 (expected) | _TBD_ |
| Eval loss | ~3.5–4.0 (expected) | _TBD_ |
| BLEU score | ~5–15 (expected) | _TBD_ |
| JSON validity % | ~10–30% (expected) | _TBD_ |
| JS syntax % | ~20–40% (expected) | _TBD_ |
| Perplexity | _TBD_ | _TBD_ |

---

## 4. Evaluation

### Evaluation Script
```bash
# Evaluate fine-tuned model
python3 ai_engine/mmsd/evaluate.py \
    --model alexchapin/portkit-coder-7b-merged \
    --baseline Qwen/Qwen2.5-Coder-7B-Instruct \
    --eval-data ai_engine/mmsd/data/processed/validated_pairs.jsonl \
    --output evaluation_results.json

# Or evaluate LoRA adapter directly
python3 ai_engine/mmsd/evaluate.py \
    --baseline Qwen/Qwen2.5-Coder-7B-Instruct \
    --lora-adapter ./portkit-lora/final \
    --eval-data ai_engine/mmsd/data/processed/validated_pairs.jsonl
```

### Metrics
1. **BLEU** — Measures n-gram overlap between generated Bedrock output and ground truth
2. **JSON validity** — % of generated manifest.json that parse as valid JSON with `format_version` and `header`
3. **JS syntax check** — % of generated .js files that pass `node --check`
4. **Reasoning coherence** — Manual rating of 20 samples (1–5 scale) on whether reasoning_trace correctly maps Java→Bedrock

---

## 5. Hugging Face Hub Repositories

| Repository | Description | URL |
|------------|-------------|-----|
| LoRA Adapter | QLoRA adapter weights only | `alexchapin/portkit-coder-7b-lora` |
| Merged Model | Base model + LoRA merged | `alexchapin/portkit-coder-7b-merged` |

Both repos are set to **private** visibility.

---

## 6. Pipeline Verification

The training pipeline was verified end-to-end using `Qwen/Qwen2.5-Coder-0.5B` on CPU:

```
Train loss: 1.7357 (1 epoch, 15 examples, max_length=512)
Pipeline test: PASSED ✓
```

Components verified:
- ✅ Data loading from `validated_pairs.jsonl`
- ✅ Stage A ChatML formatting (system + user + assistant messages)
- ✅ LoRA adapter creation and application
- ✅ SFTTrainer initialization and training loop
- ✅ Loss computation and logging
- ✅ Model saving

---

## 7. Files

| File | Description |
|------|-------------|
| `ai_engine/mmsd/train_portkit_coder.py` | Complete training script (self-contained) |
| `ai_engine/mmsd/evaluate.py` | Evaluation script (BLEU, JSON validity, JS syntax) |
| `ai_engine/mmsd/data/processed/validated_pairs.jsonl` | Clean training data (1,400 pairs) |
| `ai_engine/mmsd/data/processed/synthesis_pairs.jsonl` | Copy of raw synthesis pairs |
| `ai_engine/mmsd/TRAINING_REPORT.md` | This report |

---

## 8. Next Steps

1. **Run training** on GPU hardware (A10G 24GB or equivalent)
   - Estimated cost: ~$8–16 on HF Jobs (a10g-large, ~4–6 hours)
   - Or run on any machine with an RTX 3090/4090 or better

2. **Evaluate** using `evaluate.py` — compare baseline vs fine-tuned

3. **Stage B fine-tuning** (optional follow-up):
   - Direct conversion prompt (no reasoning trace)
   - Can be done as a second LoRA pass on top of Stage A

4. **Push to Hub** — the training script automatically pushes both LoRA adapter and merged model

5. **Integration** — connect fine-tuned model to PortKit's conversion pipeline
