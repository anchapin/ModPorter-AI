#!/usr/bin/env python3
"""
Phase 4b: GRPO on 1.5B with max_completion_length=512
======================================================
Uses SFT adapter from phase4_1.5b_model.py as warm start.
Uses 4-bit quantization for base model to save VRAM for longer completions.

Key changes from phase4:
  - max_completion_length=512 (was 384) — reduces truncation
  - load_in_4bit=True — saves ~1.6 GB, leaving more room for activations
  - num_generations=4 — same as before
  - 80 steps (was 60) — more training with longer completions

Usage:
    HSA_OVERRIDE_GFX_VERSION=10.3.0 HF_HUB_DISABLE_XET=1 python phase4b_1.5b_grpo.py
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
AI_ENGINE_PATH = PROJECT_ROOT / "ai_engine"
if AI_ENGINE_PATH.exists() and str(AI_ENGINE_PATH) not in sys.path:
    sys.path.insert(0, str(AI_ENGINE_PATH))

DATASET_PATH = PROJECT_ROOT / "ai_engine/mmsd/data/processed/validated_pairs.jsonl"
OUTPUT_DIR = SCRIPT_DIR / "phase4b_output_1.5b"
SFT_ADAPTER_PATH = SCRIPT_DIR / "phase4_output_1.5b/sft/final"

MODEL_NAME = "unsloth/Qwen2.5-Coder-1.5B-Instruct"
MAX_SEQ_LENGTH = 1024

SYSTEM_PROMPT = (
    "You are PortKit, an expert at converting Minecraft Java Edition mods (Forge) "
    "to Bedrock Edition Add-ons. Given a mod description and Java source code, "
    "first reason through the conversion step by step, then produce the complete "
    "Bedrock Add-on implementation with manifest.json and JavaScript files."
)


# =============================================================================
# Reward functions (same as Phase 3)
# =============================================================================

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
    penalty = 0.0
    for api in JAVA_ONLY_APIS:
        if re.search(api, completion):
            penalty += 0.15
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
    reward = 0.20 * manifest + 0.25 * js + 0.15 * json_v + 0.10 * bedrock + 0.15 * length - 0.15 * halluc
    return max(reward, 0.0)


# =============================================================================
# Dataset
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

    def build_prompt(row):
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
    print("  Phase 4b: GRPO on 1.5B (SFT warm start, max_compl=512)")
    print(f"  Base: {MODEL_NAME}")
    print(f"  SFT adapter: {SFT_ADAPTER_PATH}")
    print("  fp16 base + LoRA | AMD RX 6600 XT")
    print("=" * 70)
    print(f"  torch: {torch.__version__}, hip: {torch.version.hip}")
    print(f"  GPU: {torch.cuda.get_device_name(0)}")
    vram = torch.cuda.get_device_properties(0).total_memory
    print(f"  VRAM: {vram / 1e9:.1f} GB")

    output_dir = str(OUTPUT_DIR)

    # Load base model in fp16 (4-bit merge OOM'd)
    print("\n[1] Loading base model in fp16...")
    from unsloth import FastLanguageModel

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=MODEL_NAME,
        max_seq_length=MAX_SEQ_LENGTH,
        dtype=torch.float16,
        load_in_4bit=False,
        device_map="cuda",
    )
    print(f"  VRAM after load: {torch.cuda.memory_allocated() / 1e9:.2f} GB")

    # Load and merge SFT adapter
    print("\n[2] Loading SFT adapter and merging...")
    model = PeftModel.from_pretrained(model, str(SFT_ADAPTER_PATH))
    model = model.merge_and_unload()
    print(f"  SFT merged. VRAM: {torch.cuda.memory_allocated() / 1e9:.2f} GB")

    # Apply fresh LoRA for GRPO
    print("\n[3] Applying fresh LoRA for GRPO...")
    model = FastLanguageModel.get_peft_model(
        model, r=8, lora_alpha=16,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
        lora_dropout=0.0, bias="none",
        use_gradient_checkpointing="unsloth",
    )
    model.print_trainable_parameters()
    print(f"  VRAM after LoRA: {torch.cuda.memory_allocated() / 1e9:.2f} GB")

    # Load dataset
    print("\n[4] Loading dataset...")
    data = load_dataset(max_samples=200)
    print(f"  {len(data)} samples")

    # GRPO config
    print("\n[5] Configuring GRPO...")
    from trl import GRPOConfig, GRPOTrainer

    max_steps = 80

    grpo_args = GRPOConfig(
        output_dir=f"{output_dir}/grpo",
        per_device_train_batch_size=1,
        gradient_accumulation_steps=4,
        max_steps=max_steps,
        num_train_epochs=1,
        learning_rate=1e-6,
        lr_scheduler_type="cosine",
        warmup_steps=8,
        optim="adamw_torch",
        adam_beta1=0.9,
        adam_beta2=0.99,
        weight_decay=0.01,
        max_grad_norm=1.0,
        fp16=True,
        bf16=False,
        # Key change: 512-token completions (matching Phase 3 success)
        num_generations=4,
        generation_batch_size=4,
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
    print(f"  {max_steps} steps, 4 gens, max_compl=512, lr=1e-6, dapo loss")

    # Build dataset
    prompts = [d["prompt"] for d in data[:200]]
    references = [d["answer"] for d in data[:200]]
    train_dataset = Dataset.from_dict({"prompt": prompts, "reference": references})

    # Reward function
    def reward_fn(completions, prompts, **kwargs):
        ref_list = kwargs.get("reference", None)
        rewards = []
        for i, completion in enumerate(completions):
            if isinstance(completion, list) and len(completion) > 0:
                comp_text = completion[0].get("content", "") if isinstance(completion[0], dict) else str(completion[0])
            else:
                comp_text = str(completion)
            ref = ref_list[i] if ref_list and i < len(ref_list) else ""
            rewards.append(float(compute_reward(comp_text, ref)))
        return rewards

    # Initialize trainer
    print("\n[6] Initializing GRPOTrainer...")
    trainer = GRPOTrainer(
        model=model,
        reward_funcs=reward_fn,
        args=grpo_args,
        train_dataset=train_dataset,
        processing_class=tokenizer,
        peft_config=None,
    )
    print("  Trainer ready")

    # Train
    print(f"\n[7] Starting GRPO ({max_steps} steps)...")
    print(f"  VRAM: {torch.cuda.memory_allocated() / 1e9:.2f} GB")
    print("  " + "=" * 60)

    try:
        trainer.train()
        print("  " + "=" * 60)
        print("  GRPO TRAINING COMPLETE")
    except RuntimeError as e:
        if "out of memory" in str(e).lower():
            print(f"\n  OOM: {e}")
            torch.cuda.empty_cache()
            gc.collect()
            # Fall back to 384 completion length
            print("  Retrying with max_completion_length=384...")
            grpo_args.max_completion_length = 384
            trainer = GRPOTrainer(
                model=model,
                reward_funcs=reward_fn,
                args=grpo_args,
                train_dataset=train_dataset,
                processing_class=tokenizer,
                peft_config=None,
            )
            trainer.train()
        else:
            raise

    # Save
    print("\n[8] Saving model...")
    trainer.save_model(f"{output_dir}/final")
    tokenizer.save_pretrained(f"{output_dir}/final")
    print(f"  Saved to {output_dir}/final/")

    # Evaluate
    print("\n[9] Quick evaluation (3 samples)...")
    model.eval()
    eval_samples = [data[0], data[len(data)//2], data[-1]]
    eval_rewards = []
    for idx, sample in enumerate(eval_samples):
        msgs = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": sample["prompt"][:800]},
        ]
        text = tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=MAX_SEQ_LENGTH).to("cuda")
        with torch.no_grad():
            out = model.generate(
                **inputs, max_new_tokens=512, temperature=0.3, top_p=0.95,
                do_sample=True, pad_token_id=tokenizer.pad_token_id,
            )
        resp = tokenizer.decode(out[0], skip_special_tokens=True)
        if "assistant" in resp:
            resp = resp.split("assistant")[-1].strip()
        reward = compute_reward(resp, sample["answer"])
        eval_rewards.append(reward)
        print(f"  Sample {idx}: reward={reward:.3f}, len={len(resp)} chars")
        # Show key indicators
        has_manifest = bool(_extract_json_blocks(resp))
        has_js = bool(_extract_js_blocks(resp))
        has_bedrock = any(re.search(api, resp) for api in BEDROCK_APIS[:3])
        print(f"    manifest={has_manifest} js={has_js} bedrock_api={has_bedrock}")
        print(f"    Preview: {resp[:150]}...")

    elapsed = time.time() - start_time
    print(f"\n{'✓' * 3} Phase 4b complete!")
    print(f"  Model: {output_dir}/final/")
    print(f"  Eval rewards: {[f'{r:.3f}' for r in eval_rewards]} (mean={np.mean(eval_rewards):.3f})")
    print(f"  Total time: {elapsed/60:.1f} min")

    # Compare with previous phases
    print(f"\n  Comparison:")
    print(f"    Phase 3 (0.5B, dense reward): eval=0.410")
    print(f"    Phase 4  (1.5B, compl=384):   eval=0.112")
    print(f"    Phase 4b (1.5B, compl=512):   eval={np.mean(eval_rewards):.3f}")


if __name__ == "__main__":
    main()
