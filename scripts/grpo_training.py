#!/usr/bin/env python3
"""
GRPO RL Training for Minecraft Java-to-Bedrock Mod Conversion
On AMD RX 6600 XT (gfx1032/RDNA2, 8.6 GB VRAM, ROCm 7.1)

Strategy:
  - ibm-granite/granite-4.1-3b (3.4B dense, NOT MoE) in fp16 = 6.81 GB
  - LoRA r=4 on q_proj/v_proj only = ~5 MB trainable params
  - beta=0.0 (no ref model, saves ~50% VRAM)
  - num_generations=2 (minimum, each gen costs VRAM)
  - max_completion_length=128 (very short to fit VRAM during backward)
  - gradient_checkpointing=True (default in GRPOConfig)
  - per_device_train_batch_size=1 + gradient_accumulation=4
  - optim=adafactor (lower memory than adamw)

Usage:
    HSA_OVERRIDE_GFX_VERSION=10.3.0 HF_HUB_DISABLE_XET=1 python grpo_training.py
"""

import json
import re
import os
import sys
import gc
import traceback
from pathlib import Path
from typing import List

# Must be set before torch/ROCm init
os.environ["HSA_OVERRIDE_GFX_VERSION"] = "10.3.0"
os.environ["HF_HUB_DISABLE_XET"] = "1"
# Reduce VRAM fragmentation
os.environ["PYTORCH_HIP_ALLOC_CONF"] = "expandable_segments:True"

import torch
import numpy as np

SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent
AI_ENGINE_PATH = PROJECT_ROOT / "ai_engine"
if AI_ENGINE_PATH.exists() and str(AI_ENGINE_PATH) not in sys.path:
    sys.path.insert(0, str(AI_ENGINE_PATH))

DATASET_PATH = PROJECT_ROOT / "ai_engine/mmsd/data/processed/validated_pairs.jsonl"

# =============================================================================
# Reward functions
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
            ver_match = (
                1.0 if (ref_ver and comp_ver and ref_ver.group(1) == comp_ver.group(1)) else 0.5
            )
            score += 0.4 * (0.7 * field_match + 0.3 * ver_match)

    if ref_sections["js"]:
        total_weight += 0.35
        ref_js = " ".join(ref_sections["js"])
        comp_js = " ".join(comp_sections["js"]) if comp_sections["js"] else ""
        if comp_js:
            ref_funcs = set(re.findall(r"function\s+(\w+)", ref_js))
            comp_funcs = set(re.findall(r"function\s+(\w+)", comp_js))
            func_match = (
                len(ref_funcs & comp_funcs) / max(len(ref_funcs | comp_funcs), 1)
                if ref_funcs
                else 0
            )
            ref_controls = len(re.findall(r"\b(if|for|while|switch)\b", ref_js))
            comp_controls = len(re.findall(r"\b(if|for|while|switch)\b", comp_js))
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
    """Composite reward: structural alignment + length + JSON validity + density."""
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
    train_pairs = pairs[: int(len(pairs) * 0.9)]

    def build_prompt(row: dict) -> str:
        system = (
            "You are PortKit, an expert at converting Minecraft Java Edition mods (Forge) "
            "to Bedrock Edition Add-ons. Given a mod description and Java source code, "
            "first reason through the platform map, then produce the Bedrock Add-on implementation."
        )
        user = (
            f"Mod Description: {row['instruction']}\n\nJava Source:\n{row['java_source']}\n\n"
            "Convert this to a Bedrock Add-on. First explain your conversion approach, then provide the files."
        )
        return system + "\n\n" + user

    return [
        {"prompt": build_prompt(p), "answer": p["bedrock_source"]}
        for p in train_pairs[:max_samples]
    ]


# =============================================================================
# Main
# =============================================================================


def main():
    print("=" * 60)
    print("GRPO Training - Minecraft Mod Conversion")
    print("AMD RX 6600 XT | granite-4.1-3b | fp16 + LoRA")
    print("=" * 60)
    print(f"torch: {torch.__version__}, hip: {torch.version.hip}")
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    vram = torch.cuda.get_device_properties(0).total_memory
    print(f"VRAM: {vram / 1e9:.1f} GB")

    # ------------------------------------------------------------------
    # [1] Load dataset
    # ------------------------------------------------------------------
    print("\n[1] Loading dataset...")
    data = load_dataset(max_samples=200)
    print(f"  Dataset: {len(data)} samples loaded")

    # ------------------------------------------------------------------
    # [2] Load model (fp16, no quantization - bitsandbytes 4-bit segfaults on gfx1032)
    # ------------------------------------------------------------------
    print("\n[2] Loading model...")
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import LoraConfig, get_peft_model, TaskType

    model_name = "ibm-granite/granite-4.1-3b"
    max_seq_length = 512  # Short to save VRAM

    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        dtype=torch.float16,
        device_map="cuda",
        trust_remote_code=True,
    )
    print(f"  Model loaded: {model_name}")
    print(f"  VRAM after load: {torch.cuda.memory_allocated() / 1e9:.2f} GB")

    # ------------------------------------------------------------------
    # [3] Apply LoRA adapters (small rank to minimize VRAM)
    # ------------------------------------------------------------------
    print("\n[3] Applying LoRA adapters...")
    lora_config = LoraConfig(
        r=4,  # Small rank for 8.6 GB VRAM
        lora_alpha=8,
        target_modules=["q_proj", "v_proj"],  # Minimal targets
        lora_dropout=0.0,
        bias="none",
        task_type=TaskType.CAUSAL_LM,
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()
    print(f"  VRAM after LoRA: {torch.cuda.memory_allocated() / 1e9:.2f} GB")

    # Enable gradient checkpointing to save activation memory
    model.gradient_checkpointing_enable()
    model.enable_input_require_grads()
    print(f"  Gradient checkpointing enabled")

    # ------------------------------------------------------------------
    # [4] Setup GRPO trainer
    # ------------------------------------------------------------------
    print("\n[4] Setting up GRPO trainer...")
    from trl import GRPOConfig, GRPOTrainer
    from datasets import Dataset

    num_samples = 50
    max_steps = 30
    num_generations = 2  # Minimum allowed (default 8, each costs VRAM)
    max_completion_length = 128  # Short to save activation memory during backward

    print(f"  Config: {num_samples} samples, {max_steps} steps, {num_generations} gens/sample")

    output_dir = "./grpo_output"

    training_args = GRPOConfig(
        output_dir=output_dir,
        # Training hyperparams
        per_device_train_batch_size=1,
        gradient_accumulation_steps=4,
        max_steps=max_steps,
        num_train_epochs=1,
        learning_rate=2e-5,  # Higher for LoRA (10x base)
        lr_scheduler_type="cosine",
        warmup_steps=3,
        optim="adafactor",  # Lower memory than adamw (no momentum states)
        weight_decay=0.01,
        max_grad_norm=1.0,
        # Precision - fp16 for RDNA2 (no native bf16)
        fp16=True,
        bf16=False,
        # Generation
        num_generations=num_generations,
        generation_batch_size=2,
        max_completion_length=max_completion_length,
        temperature=0.8,
        top_p=0.95,
        # GRPO specifics
        beta=0.0,  # No ref model = saves ~50% VRAM
        epsilon=0.2,  # Lower clip
        epsilon_high=None,  # Defaults to epsilon (0.2) at init
        loss_type="dapo",  # Default, best for RL
        scale_rewards="group",
        mask_truncated_completions=True,
        # Memory
        gradient_checkpointing=True,  # Default ON in GRPOConfig
        # Logging
        logging_steps=1,
        logging_first_step=True,
        log_completions=True,
        num_completions_to_print=1,
        disable_tqdm=True,
        # Dataset
        shuffle_dataset=True,
        seed=42,
        report_to="none",
    )

    # Build dataset in messages format for trl GRPOTrainer
    # GRPOTrainer expects 'prompt' column (list of message dicts)
    # Truncate inputs aggressively to fit in 512 token context
    prompts = []
    references = []
    for d in data[:num_samples]:
        # Build a shorter prompt to fit context
        instruction = d["prompt"]
        # Extract just the mod description from the full prompt
        if "Mod Description:" in instruction:
            desc = instruction.split("Mod Description: ")[-1].split("\n\nJava Source:")[0]
        else:
            desc = instruction[:200]

        # Truncate java source to first 300 chars
        if "Java Source:" in instruction:
            java = instruction.split("Java Source:")[-1][:300]
        else:
            java = ""

        user_msg = f"Convert this Minecraft mod to a Bedrock Add-on.\nMod: {desc}\n"
        if java:
            user_msg += f"Java (excerpt):\n{java}\n"
        user_msg += "Provide manifest.json and main.js."

        prompts.append(
            [
                {
                    "role": "system",
                    "content": "You are PortKit, an expert at converting Minecraft Java mods to Bedrock Add-ons. Provide the manifest.json and JavaScript implementation.",
                },
                {"role": "user", "content": user_msg},
            ]
        )
        references.append(d["answer"])

    train_dataset = Dataset.from_dict(
        {
            "prompt": prompts,
            "reference": references,
        }
    )
    print(f"  Dataset: {len(train_dataset)} rows")

    # ------------------------------------------------------------------
    # [5] Define reward function
    # ------------------------------------------------------------------
    print("\n[5] Defining reward function...")

    def reward_fn(prompts, completions, **kwargs):
        """
        GRPOTrainer reward function signature:
          (prompts, completions, **kwargs) -> list[float]

        prompts: list of list of dicts (chat messages)
        completions: list of list of dicts (chat messages)
        kwargs: includes 'reference' from dataset columns
        """
        # Get reference from kwargs (passed from dataset column)
        ref_list = kwargs.get("reference", None)

        rewards = []
        for i, completion in enumerate(completions):
            # Extract text from completion (list of message dicts)
            if isinstance(completion, list) and len(completion) > 0:
                comp_text = (
                    completion[0].get("content", "")
                    if isinstance(completion[0], dict)
                    else str(completion[0])
                )
            else:
                comp_text = str(completion)

            # Get corresponding reference
            if ref_list is not None:
                ref = ref_list[i] if i < len(ref_list) else ref_list[0]
            else:
                ref = ""

            reward = compute_reward(comp_text, ref)
            rewards.append(float(reward))

        return rewards

    # ------------------------------------------------------------------
    # [6] Initialize GRPOTrainer
    # ------------------------------------------------------------------
    print("\n[6] Initializing GRPOTrainer...")
    trainer = GRPOTrainer(
        model=model,
        reward_funcs=reward_fn,
        args=training_args,
        train_dataset=train_dataset,
        processing_class=tokenizer,
        peft_config=None,  # Already applied via get_peft_model
    )
    print("  GRPOTrainer initialized")

    # ------------------------------------------------------------------
    # [7] Train!
    # ------------------------------------------------------------------
    print(f"\n[7] Starting GRPO training...")
    print(f"  VRAM before training: {torch.cuda.memory_allocated() / 1e9:.2f} GB")
    print(
        f"  Steps: {max_steps} | Generations/sample: {num_generations} | Max completion len: {max_completion_length}"
    )
    print("  " + "=" * 50)

    try:
        trainer.train()
        print("  " + "=" * 50)
        print("  TRAINING COMPLETE")
    except RuntimeError as e:
        if "out of memory" in str(e).lower():
            print(f"\n  OOM during training: {e}")
            print("  Trying recovery: clearing cache and reducing batch...")
            torch.cuda.empty_cache()
            gc.collect()
            raise
        raise

    # ------------------------------------------------------------------
    # [8] Save model
    # ------------------------------------------------------------------
    print("\n[8] Saving model...")
    trainer.save_model(f"{output_dir}/final")
    tokenizer.save_pretrained(f"{output_dir}/final")
    print(f"  Saved to {output_dir}/final/")

    # ------------------------------------------------------------------
    # [9] Quick evaluation
    # ------------------------------------------------------------------
    print("\n[9] Quick evaluation...")
    model.eval()
    sample = data[0]
    msgs = [
        {
            "role": "system",
            "content": "You are PortKit, an expert at converting Minecraft Java Edition mods to Bedrock Edition Add-ons.",
        },
        {"role": "user", "content": sample["prompt"][:500]},
    ]
    text = tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=max_seq_length).to(
        "cuda"
    )
    with torch.no_grad():
        out = model.generate(
            **inputs,
            max_new_tokens=256,
            temperature=0.8,
            top_p=0.95,
            do_sample=True,
            pad_token_id=tokenizer.pad_token_id,
        )
    resp = tokenizer.decode(out[0], skip_special_tokens=True)
    # Extract assistant response
    if "assistant" in resp:
        resp = resp.split("assistant")[-1].strip()
    reward = compute_reward(resp, sample["answer"])
    print(f"  Sample reward: {reward:.3f}")
    print(f"  Response preview: {resp[:200]}...")

    print(f"\n✓ GRPO training complete!")
    print(f"  Model saved: {output_dir}/final/")
    print(f"  Final VRAM: {torch.cuda.memory_allocated() / 1e9:.2f} GB")


if __name__ == "__main__":
    main()
