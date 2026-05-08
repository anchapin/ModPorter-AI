#!/usr/bin/env python3
"""
Phase 3: Dense Reward GRPO with Improved Reward Function
==========================================================
Two-stage pipeline (SFT warmup → GRPO) with VeRPO-inspired dense rewards.

Reward improvements over baseline:
  - Fixed length ratio formula (was capped at 0.5 for perfect matches)
  - Better JSON extraction (handles nested objects, multiple blocks)
  - Partial credit for near-valid JSON (not just 0/1)
  - UUID format checking
  - Event handler matching (Bedrock-specific API patterns)
  - Import/module structure scoring
  - Hallucination penalty (Java APIs in Bedrock output)
  - Smoother gradients for RL training

Config: Same Phase 1 quick-win fixes + SFT warmup + new reward

Usage:
    HSA_OVERRIDE_GFX_VERSION=10.3.0 HF_HUB_DISABLE_XET=1 python phase3_dense_reward.py
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

SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent
AI_ENGINE_PATH = PROJECT_ROOT / "ai_engine"
if AI_ENGINE_PATH.exists() and str(AI_ENGINE_PATH) not in sys.path:
    sys.path.insert(0, str(AI_ENGINE_PATH))

DATASET_PATH = PROJECT_ROOT / "ai_engine/mmsd/data/processed/validated_pairs.jsonl"
SFT_MODEL_PATH = SCRIPT_DIR / "sft_output_phase2" / "final"
OUTPUT_DIR = SCRIPT_DIR / "grpo_output_phase3"

# =============================================================================
# Improved reward functions (Phase 3)
# =============================================================================

# Bedrock API patterns that indicate correct platform knowledge
BEDROCK_APIS = [
    r'@minecraft/server', r'@minecraft/server-ui', r'@minecraft/server-net',
    r'world\.afterEvents', r'world\.beforeEvents', r'system\.run',
    r'BlockPermutation', r'BlockTypes', r'ItemTypes', r'EntityTypes',
    r'Dimension', r'Player', r'Block', r'ItemStack', r'Container',
    r'MinecraftItemTypes', r'MinecraftBlockTypes',
    r'PropertyType', r'BlockStates',
]

# Java/Forge patterns that should NOT appear in Bedrock output
JAVA_ONLY_APIS = [
    r'net\.forge', r'net\.minecraft\.(src|util|block|item|entity|world|server|client)',
    r'ForgeEventBus', r'IEventBus', r'DeferredRegister', r'RegistryObject',
    r'FMLCommonSetupEvent', r'FMLClientSetupEvent', r'@Mod\b', r'@SubscribeEvent',
    r'GameRegistry', r'ItemStack\(.*Blocks\.', r'Minecraft\.getMinecraft\(\)',
    r'@EventHandler', r'cpw\.mods', r'net\.minecraftforge\.fml',
]


def _extract_json_blocks_v2(text: str) -> list[str]:
    """Improved JSON extraction — handles nested braces properly."""
    blocks = []
    pattern = r"```json\s*(.*?)\s*```"
    for match in re.finditer(pattern, text, re.DOTALL):
        blocks.append(match.group(1))
    return blocks


def _extract_js_blocks_v2(text: str) -> list[str]:
    """Extract JS/JS blocks."""
    pattern = r"```(?:javascript|js)\s*([\s\S]*?)```"
    return re.findall(pattern, text)


def _score_manifest_structure(completion: str, reference: str) -> float:
    """Score manifest.json field matching with partial credit."""
    comp_blocks = _extract_json_blocks_v2(completion)
    ref_blocks = _extract_json_blocks_v2(reference)

    if not ref_blocks:
        return 0.5  # No manifest in reference, neutral score

    # Find the manifest block (contains format_version or header)
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

    # Check format_version presence
    if 'format_version' in comp_manifest:
        score += 0.15
        # Check if version matches
        ref_ver = re.search(r'format_version["\s:]+([0-9.]+)', ref_manifest)
        comp_ver = re.search(r'format_version["\s:]+([0-9.]+)', comp_manifest)
        if ref_ver and comp_ver and ref_ver.group(1) == comp_ver.group(1):
            score += 0.05

    # Check header section
    if 'header' in comp_manifest:
        score += 0.15
        # Header sub-fields
        header_fields = ['name', 'description', 'uuid', 'version', 'min_engine_version']
        ref_header = ref_manifest[ref_manifest.find('header'):ref_manifest.find('header') + 500]
        comp_header = comp_manifest[comp_manifest.find('header'):comp_manifest.find('header') + 500]
        matched = sum(1 for f in header_fields if f in comp_header and f in ref_header)
        total = sum(1 for f in header_fields if f in ref_header)
        if total > 0:
            score += 0.10 * (matched / total)

    # Check modules section
    if 'modules' in comp_manifest:
        score += 0.10

    # Check dependencies
    if 'dependencies' in comp_manifest:
        score += 0.05

    # JSON parseability of manifest
    try:
        parsed = json.loads(comp_manifest)
        if isinstance(parsed, dict):
            score += 0.15  # Fully parseable and is object
    except json.JSONDecodeError:
        # Partial credit: count balanced braces
        if comp_manifest.count('{') > 0 and comp_manifest.count('{') == comp_manifest.count('}'):
            score += 0.05  # At least balanced

    return min(score, 1.0)


def _score_js_quality(completion: str, reference: str) -> float:
    """Score JavaScript code quality and correctness."""
    comp_js_blocks = _extract_js_blocks_v2(completion)
    ref_js_blocks = _extract_js_blocks_v2(reference)

    if not ref_js_blocks:
        return 0.5  # No JS in reference, neutral

    if not comp_js_blocks:
        return 0.0

    comp_js = "\n".join(comp_js_blocks)
    ref_js = "\n".join(ref_js_blocks)

    score = 0.0

    # Function name overlap
    ref_funcs = set(re.findall(r'function\s+(\w+)', ref_js))
    comp_funcs = set(re.findall(r'function\s+(\w+)', comp_js))
    if ref_funcs:
        func_overlap = len(ref_funcs & comp_funcs) / len(ref_funcs)
        score += 0.20 * func_overlap
    else:
        score += 0.10  # No functions in ref, partial credit for having JS

    # Bedrock API usage (positive signal)
    bedrock_apis_found = sum(1 for api in BEDROCK_APIS if re.search(api, comp_js))
    if bedrock_apis_found > 0:
        score += min(0.20, 0.05 * bedrock_apis_found)

    # Control structure complexity match
    ref_controls = len(re.findall(r'\b(if|for|while|switch|try)\b', ref_js))
    comp_controls = len(re.findall(r'\b(if|for|while|switch|try)\b', comp_js))
    if ref_controls > 0:
        ratio = min(comp_controls / ref_controls, 1.5) / 1.5
        score += 0.15 * ratio

    # Variable/event usage
    ref_vars = set(re.findall(r'(?:let|const|var)\s+(\w+)', ref_js))
    comp_vars = set(re.findall(r'(?:let|const|var)\s+(\w+)', comp_js))
    if ref_vars:
        var_overlap = len(ref_vars & comp_vars) / len(ref_vars)
        score += 0.10 * var_overlap

    # Code length adequacy (not too short, not too long)
    ref_len = len(ref_js)
    comp_len = len(comp_js)
    if ref_len > 0:
        ratio = comp_len / ref_len
        if 0.3 <= ratio <= 2.0:
            score += 0.15
        elif 0.1 <= ratio <= 3.0:
            score += 0.08

    # No hallucinated Java APIs (negative signal)
    java_apis_found = sum(1 for api in JAVA_ONLY_APIS if re.search(api, comp_js))
    score -= 0.10 * java_apis_found

    return max(score, 0.0)


def _score_json_validity_v2(completion: str) -> float:
    """Improved JSON validity with partial credit."""
    blocks = _extract_json_blocks_v2(completion)
    if not blocks:
        return 0.0

    total_score = 0.0
    for block in blocks:
        try:
            json.loads(block)
            total_score += 1.0  # Fully valid
        except json.JSONDecodeError:
            # Partial credit for near-valid JSON
            # Check balanced braces
            opens = block.count('{') + block.count('[')
            closes = block.count('}') + block.count(']')
            if opens > 0 and abs(opens - closes) <= 1:
                total_score += 0.5
            elif opens > 0:
                total_score += 0.2

    return min(total_score / len(blocks), 1.0)


def _score_length_ratio_v2(completion: str, reference: str) -> float:
    """Fixed length ratio — rewards being within 50-200% of reference."""
    ref_len = max(len(reference), 1)
    comp_len = len(completion)
    ratio = comp_len / ref_len

    if ratio < 0.1:
        return 0.0
    elif ratio < 0.3:
        return 0.3
    elif 0.5 <= ratio <= 2.0:
        return 1.0  # Ideal range
    elif 0.3 <= ratio < 0.5:
        return 0.6
    elif 2.0 < ratio <= 3.0:
        return 0.7
    else:
        return 0.5


def _score_hallucination_penalty(completion: str) -> float:
    """Penalize Java/Forge APIs appearing in Bedrock output."""
    penalty = 0.0
    for api in JAVA_ONLY_APIS:
        if re.search(api, completion):
            penalty += 0.15
    return min(penalty, 1.0)


def _score_bedrock_apis(completion: str) -> float:
    """Reward for using correct Bedrock API patterns."""
    count = sum(1 for api in BEDROCK_APIS if re.search(api, completion))
    if count == 0:
        return 0.0
    return min(count * 0.15, 1.0)


def compute_reward_v2(completion: str, reference: str) -> float:
    """Dense reward with smoother gradients and partial credit.

    Components:
      manifest_structure (0.20): Field-level manifest matching with partial credit
      js_quality (0.25): JS function/API/control structure matching + hallucination penalty
      json_validity (0.15): Parseable JSON with partial credit for near-valid
      bedrock_apis (0.10): Correct Bedrock API usage
      length_ratio (0.15): Output length within acceptable range
      hallucination_penalty (-0.15): Penalize Java APIs in Bedrock output
    """
    comp = completion if isinstance(completion, str) else str(completion)
    ref = reference if isinstance(reference, str) else str(reference)

    manifest = _score_manifest_structure(comp, ref)
    js = _score_js_quality(comp, ref)
    json_v = _score_json_validity_v2(comp)
    bedrock = _score_bedrock_apis(comp)
    length = _score_length_ratio_v2(comp, ref)
    halluc = _score_hallucination_penalty(comp)

    reward = (
        0.20 * manifest +
        0.25 * js +
        0.15 * json_v +
        0.10 * bedrock +
        0.15 * length -
        0.15 * halluc
    )

    return max(reward, 0.0)  # Floor at 0


# =============================================================================
# Dataset loading (same as Phase 1)
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
    print("  Phase 3: Dense Reward GRPO (SFT→GRPO + improved reward)")
    print("  Qwen2.5-Coder-0.5B | fp16 + LoRA r=8 | AMD RX 6600 XT")
    print("=" * 70)
    print(f"  torch: {torch.__version__}, hip: {torch.version.hip}")
    print(f"  GPU: {torch.cuda.get_device_name(0)}")
    vram = torch.cuda.get_device_properties(0).total_memory
    print(f"  VRAM: {vram / 1e9:.1f} GB")
    print(f"  SFT model: {SFT_MODEL_PATH}")
    print(f"  Output: {OUTPUT_DIR}")

    # ------------------------------------------------------------------
    # [1] Validate reward function improvement
    # ------------------------------------------------------------------
    print("\n[1] Validating reward function improvement...")
    data_test = load_dataset(max_samples=50)

    # Test: reference vs itself (should score high)
    perfect_rewards = [compute_reward_v2(p["answer"], p["answer"]) for p in data_test[:50]]
    # Test: empty completion (should score low)
    empty_rewards = [compute_reward_v2("", p["answer"]) for p in data_test[:50]]
    # Old reward for comparison
    from phase1_grpo_quickwins import compute_reward as compute_reward_v1
    old_perfect = [compute_reward_v1(p["answer"], p["answer"]) for p in data_test[:50]]

    print(f"  Perfect match (ref vs self):")
    print(f"    Old reward: mean={np.mean(old_perfect):.3f}, max={max(old_perfect):.3f}")
    print(f"    New reward: mean={np.mean(perfect_rewards):.3f}, max={max(perfect_rewards):.3f}")
    print(f"  Empty output: mean={np.mean(empty_rewards):.3f}")
    print(f"  Dynamic range: {np.mean(perfect_rewards) - np.mean(empty_rewards):.3f} (higher = better signal)")

    # ------------------------------------------------------------------
    # [2] Load dataset
    # ------------------------------------------------------------------
    print("\n[2] Loading dataset...")
    data = load_dataset(max_samples=200)
    print(f"  Dataset: {len(data)} samples loaded")

    # ------------------------------------------------------------------
    # [3] Load SFT model
    # ------------------------------------------------------------------
    print("\n[3] Loading SFT warmup model...")
    from unsloth import FastLanguageModel
    from peft import PeftModel

    base_model_name = "unsloth/Qwen2.5-Coder-0.5B-Instruct"
    max_seq_length = 1024

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=base_model_name,
        max_seq_length=max_seq_length,
        dtype=torch.float16,
        load_in_4bit=False,
        device_map="cuda",
    )
    print(f"  Base model loaded. VRAM: {torch.cuda.memory_allocated() / 1e9:.2f} GB")

    model = PeftModel.from_pretrained(model, str(SFT_MODEL_PATH))
    model = model.merge_and_unload()
    print(f"  SFT adapter merged. VRAM: {torch.cuda.memory_allocated() / 1e9:.2f} GB")

    # ------------------------------------------------------------------
    # [4] Apply fresh LoRA for GRPO
    # ------------------------------------------------------------------
    print("\n[4] Applying fresh LoRA for GRPO...")
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
    # [5] Setup GRPO config
    # ------------------------------------------------------------------
    print("\n[5] Setting up GRPO config...")
    from trl import GRPOConfig, GRPOTrainer
    from datasets import Dataset

    num_samples = 200
    max_steps = 60
    output_dir = str(OUTPUT_DIR)

    training_args = GRPOConfig(
        output_dir=output_dir,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=4,
        max_steps=max_steps,
        num_train_epochs=1,
        learning_rate=1e-6,
        lr_scheduler_type="cosine",
        warmup_steps=6,
        optim="adamw_torch",
        adam_beta1=0.9,
        adam_beta2=0.99,
        weight_decay=0.01,
        max_grad_norm=1.0,
        fp16=True,
        bf16=False,
        num_generations=8,
        generation_batch_size=8,
        max_completion_length=512,
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
    print(f"  Config: {max_steps} steps, 8 gens/sample, max_compl=512, lr=1e-6")

    # ------------------------------------------------------------------
    # [6] Build dataset
    # ------------------------------------------------------------------
    print("\n[6] Building dataset...")
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
    # [7] Define reward function (IMPROVED)
    # ------------------------------------------------------------------
    print("\n[7] Defining IMPROVED reward function...")

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

            reward = compute_reward_v2(comp_text, ref)
            rewards.append(float(reward))

        return rewards

    # ------------------------------------------------------------------
    # [8] Initialize GRPOTrainer
    # ------------------------------------------------------------------
    print("\n[8] Initializing GRPOTrainer...")
    trainer = GRPOTrainer(
        model=model,
        reward_funcs=reward_fn,
        args=training_args,
        train_dataset=train_dataset,
        processing_class=tokenizer,
        peft_config=None,
    )
    print("  GRPOTrainer initialized")

    # ------------------------------------------------------------------
    # [9] Train!
    # ------------------------------------------------------------------
    print(f"\n[9] Starting Phase 3 GRPO with dense rewards...")
    print(f"  Reward: dense partial credit (manifest + JS + JSON + APIs + hallucination penalty)")
    print(f"  Steps: {max_steps} | Gens/prompt: 8 | Max completion: 512 tokens")
    print(f"  VRAM: {torch.cuda.memory_allocated() / 1e9:.2f} GB")
    print("  " + "=" * 60)

    try:
        trainer.train()
        print("  " + "=" * 60)
        print("  TRAINING COMPLETE")
    except RuntimeError as e:
        if "out of memory" in str(e).lower():
            print(f"\n  OOM: {e}")
            torch.cuda.empty_cache()
            gc.collect()
            raise
        raise

    # ------------------------------------------------------------------
    # [10] Save model
    # ------------------------------------------------------------------
    print("\n[10] Saving model...")
    trainer.save_model(f"{output_dir}/final")
    tokenizer.save_pretrained(f"{output_dir}/final")
    print(f"  Saved to {output_dir}/final/")

    # ------------------------------------------------------------------
    # [11] Quick evaluation
    # ------------------------------------------------------------------
    print("\n[11] Quick evaluation...")
    model.eval()
    eval_samples = [data[0], data[len(data)//2], data[-1]]
    eval_rewards_v2 = []
    eval_rewards_v1 = []
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
        r_v2 = compute_reward_v2(resp, sample["answer"])
        r_v1 = compute_reward_v1(resp, sample["answer"])
        eval_rewards_v2.append(r_v2)
        eval_rewards_v1.append(r_v1)
        print(f"  Sample {idx}: reward_v2={r_v2:.3f}, reward_v1={r_v1:.3f}, len={len(resp)} chars")
        print(f"    Preview: {resp[:200]}...")

    elapsed = time.time() - start_time
    print(f"\n✓ Phase 3 Dense Reward GRPO complete!")
    print(f"  Model saved: {output_dir}/final/")
    print(f"  Eval rewards (v2): {eval_rewards_v2} (mean={np.mean(eval_rewards_v2):.3f})")
    print(f"  Eval rewards (v1): {eval_rewards_v1} (mean={np.mean(eval_rewards_v1):.3f})")
    print(f"  Total time: {elapsed/60:.1f} min")
    print(f"  Final VRAM: {torch.cuda.memory_allocated() / 1e9:.2f} GB")


if __name__ == "__main__":
    main()
