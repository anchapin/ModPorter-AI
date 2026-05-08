#!/usr/bin/env python3
"""
GRPO RL Training for Minecraft Java-to-Bedrock Mod Conversion
Using trl GRPOTrainer on AMD RX 6600 XT (gfx1032/RDNA2)

Usage:
    HSA_OVERRIDE_GFX_VERSION=10.3.0 HF_HUB_DISABLE_XET=1 python grpo_unsloth_manual.py
"""

import json
import re
import os
import sys
import gc
from pathlib import Path
from typing import List
from functools import partial

os.environ["HSA_OVERRIDE_GFX_VERSION"] = "10.3.0"
os.environ["HF_HUB_DISABLE_XET"] = "1"

import torch
import numpy as np
from tqdm import tqdm

SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent
AI_ENGINE_PATH = PROJECT_ROOT / "ai_engine"
if AI_ENGINE_PATH.exists() and str(AI_ENGINE_PATH) not in sys.path:
    sys.path.insert(0, str(AI_ENGINE_PATH))

DATASET_PATH = PROJECT_ROOT / "ai_engine/mmsd/data/processed/validated_pairs.jsonl"

# ==============================================================================
# Reward functions (5 rubric functions)
# ==============================================================================

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
    precision = overlap / len(hyp_tokens) if hyp_tokens else 0
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


# ==============================================================================
# IMPROVED REWARD FUNCTION (2026 Research: MicroCoder-GRPO, P-GRPO, F-GRPO)
# ==============================================================================

def _extract_json_blocks(text: str) -> list[str]:
    """Extract all JSON code blocks from completion."""
    return re.findall(r"```json\s*(\{[^}]*(?:\{[^}]*\}[^}]*)*\})", text, re.DOTALL)


def _extract_js_blocks(text: str) -> list[str]:
    """Extract all JavaScript code blocks from completion."""
    return re.findall(r"```(?:javascript|js)\s*([\s\S]*?)```", text)


def _extract_all_sections(text: str) -> dict[str, list[str]]:
    """Extract all Bedrock add-on sections from completion text."""
    sections = {"manifest": [], "js": [], "other": []}
    
    # Extract manifest JSON blocks
    for block in _extract_json_blocks(text):
        if "format_version" in block or "header" in block or "modules" in block:
            sections["manifest"].append(block)
    
    # Extract JS blocks
    sections["js"] = _extract_js_blocks(text)
    
    return sections


def _score_structural_alignment(completion: str, reference: str) -> float:
    """Score how well completion mirrors the reference structure."""
    ref_sections = _extract_all_sections(reference)
    comp_sections = _extract_all_sections(completion)
    
    score = 0.0
    total_weight = 0.0
    
    # Manifest structure matching (weight 0.4)
    if ref_sections["manifest"]:
        total_weight += 0.4
        ref_manifest = ref_sections["manifest"][0] if ref_sections["manifest"] else ""
        comp_manifest = comp_sections["manifest"][0] if comp_sections["manifest"] else ""
        
        if comp_manifest:
            # Check required fields
            required_fields = ["format_version", "header", "modules", "dependencies"]
            ref_fields = set(re.findall(r'"(\w+)":', ref_manifest))
            comp_fields = set(re.findall(r'"(\w+)":', comp_manifest))
            field_match = len(ref_fields & comp_fields) / max(len(ref_fields | comp_fields), 1)
            
            # Check version format similarity
            ref_ver = re.search(r'format_version["\s:]+([0-9.]+)', ref_manifest)
            comp_ver = re.search(r'format_version["\s:]+([0-9.]+)', comp_manifest)
            ver_match = 1.0 if (ref_ver and comp_ver and ref_ver.group(1) == comp_ver.group(1)) else 0.5
            
            score += 0.4 * (0.7 * field_match + 0.3 * ver_match)
    
    # JS code structure matching (weight 0.35)
    if ref_sections["js"]:
        total_weight += 0.35
        ref_js = " ".join(ref_sections["js"])
        comp_js = " ".join(comp_sections["js"]) if comp_sections["js"] else ""
        
        if comp_js:
            # Check function definitions
            ref_funcs = set(re.findall(r'function\s+(\w+)', ref_js))
            comp_funcs = set(re.findall(r'function\s+(\w+)', comp_js))
            func_match = len(ref_funcs & comp_funcs) / max(len(ref_funcs | comp_funcs), 1) if ref_funcs else 0
            
            # Check control structures
            ref_controls = len(re.findall(r'\b(if|for|while|switch)\b', ref_js))
            comp_controls = len(re.findall(r'\b(if|for|while|switch)\b', comp_js))
            control_ratio = min(comp_controls / max(ref_controls, 1), 1.0) if ref_controls else 0.5
            
            score += 0.35 * (0.5 * func_match + 0.5 * control_ratio)
    
    # Normalize by actual weight used
    return score / max(total_weight, 0.1)


def _score_length_ratio(completion: str, reference: str) -> float:
    """Score based on length ratio (not keyword overlap)."""
    ref_len = len(reference.split())
    comp_len = len(completion.split())
    ratio = min(comp_len / max(ref_len, 1), 1.0)
    
    # Penalize very short or very long outputs
    if ratio < 0.3:
        return ratio * 0.5  # Severely under-length
    elif ratio > 2.0:
        return 0.5  # Over-length gets capped
    return ratio


def _score_json_validity(completion: str) -> float:
    """Check if extracted JSON is actually parseable."""
    json_blocks = _extract_json_blocks(completion)
    
    if not json_blocks:
        return 0.0
    
    valid_count = 0
    for block in json_blocks:
        try:
            json.loads(block)
            valid_count += 1
        except json.JSONDecodeError:
            pass
    
    return valid_count / max(len(json_blocks), 1)


def _score_content_density(completion: str) -> float:
    """Measure meaningful content vs boilerplate."""
    # Remove code block markers and common boilerplate
    cleaned = re.sub(r"```(?:json|javascript|js)[\s\S]*?```", "", completion)
    cleaned = re.sub(r"```", "", cleaned)
    cleaned = re.sub(r"\b(format_version|header|modules|dependencies|function\s+)\b", "", cleaned)
    cleaned = re.sub(r"[^\w\s]", " ", cleaned)
    
    words = [w for w in cleaned.split() if len(w) > 2]
    total_words = len(completion.split())
    
    if total_words == 0:
        return 0.0
    
    return len(words) / total_words


def compute_reward(completion_text: str, reference: str) -> float:
    """
    Improved reward: Structured field matching + validity + content density.
    Based on 2026 RLHF research (MicroCoder-GRPO, P-GRPO).
    
    Components:
    - structural_alignment (0.35): Does completion have the right sections as reference?
    - length_ratio (0.20): Is output length reasonable vs reference?
    - json_validity (0.25): Can we parse the JSON blocks?
    - content_density (0.20): Does completion have real content vs boilerplate?
    """
    s = _score_structural_alignment(completion_text, reference)
    l = _score_length_ratio(completion_text, reference)
    v = _score_json_validity(completion_text)
    d = _score_content_density(completion_text)
    
    return 0.35 * s + 0.20 * l + 0.25 * v + 0.20 * d


def reward_func(completions, reference, **kwargs):
    """
    Signature: (completions: List[str], reference: str, **kwargs) -> np.array
    Used by trl GRPOTrainer.
    """
    ref = reference[0] if isinstance(reference, list) else reference
    rewards = np.array([compute_reward(c, ref) for c in completions], dtype=np.float32)
    
    if len(rewards) > 1:
        mean = rewards.mean()
        std = rewards.std()
        if std > 1e-6:
            rewards = (rewards - mean) / std
    
    return rewards


def grpo_reward_func(completions, prompts, **kwargs):
    ref = kwargs.get("reference", [""])[0]
    rewards = np.array([compute_reward(c, ref) for c in completions], dtype=np.float32)
    
    if len(rewards) > 1:
        mean = rewards.mean()
        std = rewards.std()
        if std > 1e-6:
            rewards = (rewards - mean) / std
    
    return rewards


def compute_diversity_metrics(completions: List[str]) -> dict:
    """
    Compute diversity metrics across multiple completions.
    Used for logging to detect mode collapse.
    """
    if len(completions) < 2:
        return {"unique_ratio": 0.0, "avg_length": 0.0, "length_std": 0.0}
    
    lengths = [len(c) for c in completions]
    # Unique n-grams (bigrams) ratio
    all_bigrams = set()
    for c in completions:
        words = c.split()
        bigrams = [tuple(words[i:i+2]) for i in range(len(words)-1)]
        all_bigrams.update(bigrams)
    
    total_bigrams = sum(len(c.split()) - 1 for c in completions)
    unique_ratio = len(all_bigrams) / max(total_bigrams, 1)
    
    length_std = np.std(lengths) if len(lengths) > 1 else 0.0
    
    return {
        "unique_ratio": unique_ratio,
        "avg_length": np.mean(lengths),
        "length_std": length_std,
        "num_completions": len(completions),
        "truncated_count": sum(1 for c in completions if len(c) >= 500),
    }


# ==============================================================================
# Dataset loading
# ==============================================================================

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


# ==============================================================================
# Main
# ==============================================================================

def main():
    print("=" * 60)
    print("GRPO Training - Minecraft Mod Conversion on AMD RX 6600 XT")
    print("Using Unsloth + trl GRPOTrainer")
    print("=" * 60)
    print(f"torch: {torch.__version__}, hip: {torch.version.hip}")
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")

    # Load dataset
    data = load_dataset(max_samples=200)
    print(f"Dataset: {len(data)} samples")

    # ------------------------------------------------------------------
    # [1] Load model with Unsloth (FastLanguageModel)
    # ------------------------------------------------------------------
    print("\n[1] Loading model with Unsloth...")
    from unsloth import FastLanguageModel

    model_name = "ibm-granite/granite-4.0-h-micro"
    max_seq_length = 1024
    load_in_4bit = False  # Use fp16 on RX 6600 XT

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=model_name,
        max_seq_length=max_seq_length,
        dtype=torch.float16,
        load_in_4bit=load_in_4bit,
        device_map="cuda",
    )
    print(f"  Model loaded: {model_name}")

    # ------------------------------------------------------------------
    # [2] Apply LoRA adapters
    # ------------------------------------------------------------------
    print("\n[2] Applying LoRA adapters...")
    model = FastLanguageModel.get_peft_model(
        model,
        r=8,
        lora_alpha=16,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
        lora_dropout=0.0,
        bias="none",
        use_gradient_checkpointing="unsloth",
    )
    trainable, all_p = 0, 0
    for p in model.parameters():
        all_p += p.numel()
        if p.requires_grad:
            trainable += p.numel()
    print(f"  Trainable: {trainable:,} / {all_p:,} params")
    print("  LoRA adapters ready")

    # ------------------------------------------------------------------
    # [3] Import trl after model is on GPU
    # ------------------------------------------------------------------
    print("\n[3] Setting up trl GRPO trainer...")
    from trl import GRPOConfig, GRPOTrainer

    # Build prompts list (messages format for chat template)
    prompts_text = [d["prompt"] for d in data]
    references_text = [d["answer"] for d in data]

    # Use a subset for quick test
    num_samples = 50
    max_steps = 10
    num_generations = 4

    print(f"  Using {num_samples} samples, {max_steps} steps, {num_generations} gens/sample")

    # ------------------------------------------------------------------
    # [4] Build GRPO config
    # ------------------------------------------------------------------
    output_dir = "./grpo_output"

    training_args = GRPOConfig(
        output_dir=output_dir,
        per_device_train_batch_size=2,
        gradient_accumulation_steps=2,
        max_steps=max_steps,
        num_train_epochs=1,
        num_generations=4,
        generation_batch_size=4,
        learning_rate=1e-4,
        lr_scheduler_type="cosine",
        warmup_steps=5,
        optim="adamw_torch",
        adam_beta1=0.9,
        adam_beta2=0.99,
        weight_decay=0.01,
        bf16=False,  # AMD RDNA2 doesn't support bf16 well
        fp16=True,
        max_grad_norm=1.0,
        length_column_name=None,
        mask_truncated_completions=True,
        reward_weights=[1.0],
        # [IMPROVEMENT 2] Remove KL loss + raise clipping (MicroCoder-GRPO 2026)
        beta=0.0,  # Zero KL coefficient
        epsilon=0.2,
        epsilon_high=0.3,
        pad_to_multiple_of=None,
        log_completions=True,
        num_completions_to_print=2,
        logging_steps=1,
        logging_first_step=True,
        disable_tqdm=False,
        # Generation kwargs
        max_completion_length=512,
        temperature=0.8,
        top_p=0.95,
        top_k=0,
        repetition_penalty=1.0,
        # Dataset
        shuffle_dataset=True,
        # Misc
        seed=42,
        report_to="none",
    )
    print(f"  GRPOConfig: beta={training_args.beta}, num_generations={training_args.num_generations}")

    # ------------------------------------------------------------------
    # [5] Create custom dataset for trl
    # ------------------------------------------------------------------
    print("  [5a] Creating dataset...", flush=True)
    from datasets import Dataset
    import pandas as pd

    # Build dataset: each row has 'prompt' (str) and 'reference' (str)
    dataset_dict = {
        "prompt": prompts_text[:num_samples],
        "reference": references_text[:num_samples],
    }
    train_dataset = Dataset.from_dict(dataset_dict)
    print(f"  Dataset: {len(train_dataset)} rows", flush=True)

    # ------------------------------------------------------------------
    # [6] Define reward function for GRPOTrainer
    # ------------------------------------------------------------------
    print("  [6a] Defining reward function...", flush=True)
    try:
        def make_reward_func(references):
            def reward_fn(completions, prompts, **kwargs):
                rewards = []
                for c, ref in zip(completions, references):
                    rewards.append(compute_reward(c, ref))
                return np.array(rewards, dtype=np.float32)
            reward_fn.__name__ = "reward_fn"
            return reward_fn

        # Partial with reference column fixed
        print("  [6b] Creating reward_fn...", flush=True)
        reward_fn = make_reward_func(list(train_dataset["reference"]))
        print(f"  [6c] reward_fn created, name={reward_fn.__name__}", flush=True)
    except Exception as e:
        import traceback
        print(f"  [6x] ERROR creating reward_fn: {e}", flush=True)
        traceback.print_exc()
        raise

    # ------------------------------------------------------------------
    # [7] Initialize GRPOTrainer
    # ------------------------------------------------------------------
    print("\n[4] Initializing GRPOTrainer...", flush=True)
    print("  [7a] Creating GRPOTrainer object...", flush=True)
    trainer = GRPOTrainer(
        model=model,
        reward_funcs=reward_fn,
        args=training_args,
        train_dataset=train_dataset,
        processing_class=tokenizer,
        peft_config=None,  # Already applied via FastLanguageModel.get_peft_model
    )
    print("  [7b] GRPOTrainer instantiated", flush=True)

    # ------------------------------------------------------------------
    # [8] Train!
    # ------------------------------------------------------------------
    print("\n[5] Starting GRPO training...", flush=True)
    print(f"  Samples: {num_samples}, Steps: {max_steps}, Gens/step: {num_generations}", flush=True)
    print(f"  Estimated time: {(num_samples / 1 * max_steps * 20) / 60:.0f} min (approx)", flush=True)
    print("  [8a] Calling trainer.train()...", flush=True)
    print("  --- TRAINING START ---", flush=True)
    trainer.train()
    print("  --- TRAINING END ---", flush=True)

    # ------------------------------------------------------------------
    # [9] Save
    # ------------------------------------------------------------------
    print("\n[6] Saving model...")
    trainer.save_model(f"{output_dir}/final")
    tokenizer.save_pretrained(f"{output_dir}/final")
    print(f"  Saved to {output_dir}/final/")

    # ------------------------------------------------------------------
    # [10] Quick eval
    # ------------------------------------------------------------------
    print("\n[7] Quick eval...")
    sample = data[0]
    msg = [{"role": "system", "content": "You are PortKit."},
           {"role": "user", "content": sample["prompt"]}]
    text = tokenizer.apply_chat_template(msg, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(text, return_tensors="pt").to("cuda")
    with torch.no_grad():
        out = model.generate(**inputs, max_new_tokens=200, temperature=0.8, top_p=0.95,
                             do_sample=True, pad_token_id=tokenizer.eos_token_id)
    resp = tokenizer.decode(out[0], skip_special_tokens=True).split("assistant")[-1]
    reward = compute_reward(resp, sample["answer"])
    print(f"  Sample reward: {reward:.3f}")
    print("\n✓ GRPO training complete!")


if __name__ == "__main__":
    main()