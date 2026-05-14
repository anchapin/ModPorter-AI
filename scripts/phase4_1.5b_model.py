#!/usr/bin/env python3
"""
Phase 4: 1.5B Model — SFT Warmup + Dense Reward GRPO
======================================================
Upgrades from 0.5B to Qwen2.5-Coder-1.5B-Instruct with all improvements:

  Stage 1: SFT warmup on 1.5B (2 epochs, 1024 tokens, packed)
  Stage 2: GRPO with dense rewards (Phase 3 reward function)

Hardware: AMD RX 6600 XT (8.6 GB VRAM)
  - 1.5B fp16 = 3.2 GB → fits with LoRA
  - GRPO: batch=1, gen=4, max_compl=384 (reduced to fit VRAM)

Usage:
    HSA_OVERRIDE_GFX_VERSION=10.3.0 HF_HUB_DISABLE_XET=1 python phase4_1.5b_model.py
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

SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent
AI_ENGINE_PATH = PROJECT_ROOT / "ai-engine"
if AI_ENGINE_PATH.exists() and str(AI_ENGINE_PATH) not in sys.path:
    sys.path.insert(0, str(AI_ENGINE_PATH))

DATASET_PATH = PROJECT_ROOT / "ai-engine/mmsd/data/processed/validated_pairs.jsonl"
OUTPUT_DIR = SCRIPT_DIR / "phase4_output_1.5b"

MODEL_NAME = "unsloth/Qwen2.5-Coder-1.5B-Instruct"
MAX_SEQ_LENGTH = 1024

SYSTEM_PROMPT = (
    "You are PortKit, an expert at converting Minecraft Java Edition mods (Forge) "
    "to Bedrock Edition Add-ons. Given a mod description and Java source code, "
    "first reason through the conversion step by step, then produce the complete "
    "Bedrock Add-on implementation with manifest.json and JavaScript files."
)


# =============================================================================
# Reward functions (Phase 3 dense reward — same as phase3_dense_reward.py)
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


def _extract_json_blocks_v2(text):
    blocks = []
    pattern = r"```json\s*(.*?)\s*```"
    for match in re.finditer(pattern, text, re.DOTALL):
        blocks.append(match.group(1))
    return blocks


def _extract_js_blocks_v2(text):
    pattern = r"```(?:javascript|js)\s*([\s\S]*?)```"
    return re.findall(pattern, text)


def _score_manifest_structure(completion, reference):
    comp_blocks = _extract_json_blocks_v2(completion)
    ref_blocks = _extract_json_blocks_v2(reference)
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
        parsed = json.loads(comp_manifest)
        if isinstance(parsed, dict):
            score += 0.15
    except json.JSONDecodeError:
        if comp_manifest.count("{") > 0 and comp_manifest.count("{") == comp_manifest.count("}"):
            score += 0.05
    return min(score, 1.0)


def _score_js_quality(completion, reference):
    comp_js_blocks = _extract_js_blocks_v2(completion)
    ref_js_blocks = _extract_js_blocks_v2(reference)
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
        func_overlap = len(ref_funcs & comp_funcs) / len(ref_funcs)
        score += 0.20 * func_overlap
    else:
        score += 0.10

    bedrock_apis_found = sum(1 for api in BEDROCK_APIS if re.search(api, comp_js))
    if bedrock_apis_found > 0:
        score += min(0.20, 0.05 * bedrock_apis_found)

    ref_controls = len(re.findall(r"\b(if|for|while|switch|try)\b", ref_js))
    comp_controls = len(re.findall(r"\b(if|for|while|switch|try)\b", comp_js))
    if ref_controls > 0:
        ratio = min(comp_controls / ref_controls, 1.5) / 1.5
        score += 0.15 * ratio

    ref_vars = set(re.findall(r"(?:let|const|var)\s+(\w+)", ref_js))
    comp_vars = set(re.findall(r"(?:let|const|var)\s+(\w+)", comp_js))
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


def _score_json_validity_v2(completion):
    blocks = _extract_json_blocks_v2(completion)
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


def _score_length_ratio_v2(completion, reference):
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


def compute_reward_v2(completion, reference):
    comp = completion if isinstance(completion, str) else str(completion)
    ref = reference if isinstance(reference, str) else str(reference)
    manifest = _score_manifest_structure(comp, ref)
    js = _score_js_quality(comp, ref)
    json_v = _score_json_validity_v2(comp)
    bedrock = _score_bedrock_apis(comp)
    length = _score_length_ratio_v2(comp, ref)
    halluc = _score_hallucination_penalty(comp)
    reward = (
        0.20 * manifest + 0.25 * js + 0.15 * json_v + 0.10 * bedrock + 0.15 * length - 0.15 * halluc
    )
    return max(reward, 0.0)


# Also keep v1 for comparison
def _extract_json_blocks(text):
    return re.findall(r"```json\s*(\{[^}]*(?:\{[^}]*\}[^}]*)*\})", text, re.DOTALL)


def _score_json_validity(completion):
    for block in _extract_json_blocks(completion):
        try:
            json.loads(block)
            return 1.0
        except json.JSONDecodeError:
            pass
    return 0.0


def compute_reward_v1(completion, reference):
    comp = completion if isinstance(completion, str) else str(completion)
    ref = reference if isinstance(reference, str) else str(reference)
    return 0.0  # Simplified — we only need v1 for eval comparison, not reimplementation


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

    def build_prompt(row):
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


def prepare_sft_dataset(tokenizer, max_length_tokens=1024, chars_per_token=3.5):
    if not DATASET_PATH.exists():
        raise FileNotFoundError(f"Dataset not found at {DATASET_PATH}")
    pairs = []
    with open(DATASET_PATH) as f:
        for line in f:
            if line.strip():
                pairs.append(json.loads(line))

    split_idx = int(len(pairs) * 0.9)
    train_pairs = pairs[:split_idx]
    val_pairs = pairs[split_idx:]
    max_chars = int(max_length_tokens * chars_per_token)

    records = []
    skipped = 0
    for p in train_pairs + val_pairs:
        instruction = p["instruction"]
        java_source = p["java_source"]
        reasoning = p["reasoning_trace"]
        bedrock = p["bedrock_source"]

        assistant_response = bedrock
        if reasoning and len(reasoning) > 100:
            reasoning_summary = reasoning[:500]
            last_period = reasoning_summary.rfind(".")
            if last_period > 200:
                reasoning_summary = reasoning_summary[: last_period + 1]
            assistant_response = f"## Conversion Approach\n{reasoning_summary}\n\n## Bedrock Add-on Implementation\n{bedrock}"

        user_prefix = f"Mod Description: {instruction}\n\n"
        user_java_header = "Java Source:\n"
        user_suffix = "\n\nConvert this to a Bedrock Add-on. First explain your conversion approach, then provide the manifest.json and JavaScript implementation."

        fixed_chars = (
            len(SYSTEM_PROMPT)
            + len(user_prefix)
            + len(user_java_header)
            + len(user_suffix)
            + len(assistant_response)
        )
        fixed_tokens = fixed_chars / chars_per_token + 80

        remaining_tokens = max_length_tokens - fixed_tokens
        if remaining_tokens < 50:
            skipped += 1
            continue

        max_java_chars = int(remaining_tokens * chars_per_token)
        if len(java_source) > max_java_chars:
            truncated = java_source[:max_java_chars]
            last_newline = truncated.rfind("\n")
            if last_newline > max_java_chars // 2:
                truncated = truncated[:last_newline] + "\n// ... (truncated)"
            java_source = truncated

        user_content = f"{user_prefix}{user_java_header}{java_source}{user_suffix}"
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
            {"role": "assistant", "content": assistant_response},
        ]
        text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)
        records.append({"text": text})

    train = Dataset.from_list(records[: len(train_pairs) - skipped])
    val = (
        Dataset.from_list(records[len(train_pairs) - skipped :])
        if len(records) > len(train_pairs) - skipped
        else None
    )
    print(f"  SFT dataset: {len(records)} total ({skipped} skipped)")
    return train, val


# =============================================================================
# Main
# =============================================================================


def main():
    start_time = time.time()

    print("=" * 70)
    print("  Phase 4: 1.5B Model — SFT Warmup + Dense Reward GRPO")
    print(f"  {MODEL_NAME}")
    print("  fp16 + LoRA r=8 | AMD RX 6600 XT")
    print("=" * 70)
    print(f"  torch: {torch.__version__}, hip: {torch.version.hip}")
    print(f"  GPU: {torch.cuda.get_device_name(0)}")
    vram = torch.cuda.get_device_properties(0).total_memory
    print(f"  VRAM: {vram / 1e9:.1f} GB")
    print(f"  Output: {OUTPUT_DIR}")

    output_dir = str(OUTPUT_DIR)

    # ==================================================================
    # STAGE 1: SFT Warmup on 1.5B
    # ==================================================================
    print("\n" + "=" * 70)
    print("  STAGE 1: SFT Warmup on 1.5B model")
    print("=" * 70)

    # [S1.1] Load tokenizer first
    print("\n[S1.1] Loading tokenizer...")
    from unsloth import FastLanguageModel

    _, tokenizer = FastLanguageModel.from_pretrained(
        model_name=MODEL_NAME,
        max_seq_length=MAX_SEQ_LENGTH,
        dtype=torch.float16,
        load_in_4bit=False,
        device_map="cpu",
    )

    # [S1.2] Prepare SFT dataset
    print("\n[S1.2] Preparing SFT dataset...")
    train_sft, val_sft = prepare_sft_dataset(tokenizer, MAX_SEQ_LENGTH)
    print(f"  Train: {len(train_sft)} samples")

    # [S1.3] Load model on GPU
    print("\n[S1.3] Loading 1.5B model on GPU...")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=MODEL_NAME,
        max_seq_length=MAX_SEQ_LENGTH,
        dtype=torch.float16,
        load_in_4bit=False,
        device_map="cuda",
    )
    print(f"  VRAM: {torch.cuda.memory_allocated() / 1e9:.2f} GB")

    # [S1.4] Apply LoRA
    print("\n[S1.4] Applying LoRA...")
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

    # [S1.5] SFT training
    print("\n[S1.5] SFT training (2 epochs)...")
    from trl import SFTConfig, SFTTrainer

    sft_output = f"{output_dir}/sft"
    sft_args = SFTConfig(
        output_dir=sft_output,
        max_length=MAX_SEQ_LENGTH,
        per_device_train_batch_size=2,
        gradient_accumulation_steps=4,
        num_train_epochs=2,
        learning_rate=2e-5,
        lr_scheduler_type="cosine",
        warmup_steps=3,
        optim="adamw_torch",
        weight_decay=0.01,
        max_grad_norm=1.0,
        fp16=True,
        bf16=False,
        packing=True,
        packing_strategy="bfd",
        dataset_text_field="text",
        gradient_checkpointing=True,
        logging_steps=1,
        logging_first_step=True,
        disable_tqdm=True,
        save_strategy="steps",
        save_steps=100,
        save_total_limit=2,
        eval_strategy="no",
        shuffle_dataset=True,
        seed=42,
        report_to="none",
    )

    sft_trainer = SFTTrainer(
        model=model,
        args=sft_args,
        train_dataset=train_sft,
        processing_class=tokenizer,
        peft_config=None,
    )

    sft_start = time.time()
    sft_trainer.train()
    sft_time = time.time() - sft_start
    print(f"  SFT complete in {sft_time / 60:.1f} min")

    # Save SFT model
    sft_trainer.save_model(f"{sft_output}/final")
    tokenizer.save_pretrained(f"{sft_output}/final")
    print(f"  SFT saved to {sft_output}/final/")

    # Free memory
    del sft_trainer, model
    torch.cuda.empty_cache()
    gc.collect()
    print(f"  VRAM after cleanup: {torch.cuda.memory_allocated() / 1e9:.2f} GB")

    # ==================================================================
    # STAGE 2: GRPO with Dense Rewards on 1.5B
    # ==================================================================
    print("\n" + "=" * 70)
    print("  STAGE 2: GRPO with Dense Rewards on 1.5B")
    print("=" * 70)

    # [S2.1] Reload model + SFT adapter
    print("\n[S2.1] Loading base + SFT adapter...")
    from peft import PeftModel

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=MODEL_NAME,
        max_seq_length=MAX_SEQ_LENGTH,
        dtype=torch.float16,
        load_in_4bit=False,
        device_map="cuda",
    )
    print(f"  Base model loaded. VRAM: {torch.cuda.memory_allocated() / 1e9:.2f} GB")

    model = PeftModel.from_pretrained(model, f"{sft_output}/final")
    model = model.merge_and_unload()
    print(f"  SFT merged. VRAM: {torch.cuda.memory_allocated() / 1e9:.2f} GB")

    # [S2.2] Apply fresh LoRA for GRPO
    print("\n[S2.2] Applying fresh LoRA for GRPO...")
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

    # [S2.3] Load dataset
    print("\n[S2.3] Loading GRPO dataset...")
    data = load_dataset(max_samples=200)
    print(f"  Dataset: {len(data)} samples")

    # [S2.4] GRPO config — adjusted for 1.5B on 8.6 GB
    print("\n[S2.4] Setting up GRPO config...")
    from trl import GRPOConfig, GRPOTrainer

    max_steps = 60

    grpo_args = GRPOConfig(
        output_dir=f"{output_dir}/grpo",
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
        # Reduced for 1.5B VRAM: 4 gens, 384 completion
        num_generations=4,
        generation_batch_size=4,
        max_completion_length=384,
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
    print(f"  Config: {max_steps} steps, 4 gens/sample, max_compl=384, lr=1e-6")

    # [S2.5] Build dataset
    prompts = [d["prompt"] for d in data[:200]]
    references = [d["answer"] for d in data[:200]]
    train_dataset = Dataset.from_dict({"prompt": prompts, "reference": references})

    # [S2.6] Reward function
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
            ref = ref_list[i] if ref_list and i < len(ref_list) else ""
            rewards.append(float(compute_reward_v2(comp_text, ref)))
        return rewards

    # [S2.7] Initialize trainer
    print("\n[S2.7] Initializing GRPOTrainer...")
    trainer = GRPOTrainer(
        model=model,
        reward_funcs=reward_fn,
        args=grpo_args,
        train_dataset=train_dataset,
        processing_class=tokenizer,
        peft_config=None,
    )
    print("  GRPOTrainer initialized")

    # [S2.8] Train!
    print(f"\n[S2.8] Starting GRPO training...")
    print(f"  VRAM: {torch.cuda.memory_allocated() / 1e9:.2f} GB")
    print("  " + "=" * 60)

    try:
        trainer.train()
        print("  " + "=" * 60)
        print("  GRPO TRAINING COMPLETE")
    except RuntimeError as e:
        if "out of memory" in str(e).lower():
            print(f"\n  OOM: {e}")
            print("  Try: reduce num_generations to 2 or max_completion_length to 256")
            torch.cuda.empty_cache()
            gc.collect()
            raise
        raise

    # [S2.9] Save
    print("\n[S2.9] Saving model...")
    trainer.save_model(f"{output_dir}/final")
    tokenizer.save_pretrained(f"{output_dir}/final")
    print(f"  Saved to {output_dir}/final/")

    # [S2.10] Evaluate
    print("\n[S2.10] Quick evaluation...")
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
        reward = compute_reward_v2(resp, sample["answer"])
        eval_rewards.append(reward)
        print(f"  Sample {idx}: reward={reward:.3f}, len={len(resp)} chars")
        print(f"    Preview: {resp[:200]}...")

    elapsed = time.time() - start_time
    print(f"\n✓ Phase 4 (1.5B) complete!")
    print(f"  Model: {output_dir}/final/")
    print(f"  Eval rewards: {eval_rewards} (mean={np.mean(eval_rewards):.3f})")
    print(f"  Total time: {elapsed / 60:.1f} min")
    print(f"  Final VRAM: {torch.cuda.memory_allocated() / 1e9:.2f} GB")


if __name__ == "__main__":
    main()
