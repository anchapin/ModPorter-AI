#!/usr/bin/env python3
"""
PortKit Coder Fine-Tuning — Kaggle Version
Fine-tunes Qwen2.5-Coder-7B-Instruct with QLoRA on MMSD synthesis pairs.

Kaggle-specific features:
- Google Drive mounting for persistent storage & checkpoints
- Auto-resume from last checkpoint on restart
- More frequent checkpointing to prevent lost progress
- HuggingFace token from Kaggle secrets or environment

Usage:
1. Upload this script to Kaggle
2. Add HF_TOKEN to Kaggle secrets (or set HF_TOKEN env var)
3. Mount Google Drive when prompted (or set USE_GOOGLE_DRIVE=0)
4. Run!
"""

import os
import json
import subprocess
import re
import shutil
import gc
from pathlib import Path
from typing import Tuple

import torch

IS_KAGGLE = os.path.exists("/kaggle")
WORK_DIR = Path("/kaggle/working") if IS_KAGGLE else Path("./output")
CHECKPOINT_DIR = WORK_DIR / "checkpoints"
FINAL_DIR = WORK_DIR / "final"
DATA_DIR = WORK_DIR / "data"

os.makedirs(WORK_DIR, exist_ok=True)
os.makedirs(CHECKPOINT_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

# Reduce memory fragmentation on CUDA
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"


def get_checkpoint_path() -> Path:
    """Find the latest checkpoint if it exists."""
    if not CHECKPOINT_DIR.exists():
        return None
    checkpoints = list(CHECKPOINT_DIR.glob("checkpoint-*"))
    if not checkpoints:
        return None
    return max(checkpoints, key=lambda p: p.stat().st_mtime)


def check_torch_cuda_compat():
    """Check PyTorch CUDA compatibility and warn if needed."""
    if not torch.cuda.is_available():
        return
    props = torch.cuda.get_device_properties(0)
    cap = props.major * 10 + props.minor
    supported_caps = [70, 75, 80, 86, 90, 100, 120]
    if cap not in supported_caps:
        print(f"\n⚠️  WARNING: GPU compute capability sm_{cap} may not be fully supported")
        print(f"   If you encounter issues, consider switching to T4 in Notebook Settings")
        print()


# ── Config ─────────────────────────────────────────────────────────────────

MODEL_ID = "Qwen/Qwen2.5-Coder-1.5B-Instruct"
LORA_REPO = "alexchapin/portkit-coder-1b-lora"
MERGED_REPO = "alexchapin/portkit-coder-1b-merged"

HF_TOKEN = os.environ.get("HF_TOKEN", "")

# QLoRA
LORA_R = 16  # Reduced for 1.5B model (was 64)
LORA_ALPHA = 32  # Standard alpha = 2 * r for smaller models
LORA_DROPOUT = 0.1
TARGET_MODULES = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]

# Kaggle T4 settings (optimized for 16GB GPU)
MAX_LENGTH = 2048
NUM_EPOCHS = 3
BATCH_SIZE = 2
GRAD_ACCUM = 8
LR = 2e-4
WARMUP = 0.05
SCHEDULER = "cosine"
SEED = 42
TRAIN_RATIO = 0.9

# Kaggle: save checkpoint every N steps (more frequent than default)
CHECKPOINT_STEPS = 100  # Save every 100 steps to prevent lost progress
LR = 2e-4
WARMUP = 0.05
SCHEDULER = "cosine"
SEED = 42
TRAIN_RATIO = 0.9

# Kaggle: save checkpoint every N steps (more frequent than default)
CHECKPOINT_STEPS = 100  # Save every 100 steps to prevent lost progress

SYSTEM_PROMPT = (
    "You are PortKit, an expert at converting Minecraft Java Edition mods (Forge) "
    "to Bedrock Edition Add-ons. Given a mod description and Java source code, "
    "first reason through the platform mapping, then produce the Bedrock Add-on implementation."
)


# ── Data ───────────────────────────────────────────────────────────────────


def clone_and_validate() -> str:
    """Clone portkit repo, run validation, return path to validated_pairs.jsonl."""
    validated = DATA_DIR / "validated_pairs.jsonl"

    if validated.exists() and validated.stat().st_size > 1000:
        print(f"[data] Using cached {validated}")
        return str(validated)

    work = Path("/tmp/portkit_train")
    work.mkdir(exist_ok=True)

    repo = work / "portkit"
    if not repo.exists():
        print("[data] Cloning portkit repo (sparse + LFS)...")
        subprocess.run(
            [
                "git",
                "clone",
                "--filter=blob:none",
                "--sparse",
                "https://github.com/anchapin/portkit.git",
                str(repo),
            ],
            check=True,
        )
        subprocess.run(
            [
                "git",
                "-C",
                str(repo),
                "sparse-checkout",
                "set",
                "ai_engine/mmsd/synthesis_pairs.jsonl",
                "ai_engine/mmsd/validators/",
                "ai_engine/mmsd/run_validation.py",
                "ai_engine/mmsd/__init__.py",
                "ai_engine/__init__.py",
            ],
            check=True,
        )
        subprocess.run(
            [
                "git",
                "-C",
                str(repo),
                "lfs",
                "pull",
                "--include=ai_engine/mmsd/synthesis_pairs.jsonl",
            ],
            check=False,
        )

    raw = repo / "ai_engine/mmsd/synthesis_pairs.jsonl"
    assert raw.exists() and raw.stat().st_size > 100_000, (
        f"Bad data file: {raw.stat().st_size if raw.exists() else 0} bytes"
    )

    # Prepare processed dir
    proc_dir = repo / "ai_engine/mmsd/data/processed"
    proc_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(raw), str(proc_dir / "synthesis_pairs.jsonl"))

    # Run validation
    print("[data] Running validation...")
    _run_validation(str(proc_dir / "synthesis_pairs.jsonl"), str(validated))

    if not validated.exists() or validated.stat().st_size < 1000:
        print("[data] Validation output empty, falling back to raw data")
        shutil.copy2(str(raw), str(validated))

    print(f"[data] {validated.stat().st_size / 1e6:.1f} MB ready")
    return str(validated)


def _has_error_fields(entry: dict) -> bool:
    for field in ["reasoning_trace", "java_source", "bedrock_source"]:
        val = entry.get(field, "")
        if isinstance(val, str) and (val.startswith("Error:") or val.startswith("ERROR_PREFIX")):
            return True
    return False


def _validate_java(source: str) -> Tuple[bool, str]:
    code = re.sub(r"```java(.*?)```", r"\1", source, flags=re.DOTALL).strip()
    if not code:
        code = source
    checks = {
        "package": r"package [\w.]+;",
        "class": r"public class \w+",
        "imports": r"import [\w.*]+;",
        "braces": r"\{.*?\}",
    }
    for name, pat in checks.items():
        if not re.search(pat, code, re.DOTALL):
            return False, f"Missing {name}"
    return True, "OK"


def _validate_bedrock(source: str) -> Tuple[bool, str]:
    blocks = re.findall(r"```json(.*?)```", source, re.DOTALL)
    if not blocks and "format_version" not in source:
        return False, "No JSON blocks"
    for block in blocks:
        clean = re.sub(r"//.*", "", block)
        try:
            json.loads(clean)
        except json.JSONDecodeError:
            return False, "Invalid JSON"
    return True, "OK"


def _run_validation(input_path: str, output_path: str):
    valid = 0
    total = 0
    with open(input_path) as inf, open(output_path, "w") as outf:
        for line in inf:
            total += 1
            try:
                entry = json.loads(line)
                if _has_error_fields(entry):
                    continue
                j_ok, _ = _validate_java(entry["java_source"])
                b_ok, _ = _validate_bedrock(entry["bedrock_source"])
                if j_ok and b_ok:
                    outf.write(json.dumps(entry) + "\n")
                    valid += 1
            except Exception:
                pass
    print(f"[data] Validated: {valid}/{total}")


def format_stage_a(example: dict) -> dict:
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Mod Description: {example['instruction']}\n\n"
                    f"Java Source:\n{example['java_source']}\n\n"
                    "Convert this to a Bedrock Add-on. First explain your conversion approach, then provide the files."
                ),
            },
            {
                "role": "assistant",
                "content": (
                    f"## Conversion Plan\n{example['reasoning_trace']}\n\n"
                    f"## Bedrock Add-on Output\n{example['bedrock_source']}"
                ),
            },
        ]
    }


# ── Main ───────────────────────────────────────────────────────────────────


def main():
    # Set environment variables for stability
    os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"
    os.environ["CUDA_LAUNCH_BLOCKING"] = "1"

    print("=" * 60)
    print("PortKit Coder SFT — Kaggle Version")
    print(f"Model: {MODEL_ID}")
    print(f"LoRA: r={LORA_R}, α={LORA_ALPHA}")
    print(f"Effective batch: {BATCH_SIZE * GRAD_ACCUM}, LR: {LR}")
    print(f"CUDA: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        props = torch.cuda.get_device_properties(0)
        print(f"GPU: {props.name}, VRAM: {props.total_memory / 1e9:.1f} GB")
    print(f"Work dir: {WORK_DIR}")
    print(f"Checkpoint dir: {CHECKPOINT_DIR}")
    check_torch_cuda_compat()
    print("=" * 60)

    # ── Auth with HuggingFace ────────────────────────────────────────────────
    if HF_TOKEN:
        os.environ["HF_TOKEN"] = HF_TOKEN
        print(f"[auth] HF_TOKEN set for {LORA_REPO}")

    # ── Data ────────────────────────────────────────────────────────────────
    data_path = clone_and_validate()
    pairs = []
    with open(data_path) as f:
        for line in f:
            if line.strip():
                pairs.append(json.loads(line))

    n = len(pairs)
    split = int(n * TRAIN_RATIO)
    from datasets import Dataset

    train_ds = Dataset.from_list([format_stage_a(p) for p in pairs[:split]])
    eval_ds = Dataset.from_list([format_stage_a(p) for p in pairs[split:]])
    print(f"Data: {n} total → {len(train_ds)} train, {len(eval_ds)} eval")

    # ── Model ───────────────────────────────────────────────────────────────
    print("\nLoading model...")
    from datasets import Dataset
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from peft import LoraConfig, TaskType
    from trl import SFTTrainer, SFTConfig

    bnb = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        quantization_config=bnb,
        torch_dtype=torch.bfloat16,
        use_cache=False,
        device_map="auto",
        attn_implementation="eager",  # Safer on T4, avoids SDPA issues
    )
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    peft_config = LoraConfig(
        r=LORA_R,
        lora_alpha=LORA_ALPHA,
        lora_dropout=LORA_DROPOUT,
        target_modules=TARGET_MODULES,
        task_type=TaskType.CAUSAL_LM,
        bias="none",
    )

    # ── Training ─────────────────────────────────────────────────────────────
    resume_from_checkpoint = None
    last_checkpoint = get_checkpoint_path()
    if last_checkpoint and CHECKPOINT_DIR.exists():
        print(f"[resume] Found checkpoint: {last_checkpoint}")
        resume_from_checkpoint = str(last_checkpoint)

    args = SFTConfig(
        output_dir=str(CHECKPOINT_DIR),
        max_length=MAX_LENGTH,
        packing=False,
        num_train_epochs=NUM_EPOCHS,
        per_device_train_batch_size=BATCH_SIZE,
        gradient_accumulation_steps=GRAD_ACCUM,
        learning_rate=LR,
        warmup_ratio=WARMUP,
        lr_scheduler_type=SCHEDULER,
        optim="paged_adamw_8bit",
        seed=SEED,
        gradient_checkpointing=True,
        bf16=True,
        logging_strategy="steps",
        logging_steps=10,
        logging_first_step=True,
        disable_tqdm=False,
        eval_strategy="steps",
        eval_steps=100,
        save_strategy="steps",
        save_steps=CHECKPOINT_STEPS,
        save_total_limit=5,
        resume_from_checkpoint=resume_from_checkpoint,
        push_to_hub=True,
        hub_model_id=LORA_REPO,
        hub_private_repo=True,
        hub_token=HF_TOKEN,
        run_name=f"portkit-sft-kaggle-lr{LR}-bs{BATCH_SIZE * GRAD_ACCUM}",
        report_to="none",
    )

    trainer = SFTTrainer(
        model=model,
        args=args,
        train_dataset=train_ds,
        eval_dataset=eval_ds,
        processing_class=tokenizer,
        peft_config=peft_config,
    )

    print("\n▶ Training...")
    result = trainer.train()
    train_metrics = result.metrics
    print(f"✓ Train loss: {train_metrics.get('train_loss', 'N/A'):.4f}")
    print(f"  Runtime: {train_metrics.get('train_runtime', 'N/A'):.0f}s")

    print("\n▶ Evaluation...")
    eval_metrics = trainer.evaluate()
    for k, v in eval_metrics.items():
        print(f"  {k}: {v}")

    # ── Save & Push LoRA ────────────────────────────────────────────────────
    trainer.save_model(str(FINAL_DIR / "lora"))
    try:
        trainer.push_to_hub()
        print(f"✓ LoRA pushed to {LORA_REPO}")
    except Exception as e:
        print(f"✗ LoRA push failed: {e}")

    # ── Merge & Push ────────────────────────────────────────────────────────
    print("\n▶ Merging & pushing...")
    try:
        from peft import AutoPeftModelForCausalLM

        del model, trainer
        gc.collect()
        torch.cuda.empty_cache()

        merged = AutoPeftModelForCausalLM.from_pretrained(
            str(FINAL_DIR / "lora"),
            torch_dtype=torch.bfloat16,
            device_map="auto",
        ).merge_and_unload()

        merged.push_to_hub(MERGED_REPO, private=True, safe_serialization=True, token=HF_TOKEN)
        tokenizer.push_to_hub(MERGED_REPO, private=True, token=HF_TOKEN)
        print(f"✓ Merged model pushed to {MERGED_REPO}")
    except Exception as e:
        print(f"✗ Merge/push failed: {e}")

    # ── Summary ─────────────────────────────────────────────────────────────
    summary = {
        "model_id": MODEL_ID,
        "lora": {
            "r": LORA_R,
            "alpha": LORA_ALPHA,
            "dropout": LORA_DROPOUT,
            "target_modules": TARGET_MODULES,
        },
        "training": {
            "epochs": NUM_EPOCHS,
            "batch_size": BATCH_SIZE,
            "grad_accum": GRAD_ACCUM,
            "effective_bs": BATCH_SIZE * GRAD_ACCUM,
            "lr": LR,
            "max_length": MAX_LENGTH,
            "warmup": WARMUP,
            "scheduler": SCHEDULER,
            "checkpoint_steps": CHECKPOINT_STEPS,
        },
        "data": {"total": n, "train": len(train_ds), "eval": len(eval_ds)},
        "results": {
            "train_loss": train_metrics.get("train_loss"),
            "eval_loss": eval_metrics.get("eval_loss"),
            "train_runtime_s": train_metrics.get("train_runtime"),
        },
        "repos": {"lora": LORA_REPO, "merged": MERGED_REPO},
    }
    with open(str(WORK_DIR / "training_summary.json"), "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\n✓ Summary: {json.dumps(summary['results'], indent=2)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
