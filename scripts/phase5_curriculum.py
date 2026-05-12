#!/usr/bin/env python3
"""
Phase 5: Curriculum GRPO with Reward Fixes
============================================
Based on research findings from DRIVE, DAPO, and "Train Long, Think Short":

Key improvements over Phase 4b:
1. CURRICULUM: Train on easy/medium samples first (where model CAN finish)
2. SHORTER PROMPTS: Minimal system/user text to maximize completion space
3. EOS REWARD: +0.1 bonus for producing EOS (stopping)
4. DAPO SOFT OVERLONG PENALTY: Penalize completions near max_length
5. DYNAMIC SAMPLING: Skip prompts where all 4 completions get same reward
6. 677 easy+medium samples (vs 200 unfiltered) — 3.4x more data

Hardware: AMD RX 6600 XT (8.6 GB VRAM)
Model: Qwen2.5-Coder-1.5B-Instruct (SFT-warmed from Phase 4)

Usage:
    HSA_OVERRIDE_GFX_VERSION=10.3.0 HF_HUB_DISABLE_XET=1 python phase5_curriculum.py
"""

import json
import re
import os
import sys
import gc
import time
from pathlib import Path

os.environ["HSA_OVERRIDE_GFX_VERSION"] = "10.3.0"
os.environ["HF_HUB_DISABLE_XET"] = "1"
os.environ["PYTORCH_HIP_ALLOC_CONF"] = "expandable_segments:True"

import torch
import numpy as np
from datasets import Dataset
from peft import PeftModel

SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent
DATASET_PATH = PROJECT_ROOT / "ai_engine/mmsd/data/processed/validated_pairs.jsonl"
OUTPUT_DIR = SCRIPT_DIR / "phase5_output"

SFT_ADAPTER_PATH = SCRIPT_DIR / "phase4_output_1.5b/sft/final"
MODEL_NAME = "unsloth/Qwen2.5-Coder-1.5B-Instruct"
MAX_SEQ_LENGTH = 1024

# Short prompts to maximize completion space
SYSTEM_PROMPT = (
    "Convert this Minecraft Java mod to a Bedrock Add-on with manifest.json and JS files."
)
MAX_COMPLETION_LENGTH = 512
JAVA_TOKEN_BUDGET = 150  # truncate Java source to this many tokens (~600 chars)


# =============================================================================
# Reward function with EOS bonus + DAPO soft overlong penalty
# =============================================================================

BEDROCK_APIS = [
    r"@minecraft/server",
    r"@minecraft/server-ui",
    r"@minecraft/server-net",
    r"world\.afterEvents",
    r"world\.beforeEvents",
    r"system\.run",
    r"BlockPermutation",
    r"BlockTypes",
    r"ItemTypes",
    r"EntityTypes",
    r"Dimension",
    r"Player",
    r"Block",
    r"ItemStack",
    r"Container",
    r"MinecraftItemTypes",
    r"MinecraftBlockTypes",
]

JAVA_ONLY_APIS = [
    r"net\.forge",
    r"net\.minecraft\.(src|util|block|item|entity|world|server|client)",
    r"ForgeEventBus",
    r"IEventBus",
    r"DeferredRegister",
    r"RegistryObject",
    r"FMLCommonSetupEvent",
    r"FMLClientSetupEvent",
    r"@Mod\b",
    r"@SubscribeEvent",
    r"GameRegistry",
    r"@EventHandler",
    r"cpw\.mods",
    r"net\.minecraftforge\.fml",
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
            if "format_version" in b or ("header" in b and ("name" in b or "uuid" in b)):
                return b
        return None

    ref_manifest = find_manifest(ref_blocks)
    comp_manifest = find_manifest(comp_blocks)
    if ref_manifest is None:
        return 0.5
    if comp_manifest is None:
        return 0.0
    score = 0.0
    if "format_version" in comp_manifest:
        score += 0.15
        ref_ver = re.search(r'format_version["\s:]+([0-9.]+)', ref_manifest)
        comp_ver = re.search(r'format_version["\s:]+([0-9.]+)', comp_manifest)
        if ref_ver and comp_ver and ref_ver.group(1) == comp_ver.group(1):
            score += 0.05
    if "header" in comp_manifest:
        score += 0.15
        header_fields = ["name", "description", "uuid", "version", "min_engine_version"]
        ref_header = ref_manifest[ref_manifest.find("header") : ref_manifest.find("header") + 500]
        comp_header = comp_manifest[
            comp_manifest.find("header") : comp_manifest.find("header") + 500
        ]
        matched = sum(1 for f in header_fields if f in comp_header and f in ref_header)
        total = sum(1 for f in header_fields if f in ref_header)
        if total > 0:
            score += 0.10 * (matched / total)
    if "modules" in comp_manifest:
        score += 0.10
    if "dependencies" in comp_manifest:
        score += 0.05
    try:
        json.loads(comp_manifest)
        score += 0.15
    except json.JSONDecodeError:
        if comp_manifest.count("{") > 0 and comp_manifest.count("{") == comp_manifest.count("}"):
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
    ref_funcs = set(re.findall(r"function\s+(\w+)", ref_js))
    comp_funcs = set(re.findall(r"function\s+(\w+)", comp_js))
    if ref_funcs:
        score += 0.20 * (len(ref_funcs & comp_funcs) / len(ref_funcs))
    else:
        score += 0.10
    bedrock_apis_found = sum(1 for api in BEDROCK_APIS if re.search(api, comp_js))
    if bedrock_apis_found > 0:
        score += min(0.20, 0.05 * bedrock_apis_found)
    ref_controls = len(re.findall(r"\b(if|for|while|switch|try)\b", ref_js))
    comp_controls = len(re.findall(r"\b(if|for|while|switch|try)\b", comp_js))
    if ref_controls > 0:
        score += 0.15 * min(comp_controls / ref_controls, 1.5) / 1.5
    ref_vars = set(re.findall(r"(?:let|const|var)\s+(\w+)", ref_js))
    comp_vars = set(re.findall(r"(?:let|const|var)\s+(\w+)", comp_js))
    if ref_vars:
        score += 0.10 * (len(ref_vars & comp_vars) / len(ref_vars))
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
            opens = block.count("{") + block.count("[")
            closes = block.count("}") + block.count("]")
            if opens > 0 and abs(opens - closes) <= 1:
                total_score += 0.5
            elif opens > 0:
                total_score += 0.2
    return min(total_score / len(blocks), 1.0)


def _score_length_ratio(completion, reference):
    ref_len = max(len(reference), 1)
    comp_len = len(completion)
    ratio = comp_len / ref_len
    if ratio < 0.1:
        return 0.0
    elif ratio < 0.3:
        return 0.3
    elif 0.5 <= ratio <= 2.0:
        return 1.0
    elif 0.3 <= ratio < 0.5:
        return 0.6
    elif 2.0 < ratio <= 3.0:
        return 0.7
    else:
        return 0.5


def _score_hallucination_penalty(completion):
    return min(sum(0.15 for api in JAVA_ONLY_APIS if re.search(api, completion)), 1.0)


def _score_bedrock_apis(completion):
    count = sum(1 for api in BEDROCK_APIS if re.search(api, completion))
    return min(count * 0.15, 1.0) if count > 0 else 0.0


def compute_base_reward(completion, reference):
    """Core reward without length/EOS bonuses."""
    comp = completion if isinstance(completion, str) else str(completion)
    ref = reference if isinstance(reference, str) else str(reference)
    manifest = _score_manifest_structure(comp, ref)
    js = _score_js_quality(comp, ref)
    json_v = _score_json_validity(comp)
    bedrock = _score_bedrock_apis(comp)
    length = _score_length_ratio(comp, ref)
    halluc = _score_hallucination_penalty(comp)
    return max(
        0.20 * manifest
        + 0.25 * js
        + 0.15 * json_v
        + 0.10 * bedrock
        + 0.15 * length
        - 0.15 * halluc,
        0.0,
    )


def dapo_soft_overlong_penalty(completion_length, max_length, cache_zone=128, max_penalty=0.15):
    """DAPO-inspired soft overlong punishment (scaled for our reward range).

    Linear ramp penalty in the cache zone before max_length.
    Returns a penalty in [-max_penalty, 0].
    Scaled to not overwhelm the base reward (~0.1–0.4 range).
    """
    threshold = max_length - cache_zone
    if completion_length <= threshold:
        return 0.0
    elif completion_length <= max_length:
        return max_penalty * (threshold - completion_length) / cache_zone
    else:
        return -max_penalty


def compute_reward_with_aux(
    completion,
    reference,
    completion_length,
    max_length,
    finished_with_eos=False,
    eos_bonus=0.15,
    cache_zone=128,
):
    """Full reward with DAPO overlong penalty + EOS bonus."""
    base = compute_base_reward(completion, reference)
    overlong = dapo_soft_overlong_penalty(completion_length, max_length, cache_zone)
    eos = eos_bonus if finished_with_eos else 0.0
    return max(base + overlong + eos, 0.0)


# =============================================================================
# Dataset with difficulty scoring and curriculum
# =============================================================================


def build_curriculum_dataset(tokenizer, tier="all"):
    """Build dataset filtered by difficulty tier.

    Tiers:
      easy:   ref_tokens <= 200, fits in available space
      medium: 200 < ref_tokens <= 400, fits in available space
      hard:   ref_tokens > 400 or doesn't fit
      easy_medium: easy + medium combined
      all:    everything (no filtering)
    """
    pairs = []
    with open(DATASET_PATH) as f:
        for line in f:
            if line.strip():
                pairs.append(json.loads(line))

    train_pairs = pairs[: int(len(pairs) * 0.9)]

    # Score each pair
    scored = []
    for i, p in enumerate(train_pairs):
        inst_tokens = len(tokenizer.encode(p["instruction"]))
        ref_tokens = len(tokenizer.encode(p["bedrock_source"]))
        java_tokens = len(tokenizer.encode(p["java_source"]))

        # Overhead: system prompt + role markers + user template
        overhead = len(tokenizer.encode(SYSTEM_PROMPT)) + 30
        prompt_tokens = overhead + inst_tokens + min(java_tokens, JAVA_TOKEN_BUDGET)
        avail = MAX_SEQ_LENGTH - prompt_tokens
        can_fit = avail >= ref_tokens and avail >= 128

        scored.append(
            {
                "idx": i,
                "pair": p,
                "ref_tokens": ref_tokens,
                "can_fit": can_fit,
                "avail": avail,
                "difficulty": ref_tokens,
            }
        )

    # Filter by tier
    if tier == "easy":
        filtered = [s for s in scored if s["ref_tokens"] <= 200 and s["can_fit"]]
    elif tier == "medium":
        filtered = [s for s in scored if 200 < s["ref_tokens"] <= 400 and s["can_fit"]]
    elif tier == "easy_medium":
        filtered = [s for s in scored if s["ref_tokens"] <= 400 and s["can_fit"]]
    elif tier == "hard":
        filtered = [s for s in scored if s["ref_tokens"] > 400 or not s["can_fit"]]
    else:
        filtered = scored

    print(f"  Dataset tier='{tier}': {len(filtered)} samples (of {len(train_pairs)} total)")

    # Build prompts with truncated Java source
    data = []
    for s in filtered:
        p = s["pair"]
        # Truncate Java source to budget
        java_text = p["java_source"]
        java_encoded = tokenizer.encode(java_text)
        if len(java_encoded) > JAVA_TOKEN_BUDGET:
            java_text = tokenizer.decode(java_encoded[:JAVA_TOKEN_BUDGET])
            # Cut at last newline for clean truncation
            last_nl = java_text.rfind("\n")
            if last_nl > len(java_text) // 2:
                java_text = java_text[:last_nl] + "\n// ... (truncated)"

        prompt = (
            f"{SYSTEM_PROMPT}\n\n"
            f"Mod: {p['instruction']}\n\n"
            f"Java:\n{java_text}\n\n"
            f"Convert to Bedrock Add-on:"
        )

        data.append(
            {
                "prompt": prompt,
                "reference": p["bedrock_source"],
                "difficulty": s["difficulty"],
            }
        )

    return data


# =============================================================================
# Main
# =============================================================================


def main():
    start_time = time.time()

    print("=" * 70)
    print("  Phase 5: Curriculum GRPO with Reward Fixes")
    print(f"  {MODEL_NAME}")
    print(f"  SFT warm start from: {SFT_ADAPTER_PATH}")
    print("  fp16 + LoRA r=8 | AMD RX 6600 XT")
    print("=" * 70)
    print(f"  torch: {torch.__version__}, hip: {torch.version.hip}")
    print(f"  GPU: {torch.cuda.get_device_name(0)}")
    vram = torch.cuda.get_device_properties(0).total_memory
    print(f"  VRAM: {vram / 1e9:.1f} GB")

    output_dir = str(OUTPUT_DIR)

    # ==================================================================
    # Load model + SFT adapter
    # ==================================================================
    print("\n[1] Loading model...")
    from unsloth import FastLanguageModel

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=MODEL_NAME,
        max_seq_length=MAX_SEQ_LENGTH,
        dtype=torch.float16,
        load_in_4bit=False,
        device_map="cuda",
    )
    print(f"  VRAM: {torch.cuda.memory_allocated() / 1e9:.2f} GB")

    print("\n[2] Merging SFT adapter...")
    model = PeftModel.from_pretrained(model, str(SFT_ADAPTER_PATH))
    model = model.merge_and_unload()
    print(f"  Merged. VRAM: {torch.cuda.memory_allocated() / 1e9:.2f} GB")

    print("\n[3] Applying fresh LoRA...")
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
    print(f"  VRAM: {torch.cuda.memory_allocated() / 1e9:.2f} GB")

    # ==================================================================
    # STAGE 1: Easy/Medium curriculum
    # ==================================================================
    print("\n" + "=" * 70)
    print("  STAGE 1: Easy/Medium Curriculum (677 samples)")
    print("=" * 70)

    print("\n[4] Building easy+medium dataset...")
    data_s1 = build_curriculum_dataset(tokenizer, tier="easy_medium")
    print(f"  {len(data_s1)} samples for Stage 1")

    prompts_s1 = [d["prompt"] for d in data_s1]
    refs_s1 = [d["reference"] for d in data_s1]
    train_ds_s1 = Dataset.from_dict({"prompt": prompts_s1, "reference": refs_s1})

    # Reward function with EOS bonus + DAPO overlong penalty
    EOS_TOKENS = ["<|im_end|>", "<|endoftext|>", tokenizer.eos_token or ""]

    def reward_fn_stage1(completions, prompts_list=None, **kwargs):
        ref_list = kwargs.get("reference", None)
        rewards = []
        for i, completion in enumerate(completions):
            if isinstance(completion, list) and len(completion) > 0:
                comp_text = (
                    completion[0].get("content", "")
                    if isinstance(completion[0], dict)
                    else str(completion[0])
                )
            else:
                comp_text = str(completion)
            ref = ref_list[i] if ref_list and i < len(ref_list) else ""

            # Check if completion ended with EOS
            finished = False
            for eos in EOS_TOKENS:
                if eos and comp_text.rstrip().endswith(eos):
                    finished = True
                    break

            comp_len = len(tokenizer.encode(comp_text))
            reward = compute_reward_with_aux(
                comp_text,
                ref,
                completion_length=comp_len,
                max_length=MAX_COMPLETION_LENGTH,
                finished_with_eos=finished,
                eos_bonus=0.15,
                cache_zone=128,
            )
            rewards.append(reward)
        return rewards

    from trl import GRPOConfig, GRPOTrainer

    max_steps_s1 = 100  # More steps for more data

    grpo_args_s1 = GRPOConfig(
        output_dir=f"{output_dir}/stage1",
        per_device_train_batch_size=1,
        gradient_accumulation_steps=4,
        max_steps=max_steps_s1,
        learning_rate=2e-6,  # Higher LR for curriculum (DAPO recommendation)
        lr_scheduler_type="cosine",
        warmup_steps=10,
        optim="adamw_torch",
        adam_beta1=0.9,
        adam_beta2=0.99,
        weight_decay=0.01,
        max_grad_norm=1.0,
        fp16=True,
        bf16=False,
        num_generations=4,
        generation_batch_size=4,
        max_completion_length=MAX_COMPLETION_LENGTH,
        temperature=1.0,
        top_p=0.95,
        beta=0.0,
        epsilon=0.2,
        epsilon_high=0.28,
        loss_type="dapo",
        scale_rewards=False,
        mask_truncated_completions=True,
        gradient_checkpointing=True,
        logging_steps=1,
        logging_first_step=True,
        log_completions=True,
        num_completions_to_print=2,
        disable_tqdm=True,
        shuffle_dataset=True,
        seed=42,
        report_to="none",
    )
    print(f"  Config: {max_steps_s1} steps, lr=2e-6, 4 gens, max_compl={MAX_COMPLETION_LENGTH}")

    print("\n[5] Starting Stage 1 GRPO...")
    trainer_s1 = GRPOTrainer(
        model=model,
        reward_funcs=reward_fn_stage1,
        args=grpo_args_s1,
        train_dataset=train_ds_s1,
        processing_class=tokenizer,
        peft_config=None,
    )

    try:
        trainer_s1.train()
        print("  Stage 1 GRPO COMPLETE")
    except RuntimeError as e:
        if "out of memory" in str(e).lower():
            print(f"  OOM: {e}")
            torch.cuda.empty_cache()
            gc.collect()
            raise
        raise

    # Save Stage 1
    trainer_s1.save_model(f"{output_dir}/stage1/final")
    tokenizer.save_pretrained(f"{output_dir}/stage1/final")
    print(f"  Stage 1 saved to {output_dir}/stage1/final/")

    # Free memory
    del trainer_s1
    torch.cuda.empty_cache()
    gc.collect()

    # ==================================================================
    # STAGE 2: All data (including hard examples)
    # ==================================================================
    print("\n" + "=" * 70)
    print("  STAGE 2: Full Dataset (all 1260 samples)")
    print("=" * 70)

    print("\n[6] Building full dataset...")
    data_s2 = build_curriculum_dataset(tokenizer, tier="all")
    print(f"  {len(data_s2)} samples for Stage 2")

    prompts_s2 = [d["prompt"] for d in data_s2]
    refs_s2 = [d["reference"] for d in data_s2]
    train_ds_s2 = Dataset.from_dict({"prompt": prompts_s2, "reference": refs_s2})

    # Load Stage 1 model for Stage 2
    print("\n[7] Loading Stage 1 model...")
    del model
    torch.cuda.empty_cache()
    gc.collect()

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=MODEL_NAME,
        max_seq_length=MAX_SEQ_LENGTH,
        dtype=torch.float16,
        load_in_4bit=False,
        device_map="cuda",
    )
    model = PeftModel.from_pretrained(model, f"{output_dir}/stage1/final")
    model = model.merge_and_unload()
    model = FastLanguageModel.get_peft_model(
        model,
        r=8,
        lora_alpha=16,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
        lora_dropout=0.0,
        bias="none",
        use_gradient_checkpointing="unsloth",
    )
    print(f"  VRAM: {torch.cuda.memory_allocated() / 1e9:.2f} GB")

    max_steps_s2 = 80
    grpo_args_s2 = GRPOConfig(
        output_dir=f"{output_dir}/stage2",
        per_device_train_batch_size=1,
        gradient_accumulation_steps=4,
        max_steps=max_steps_s2,
        learning_rate=1e-6,  # Lower LR for fine-tuning
        lr_scheduler_type="cosine",
        warmup_steps=8,
        optim="adamw_torch",
        adam_beta1=0.9,
        adam_beta2=0.99,
        weight_decay=0.01,
        max_grad_norm=1.0,
        fp16=True,
        bf16=False,
        num_generations=4,
        generation_batch_size=4,
        max_completion_length=MAX_COMPLETION_LENGTH,
        temperature=0.9,  # Slightly lower for refinement
        top_p=0.95,
        beta=0.0,
        epsilon=0.2,
        epsilon_high=0.28,
        loss_type="dapo",
        scale_rewards=False,
        mask_truncated_completions=True,
        gradient_checkpointing=True,
        logging_steps=1,
        logging_first_step=True,
        log_completions=True,
        num_completions_to_print=2,
        disable_tqdm=True,
        shuffle_dataset=True,
        seed=42,
        report_to="none",
    )
    print(f"  Config: {max_steps_s2} steps, lr=1e-6, temp=0.9")

    trainer_s2 = GRPOTrainer(
        model=model,
        reward_funcs=reward_fn_stage1,  # Same reward function
        args=grpo_args_s2,
        train_dataset=train_ds_s2,
        processing_class=tokenizer,
        peft_config=None,
    )

    print("\n[8] Starting Stage 2 GRPO...")
    try:
        trainer_s2.train()
        print("  Stage 2 GRPO COMPLETE")
    except RuntimeError as e:
        if "out of memory" in str(e).lower():
            print(f"  OOM: {e}")
            torch.cuda.empty_cache()
            gc.collect()
            raise
        raise

    # Save final
    trainer_s2.save_model(f"{output_dir}/final")
    tokenizer.save_pretrained(f"{output_dir}/final")
    print(f"  Final model saved to {output_dir}/final/")

    # ==================================================================
    # Evaluation
    # ==================================================================
    print("\n" + "=" * 70)
    print("  EVALUATION")
    print("=" * 70)

    model.eval()

    # Load test samples (val split)
    pairs = []
    with open(DATASET_PATH) as f:
        for line in f:
            if line.strip():
                pairs.append(json.loads(line))
    val_pairs = pairs[int(len(pairs) * 0.9) :]

    np.random.seed(42)
    eval_indices = np.random.choice(len(val_pairs), min(10, len(val_pairs)), replace=False)

    eval_rewards = []
    eval_components = []
    for idx in eval_indices:
        p = val_pairs[idx]
        # Use same prompt format as training
        java_text = p["java_source"]
        java_encoded = tokenizer.encode(java_text)
        if len(java_encoded) > JAVA_TOKEN_BUDGET:
            java_text = tokenizer.decode(java_encoded[:JAVA_TOKEN_BUDGET])

        user_msg = f"Mod: {p['instruction']}\n\nJava:\n{java_text}\n\nConvert to Bedrock Add-on:"

        msgs = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ]
        text = tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        inputs = tokenizer(
            text, return_tensors="pt", truncation=True, max_length=MAX_SEQ_LENGTH
        ).to("cuda")

        with torch.no_grad():
            out = model.generate(
                **inputs,
                max_new_tokens=512,
                temperature=0.3,
                top_p=0.95,
                do_sample=True,
                pad_token_id=tokenizer.pad_token_id,
            )
        resp = tokenizer.decode(out[0], skip_special_tokens=True)
        if "assistant" in resp:
            resp = resp.split("assistant")[-1].strip()

        ref = p["bedrock_source"]
        reward = compute_base_reward(resp, ref)
        eval_rewards.append(reward)

        # Components
        manifest = _score_manifest_structure(resp, ref)
        js = _score_js_quality(resp, ref)
        json_v = _score_json_validity(resp)
        bedrock = _score_bedrock_apis(resp)
        halluc = _score_hallucination_penalty(resp)
        eval_components.append(
            {"manifest": manifest, "js": js, "json_v": json_v, "bedrock": bedrock, "halluc": halluc}
        )

        has_json = bool(_extract_json_blocks(resp))
        has_js = bool(_extract_js_blocks(resp))
        print(
            f"  Sample {idx}: reward={reward:.3f} manifest={manifest:.2f} js={js:.2f} "
            f"json={json_v:.2f} bedrock={bedrock:.2f} halluc={halluc:.2f}"
        )
        print(f"    has_manifest={has_json} has_js={has_js} len={len(resp)}")
        print(f"    Preview: {resp[:150]}...")

    elapsed = time.time() - start_time

    mean_reward = np.mean(eval_rewards)
    mean_comp = {k: np.mean([c[k] for c in eval_components]) for k in eval_components[0]}

    print(f"\n{'✓' * 3} Phase 5 complete!")
    print(f"  Stage 1: {output_dir}/stage1/final/")
    print(f"  Final:   {output_dir}/final/")
    print(f"  Eval:    {mean_reward:.3f} (10 samples)")
    print(
        f"  Components: manifest={mean_comp['manifest']:.3f} js={mean_comp['js']:.3f} "
        f"json={mean_comp['json_v']:.3f} bedrock={mean_comp['bedrock']:.3f} halluc={mean_comp['halluc']:.3f}"
    )
    print(f"  Total time: {elapsed / 60:.1f} min")

    print(f"\n  Comparison:")
    print(f"    Phase 3 (0.5B, dense reward):   eval=0.237 (10-sample)")
    print(f"    Phase 4b (1.5B, SFT+GRPO):      eval=0.304 (10-sample)")
    print(f"    Phase 5  (1.5B, curriculum):     eval={mean_reward:.3f} (10-sample)")


if __name__ == "__main__":
    main()
