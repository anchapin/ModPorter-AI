#!/usr/bin/env python3
"""
PortKit Coder Fine-Tuning — Stage A (Reasoning + Code Generation)
Fine-tunes Qwen2.5-Coder-7B-Instruct with QLoRA on MMSD synthesis pairs.

Data pipeline:
1. git clone portkit repo (sparse) + git lfs pull for synthesis_pairs.jsonl
2. Run structural validation → validated_pairs.jsonl
3. Format as ChatML conversations (system + user + assistant)
4. 90/10 train/eval split (no shuffle, deterministic)
5. QLoRA fine-tuning with SFTTrainer
6. Push LoRA adapter + merged model to HF Hub
"""

import os
import json
import subprocess
import re
import shutil
import torch
import gc
from pathlib import Path
from typing import Tuple

from datasets import Dataset
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import LoraConfig, TaskType
from trl import SFTTrainer, SFTConfig

# ── Config ─────────────────────────────────────────────────────────────────

MODEL_ID = "Qwen/Qwen2.5-Coder-7B-Instruct"
LORA_REPO = "alexchapin/portkit-coder-7b-lora"
MERGED_REPO = "alexchapin/portkit-coder-7b-merged"

TRACKIO_PROJECT = os.environ.get("TRACKIO_PROJECT", "portkit-sft")
TRACKIO_SPACE_ID = os.environ.get("TRACKIO_SPACE_ID", "")

# QLoRA
LORA_R = 64
LORA_ALPHA = 128
LORA_DROPOUT = 0.1
TARGET_MODULES = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]

# Training
MAX_LENGTH = 4096
NUM_EPOCHS = 3
BATCH_SIZE = 2
GRAD_ACCUM = 8
LR = 2e-4
WARMUP = 0.05
SCHEDULER = "cosine"
SEED = 42
TRAIN_RATIO = 0.9

SYSTEM_PROMPT = (
    "You are PortKit, an expert at converting Minecraft Java Edition mods (Forge) "
    "to Bedrock Edition Add-ons. Given a mod description and Java source code, "
    "first reason through the platform mapping, then produce the Bedrock Add-on implementation."
)


# ── Data ───────────────────────────────────────────────────────────────────


def clone_and_validate() -> str:
    """Clone portkit repo, run validation, return path to validated_pairs.jsonl."""
    work = Path("/tmp/portkit_train")
    work.mkdir(exist_ok=True)
    validated = work / "validated_pairs.jsonl"

    if validated.exists() and validated.stat().st_size > 1000:
        print(f"[data] Using cached {validated}")
        return str(validated)

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
    print("=" * 60)
    print("PortKit Coder SFT — Stage A")
    print(f"Model: {MODEL_ID}")
    print(f"LoRA: r={LORA_R}, α={LORA_ALPHA}")
    print(f"Effective batch: {BATCH_SIZE * GRAD_ACCUM}, LR: {LR}")
    print(f"CUDA: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(
            f"GPU: {torch.cuda.get_device_name(0)}, VRAM: {torch.cuda.get_device_properties(0).total_mem / 1e9:.1f} GB"
        )
    print("=" * 60)

    # ── Data ────────────────────────────────────────────────────────────────
    data_path = clone_and_validate()
    pairs = []
    with open(data_path) as f:
        for line in f:
            if line.strip():
                pairs.append(json.loads(line))

    n = len(pairs)
    split = int(n * TRAIN_RATIO)
    train_ds = Dataset.from_list([format_stage_a(p) for p in pairs[:split]])
    eval_ds = Dataset.from_list([format_stage_a(p) for p in pairs[split:]])
    print(f"Data: {n} total → {len(train_ds)} train, {len(eval_ds)} eval")

    # ── Model ───────────────────────────────────────────────────────────────
    print("\nLoading model...")
    # Use adaptive dtype based on GPU support
    use_bf16 = torch.cuda.is_bf16_supported() if torch.cuda.is_available() else False
    compute_dtype = torch.bfloat16 if use_bf16 else torch.float16

    bnb = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=compute_dtype,
        bnb_4bit_use_double_quant=True,
    )
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        quantization_config=bnb,
        dtype=compute_dtype,
        use_cache=False,
        device_map="auto",
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

    # ── Train ───────────────────────────────────────────────────────────────
    report_to = "trackio" if TRACKIO_SPACE_ID else "none"

    # Detect bf16 support (T4 doesn't support bf16, only fp16)
    use_bf16 = torch.cuda.is_bf16_supported() if torch.cuda.is_available() else False
    compute_dtype = torch.bfloat16 if use_bf16 else torch.float16
    print(f"Precision: {'bf16' if use_bf16 else 'fp16'} (compute_dtype={compute_dtype})")

    args = SFTConfig(
        output_dir="./portkit-lora",
        max_length=MAX_LENGTH,
        packing=False,
        num_train_epochs=NUM_EPOCHS,
        per_device_train_batch_size=BATCH_SIZE,
        per_device_eval_batch_size=1,  # Prevent OOM during eval — logits tensor is huge
        prediction_loss_only=True,     # Don't materialize logits we'll discard anyway
        gradient_accumulation_steps=GRAD_ACCUM,
        learning_rate=LR,
        warmup_ratio=WARMUP,
        lr_scheduler_type=SCHEDULER,
        optim="paged_adamw_8bit",
        seed=SEED,
        gradient_checkpointing=True,
        bf16=use_bf16,
        fp16=not use_bf16,
        fp16_full_eval=not use_bf16,  # Force fp16 during eval on non-bf16 GPUs
        logging_strategy="steps",
        logging_steps=10,
        logging_first_step=True,
        disable_tqdm=True,
        eval_strategy="steps",
        eval_steps=100,
        save_strategy="steps",
        save_steps=200,
        save_total_limit=3,
        push_to_hub=True,
        hub_model_id=LORA_REPO,
        hub_private_repo=True,
        run_name=f"portkit-sft-stageA-lr{LR}-bs{BATCH_SIZE * GRAD_ACCUM}",
        report_to=report_to,
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
    trainer.save_model("./portkit-lora/final")
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
            "./portkit-lora/final",
            dtype=compute_dtype,
            device_map="auto",
        ).merge_and_unload()

        merged.push_to_hub(MERGED_REPO, private=True, safe_serialization=True)
        tokenizer.push_to_hub(MERGED_REPO, private=True)
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
        },
        "data": {"total": n, "train": len(train_ds), "eval": len(eval_ds)},
        "results": {
            "train_loss": train_metrics.get("train_loss"),
            "eval_loss": eval_metrics.get("eval_loss"),
            "train_runtime_s": train_metrics.get("train_runtime"),
        },
        "repos": {"lora": LORA_REPO, "merged": MERGED_REPO},
    }
    with open("./training_summary.json", "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\n✓ Summary: {json.dumps(summary['results'], indent=2)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
