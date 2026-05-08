#!/usr/bin/env python3
"""
GRPO RL Training for Minecraft Java-to-Bedrock Mod Conversion
Using Unsloth on AMD RX 6600 XT (gfx1032/RDNA2)

Key setup:
- HSA_OVERRIDE_GFX_VERSION=10.3.0 (RDNA2 compatibility)
- torch 2.10.0+rocm7.1 (NOT 2.11+ which has SIGSEGV on RDNA2)
- Unsloth 2026.5+ with bitsandbytes 0.50.0.dev0
- 4-bit LoRA fine-tuning via Unsloth FastLanguageModel

Usage:
    HSA_OVERRIDE_GFX_VERSION=10.3.0 python grpo_train_unsloth.py
"""

import json
import re
import os
import sys
from pathlib import Path
from typing import List, Dict, Any
from functools import partial

# ── Env setup BEFORE importing torch ──────────────────────────────────────────
os.environ["HSA_OVERRIDE_GFX_VERSION"] = "10.3.0"
os.environ["HF_HUB_DISABLE_XET"] = "1"

import torch
import asyncio
from datasets import Dataset
from transformers import AutoTokenizer
from trl import GRPOConfig, GRPOTrainer

from unsloth import FastLanguageModel

# ── Path setup ─────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent.parent
AI_ENGINE_PATH = PROJECT_ROOT / "ai_engine"
if AI_ENGINE_PATH.exists() and str(AI_ENGINE_PATH) not in sys.path:
    sys.path.insert(0, str(AI_ENGINE_PATH))

DATASET_PATH = PROJECT_ROOT / "ai_engine/mmsd/data/processed/validated_pairs.jsonl"

# ── Reward Functions (from portkit_mod_convert.py) ────────────────────────────

def _simple_tokenize(text: str) -> List[str]:
    text = re.sub(r"```[^`]*```", "", text)
    text = re.sub(r"[^\w\s]", " ", text)
    return [t.lower() for t in text.split() if t.strip()]


def _bleu_like(reference: str, hypothesis: str) -> float:
    ref_tokens = _simple_tokenize(reference)
    hyp_tokens = _simple_tokenize(hypothesis)
    if not hyp_tokens or not ref_tokens:
        return 0.0
    overlap = sum(1 for t in hyp_tokens if t in ref_tokens)
    precision = overlap / len(hyp_tokens)
    ref_set = set(ref_tokens)
    hyp_set = set(hyp_tokens)
    recall = len(ref_set & hyp_set) / len(ref_set) if ref_set else 0
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def _extract_manifest(text: str):
    json_blocks = re.findall(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    for block in json_blocks:
        if "format_version" in block or "header" in block:
            return block.strip()
    section = re.search(r"## Bedrock Add-on Output(.*?)(?:##|$)", text, re.DOTALL)
    if section:
        m = re.search(r'\{[^{}]*"format_version"[^{}]*\}', section.group(1), re.DOTALL)
        if m:
            return m.group(0)
    return None


def _extract_js(text: str):
    js_blocks = re.findall(r"```(?:javascript|js)\s*(.*?)\s*```", text, re.DOTALL)
    if js_blocks:
        return max(js_blocks, key=len).strip()
    scripts = re.search(r"(?:scripts|behavior_pack|content).*?\.js", text, re.DOTALL | re.IGNORECASE)
    if scripts:
        return text[scripts.start():min(scripts.start() + 10000, len(text))]
    return None


def extract_manifest_reward(completion_text: str) -> float:
    has_json_block = bool(re.search(r"```json\s*\{", completion_text, re.DOTALL))
    has_keywords = bool(re.search(r"format_version|header|modules|dependencies", completion_text))
    score = 0.0
    if has_json_block:
        score += 0.5
    if has_keywords:
        score += 0.5
    return min(score, 1.0)


def extract_js_reward(completion_text: str) -> float:
    has_js_block = bool(re.search(r"```(?:javascript|js)\s*", completion_text, re.DOTALL))
    has_keywords = bool(re.search(r"\bfunction\b|\bvar\b|\blet\b|\bconst\b|\bexport\b", completion_text))
    score = 0.0
    if has_js_block:
        score += 0.5
    if has_keywords:
        score += 0.5
    return min(score, 1.0)


def json_validity_reward(completion_text: str) -> float:
    manifest_str = _extract_manifest(completion_text)
    if manifest_str is None:
        return 0.0
    try:
        data = json.loads(manifest_str)
    except json.JSONDecodeError:
        return 0.0
    has_version = "format_version" in data
    has_header = "header" in data
    if has_version and has_header:
        return 1.0
    elif has_version or has_header:
        return 0.5
    return 0.0


def js_syntax_reward(completion_text: str) -> float:
    js_code = _extract_js(completion_text)
    if js_code is None:
        return 0.0
    has_function = bool(re.search(r"\bfunction\s+\w+|\(\)\s*=>|\w+\s*\(\s*\)", js_code))
    has_control = bool(re.search(r"\b(if|else|for|while|switch|case)\b", js_code))
    has_valid = bool(re.search(r"[\{\}]", js_code))
    score = 0.0
    if has_function:
        score += 0.4
    if has_control:
        score += 0.3
    if has_valid:
        score += 0.3
    return min(score, 1.0)


def bleu_reward_fn(completion_text: str, reference: str) -> float:
    return _bleu_like(reference, completion_text)


def compute_reward(completion_text: str, reference: str) -> float:
    """Combined reward from all 5 rubric functions (matching portkit weights)."""
    w = [0.20, 0.20, 0.25, 0.15, 0.20]
    r1 = extract_manifest_reward(completion_text)
    r2 = extract_js_reward(completion_text)
    r3 = json_validity_reward(completion_text)
    r4 = js_syntax_reward(completion_text)
    r5 = bleu_reward_fn(completion_text, reference)
    return w[0]*r1 + w[1]*r2 + w[2]*r3 + w[3]*r4 + w[4]*r5


# ── Dataset Loading ─────────────────────────────────────────────────────────────

def load_dataset(max_samples=200):
    """Load training data from validated_pairs.jsonl."""
    if not DATASET_PATH.exists():
        raise FileNotFoundError(f"Dataset not found at {DATASET_PATH}")

    pairs = []
    with open(DATASET_PATH) as f:
        for line in f:
            if line.strip():
                pairs.append(json.loads(line))

    n = len(pairs)
    split = int(n * 0.9)
    train_pairs = pairs[:split]
    eval_pairs = pairs[split:]

    print(f"  Loaded {len(train_pairs)} train, {len(eval_pairs)} eval pairs")

    def build_prompt(row: dict) -> str:
        system = (
            "You are PortKit, an expert at converting Minecraft Java Edition mods (Forge) "
            "to Bedrock Edition Add-ons. Given a mod description and Java source code, "
            "first reason through the platform mapping, then produce the Bedrock Add-on implementation."
        )
        user = (
            f"Mod Description: {row['instruction']}\n\n"
            f"Java Source:\n{row['java_source']}\n\n"
            "Convert this to a Bedrock Add-on. First explain your conversion approach, then provide the files."
        )
        return system + "\n\n" + user

    # Use max_samples for quick training test
    train_rows = [
        {
            "prompt": build_prompt(p),
            "answer": p["bedrock_source"],
        }
        for p in train_pairs[:max_samples]
    ]

    return Dataset.from_list(train_rows)


# ── Reward function for GRPO ───────────────────────────────────────────────────

def reward_func(prompt: str, response: str, reference: str) -> float:
    """GRPO reward function: receives (prompt, response, ground_truth) -> scalar reward."""
    return compute_reward(response, reference)


# ── Main training ────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("GRPO Training - Minecraft Mod Conversion on AMD RX 6600 XT")
    print("=" * 60)
    print(f"torch: {torch.__version__}, hip: {torch.version.hip}")
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
    print()

    # 1. Load dataset
    print("[1] Loading dataset...")
    dataset = load_dataset(max_samples=200)
    print(f"    Dataset: {len(dataset)} samples")

    # 2. Load model with Unsloth
    print("\n[2] Loading model with Unsloth...")
    model_name = "Qwen/Qwen2.5-Coder-3B-Instruct"
    max_seq_length = 512
    lora_rank = 16

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=model_name,
        max_seq_length=max_seq_length,
        load_in_4bit=True,
        fast_inference=True,
        max_lora_rank=lora_rank,
    )
    print(f"    Model: {model_name}")
    print(f"    LoRA rank: {lora_rank}, max_seq: {max_seq_length}")

    # 3. Apply LoRA
    print("\n[3] Applying LoRA adapter...")
    model = FastLanguageModel.get_peft_model(
        model,
        r=lora_rank,
        target_modules=[
            "q_proj", "k_proj", "v_proj", "o_proj",
            "gate_proj", "up_proj", "down_proj",
        ],
        lora_alpha=lora_rank,
        use_gradient_checkpointing="unsloth",
        random_state=42,
    )
    print("    LoRA adapter applied")

    # 4. Format dataset for GRPO
    def format_for_grpo(example):
        # GRPO needs: prompt (str) and answer/reference for reward
        return {
            "prompt": example["prompt"],
            "reference": example["answer"],
        }

    formatted_dataset = dataset.map(format_for_grpo)

    # Custom reward function that has access to reference
    def reward_fn(prompt, response, **kwargs):
        reference = kwargs.get("reference", "")
        return compute_reward(response, reference)

    # 5. GRPO Training Config
    print("\n[4] Setting up GRPO training...")
    training_args = GRPOConfig(
        # Learning
        learning_rate=5e-6,
        adam_beta1=0.9,
        adam_beta2=0.99,
        weight_decay=0.1,
        warmup_ratio=0.1,
        lr_scheduler_type="cosine",
        optim="paged_adamw_8bit",

        # Generation
        num_generations=4,           # Group size per prompt
        max_prompt_length=256,
        max_completion_length=max_seq_length - 256,

        # Batch
        per_device_train_batch_size=1,
        gradient_accumulation_steps=4,
        num_iterations=2,            # PPO epochs per batch

        # Steps
        max_steps=100,
        save_steps=50,
        eval_steps=50,
        logging_steps=1,

        # Output
        output_dir="./grpo_output",
        bf16=True,
        gradient_checkpointing=True,
        remove_unused_columns=False,

        # Misc
        report_to="none",
    )

    print(f"    num_generations: {training_args.num_generations}")
    print(f"    max_steps: {training_args.max_steps}")
    print(f"    max_completion_length: {training_args.max_completion_length}")

    # 6. Create GRPO Trainer
    print("\n[5] Initializing GRPO Trainer...")

    # We need a custom collator that passes reference to reward_fn
    def grpo_reward_fn(prompt, response, reference, **kwargs):
        return compute_reward(response, reference)

    trainer = GRPOTrainer(
        model=model,
        processing_class=tokenizer,
        reward_func=grpo_reward_fn,
        args=training_args,
        train_dataset=formatted_dataset,
    )

    # 7. Train!
    print("\n[6] Starting GRPO training...")
    print("    (reward = weighted sum of 5 rubric functions)")
    print("    (weights: manifest=0.20, js=0.20, json_valid=0.25, syntax=0.15, bleu=0.20)")
    print()
    trainer.train()

    # 8. Save
    print("\n[7] Saving model...")
    model.save_pretrained("./grpo_output_final")
    tokenizer.save_pretrained("./grpo_output_final")
    print("    Saved to ./grpo_output_final/")

    # 9. Quick eval
    print("\n[8] Quick eval on sample...")
    FastLanguageModel.for_inference(model)
    sample = formatted_dataset[0]
    messages = [
        {"role": "system", "content": "You are PortKit."},
        {"role": "user", "content": sample["prompt"].split("You are PortKit")[-1].strip()[:500]},
    ]
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=256).to("cuda")
    outputs = model.generate(**inputs, max_new_tokens=150, temperature=0.7, do_sample=True)
    generated = tokenizer.decode(outputs[0], skip_special_tokens=True)
    reward = compute_reward(generated, sample["reference"])
    print(f"    Eval reward: {reward:.3f}")
    print(f"    (Sample generated, see grpo_output/ for full logs)")

    print("\n✓ GRPO training complete!")
    print(f"  Model saved to: {os.path.abspath('./grpo_output_final')}")


if __name__ == "__main__":
    main()