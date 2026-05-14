#!/usr/bin/env python3
"""
Baseline vs GRPO-trained model evaluation
Compares IBM Granite-4.0-H-Micro before and after GRPO training
"""

import json
import re
import os
import sys
from pathlib import Path
from typing import List

os.environ["HSA_OVERRIDE_GFX_VERSION"] = "10.3.0"
os.environ["HF_HUB_DISABLE_XET"] = "1"

import torch
import numpy as np

SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent
AI_ENGINE_PATH = PROJECT_ROOT / "ai-engine"
if AI_ENGINE_PATH.exists() and str(AI_ENGINE_PATH) not in sys.path:
    sys.path.insert(0, str(AI_ENGINE_PATH))

DATASET_PATH = PROJECT_ROOT / "ai-engine/mmsd/data/processed/validated_pairs.jsonl"
CHECKPOINT_PATH = PROJECT_ROOT / "scripts/grpo_output/final"


def load_dataset(max_samples=20):
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
            comp_ver = re.search(r'format_version["\s:]+([0-9.]+)', ref_manifest)
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


def evaluate_model(model, tokenizer, data, model_name):
    rewards = []
    for i, sample in enumerate(data):
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
                pad_token_id=tokenizer.eos_token_id,
            )
        resp = tokenizer.decode(out[0], skip_special_tokens=True).split("assistant")[-1]
        reward = compute_reward(resp, sample["answer"])
        rewards.append(reward)

        if i < 3:
            print(f"\n--- Sample {i + 1} ---")
            print(f"Prompt (truncated): {sample['prompt'][:100]}...")
            print(f"Response (truncated): {resp[:200]}...")
            print(f"Reward: {reward:.3f}")

    return np.mean(rewards), np.std(rewards)


def main():
    print("=" * 60)
    print("Baseline vs GRPO-Trained Model Evaluation")
    print("=" * 60)

    if not torch.cuda.is_available():
        print("ERROR: CUDA not available")
        return

    print(f"torch: {torch.__version__}, hip: {torch.version.hip}")
    print(f"GPU: {torch.cuda.get_device_name(0)}")

    data = load_dataset(max_samples=20)
    print(f"Dataset: {len(data)} samples")

    print("\n" + "=" * 40)
    print("EVALUATION 1: Baseline Granite-4.0-H-Micro")
    print("=" * 40)

    from unsloth import FastLanguageModel

    model_name = "ibm-granite/granite-4.0-h-micro"

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=model_name,
        max_seq_length=1024,
        dtype=torch.float16,
        load_in_4bit=False,
        device_map="cuda",
        attn_implementation="eager",
    )
    print(f"Loaded: {model_name}")

    mean, std = evaluate_model(model, tokenizer, data, model_name)
    baseline_reward = mean
    print(f"\n>>> Baseline reward: {mean:.4f} ± {std:.4f}")

    del model
    torch.cuda.empty_cache()
    gc = __import__("gc")
    gc.collect()

    print("\n" + "=" * 40)
    print("EVALUATION 2: GRPO-Trained Model")
    print("=" * 40)

    if CHECKPOINT_PATH.exists():
        model, tokenizer = FastLanguageModel.from_pretrained(
            model_name=str(CHECKPOINT_PATH),
            max_seq_length=1024,
            dtype=torch.float16,
            load_in_4bit=False,
            device_map="cuda",
            attn_implementation="eager",
        )
        print(f"Loaded: {CHECKPOINT_PATH}")

        mean, std = evaluate_model(model, tokenizer, data, "GRPO-Trained")
        grpo_reward = mean
        print(f"\n>>> GRPO reward: {mean:.4f} ± {std:.4f}")

        delta = grpo_reward - baseline_reward
        print(f"\n>>> Delta: {delta:+.4f} ({'IMPROVED' if delta > 0 else 'REGRESSED'})")
    else:
        print(f"WARNING: GRPO checkpoint not found at {CHECKPOINT_PATH}")

    print("\n" + "=" * 60)
    print("Evaluation complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
