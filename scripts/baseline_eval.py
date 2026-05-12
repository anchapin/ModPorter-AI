#!/usr/bin/env python3
"""Baseline eval: base model (no LoRA) on same sample as post-training eval."""

import json
import re
import sys
import os
from pathlib import Path
import torch

os.environ["HSA_OVERRIDE_GFX_VERSION"] = "10.3.0"
os.environ["HF_HUB_DISABLE_XET"] = "1"

SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent
DATASET_PATH = PROJECT_ROOT / "ai_engine/mmsd/data/processed/validated_pairs.jsonl"

def _simple_tokenize(text):
    text = re.sub(r"```[^`]*```", "", text)
    text = re.sub(r"[^\w\s]", " ", text)
    return [t.lower() for t in text.split() if t.strip()]

def _bleu_like(reference, hypothesis):
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

def _extract_manifest(text):
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

def compute_reward(completion, reference):
    w = [0.30, 0.25, 0.20, 0.15, 0.10]
    manifest = _extract_manifest(completion)
    r1 = 1.0 if manifest else 0.0
    r2 = _bleu_like(reference, completion)
    word_count = len(completion.split())
    r3 = min(1.0, word_count / 50)
    key_terms = ["block", "item", "entity", "recipe", "biome", "dimension", "structure"]
    completion_lower = completion.lower()
    r4 = sum(1 for term in key_terms if term in completion_lower) / len(key_terms)
    code_blocks = re.findall(r"```[\s\S]*?```", completion)
    r5 = min(1.0, len(code_blocks) / 3)
    return w[0]*r1 + w[1]*r2 + w[2]*r3 + w[3]*r4 + w[4]*r5

def build_prompt(row):
    system = ("You are PortKit, an expert at converting Minecraft Java Edition mods (Forge) "
              "to Bedrock Edition Add-ons. Given a mod description and Java source code, "
              "first reason through the platform map, then produce the Bedrock Add-on implementation.")
    user = (f"Mod Description: {row['instruction']}\n\nJava Source:\n{row['java_source']}\n\n"
            "Convert this to a Bedrock Add-on. First explain your conversion approach, then provide the files.")
    return system + "\n\n" + user

def main():
    print("=" * 60)
    print("BASELINE EVAL: Base model (no LoRA)")
    print("=" * 60)

    with open(DATASET_PATH) as f:
        data = [json.loads(line) for line in f]

    sample = data[0]
    prompt_text = build_prompt(sample)
    reference = sample["bedrock_source"]

    print(f"\nPrompt (first 100 chars): {prompt_text[:100]}...")
    print(f"Reference (first 100 chars): {reference[:100]}...")

    from unsloth import FastLanguageModel
    model_name = "unsloth/Qwen2.5-Coder-0.5B-Instruct"

    print(f"\nLoading base model: {model_name}")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=model_name,
        max_seq_length=2048,
        dtype=torch.float16,
        load_in_4bit=True,
        device_map="cuda",
        attn_implementation="eager",
    )
    print("  Base model loaded (no LoRA)")

    print("\nGenerating completion...")
    msg = [{"role": "system", "content": "You are PortKit."},
           {"role": "user", "content": prompt_text}]
    text = tokenizer.apply_chat_template(msg, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(text, return_tensors="pt").to("cuda")

    with torch.no_grad():
        out = model.generate(
            **inputs,
            max_new_tokens=150,
            temperature=0.8,
            top_p=0.95,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id,
            use_cache=False
        )

    resp = tokenizer.decode(out[0], skip_special_tokens=True).split("assistant")[-1]
    print(f"\nCompletion (first 300 chars):\n{resp[:300]}...")
    print(f"\nCompletion length: {len(resp)} chars, {len(resp.split())} words")

    reward = compute_reward(resp, reference)
    print(f"\n{'='*60}")
    print(f"BASELINE REWARD:       {reward:.4f}")
    print(f"POST-TRAINING REWARD:  0.039")
    print(f"{'='*60}")

    diff = 0.039 - reward
    if diff > 0:
        print(f"\n→ Training improved reward by {diff:.4f}")
    elif diff < 0:
        print(f"\n→ Training decreased reward by {-diff:.4f}")
    else:
        print(f"\n→ No change in reward")

if __name__ == "__main__":
    main()