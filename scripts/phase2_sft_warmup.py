#!/usr/bin/env python3
"""
Phase 2: SFT Warmup before GRPO
=================================
Supervised fine-tuning on 1300+ Minecraft Java→Bedrock conversion pairs
using the reasoning traces + bedrock_source as training targets.

Based on DRIVE paper (arxiv:2511.06307):
  - SFT teaches the model correct output format before RL exploration
  - +58% improvement on code tasks when SFT precedes GRPO
  - Using reasoning traces provides chain-of-thought guidance (G²RPO-A)

Config:
  - Model: Qwen2.5-Coder-0.5B-Instruct, fp16 + LoRA r=8
  - Data: ~1260 pairs (90% train / 10% val), messages format
  - Max length: 2048 tokens (88% of pairs fit with java truncation)
  - Epochs: 3, LR: 2e-5, batch: 2, grad_accum: 4
  - Loss: assistant_only_loss=True (only train on assistant response)
  - Java source is truncated to fit within token budget

Usage:
    HSA_OVERRIDE_GFX_VERSION=10.3.0 HF_HUB_DISABLE_XET=1 python phase2_sft_warmup.py
"""

import json
import re
import os
import sys
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
OUTPUT_DIR = SCRIPT_DIR / "sft_output_phase2"

SYSTEM_PROMPT = (
    "You are PortKit, an expert at converting Minecraft Java Edition mods (Forge) "
    "to Bedrock Edition Add-ons. Given a mod description and Java source code, "
    "first reason through the conversion step by step, then produce the complete "
    "Bedrock Add-on implementation with manifest.json and JavaScript files."
)


# =============================================================================
# Dataset preparation
# =============================================================================


def prepare_sft_dataset(tokenizer, max_length_tokens=2048, chars_per_token=3.5):
    """Load and format dataset for SFT with messages format.

    Strategy:
    - System prompt (fixed) + User (instruction + java_source) → Assistant (reasoning + bedrock)
    - Truncate java_source to fit within token budget
    - Skip samples where target alone exceeds budget
    """
    if not DATASET_PATH.exists():
        raise FileNotFoundError(f"Dataset not found at {DATASET_PATH}")

    pairs = []
    with open(DATASET_PATH) as f:
        for line in f:
            if line.strip():
                pairs.append(json.loads(line))

    print(f"  Loaded {len(pairs)} raw pairs")

    # Split 90/10 before filtering
    split_idx = int(len(pairs) * 0.9)
    train_pairs = pairs[:split_idx]
    val_pairs = pairs[split_idx:]

    max_chars = int(max_length_tokens * chars_per_token)

    def build_messages(pair):
        """Build chat messages for one sample, truncating java to fit."""
        instruction = pair["instruction"]
        java_source = pair["java_source"]
        reasoning = pair["reasoning_trace"]
        bedrock = pair["bedrock_source"]

        # Assistant response = reasoning trace + bedrock source
        # Use reasoning trace as chain-of-thought prefix (G²RPO-A approach)
        # If reasoning is very long, truncate it to keep room for bedrock
        assistant_response = bedrock  # Just the bedrock source for now
        # Reasoning trace is often too long (>2000 tokens). Use a compressed version.
        # Take first 500 chars of reasoning as a brief approach summary
        if reasoning and len(reasoning) > 100:
            reasoning_summary = reasoning[:500]
            # Try to end at a sentence boundary
            last_period = reasoning_summary.rfind(".")
            if last_period > 200:
                reasoning_summary = reasoning_summary[: last_period + 1]
            assistant_response = (
                f"## Conversion Approach\n{reasoning_summary}\n\n"
                f"## Bedrock Add-on Implementation\n{bedrock}"
            )

        # User message: instruction + java source
        user_prefix = f"Mod Description: {instruction}\n\n"
        user_java_header = "Java Source:\n"
        user_suffix = (
            "\n\nConvert this to a Bedrock Add-on. "
            "First explain your conversion approach, "
            "then provide the manifest.json and JavaScript implementation."
        )

        # Calculate fixed overhead
        # System + user_prefix + user_java_header + user_suffix + assistant_response + chat template tokens
        template_overhead = 80  # approximate tokens for chat template markers
        fixed_chars = (
            len(SYSTEM_PROMPT)
            + len(user_prefix)
            + len(user_java_header)
            + len(user_suffix)
            + len(assistant_response)
        )
        fixed_tokens = fixed_chars / chars_per_token + template_overhead

        # Remaining budget for java source
        remaining_tokens = max_length_tokens - fixed_tokens
        if remaining_tokens < 50:
            return None  # Can't fit this sample

        max_java_chars = int(remaining_tokens * chars_per_token)
        if len(java_source) > max_java_chars:
            # Truncate java source, try to end at a line boundary
            truncated = java_source[:max_java_chars]
            last_newline = truncated.rfind("\n")
            if last_newline > max_java_chars // 2:
                truncated = truncated[:last_newline] + "\n// ... (truncated)"
            java_source = truncated

        user_content = f"{user_prefix}{user_java_header}{java_source}{user_suffix}"

        return {
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
                {"role": "assistant", "content": assistant_response},
            ]
        }

    def process_split(split_pairs, split_name):
        records = []
        skipped = 0
        for p in split_pairs:
            result = build_messages(p)
            if result is not None:
                # Pre-apply chat template to create a 'text' field
                # This avoids the Unsloth formatting_func issues
                text = tokenizer.apply_chat_template(
                    result["messages"], tokenize=False, add_generation_prompt=False
                )
                records.append({"text": text})
            else:
                skipped += 1
        print(f"  {split_name}: {len(records)} samples ({skipped} skipped — target too long)")
        return records

    train_records = process_split(train_pairs, "Train")
    val_records = process_split(val_pairs, "Val")

    train_dataset = Dataset.from_list(train_records)
    val_dataset = Dataset.from_list(val_records) if val_records else None

    return train_dataset, val_dataset


# =============================================================================
# Main
# =============================================================================


def main():
    start_time = time.time()

    print("=" * 70)
    print("  Phase 2: SFT Warmup — Minecraft Java→Bedrock Conversion")
    print("  Qwen2.5-Coder-0.5B | fp16 + LoRA r=8 | AMD RX 6600 XT")
    print("=" * 70)
    print(f"  torch: {torch.__version__}, hip: {torch.version.hip}")
    print(f"  GPU: {torch.cuda.get_device_name(0)}")
    vram = torch.cuda.get_device_properties(0).total_memory
    print(f"  VRAM: {vram / 1e9:.1f} GB")

    # ------------------------------------------------------------------
    # [1] Load tokenizer first (needed for chat template in dataset prep)
    # ------------------------------------------------------------------
    print("\n[1] Loading tokenizer...")
    from unsloth import FastLanguageModel

    model_name = "unsloth/Qwen2.5-Coder-0.5B-Instruct"
    max_length = 1024  # Packed sequences fit in 8.6 GB VRAM

    # Load just tokenizer first for dataset prep
    _, tokenizer = FastLanguageModel.from_pretrained(
        model_name=model_name,
        max_seq_length=max_length,
        dtype=torch.float16,
        load_in_4bit=False,
        device_map="cpu",  # Don't use GPU yet
    )
    print(f"  Tokenizer loaded: {model_name}")

    # ------------------------------------------------------------------
    # [2] Prepare dataset (uses tokenizer for chat template)
    # ------------------------------------------------------------------
    print("\n[2] Preparing SFT dataset...")
    train_dataset, val_dataset = prepare_sft_dataset(
        tokenizer,
        max_length_tokens=max_length,
        chars_per_token=3.5,
    )
    print(f"  Train: {len(train_dataset)} samples")
    if val_dataset:
        print(f"  Val:   {len(val_dataset)} samples")

    # Show a sample
    sample_text = train_dataset[0]["text"]
    print(f"\n  Sample (first 500 chars):")
    print(f"    {sample_text[:500]}...")
    print(f"  Sample length: {len(sample_text)} chars")

    # ------------------------------------------------------------------
    # [3] Load model with Unsloth
    # ------------------------------------------------------------------
    print("\n[3] Loading model with Unsloth...")
    # Reload model on GPU (tokenizer already loaded)
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=model_name,
        max_seq_length=max_length,
        dtype=torch.float16,
        load_in_4bit=False,
        device_map="cuda",
    )
    print(f"  Model loaded: {model_name}")
    print(f"  VRAM: {torch.cuda.memory_allocated() / 1e9:.2f} GB")

    # ------------------------------------------------------------------
    # [4] Apply LoRA adapters
    # ------------------------------------------------------------------
    print("\n[4] Applying LoRA adapters (r=8, q/k/v/o_proj)...")
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
    # [5] Setup SFT config
    # ------------------------------------------------------------------
    print("\n[5] Setting up SFT config...")
    from trl import SFTConfig, SFTTrainer

    output_dir = str(OUTPUT_DIR)

    training_args = SFTConfig(
        output_dir=output_dir,
        # Sequence length
        max_length=max_length,
        # Training hyperparams (SFT defaults are good, slightly adjusted)
        per_device_train_batch_size=2,
        gradient_accumulation_steps=4,
        num_train_epochs=2,
        learning_rate=2e-5,  # SFT default, good for LoRA
        lr_scheduler_type="cosine",
        warmup_ratio=0.1,
        optim="adamw_torch",
        weight_decay=0.01,
        max_grad_norm=1.0,
        # Precision
        fp16=True,
        bf16=False,
        # Loss
        loss_type="nll",
        completion_only_loss=None,  # Auto: full sequence for messages format
        # Packing: enabled with BFD strategy (best-fit decreasing)
        # Required by Unsloth's padding_free=True; also more efficient
        packing=True,
        packing_strategy="bfd",
        # Gradient checkpointing
        gradient_checkpointing=True,
        # Logging
        logging_steps=1,
        logging_first_step=True,
        disable_tqdm=True,
        # Eval
        eval_strategy="steps" if val_dataset else "no",
        eval_steps=100 if val_dataset else None,
        # Save
        save_strategy="steps",
        save_steps=100,
        save_total_limit=3,
        load_best_model_at_end=True if val_dataset else False,
        metric_for_best_model="eval_loss" if val_dataset else None,
        # Dataset: use pre-formatted text column
        dataset_text_field="text",
        shuffle_dataset=True,
        seed=42,
        report_to="none",
    )
    print(f"  Config: 2 epochs, lr=2e-5, batch=2×4=8, max_length={max_length}")

    # ------------------------------------------------------------------
    # [6] Initialize SFTTrainer
    # ------------------------------------------------------------------
    print("\n[6] Initializing SFTTrainer...")

    trainer = SFTTrainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        processing_class=tokenizer,
        peft_config=None,  # Already applied via FastLanguageModel.get_peft_model
    )
    print("  SFTTrainer initialized")

    # Count total steps
    total_steps = (
        len(train_dataset)
        // (training_args.per_device_train_batch_size * training_args.gradient_accumulation_steps)
    ) * training_args.num_train_epochs
    print(f"  Estimated total steps: ~{total_steps}")

    # ------------------------------------------------------------------
    # [7] Train!
    # ------------------------------------------------------------------
    print(f"\n[7] Starting SFT training...")
    print(f"  VRAM before training: {torch.cuda.memory_allocated() / 1e9:.2f} GB")
    print("  " + "=" * 60)

    try:
        trainer.train()
        print("  " + "=" * 60)
        print("  SFT TRAINING COMPLETE")
    except RuntimeError as e:
        if "out of memory" in str(e).lower():
            print(f"\n  OOM: {e}")
            import gc

            torch.cuda.empty_cache()
            gc.collect()
            raise
        raise

    # ------------------------------------------------------------------
    # [8] Save model
    # ------------------------------------------------------------------
    print("\n[8] Saving SFT model...")
    trainer.save_model(f"{output_dir}/final")
    tokenizer.save_pretrained(f"{output_dir}/final")
    print(f"  Saved to {output_dir}/final/")

    # ------------------------------------------------------------------
    # [9] Quick evaluation — generate a sample
    # ------------------------------------------------------------------
    print("\n[9] Quick evaluation...")
    model.eval()
    FastLanguageModel.for_inference(model)

    # Test on a sample from the training set
    sample_text = train_dataset[0]["text"]
    # Extract just the system + user parts (before assistant)
    # The text is pre-formatted with chat template, find the assistant cutoff
    if "<|im_start|>assistant" in sample_text:
        prompt_text = sample_text[: sample_text.index("<|im_start|>assistant")]
        expected_text = sample_text[sample_text.index("<|im_start|>assistant") :]
        # Clean expected text
        expected_text = (
            expected_text.replace("<|im_start|>assistant\n", "").replace("<|im_end|>", "").strip()
        )
    else:
        prompt_text = sample_text[:500]
        expected_text = ""

    inputs = tokenizer(prompt_text, return_tensors="pt", truncation=True, max_length=max_length).to(
        "cuda"
    )

    print(f"  Generating from test prompt...")
    with torch.no_grad():
        out = model.generate(
            **inputs,
            max_new_tokens=512,
            temperature=0.3,  # Low temperature for deterministic output
            top_p=0.95,
            do_sample=True,
            pad_token_id=tokenizer.pad_token_id,
        )

    response = tokenizer.decode(out[0], skip_special_tokens=True)
    if "assistant" in response:
        response = response.split("assistant")[-1].strip()

    # Compare with expected
    print(f"  Generated ({len(response)} chars): {response[:300]}...")
    print(f"  Expected ({len(expected_text)} chars): {expected_text[:300]}...")

    # Compute reward using the same reward function as GRPO
    sys.path.insert(0, str(SCRIPT_DIR))
    from phase1_grpo_quickwins import compute_reward

    reward = compute_reward(response, expected_text)
    print(f"  Reward vs expected: {reward:.3f}")

    # ------------------------------------------------------------------
    # [10] Summary
    # ------------------------------------------------------------------
    elapsed = time.time() - start_time
    print(f"\n✓ Phase 2 SFT warmup complete!")
    print(f"  Model saved: {output_dir}/final/")
    print(f"  Total time: {elapsed / 60:.1f} min")
    print(f"  Final VRAM: {torch.cuda.memory_allocated() / 1e9:.2f} GB")
    print(f"\n  Next step: Use this SFT model as the starting point for Phase 1 GRPO")
    print(f"  → Load from {output_dir}/final/ instead of the base model")


if __name__ == "__main__":
    main()
