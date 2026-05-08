#!/usr/bin/env python3
"""
Minimal GRPO RL Training for PortKit Mod Conversion on AMD ROCm

Uses GRPO (Group Relative Policy Optimization) - a simplified PPO variant:
- Sample multiple responses per prompt
- Compute rewards using portkit's reward functions
- Use clipped surrogate objective for stable updates

Reuses reward functions from:
- portkit_mod_convert.py (5 rubric rewards)
- minecraft_contracts.py (contract validators)

Usage:
    python rl_ppo_train.py \
        --model Qwen/Qwen2.5-Coder-7B-Instruct \
        --num_samples 4 \
        --ppo_epochs 2 \
        --max_length 1024 \
        --batch_size 1
"""

import json
import re
import gc
import os
import sys
import time
import random
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader
from datasets import Dataset

from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import LoraConfig, get_peft_model, TaskType
from tqdm import tqdm

# ── Add ai-engine to path for contract validators ───────────────────────────────
AI_ENGINE_PATH = Path(__file__).parent.parent / "ai-engine"
if AI_ENGINE_PATH.exists() and str(AI_ENGINE_PATH) not in sys.path:
    sys.path.insert(0, str(AI_ENGINE_PATH))

# ── Device ────────────────────────────────────────────────────────────────────
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"[RL] Device: {DEVICE}, ROCm: {torch.version.hip if hasattr(torch.version, 'hip') else 'N/A'}")

# ── Reward Function Helpers (from portkit_mod_convert.py) ──────────────────────

def _extract_manifest(text: str) -> Optional[str]:
    """Extract manifest.json content from completion text."""
    json_blocks = re.findall(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    for block in json_blocks:
        if "format_version" in block or "header" in block:
            return block.strip()

    bedrock_section = re.search(
        r"## Bedrock Add-on Output(.*?)(?:##|$)", text, re.DOTALL
    )
    if bedrock_section:
        section = bedrock_section.group(1)
        brace_match = re.search(
            r'\{[^{}]*"format_version"[^{}]*\}', section, re.DOTALL
        )
        if brace_match:
            return brace_match.group(0)
    return None


def _extract_js(text: str) -> Optional[str]:
    """Extract JavaScript code from completion text."""
    js_blocks = re.findall(r"```(?:javascript|js)\s*(.*?)\s*```", text, re.DOTALL)
    if js_blocks:
        return max(js_blocks, key=len).strip()

    scripts_section = re.search(
        r"(?:scripts|behavior_pack|content).*?\.js", text, re.DOTALL | re.IGNORECASE
    )
    if scripts_section:
        start = scripts_section.start()
        end = min(start + 10000, len(text))
        return text[start:end]
    return None


def _simple_tokenize(text: str) -> List[str]:
    """Simple word-based tokenization."""
    text = re.sub(r"```[^`]*```", "", text)
    text = re.sub(r"[^\w\s]", " ", text)
    return [t.lower() for t in text.split() if t.strip()]


def _bleu_score(reference: str, hypothesis: str) -> float:
    """Compute simple BLEU-like F1 score (1-gram precision + recall)."""
    ref_tokens = _simple_tokenize(reference)
    hyp_tokens = _simple_tokenize(hypothesis)
    if not hyp_tokens or not ref_tokens:
        return 0.0
    overlap = sum(1 for t in hyp_tokens if t in ref_tokens)
    precision = overlap / len(hyp_tokens)
    ref_set = set(ref_tokens)
    hyp_set = set(hyp_tokens)
    overlap_set = len(ref_set & hyp_set)
    recall = overlap_set / len(ref_set) if ref_set else 0
    if precision + recall == 0:
        return 0.0
    f1 = 2 * precision * recall / (precision + recall)
    return f1


# ── Contract Validators (from ai-engine/rl/minecraft_contracts.py) ────────────

class ViolationSeverity:
    CRITICAL = "critical"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ContractType:
    COORDINATE_SEMANTICS = "coordinate_semantics"
    COMPONENT_NESTING = "component_nesting"
    JSON_SCHEMA = "json_schema"
    API_CONTRACT = "api_contract"


def validate_minecraft_contracts(code: str) -> Tuple[float, List[str]]:
    """Validate Bedrock code against Minecraft contracts. Returns (score, violations)."""
    violations = []
    score = 1.0

    # Coordinate semantics: block coords must be integers
    coord_pattern = re.compile(r'"(-?\d+(?:\.\d+)?)"')
    for line_num, line in enumerate(code.split('\n'), 1):
        stripped = line.strip()
        if stripped.startswith('"x"') or stripped.startswith('"y"') or stripped.startswith('"z"'):
            coord_matches = re.findall(r':\s*(-?\d+\.\d+)', line)
            for match in coord_matches:
                violations.append(f"float-coordinate:{match}")
                score -= 0.1

    # JSON Schema validation
    try:
        data = json.loads(code) if code.startswith("{") else None
        if data:
            if "format_version" not in data:
                violations.append("missing:format_version")
                score -= 0.15
            if "header" not in data:
                violations.append("missing:header")
                score -= 0.15
    except json.JSONDecodeError:
        if code.strip().startswith("{"):
            violations.append("invalid-json")
            score -= 0.3

    # Component nesting check
    FORBIDDEN = {
        "minecraft:lodestone": ["minecraft:display_name", "minecraft:lore"],
        "minecraft:enchantments": ["minecraft:enchantment"],
    }
    try:
        data = json.loads(code) if code.startswith("{") else {}
        if isinstance(data, dict):
            for key, value in data.items():
                if key in FORBIDDEN and isinstance(value, dict):
                    for child_key in value.keys():
                        if child_key in FORBIDDEN[key]:
                            violations.append(f"forbidden-nesting:{key}>{child_key}")
                            score -= 0.1
    except (json.JSONDecodeError, TypeError):
        pass

    return max(0.0, score), violations


# ── Reward Functions ──────────────────────────────────────────────────────────

def extract_manifest_reward(text: str) -> float:
    """Check if model produces JSON block with manifest keywords."""
    has_json_block = bool(re.search(r"```json\s*\{", text, re.DOTALL))
    has_manifest_keywords = bool(
        re.search(r"format_version|header|modules|dependencies", text)
    )
    score = 0.0
    if has_json_block:
        score += 0.5
    if has_manifest_keywords:
        score += 0.5
    return min(score, 1.0)


def extract_js_reward(text: str) -> float:
    """Check if model produces JavaScript code blocks."""
    has_js_block = bool(re.search(r"```(?:javascript|js)\s*", text, re.DOTALL))
    has_js_keywords = bool(
        re.search(r"\bfunction\b|\bvar\b|\blet\b|\bconst\b|\bexport\b", text)
    )
    score = 0.0
    if has_js_block:
        score += 0.5
    if has_js_keywords:
        score += 0.5
    return min(score, 1.0)


def json_validity_reward(text: str) -> float:
    """Check if extracted manifest is valid JSON with required fields."""
    manifest_str = _extract_manifest(text)
    if manifest_str is None:
        return 0.0
    try:
        data = json.loads(manifest_str)
    except json.JSONDecodeError:
        return 0.0
    has_version = "format_version" in data
    has_header = "header" in data
    if has_version and has_header:
        return 1.0
    elif has_version or has_header:
        return 0.5
    return 0.0


def js_syntax_reward(text: str) -> float:
    """Check if extracted JS has valid syntax patterns."""
    js_code = _extract_js(text)
    if js_code is None:
        return 0.0
    has_function = bool(re.search(r"\bfunction\s+\w+|\(\)\s*=>|\w+\s*\(\s*\)", js_code))
    has_control = bool(re.search(r"\b(if|else|for|while|switch|case)\b", js_code))
    has_valid_structure = bool(re.search(r"[\{\}]", js_code))
    score = 0.0
    if has_function:
        score += 0.4
    if has_control:
        score += 0.3
    if has_valid_structure:
        score += 0.3
    return min(score, 1.0)


def bleu_reward(text: str, ground_truth: str) -> float:
    """Compute BLEU-like score between completion and ground truth."""
    return _bleu_score(ground_truth, text)


def contract_reward(text: str) -> float:
    """Reward based on Minecraft contract validation score."""
    score, _ = validate_minecraft_contracts(text)
    return score  # 0.0 to 1.0


def compute_total_reward(text: str, ground_truth: str) -> float:
    """
    Compute weighted total reward from all reward functions.
    Weights match the verifiers rubric: [0.20, 0.20, 0.25, 0.15, 0.20] + contract bonus
    """
    r1 = extract_manifest_reward(text)
    r2 = extract_js_reward(text)
    r3 = json_validity_reward(text)
    r4 = js_syntax_reward(text)
    r5 = bleu_reward(text, ground_truth)
    r6 = contract_reward(text)

    base_reward = r1 * 0.20 + r2 * 0.20 + r3 * 0.25 + r4 * 0.15 + r5 * 0.20
    contract_bonus = r6 * 0.10  # Small bonus for contract compliance

    return min(1.0, base_reward + contract_bonus)


# ── Data Loading ──────────────────────────────────────────────────────────────

SYSTEM_PROMPT = (
    "You are PortKit, an expert at converting Minecraft Java Edition mods (Forge) "
    "to Bedrock Edition Add-ons. Given a mod description and Java source code, "
    "first reason through the platform mapping, then produce the Bedrock Add-on implementation."
)


def load_pairs(
    data_path: Optional[Path] = None,
    train_split: float = 0.9,
    max_examples: int = -1,
    shuffle_seed: int = 42,
) -> Tuple[List[Dict], List[Dict]]:
    """Load validated pairs from MMSD dataset."""
    if data_path is None:
        data_path = Path(__file__).parent.parent / "ai_engine/mmsd/data/processed/validated_pairs.jsonl"

    pairs = []
    with open(data_path) as f:
        for line in f:
            if line.strip():
                pairs.append(json.loads(line))

    if shuffle_seed >= 0:
        random.seed(shuffle_seed)
        random.shuffle(pairs)

    if max_examples > 0:
        pairs = pairs[:max_examples]

    n = len(pairs)
    split = int(n * train_split)
    return pairs[:split], pairs[split:]


def build_prompt(row: dict) -> str:
    """Build full prompt string from a data row."""
    user = (
        f"Mod Description: {row['instruction']}\n\n"
        f"Java Source:\n{row['java_source']}\n\n"
        "Convert this to a Bedrock Add-on. First explain your conversion approach, then provide the files."
    )
    return f"<|im_start|>system\n{SYSTEM_PROMPT}<|im_end|>\n<|im_start|>user\n{user}<|im_end|>\n<|im_start|>assistant\n"


# ── GRPO Training ─────────────────────────────────────────────────────────────

@dataclass
class GRPOConfig:
    num_samples: int = 4          # Responses per prompt per update
    ppo_epochs: int = 2           # PPO update epochs per batch
    max_length: int = 1024        # Max tokens per response
    max_new_tokens: int = 512     # Max new tokens to generate
    temperature: float = 0.8       # Sampling temperature
    top_p: float = 0.9            # Nucleus sampling
    lr: float = 1e-5              # Learning rate
    clip_eps: float = 0.2         # PPO clip epsilon
    gamma: float = 1.0             # Discount factor
    lambda_: float = 0.95          # GAE lambda
    max_grad_norm: float = 1.0     # Gradient clipping
    weight_decay: float = 0.01
    warmup_steps: int = 10
    logging_steps: int = 5
    save_steps: int = 100
    seed: int = 42


class GRPOTrainer:
    """
    GRPO (Group Relative Policy Optimization) trainer.

    For each batch of prompts:
    1. Sample num_samples responses per prompt
    2. Compute rewards for all responses
    3. Compute advantages via reward normalization within each group
    4. Run PPO epochs with clipped surrogate objective
    5. Use reward as baseline for advantage (simplified, no value network)
    """

    def __init__(
        self,
        model,
        tokenizer,
        config: GRPOConfig,
        train_pairs: List[Dict],
        device: torch.device = DEVICE,
    ):
        self.model = model
        self.tokenizer = tokenizer
        self.config = config
        self.train_pairs = train_pairs
        self.device = device
        self.old_policy_log_probs: Optional[torch.Tensor] = None
        self.step = 0

        # Optimizer
        self.optimizer = torch.optim.AdamW(
            model.parameters(),
            lr=config.lr,
            weight_decay=config.weight_decay,
        )

        # LR scheduler
        self.scheduler = torch.optim.lr_scheduler.LinearLR(
            self.optimizer,
            start_factor=0.1,
            end_factor=1.0,
            total_iters=config.warmup_steps,
        )

    @torch.no_grad()
    def generate_batch(self, prompts: List[str]) -> List[str]:
        """Generate num_samples responses for each prompt."""
        all_outputs = []

        for prompt in prompts:
            enc = self.tokenizer(
                prompt,
                return_tensors="pt",
                truncation=True,
                max_length=self.config.max_length,
            ).to(self.device)

            prompt_len = enc["input_ids"].shape[1]

            outputs = self.model.generate(
                **enc,
                max_new_tokens=self.config.max_new_tokens,
                temperature=self.config.temperature,
                top_p=self.config.top_p,
                do_sample=True,
                pad_token_id=self.tokenizer.pad_token_id or self.tokenizer.eos_token_id,
                repetition_penalty=1.1,
            )

            for i in range(self.config.num_samples):
                response_ids = outputs[i, prompt_len:]
                response_text = self.tokenizer.decode(response_ids, skip_special_tokens=True)
                all_outputs.append((prompt, response_text))

        return all_outputs

    def compute_advantages(self, rewards: List[float]) -> torch.Tensor:
        """
        Compute advantages within each group of num_samples.
        Simplified: use reward as baseline (no value network).
        Advantage = reward - mean(rewards)  (centered)
        """
        advantages = []
        for i in range(0, len(rewards), self.config.num_samples):
            group = rewards[i:i + self.config.num_samples]
            group_t = torch.tensor(group, dtype=torch.float32, device=self.device)
            baseline = group_t.mean()
            group_adv = group_t - baseline
            advantages.extend(group_adv.tolist())
        return torch.tensor(advantages, dtype=torch.float32, device=self.device)

    def compute_policy_loss(
        self,
        log_probs: torch.Tensor,
        old_log_probs: torch.Tensor,
        advantages: torch.Tensor,
        mask: torch.Tensor,
    ) -> torch.Tensor:
        """
        PPO clipped surrogate objective.
        L = -min(r * A, clip(r, 1-eps, 1+eps) * A)
        where r = exp(log_prob - old_log_prob)
        """
        ratio = torch.exp(log_probs - old_log_probs)
        surr1 = ratio * advantages
        surr2 = torch.clamp(ratio, 1 - self.config.clip_eps, 1 + self.config.clip_eps) * advantages
        loss = -torch.min(surr1, surr2)
        loss = (loss * mask).sum() / mask.sum()
        return loss

    def ppo_update(self, prompts: List[str], outputs: List[str], rewards: List[float]):
        """
        Run PPO update on a batch of (prompt, output, reward) tuples.
        """
        self.model.train()

        # Tokenize
        enc = self.tokenizer(
            prompts + outputs,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=self.config.max_length,
        ).to(self.device)

        prompt_lens = [
            self.tokenizer(p, return_tensors="pt")["input_ids"].shape[1]
            for p in prompts
        ] * self.config.num_samples

        response_enc = self.tokenizer(
            outputs,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=self.config.max_length,
        ).to(self.device)

        advantages = self.compute_advantages(rewards).clamp(-5, 5)

        all_loss = []
        for _ in range(self.config.ppo_epochs):
            # Forward pass
            outputs_enc = self.tokenizer(
                outputs,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=self.config.max_length,
            ).to(self.device)

            forward_enc = {
                "input_ids": outputs_enc["input_ids"],
                "attention_mask": outputs_enc["attention_mask"],
            }

            logits = self.model(**forward_enc).logits  # (batch, seq, vocab)
            response_lens = (outputs_enc["attention_mask"].sum(dim=1) - 1).clamp(min=1)

            log_probs = F.log_softmax(logits, dim=-1)
            response_log_probs = torch.gather(
                log_probs[:, :-1, :],
                2,
                outputs_enc["input_ids"][:, 1:].unsqueeze(-1),
            ).squeeze(-1)  # (batch, seq-1)

            # Mask padding
            mask = outputs_enc["attention_mask"][:, :-1].float()
            masked_log_probs = (response_log_probs * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1)

            # Old log probs (from first generation)
            if self.old_policy_log_probs is None:
                self.old_policy_log_probs = masked_log_probs.detach()

            # Compute loss
            loss = self.compute_policy_loss(
                masked_log_probs,
                self.old_policy_log_probs,
                advantages,
                mask.sum(dim=1) / mask.shape[1],
            )

            # Backward
            self.optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), self.config.max_grad_norm)
            self.optimizer.step()
            self.scheduler.step()

            all_loss.append(loss.item())

            # Update old log progs with current for next epoch
            self.old_policy_log_probs = masked_log_probs.detach()

        self.step += 1
        return sum(all_loss) / len(all_loss)

    def train_step(self, batch_pairs: List[Dict]) -> Dict[str, float]:
        """Single training step on a batch of pairs."""
        prompts = [build_prompt(p) for p in batch_pairs]
        ground_truths = [p["bedrock_source"] for p in batch_pairs]

        # Generate multiple samples
        all_prompts = []
        all_outputs = []
        all_rewards = []

        for _ in range(self.config.num_samples):
            for p_idx, prompt in enumerate(prompts):
                enc = self.tokenizer(
                    prompt,
                    return_tensors="pt",
                    truncation=True,
                    max_length=self.config.max_length,
                ).to(self.device)

                prompt_len = enc["input_ids"].shape[1]

                output_ids = self.model.generate(
                    **enc,
                    max_new_tokens=self.config.max_new_tokens,
                    temperature=self.config.temperature,
                    top_p=self.config.top_p,
                    do_sample=True,
                    pad_token_id=self.tokenizer.pad_token_id or self.tokenizer.eos_token_id,
                    repetition_penalty=1.1,
                )

                response_ids = output_ids[0, prompt_len:]
                response_text = self.tokenizer.decode(response_ids, skip_special_tokens=True)

                all_prompts.append(prompt)
                all_outputs.append(response_text)

                reward = compute_total_reward(response_text, ground_truths[p_idx])
                all_rewards.append(reward)

        # PPO update
        mean_reward = sum(all_rewards) / len(all_rewards)
        loss = self.ppo_update(all_prompts, all_outputs, all_rewards)

        return {
            "loss": loss,
            "mean_reward": mean_reward,
            "max_reward": max(all_rewards),
            "min_reward": min(all_rewards),
        }


# ── Main Training Loop ────────────────────────────────────────────────────────

def train(
    model_id: str = "Qwen/Qwen2.5-Coder-7B-Instruct",
    num_samples: int = 4,
    ppo_epochs: int = 2,
    max_length: int = 1024,
    max_new_tokens: int = 512,
    batch_size: int = 1,
    max_examples: int = 50,
    total_steps: int = 100,
    lr: float = 1e-5,
    temperature: float = 0.8,
    seed: int = 42,
    lora_r: int = 32,
    lora_alpha: int = 64,
    save_dir: str = "/tmp/portkit-rl-checkpoints",
):
    """Main training function."""
    print(f"\n{'='*60}")
    print(f"PortKit GRPO Training on AMD ROCm")
    print(f"{'='*60}")
    print(f"Model: {model_id}")
    print(f"Num samples per prompt: {num_samples}")
    print(f"PPO epochs per step: {ppo_epochs}")
    print(f"Max examples: {max_examples}")
    print(f"Total steps: {total_steps}")
    print(f"Learning rate: {lr}")
    print(f"Temperature: {temperature}")
    print(f"LoRA r={lora_r}, alpha={lora_alpha}")
    print(f"{'='*60}\n")

    # Set seeds
    random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

    # Load data
    print("[1/6] Loading training data...")
    train_pairs, eval_pairs = load_pairs(max_examples=max_examples if max_examples > 0 else -1)
    print(f"  Train pairs: {len(train_pairs)}, Eval pairs: {len(eval_pairs)}")

    # Load tokenizer
    print("[2/6] Loading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token_id = tokenizer.eos_token_id

    # Load model with LoRA
    print("[3/6] Loading model with LoRA...")
    torch_dtype = torch.bfloat16
    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        torch_dtype=torch_dtype,
        device_map="auto",
        trust_remote_code=True,
    )

    lora_config = LoraConfig(
        r=lora_r,
        lora_alpha=lora_alpha,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        lora_dropout=0.05,
        bias="none",
        task_type=TaskType.CAUSAL_LM,
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    # GRPO config
    config = GRPOConfig(
        num_samples=num_samples,
        ppo_epochs=ppo_epochs,
        max_length=max_length,
        max_new_tokens=max_new_tokens,
        lr=lr,
        temperature=temperature,
        clip_eps=0.2,
    )

    # Trainer
    trainer =GRPOTrainer(
        model=model,
        tokenizer=tokenizer,
        config=config,
        train_pairs=train_pairs,
        device=DEVICE,
    )

    # Training loop
    print(f"[4/6] Starting training for {total_steps} steps...")
    save_path = Path(save_dir)
    save_path.mkdir(parents=True, exist_ok=True)

    batch_size = max(1, batch_size)
    step = 0
    best_reward = 0.0

    while step < total_steps:
        # Sample batch
        batch_indices = random.sample(range(len(train_pairs)), min(batch_size, len(train_pairs)))
        batch = [train_pairs[i] for i in batch_indices]

        # Training step
        metrics = trainer.train_step(batch)

        step += 1

        # Logging
        if step % config.logging_steps == 0:
            print(
                f"  Step {step}/{total_steps} | "
                f"loss={metrics['loss']:.4f} | "
                f"mean_reward={metrics['mean_reward']:.4f} | "
                f"max_reward={metrics['max_reward']:.4f}"
            )

        # Save
        if step % config.save_steps == 0:
            ckpt_path = save_path / f"step_{step}"
            model.save_pretrained(ckpt_path)
            tokenizer.save_pretrained(ckpt_path)
            print(f"  [Saved checkpoint to {ckpt_path}]")

        # Update best
        if metrics["mean_reward"] > best_reward:
            best_reward = metrics["mean_reward"]

    # Final save
    final_path = save_path / "final"
    model.save_pretrained(final_path)
    tokenizer.save_pretrained(final_path)
    print(f"\n[5/6] Training complete! Best reward: {best_reward:.4f}")
    print(f"  Final checkpoint: {final_path}")

    # Evaluation
    print(f"\n[6/6] Running evaluation on {len(eval_pairs)} eval pairs...")
    eval_rewards = []
    model.eval()
    with torch.no_grad():
        for pair in tqdm(eval_pairs, desc="Evaluating"):
            prompt = build_prompt(pair)
            enc = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=max_length).to(DEVICE)
            prompt_len = enc["input_ids"].shape[1]
            output_ids = model.generate(
                **enc,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                top_p=0.9,
                do_sample=False,
                pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id,
            )
            response_text = tokenizer.decode(output_ids[0, prompt_len:], skip_special_tokens=True)
            reward = compute_total_reward(response_text, pair["bedrock_source"])
            eval_rewards.append(reward)

    mean_eval = sum(eval_rewards) / len(eval_rewards)
    print(f"\n  Eval Results:")
    print(f"  Mean reward: {mean_eval:.4f}")
    print(f"  Max reward: {max(eval_rewards):.4f}")
    print(f"  Min reward: {min(eval_rewards):.4f}")

    return mean_eval


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="PortKit GRPO Training on AMD ROCm")
    parser.add_argument("--model", default="Qwen/Qwen2.5-Coder-7B-Instruct")
    parser.add_argument("--num_samples", type=int, default=4)
    parser.add_argument("--ppo_epochs", type=int, default=2)
    parser.add_argument("--max_length", type=int, default=1024)
    parser.add_argument("--max_new_tokens", type=int, default=512)
    parser.add_argument("--batch_size", type=int, default=1)
    parser.add_argument("--max_examples", type=int, default=50,
                        help="Max training examples to use (-1 for all)")
    parser.add_argument("--total_steps", type=int, default=100)
    parser.add_argument("--lr", type=float, default=1e-5)
    parser.add_argument("--temperature", type=float, default=0.8)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--lora_r", type=int, default=32)
    parser.add_argument("--lora_alpha", type=int, default=64)
    parser.add_argument("--save_dir", default="/tmp/portkit-rl-checkpoints")

    args = parser.parse_args()

    try:
        final_reward = train(
            model_id=args.model,
            num_samples=args.num_samples,
            ppo_epochs=args.ppo_epochs,
            max_length=args.max_length,
            max_new_tokens=args.max_new_tokens,
            batch_size=args.batch_size,
            max_examples=args.max_examples,
            total_steps=args.total_steps,
            lr=args.lr,
            temperature=args.temperature,
            seed=args.seed,
            lora_r=args.lora_r,
            lora_alpha=args.lora_alpha,
            save_dir=args.save_dir,
        )
    except KeyboardInterrupt:
        print("\nTraining interrupted.")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)