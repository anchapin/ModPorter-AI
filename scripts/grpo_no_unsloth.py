#!/usr/bin/env python3
"""
GRPO RL Training for Minecraft Java-to-Bedrock Mod Conversion
Using standard transformers + trl GRPOTrainer on AMD RX 6600 XT (gfx1032/RDNA2)

Usage:
    HSA_OVERRIDE_GFX_VERSION=10.3.0 HF_HUB_DISABLE_XET=1 python grpo_no_unsloth.py
"""

import json
import re
import os
import sys
import gc
from pathlib import Path
from typing import List

os.environ["HSA_OVERRIDE_GFX_VERSION"] = "10.3.0"
os.environ["HF_HUB_DISABLE_XET"] = "1"

import torch
import numpy as np

SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent
AI_ENGINE_PATH = PROJECT_ROOT / "ai_engine"
if AI_ENGINE_PATH.exists() and str(AI_ENGINE_PATH) not in sys.path:
    sys.path.insert(0, str(AI_ENGINE_PATH))

DATASET_PATH = PROJECT_ROOT / "ai_engine/mmsd/data/processed/validated_pairs.jsonl"


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
        except:
            pass
    return 0.0


def _score_content_density(completion: str) -> float:
    code_blocks = re.findall(r"```[\s\S]*?```", completion)
    if not code_blocks:
        return 0.0
    total_chars = sum(len(b) for b in code_blocks)
    return min(total_chars / 500.0, 1.0)


def compute_reward(completion: str, reference: str) -> float:
    completion_text = completion if isinstance(completion, str) else str(completion)
    reference_text = reference if isinstance(reference, str) else str(reference)

    s = _score_structural_alignment(completion_text, reference_text)
    l = _score_length_ratio(completion_text, reference_text)
    v = _score_json_validity(completion_text)
    d = _score_content_density(completion_text)

    return 0.35 * s + 0.20 * l + 0.25 * v + 0.20 * d


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


def main():
    print("=" * 60)
    print("GRPO Training - Minecraft Mod Conversion on AMD RX 6600 XT")
    print("Using standard transformers + trl GRPOTrainer")
    print("=" * 60)
    print(f"torch: {torch.__version__}, hip: {torch.version.hip}")
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")

    data = load_dataset(max_samples=200)
    print(f"Dataset: {len(data)} samples")

    print("\n[1] Loading model with standard transformers...")
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    import peft

    model_name = "ibm-granite/granite-4.0-h-micro"
    max_seq_length = 1024

    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        torch_dtype=torch.float16,
        device_map="cuda",
        trust_remote_code=True,
    )
    print(f"  Model loaded: {model_name}")

    print("\n[2] Applying LoRA adapters...")
    lora_config = peft.LoraConfig(
        r=8,
        lora_alpha=16,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
        lora_dropout=0.0,
        bias="none",
        task_type="CAUSAL_LM",
    )
    model = peft.get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    print("\n[3] Setting up trl GRPO trainer...")
    from trl import GRPOConfig, GRPOTrainer
    from datasets import Dataset

    prompts_text = [d["prompt"] for d in data]
    references_text = [d["answer"] for d in data]

    num_samples = 50
    max_steps = 10
    num_generations = 4

    print(f"  Using {num_samples} samples, {max_steps} steps, {num_generations} gens/sample")

    output_dir = "./grpo_output"

    training_args = GRPOConfig(
        output_dir=output_dir,
        per_device_train_batch_size=2,
        gradient_accumulation_steps=2,
        max_steps=max_steps,
        num_train_epochs=1,
        num_generations=num_generations,
        generation_batch_size=4,
        learning_rate=1e-4,
        lr_scheduler_type="cosine",
        warmup_steps=5,
        optim="adamw_torch",
        adam_beta1=0.9,
        adam_beta2=0.99,
        weight_decay=0.01,
        bf16=False,
        fp16=True,
        max_grad_norm=1.0,
        length_column_name=None,
        mask_truncated_completions=True,
        reward_weights=[1.0],
        beta=0.0,
        epsilon=0.2,
        epsilon_high=0.3,
        pad_to_multiple_of=None,
        log_completions=True,
        num_completions_to_print=2,
        logging_steps=1,
        logging_first_step=True,
        disable_tqdm=False,
        max_completion_length=512,
        temperature=0.8,
        top_p=0.95,
        top_k=0,
        repetition_penalty=1.0,
        shuffle_dataset=True,
        seed=42,
        report_to="none",
    )

    dataset_dict = {
        "prompt": prompts_text[:num_samples],
        "reference": references_text[:num_samples],
    }
    train_dataset = Dataset.from_dict(dataset_dict)
    print(f"  Dataset: {len(train_dataset)} rows")

    def make_reward_func(references):
        def reward_fn(completions, prompts, **kwargs):
            rewards = []
            for c, ref in zip(completions, references):
                rewards.append(compute_reward(c, ref))
            return np.array(rewards, dtype=np.float32)

        reward_fn.__name__ = "reward_fn"
        return reward_fn

    reward_fn = make_reward_func(list(train_dataset["reference"]))

    print("\n[4] Initializing GRPOTrainer...")
    trainer = GRPOTrainer(
        model=model,
        reward_funcs=reward_fn,
        args=training_args,
        train_dataset=train_dataset,
        processing_class=tokenizer,
    )
    print("  GRPOTrainer instantiated")

    print("\n[5] Starting GRPO training...")
    print(f"  Samples: {num_samples}, Steps: {max_steps}, Gens/step: {num_generations}")
    print("  --- TRAINING START ---")
    trainer.train()
    print("  --- TRAINING END ---")

    print("\n[6] Saving model...")
    trainer.save_model(f"{output_dir}/final")
    tokenizer.save_pretrained(f"{output_dir}/final")
    print(f"  Saved to {output_dir}/final/")

    print("\n[7] Quick eval...")
    sample = data[0]
    msgs = [
        {"role": "system", "content": "You are PortKit."},
        {"role": "user", "content": sample["prompt"]},
    ]
    text = tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(text, return_tensors="pt").to("cuda")
    with torch.no_grad():
        out = model.generate(
            **inputs,
            max_new_tokens=512,
            temperature=0.8,
            top_p=0.95,
            do_sample=True,
            pad_token_id=tokenizer.pad_token_id,
        )
    resp = tokenizer.decode(out[0], skip_special_tokens=True).split("assistant")[-1]
    reward = compute_reward(resp, sample["answer"])
    print(f"  Sample reward: {reward:.3f}")
    print("\n✓ GRPO training complete!")


if __name__ == "__main__":
    main()
