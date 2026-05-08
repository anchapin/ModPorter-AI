#!/usr/bin/env python3
"""
Phase 1: GRPO Training with Quick-Win Improvements
====================================================
All LOW-effort fixes applied simultaneously based on research:

Changes from baseline:
  - max_completion_length: 200 → 512  (was truncating 85% of completions)
  - learning_rate: 1e-4 → 1e-6        (was 100x too high, causing grad spikes)
  - beta (KL weight): 0.04 → 0.0      (remove KL for code tasks, per DAPO)
  - loss_type: bnpo → dapo             (token-level loss for variable-length code)
  - epsilon_high: 0.2 → 0.28           (asymmetric clipping prevents entropy collapse)
  - num_generations: 4 → 8             (better advantage estimates, per G²RPO-A)
  - temperature: 0.8 → 1.0             (higher diversity for code, per MicroCoder)
  - scale_rewards: group → false        (remove std normalization bias, per DAPO)
  - batch_size: 4 → 1, grad_accum: 1→4 (compensate for longer sequences)
  - num_samples: 50 → 200              (more data diversity)
  - max_steps: 30 → 60                 (more training with stable lr)
  - max_seq_length: 512 → 1024         (73% of prompts need >512 tokens)

Research sources:
  - MicroCoder-GRPO (arxiv:2603.07777): truncation fix, temperature
  - DAPO (arxiv:2503.14476): loss_type, beta=0, asymmetric clipping
  - G²RPO-A (arxiv:2508.13023): num_generations for small models
  - DRIVE (arxiv:2511.06307): training pipeline design

Usage:
    HSA_OVERRIDE_GFX_VERSION=10.3.0 HF_HUB_DISABLE_XET=1 python phase1_grpo_quickwins.py
"""

import json
import re
import os
import sys
import gc
import time
from pathlib import Path

# Must be set before torch/ROCm init
os.environ["HSA_OVERRIDE_GFX_VERSION"] = "10.3.0"
os.environ["HF_HUB_DISABLE_XET"] = "1"
os.environ["PYTORCH_HIP_ALLOC_CONF"] = "expandable_segments:True"

import torch
import numpy as np

SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent
AI_ENGINE_PATH = PROJECT_ROOT / "ai_engine"
if AI_ENGINE_PATH.exists() and str(AI_ENGINE_PATH) not in sys.path:
    sys.path.insert(0, str(AI_ENGINE_PATH))

DATASET_PATH = PROJECT_ROOT / "ai_engine/mmsd/data/processed/validated_pairs.jsonl"
OUTPUT_DIR = SCRIPT_DIR / "grpo_output_phase1"

# =============================================================================
# Reward functions (unchanged from baseline — Phase 3 will improve these)
# =============================================================================

def _extract_json_blocks(text: str) -> list[str]:
    return re.findall(r"```json\s*(\{[^}]*(?:\{[^}]*\}[^}]*)*\})", text, re.DOTALL)


def _extract_js_blocks(text: str) -> list[str]:
    return re.findall(r"```(?:javascript|js)\s*([\s\S]*?)```", text)


def _extract_all_sections(text: str) -> dict[str, list[str]]:
    sections = {"manifest": [], "js": []}
    for block in _extract_json_blocks(text):
        if "format_version" in block or "header" in block or "modules" in block:
            sections["manifest"].append(block)
    sections["js"] = _extract_js_blocks(text)
    return sections


def _score_structural_alignment(completion: str, reference: str) -> float:
    ref_sections = _extract_all_sections(reference)
    comp_sections = _extract_all_sections(completion)
    score = 0.0
    total_weight = 0.0

    if ref_sections["manifest"]:
        total_weight += 0.4
        ref_manifest = ref_sections["manifest"][0] if ref_sections["manifest"] else ""
        comp_manifest = comp_sections["manifest"][0] if comp_sections["manifest"] else ""
        if comp_manifest:
            ref_fields = set(re.findall(r'"(\w+)":', ref_manifest))
            comp_fields = set(re.findall(r'"(\w+)":', comp_manifest))
            field_match = len(ref_fields & comp_fields) / max(len(ref_fields | comp_fields), 1)
            ref_ver = re.search(r'format_version["\s:]+([0-9.]+)', ref_manifest)
            comp_ver = re.search(r'format_version["\s:]+([0-9.]+)', comp_manifest)
            ver_match = 1.0 if (ref_ver and comp_ver and ref_ver.group(1) == comp_ver.group(1)) else 0.5
            score += 0.4 * (0.7 * field_match + 0.3 * ver_match)

    if ref_sections["js"]:
        total_weight += 0.35
        ref_js = " ".join(ref_sections["js"])
        comp_js = " ".join(comp_sections["js"]) if comp_sections["js"] else ""
        if comp_js:
            ref_funcs = set(re.findall(r'function\s+(\w+)', ref_js))
            comp_funcs = set(re.findall(r'function\s+(\w+)', comp_js))
            func_match = len(ref_funcs & comp_funcs) / max(len(ref_funcs | comp_funcs), 1) if ref_funcs else 0
            ref_controls = len(re.findall(r'\b(if|for|while|switch)\b', ref_js))
            comp_controls = len(re.findall(r'\b(if|for|while|switch)\b', comp_js))
            control_ratio = min(comp_controls / max(ref_controls, 1), 1.0) if ref_controls else 0.5
            score += 0.35 * (0.5 * func_match + 0.5 * control_ratio)

    return score / max(total_weight, 1.0) if total_weight > 0 else 0.0


def _score_length_ratio(completion: str, reference: str) -> float:
    ref_len = len(reference)
    comp_len = len(completion)
    if ref_len == 0:
        return 0.0
    ratio = comp_len / ref_len
    return min(ratio, 2.0) / 2.0


def _score_json_validity(completion: str) -> float:
    for block in _extract_json_blocks(completion):
        try:
            json.loads(block)
            return 1.0
        except json.JSONDecodeError:
            pass
    return 0.0


def _score_content_density(completion: str) -> float:
    code_blocks = re.findall(r"```[\s\S]*?```", completion)
    if not code_blocks:
        return 0.0
    total_chars = sum(len(b) for b in code_blocks)
    return min(total_chars / 500.0, 1.0)


def compute_reward(completion: str, reference: str) -> float:
    """Same composite reward as baseline."""
    completion_text = completion if isinstance(completion, str) else str(completion)
    reference_text = reference if isinstance(reference, str) else str(reference)
    s = _score_structural_alignment(completion_text, reference_text)
    l = _score_length_ratio(completion_text, reference_text)
    v = _score_json_validity(completion_text)
    d = _score_content_density(completion_text)
    return 0.35 * s + 0.20 * l + 0.25 * v + 0.20 * d


# =============================================================================
# Dataset loading
# =============================================================================

def load_dataset(max_samples=200):
    if not DATASET_PATH.exists():
        raise FileNotFoundError(f"Dataset not found at {DATASET_PATH}")
    pairs = []
    with open(DATASET_PATH) as f:
        for line in f:
            if line.strip():
                pairs.append(json.loads(line))
    train_pairs = pairs[:int(len(pairs) * 0.9)]

    def build_prompt(row: dict) -> str:
        system = ("You are PortKit, an expert at converting Minecraft Java Edition mods (Forge) "
                  "to Bedrock Edition Add-ons. Given a mod description and Java source code, "
                  "first reason through the platform map, then produce the Bedrock Add-on implementation.")
        user = (f"Mod Description: {row['instruction']}\n\nJava Source:\n{row['java_source']}\n\n"
                "Convert this to a Bedrock Add-on. First explain your conversion approach, then provide the files.")
        return system + "\n\n" + user

    return [{"prompt": build_prompt(p), "answer": p["bedrock_source"]} for p in train_pairs[:max_samples]]


# =============================================================================
# Main
# =============================================================================

def main():
    start_time = time.time()

    print("=" * 70)
    print("  Phase 1: GRPO Quick-Win Improvements")
    print("  Qwen2.5-Coder-0.5B | fp16 + LoRA r=8 | AMD RX 6600 XT")
    print("=" * 70)
    print(f"  torch: {torch.__version__}, hip: {torch.version.hip}")
    print(f"  GPU: {torch.cuda.get_device_name(0)}")
    vram = torch.cuda.get_device_properties(0).total_memory
    print(f"  VRAM: {vram / 1e9:.1f} GB")

    # Print config diff from baseline
    print("\n  Phase 1 config changes from baseline:")
    changes = [
        ("max_completion_length", "200", "512"),
        ("learning_rate", "1e-4", "1e-6"),
        ("beta (KL)", "0.04", "0.0"),
        ("loss_type", "bnpo", "dapo"),
        ("epsilon_high", "0.2", "0.28"),
        ("num_generations", "4", "8"),
        ("temperature", "0.8", "1.0"),
        ("scale_rewards", "group", "false"),
        ("batch_size", "4", "1 (grad_accum=4)"),
        ("max_seq_length", "512", "1024"),
        ("num_samples", "50", "200"),
        ("max_steps", "30", "60"),
    ]
    for name, old, new in changes:
        print(f"    {name:>25s}: {old:>10s} → {new}")

    # ------------------------------------------------------------------
    # [1] Load dataset
    # ------------------------------------------------------------------
    print("\n[1] Loading dataset...")
    data = load_dataset(max_samples=200)
    print(f"  Dataset: {len(data)} samples loaded")

    # ------------------------------------------------------------------
    # [2] Load model with Unsloth
    # ------------------------------------------------------------------
    print("\n[2] Loading model with Unsloth...")
    from unsloth import FastLanguageModel

    model_name = "unsloth/Qwen2.5-Coder-0.5B-Instruct"
    max_seq_length = 1024  # Was 512 — 73% of prompts need >512 tokens

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=model_name,
        max_seq_length=max_seq_length,
        dtype=torch.float16,
        load_in_4bit=False,
        device_map="cuda",
    )
    print(f"  Model loaded: {model_name}")
    print(f"  VRAM after load: {torch.cuda.memory_allocated() / 1e9:.2f} GB")

    # ------------------------------------------------------------------
    # [3] Apply LoRA adapters (fresh — NOT resuming from old checkpoint)
    # ------------------------------------------------------------------
    print("\n[3] Applying LoRA adapters (r=8, q/k/v/o_proj)...")
    model = FastLanguageModel.get_peft_model(
        model,
        r=8,
        lora_alpha=16,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
        lora_dropout=0.0,
        bias="none",
        use_gradient_checkpointing="unsloth",
    )
    model.print_trainable_parameters()
    print(f"  VRAM after LoRA: {torch.cuda.memory_allocated() / 1e9:.2f} GB")

    # ------------------------------------------------------------------
    # [4] Setup GRPO config — ALL PHASE 1 FIXES HERE
    # ------------------------------------------------------------------
    print("\n[4] Setting up Phase 1 GRPO config...")
    from trl import GRPOConfig, GRPOTrainer
    from datasets import Dataset

    num_samples = 200
    max_steps = 60

    output_dir = str(OUTPUT_DIR)

    training_args = GRPOConfig(
        output_dir=output_dir,
        # ── Phase 1 fixes ──
        # Batch: reduce per-device but keep effective batch = 4 via grad accum
        per_device_train_batch_size=1,
        gradient_accumulation_steps=4,
        max_steps=max_steps,
        num_train_epochs=1,
        # LR: 1e-6 (was 1e-4 — 100x too high per all GRPO papers)
        learning_rate=1e-6,
        lr_scheduler_type="cosine",
        warmup_steps=6,
        optim="adamw_torch",
        adam_beta1=0.9,
        adam_beta2=0.99,
        weight_decay=0.01,
        max_grad_norm=1.0,
        # Precision
        fp16=True,
        bf16=False,
        # Generation: 8 generations per prompt (was 4), 512 tokens (was 200)
        num_generations=8,
        generation_batch_size=8,
        max_completion_length=512,
        # Temperature: 1.0 (was 0.8 — higher diversity for code)
        temperature=1.0,
        top_p=0.95,
        # GRPO specifics
        beta=0.0,                   # No KL penalty (was 0.04 — DAPO shows KL hurts code tasks)
        epsilon=0.2,                # Lower clip
        epsilon_high=0.28,          # Higher clip (was 0.2 — asymmetric prevents entropy collapse)
        loss_type="dapo",           # Token-level loss (was bnpo — better for variable-length code)
        scale_rewards=False,         # No std normalization (was "group" — removes difficulty bias)
        mask_truncated_completions=True,
        # Memory
        gradient_checkpointing=True,
        # Logging
        logging_steps=1,
        logging_first_step=True,
        log_completions=True,
        num_completions_to_print=2,
        disable_tqdm=True,
        # Dataset
        shuffle_dataset=True,
        seed=42,
        report_to="none",
    )
    print(f"  Config: {max_steps} steps, 8 gens/sample, max_compl=512, lr=1e-6")

    # ------------------------------------------------------------------
    # [5] Build dataset
    # ------------------------------------------------------------------
    print("\n[5] Building dataset...")
    prompts = []
    references = []
    for d in data[:num_samples]:
        prompts.append(d["prompt"])
        references.append(d["answer"])

    train_dataset = Dataset.from_dict({
        "prompt": prompts,
        "reference": references,
    })
    print(f"  Dataset: {len(train_dataset)} rows")

    # ------------------------------------------------------------------
    # [6] Define reward function
    # ------------------------------------------------------------------
    print("\n[6] Defining reward function...")

    def reward_fn(completions, prompts, **kwargs):
        ref_list = kwargs.get("reference", None)
        rewards = []
        for i, completion in enumerate(completions):
            if isinstance(completion, list) and len(completion) > 0:
                comp_text = completion[0].get("content", "") if isinstance(completion[0], dict) else str(completion[0])
            else:
                comp_text = str(completion)

            if ref_list is not None:
                ref = ref_list[i] if i < len(ref_list) else ref_list[0]
            else:
                ref = ""

            reward = compute_reward(comp_text, ref)
            rewards.append(float(reward))

        return rewards

    # ------------------------------------------------------------------
    # [7] Initialize GRPOTrainer
    # ------------------------------------------------------------------
    print("\n[7] Initializing GRPOTrainer...")
    trainer = GRPOTrainer(
        model=model,
        reward_funcs=reward_fn,
        args=training_args,
        train_dataset=train_dataset,
        processing_class=tokenizer,
        peft_config=None,  # Already applied via FastLanguageModel.get_peft_model
    )
    print("  GRPOTrainer initialized")

    # ------------------------------------------------------------------
    # [8] Train! (fresh start, not resuming)
    # ------------------------------------------------------------------
    print(f"\n[8] Starting Phase 1 GRPO training...")
    print(f"  Steps: {max_steps} | Gens/prompt: 8 | Max completion: 512 tokens")
    print(f"  VRAM before training: {torch.cuda.memory_allocated() / 1e9:.2f} GB")
    print("  " + "=" * 60)

    try:
        trainer.train()
        print("  " + "=" * 60)
        print("  TRAINING COMPLETE")
    except RuntimeError as e:
        if "out of memory" in str(e).lower():
            print(f"\n  OOM during training: {e}")
            print("  Suggestion: reduce num_generations to 4 or max_completion_length to 256")
            torch.cuda.empty_cache()
            gc.collect()
            raise
        raise

    # ------------------------------------------------------------------
    # [9] Save model
    # ------------------------------------------------------------------
    print("\n[9] Saving model...")
    trainer.save_model(f"{output_dir}/final")
    tokenizer.save_pretrained(f"{output_dir}/final")
    print(f"  Saved to {output_dir}/final/")

    # ------------------------------------------------------------------
    # [10] Quick evaluation (3 samples)
    # ------------------------------------------------------------------
    print("\n[10] Quick evaluation...")
    model.eval()
    eval_samples = [data[0], data[len(data)//2], data[-1]]
    for idx, sample in enumerate(eval_samples):
        msgs = [
            {"role": "system", "content": "You are PortKit, an expert at converting Minecraft Java Edition mods to Bedrock Edition Add-ons."},
            {"role": "user", "content": sample["prompt"][:800]},
        ]
        text = tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=max_seq_length).to("cuda")
        with torch.no_grad():
            out = model.generate(
                **inputs,
                max_new_tokens=512,
                temperature=1.0,
                top_p=0.95,
                do_sample=True,
                pad_token_id=tokenizer.pad_token_id,
            )
        resp = tokenizer.decode(out[0], skip_special_tokens=True)
        if "assistant" in resp:
            resp = resp.split("assistant")[-1].strip()
        reward = compute_reward(resp, sample["answer"])
        print(f"  Sample {idx}: reward={reward:.3f}, len={len(resp)} chars")
        print(f"    Preview: {resp[:150]}...")

    elapsed = time.time() - start_time
    print(f"\n✓ Phase 1 GRPO training complete!")
    print(f"  Model saved: {output_dir}/final/")
    print(f"  Total time: {elapsed/60:.1f} min")
    print(f"  Final VRAM: {torch.cuda.memory_allocated() / 1e9:.2f} GB")


if __name__ == "__main__":
    main()
