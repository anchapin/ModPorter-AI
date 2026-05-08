#!/usr/bin/env python3
"""
Evaluate and compare all phase models.
Generates completions for test samples and computes reward metrics.
"""

import json
import re
import os
import sys
import gc
import time
import numpy as np
from pathlib import Path

os.environ["HSA_OVERRIDE_GFX_VERSION"] = "10.3.0"
os.environ["HF_HUB_DISABLE_XET"] = "1"

import torch
from datasets import Dataset

SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent
DATASET_PATH = PROJECT_ROOT / "ai_engine/mmsd/data/processed/validated_pairs.jsonl"

SYSTEM_PROMPT = (
    "You are PortKit, an expert at converting Minecraft Java Edition mods (Forge) "
    "to Bedrock Edition Add-ons. Given a mod description and Java source code, "
    "first reason through the conversion step by step, then produce the complete "
    "Bedrock Add-on implementation with manifest.json and JavaScript files."
)

BEDROCK_APIS = [
    r'@minecraft/server', r'@minecraft/server-ui', r'@minecraft/server-net',
    r'world\.afterEvents', r'world\.beforeEvents', r'system\.run',
    r'BlockPermutation', r'BlockTypes', r'ItemTypes', r'EntityTypes',
    r'Dimension', r'Player', r'Block', r'ItemStack', r'Container',
    r'MinecraftItemTypes', r'MinecraftBlockTypes',
]

JAVA_ONLY_APIS = [
    r'net\.forge', r'net\.minecraft\.(src|util|block|item|entity|world|server|client)',
    r'ForgeEventBus', r'IEventBus', r'DeferredRegister', r'RegistryObject',
    r'FMLCommonSetupEvent', r'FMLClientSetupEvent', r'@Mod\b', r'@SubscribeEvent',
    r'GameRegistry', r'@EventHandler', r'cpw\.mods', r'net\.minecraftforge\.fml',
]


def _extract_json_blocks(text):
    return re.findall(r"```json\s*(.*?)\s*```", text, re.DOTALL)

def _extract_js_blocks(text):
    return re.findall(r"```(?:javascript|js)\s*([\s\S]*?)```", text)

def _score_manifest_structure(completion, reference):
    comp_blocks = _extract_json_blocks(completion)
    ref_blocks = _extract_json_blocks(reference)
    if not ref_blocks:
        return 0.5
    def find_manifest(blocks):
        for b in blocks:
            if 'format_version' in b or ('header' in b and ('name' in b or 'uuid' in b)):
                return b
        return None
    ref_manifest = find_manifest(ref_blocks)
    comp_manifest = find_manifest(comp_blocks)
    if ref_manifest is None:
        return 0.5
    if comp_manifest is None:
        return 0.0
    score = 0.0
    if 'format_version' in comp_manifest:
        score += 0.15
        ref_ver = re.search(r'format_version["\s:]+([0-9.]+)', ref_manifest)
        comp_ver = re.search(r'format_version["\s:]+([0-9.]+)', comp_manifest)
        if ref_ver and comp_ver and ref_ver.group(1) == comp_ver.group(1):
            score += 0.05
    if 'header' in comp_manifest:
        score += 0.15
        header_fields = ['name', 'description', 'uuid', 'version', 'min_engine_version']
        ref_header = ref_manifest[ref_manifest.find('header'):ref_manifest.find('header') + 500]
        comp_header = comp_manifest[comp_manifest.find('header'):comp_manifest.find('header') + 500]
        matched = sum(1 for f in header_fields if f in comp_header and f in ref_header)
        total = sum(1 for f in header_fields if f in ref_header)
        if total > 0:
            score += 0.10 * (matched / total)
    if 'modules' in comp_manifest:
        score += 0.10
    if 'dependencies' in comp_manifest:
        score += 0.05
    try:
        json.loads(comp_manifest)
        score += 0.15
    except json.JSONDecodeError:
        if comp_manifest.count('{') > 0 and comp_manifest.count('{') == comp_manifest.count('}'):
            score += 0.05
    return min(score, 1.0)


def _score_js_quality(completion, reference):
    comp_js_blocks = _extract_js_blocks(completion)
    ref_js_blocks = _extract_js_blocks(reference)
    if not ref_js_blocks:
        return 0.5
    if not comp_js_blocks:
        return 0.0
    comp_js = "\n".join(comp_js_blocks)
    ref_js = "\n".join(ref_js_blocks)
    score = 0.0
    ref_funcs = set(re.findall(r'function\s+(\w+)', ref_js))
    comp_funcs = set(re.findall(r'function\s+(\w+)', comp_js))
    if ref_funcs:
        func_overlap = len(ref_funcs & comp_funcs) / len(ref_funcs)
        score += 0.20 * func_overlap
    else:
        score += 0.10
    bedrock_apis_found = sum(1 for api in BEDROCK_APIS if re.search(api, comp_js))
    if bedrock_apis_found > 0:
        score += min(0.20, 0.05 * bedrock_apis_found)
    ref_controls = len(re.findall(r'\b(if|for|while|switch|try)\b', ref_js))
    comp_controls = len(re.findall(r'\b(if|for|while|switch|try)\b', comp_js))
    if ref_controls > 0:
        ratio = min(comp_controls / ref_controls, 1.5) / 1.5
        score += 0.15 * ratio
    ref_vars = set(re.findall(r'(?:let|const|var)\s+(\w+)', ref_js))
    comp_vars = set(re.findall(r'(?:let|const|var)\s+(\w+)', comp_js))
    if ref_vars:
        var_overlap = len(ref_vars & comp_vars) / len(ref_vars)
        score += 0.10 * var_overlap
    ref_len = len(ref_js)
    comp_len = len(comp_js)
    if ref_len > 0:
        ratio = comp_len / ref_len
        if 0.3 <= ratio <= 2.0:
            score += 0.15
        elif 0.1 <= ratio <= 3.0:
            score += 0.08
    java_apis_found = sum(1 for api in JAVA_ONLY_APIS if re.search(api, comp_js))
    score -= 0.10 * java_apis_found
    return max(score, 0.0)


def _score_json_validity(completion):
    blocks = _extract_json_blocks(completion)
    if not blocks:
        return 0.0
    total_score = 0.0
    for block in blocks:
        try:
            json.loads(block)
            total_score += 1.0
        except json.JSONDecodeError:
            opens = block.count('{') + block.count('[')
            closes = block.count('}') + block.count(']')
            if opens > 0 and abs(opens - closes) <= 1:
                total_score += 0.5
            elif opens > 0:
                total_score += 0.2
    return min(total_score / len(blocks), 1.0)


def _score_length_ratio(completion, reference):
    ref_len = max(len(reference), 1)
    comp_len = len(completion)
    ratio = comp_len / ref_len
    if ratio < 0.1: return 0.0
    elif ratio < 0.3: return 0.3
    elif 0.5 <= ratio <= 2.0: return 1.0
    elif 0.3 <= ratio < 0.5: return 0.6
    elif 2.0 < ratio <= 3.0: return 0.7
    else: return 0.5


def _score_hallucination_penalty(completion):
    penalty = sum(0.15 for api in JAVA_ONLY_APIS if re.search(api, completion))
    return min(penalty, 1.0)


def _score_bedrock_apis(completion):
    count = sum(1 for api in BEDROCK_APIS if re.search(api, completion))
    return min(count * 0.15, 1.0) if count > 0 else 0.0


def compute_reward(completion, reference):
    comp = completion if isinstance(completion, str) else str(completion)
    ref = reference if isinstance(reference, str) else str(reference)
    manifest = _score_manifest_structure(comp, ref)
    js = _score_js_quality(comp, ref)
    json_v = _score_json_validity(comp)
    bedrock = _score_bedrock_apis(comp)
    length = _score_length_ratio(comp, ref)
    halluc = _score_hallucination_penalty(comp)
    return {
        'total': max(0.20 * manifest + 0.25 * js + 0.15 * json_v + 0.10 * bedrock + 0.15 * length - 0.15 * halluc, 0.0),
        'manifest': manifest,
        'js': js,
        'json_validity': json_v,
        'bedrock_apis': bedrock,
        'length': length,
        'hallucination': halluc,
    }


def load_test_data(n_samples=10):
    pairs = []
    with open(DATASET_PATH) as f:
        for line in f:
            if line.strip():
                pairs.append(json.loads(line))
    # Use val split (last 10%)
    val_pairs = pairs[int(len(pairs) * 0.9):]
    np.random.seed(42)
    indices = np.random.choice(len(val_pairs), min(n_samples, len(val_pairs)), replace=False)
    
    samples = []
    for idx in indices:
        p = val_pairs[idx]
        user = (f"Mod Description: {p['instruction']}\n\nJava Source:\n{p['java_source'][:2000]}\n\n"
                "Convert this to a Bedrock Add-on. First explain your conversion approach, then provide the files.")
        samples.append({"prompt": user, "reference": p["bedrock_source"]})
    return samples


def evaluate_model(model_path, model_name, tokenizer, samples, max_new_tokens=512):
    """Evaluate a model on test samples."""
    from unsloth import FastLanguageModel
    from peft import PeftModel
    
    print(f"\n{'=' * 60}")
    print(f"  Evaluating: {model_name}")
    print(f"  Path: {model_path}")
    print(f"{'=' * 60}")
    
    # Load model
    model, tok = FastLanguageModel.from_pretrained(
        model_name=model_path,
        max_seq_length=1024,
        dtype=torch.float16,
        load_in_4bit=False,
        device_map="cuda",
    )
    model.eval()
    
    all_rewards = []
    all_components = {k: [] for k in ['manifest', 'js', 'json_validity', 'bedrock_apis', 'length', 'hallucination']}
    
    for i, sample in enumerate(samples):
        msgs = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": sample["prompt"][:1200]},
        ]
        text = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        inputs = tok(text, return_tensors="pt", truncation=True, max_length=1024).to("cuda")
        
        with torch.no_grad():
            out = model.generate(
                **inputs, max_new_tokens=max_new_tokens, temperature=0.3, top_p=0.95,
                do_sample=True, pad_token_id=tok.pad_token_id,
            )
        resp = tok.decode(out[0], skip_special_tokens=True)
        if "assistant" in resp:
            resp = resp.split("assistant")[-1].strip()
        
        rewards = compute_reward(resp, sample["reference"])
        all_rewards.append(rewards['total'])
        for k in all_components:
            all_components[k].append(rewards[k])
        
        # Show details for first 3
        if i < 3:
            print(f"\n  Sample {i}: total={rewards['total']:.3f}")
            print(f"    manifest={rewards['manifest']:.2f} js={rewards['js']:.2f} "
                  f"json_v={rewards['json_validity']:.2f} bedrock={rewards['bedrock_apis']:.2f} "
                  f"len={rewards['length']:.2f} halluc={rewards['hallucination']:.2f}")
            has_json = bool(_extract_json_blocks(resp))
            has_js = bool(_extract_js_blocks(resp))
            print(f"    has_manifest_block={has_json} has_js_block={has_js} len={len(resp)} chars")
            print(f"    Preview: {resp[:200]}...")
    
    # Free memory
    del model
    torch.cuda.empty_cache()
    gc.collect()
    
    mean_total = np.mean(all_rewards)
    mean_components = {k: np.mean(v) for k, v in all_components.items()}
    
    print(f"\n  Results ({len(samples)} samples):")
    print(f"    Total reward: {mean_total:.3f} (std={np.std(all_rewards):.3f})")
    print(f"    Components:")
    for k, v in mean_components.items():
        print(f"      {k}: {v:.3f}")
    
    return {'total': mean_total, 'components': mean_components, 'per_sample': all_rewards}


def main():
    print("=" * 70)
    print("  Phase Comparison Evaluation")
    print("=" * 70)
    
    samples = load_test_data(n_samples=10)
    print(f"  Loaded {len(samples)} test samples")
    
    # Models to evaluate
    models = [
        {
            'path': str(SCRIPT_DIR / "grpo_output_phase3/final"),
            'name': 'Phase 3 (0.5B, dense reward)',
        },
        {
            'path': str(SCRIPT_DIR / "phase4b_output_1.5b/final"),
            'name': 'Phase 4b (1.5B, SFT+GRPO, compl=512)',
        },
        {
            'path': str(SCRIPT_DIR / "phase5_output/final"),
            'name': 'Phase 5 (1.5B, curriculum GRPO)',
        },
    ]
    
    # Also evaluate base model for baseline
    results = {}
    
    for m in models:
        if not Path(m['path']).exists():
            print(f"\n  SKIPPING {m['name']}: path not found ({m['path']})")
            continue
        try:
            r = evaluate_model(m['path'], m['name'], None, samples)
            results[m['name']] = r
        except Exception as e:
            print(f"\n  ERROR evaluating {m['name']}: {e}")
            import traceback
            traceback.print_exc()
    
    # Summary
    print("\n" + "=" * 70)
    print("  COMPARISON SUMMARY")
    print("=" * 70)
    print(f"  {'Model':<40} {'Total':>8} {'Manifest':>10} {'JS':>8} {'JSON':>8} {'Bedrock':>8} {'Halluc':>8}")
    print("  " + "-" * 90)
    for name, r in results.items():
        c = r['components']
        print(f"  {name:<40} {r['total']:>8.3f} {c['manifest']:>10.3f} {c['js']:>8.3f} {c['json_validity']:>8.3f} {c['bedrock_apis']:>8.3f} {c['hallucination']:>8.3f}")


if __name__ == "__main__":
    main()
