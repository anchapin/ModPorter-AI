#!/usr/bin/env python3
"""
SFT→GRPO Two-Stage Pipeline (Phase 2 + Phase 1 combined)
==========================================================
Loads the Phase 2 SFT warmup model, then runs Phase 1 GRPO on top.

Pipeline:
  1. Load base model (Qwen2.5-Coder-0.5B-Instruct)
  2. Load SFT LoRA adapter from sft_output_phase2/final/
  3. Apply fresh LoRA on top for GRPO (continues from SFT weights)
  4. Run GRPO with all Phase 1 quick-win fixes

Research basis:
  - DRIVE (arxiv:2511.06307): SFT→GRPO gives +58% on code tasks
  - All Phase 1 fixes from MicroCoder, DAPO, G²RPO-A

Usage:
    HSA_OVERRIDE_GFX_VERSION=10.3.0 HF_HUB_DISABLE_XET=1 python phase2_grpo_from_sft.py
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
OUTPUT_DIR = SCRIPT_DIR / "grpo_output_sft_pipeline"

# =============================================================================
# Reward functions (same as Phase 1)
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
    start_time = time.time()

    print("=" * 70)
    print("  SFT→GRPO Two-Stage Pipeline")
    print("  Phase 2 SFT → Phase 1 GRPO (all quick-win fixes)")
    print("  Qwen2.5-Coder-0.5B | fp16 + LoRA r=8 | AMD RX 6600 XT")
    print("=" * 70)
    print(f"  torch: {torch.__version__}, hip: {torch.version.hip}")
    print(f"  GPU: {torch.cuda.get_device_name(0)}")
    vram = torch.cuda.get_device_properties(0).total_memory
    print(f"  VRAM: {vram / 1e9:.1f} GB")
    print(f"  SFT model: {SFT_MODEL_PATH}")
    print(f"  Output: {OUTPUT_DIR}")

    # ------------------------------------------------------------------
    # [1] Load dataset
    # ------------------------------------------------------------------
    print("\n[1] Loading dataset...")
    data = load_dataset(max_samples=200)
    print(f"  Dataset: {len(data)} samples loaded")

    # ------------------------------------------------------------------
    # [2] Load SFT model (base + LoRA adapter from Phase 2)
    # ------------------------------------------------------------------
    print("\n[2] Loading SFT warmup model...")
    from unsloth import FastLanguageModel

    max_seq_length = 1024

    # Load base model
    base_model_name = "unsloth/Qwen2.5-Coder-0.5B-Instruct"
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=base_model_name,
        max_seq_length=max_seq_length,
        dtype=torch.float16,
        load_in_4bit=False,
        device_map="cuda",
    )
    print(f"  Base model loaded: {base_model_name}")
    print(f"  VRAM: {torch.cuda.memory_allocated() / 1e9:.2f} GB")

    # Load SFT LoRA adapter on top of base model
    from peft import PeftModel

    print(f"  Loading SFT adapter from {SFT_MODEL_PATH}...")
    model = PeftModel.from_pretrained(model, str(SFT_MODEL_PATH))
    # Merge adapter into base weights for GRPO (faster inference during generation)
    print(f"  Merging SFT adapter into base model...")
    model = model.merge_and_unload()
    print(f"  SFT model merged. VRAM: {torch.cuda.memory_allocated() / 1e9:.2f} GB")

    # ------------------------------------------------------------------
    # [3] Apply fresh LoRA for GRPO training on top of SFT weights
    # ------------------------------------------------------------------
    print("\n[3] Applying fresh LoRA for GRPO (on top of SFT weights)...")
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
    # [4] Setup GRPO config (all Phase 1 quick-win fixes)
    # ------------------------------------------------------------------
    print("\n[4] Setting up GRPO config (Phase 1 fixes)...")
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
    # [5] Build dataset
    # ------------------------------------------------------------------
    print("\n[5] Building dataset...")
    prompts = []
    references = []
    for d in data[:num_samples]:
        prompts.append(d["prompt"])
        references.append(d["answer"])

    train_dataset = Dataset.from_dict(
        {
            "prompt": prompts,
            "reference": references,
        }
    )
    print(f"  Dataset: {len(train_dataset)} rows")

    # ------------------------------------------------------------------
    # [6] Define reward function
    # ------------------------------------------------------------------
    print("\n[6] Defining reward function...")

    def reward_fn(completions, prompts, **kwargs):
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

            if ref_list is not None:
                ref = ref_list[i] if i < len(ref_list) else ref_list[0]
            else:
                ref = ""

            reward = compute_reward(comp_text, ref)
            rewards.append(float(reward))

        return rewards

    # ------------------------------------------------------------------
    # [7] Initialize GRPOTrainer
    # ------------------------------------------------------------------
    print("\n[7] Initializing GRPOTrainer...")
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
    # [8] Train!
    # ------------------------------------------------------------------
    print(f"\n[8] Starting SFT→GRPO training...")
    print(f"  Starting point: SFT model (already knows output format)")
    print(f"  Steps: {max_steps} | Gens/prompt: 8 | Max completion: 512 tokens")
    print(f"  VRAM before training: {torch.cuda.memory_allocated() / 1e9:.2f} GB")
    print("  " + "=" * 60)

    try:
        trainer.train()
        print("  " + "=" * 60)
        print("  TRAINING COMPLETE")
    except RuntimeError as e:
        if "out of memory" in str(e).lower():
            print(f"\n  OOM during training: {e}")
            torch.cuda.empty_cache()
            gc.collect()
            raise
        raise

    # ------------------------------------------------------------------
    # [9] Save model
    # ------------------------------------------------------------------
    print("\n[9] Saving model...")
    trainer.save_model(f"{output_dir}/final")
    tokenizer.save_pretrained(f"{output_dir}/final")
    print(f"  Saved to {output_dir}/final/")

    # ------------------------------------------------------------------
    # [10] Quick evaluation (3 samples)
    # ------------------------------------------------------------------
    print("\n[10] Quick evaluation...")
    model.eval()
    eval_samples = [data[0], data[len(data) // 2], data[-1]]
    eval_rewards = []
    for idx, sample in enumerate(eval_samples):
        msgs = [
            {
                "role": "system",
                "content": "You are PortKit, an expert at converting Minecraft Java Edition mods to Bedrock Edition Add-ons.",
            },
            {"role": "user", "content": sample["prompt"][:800]},
        ]
        text = tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        inputs = tokenizer(
            text, return_tensors="pt", truncation=True, max_length=max_seq_length
        ).to("cuda")
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
        reward = compute_reward(resp, sample["answer"])
        eval_rewards.append(reward)
        print(f"  Sample {idx}: reward={reward:.3f}, len={len(resp)} chars")
        print(f"    Preview: {resp[:200]}...")

    elapsed = time.time() - start_time
    print(f"\n✓ SFT→GRPO pipeline complete!")
    print(f"  Model saved: {output_dir}/final/")
    print(f"  Eval rewards: {eval_rewards} (mean={np.mean(eval_rewards):.3f})")
    print(f"  Total time: {elapsed / 60:.1f} min")
    print(f"  Final VRAM: {torch.cuda.memory_allocated() / 1e9:.2f} GB")


if __name__ == "__main__":
    main()
