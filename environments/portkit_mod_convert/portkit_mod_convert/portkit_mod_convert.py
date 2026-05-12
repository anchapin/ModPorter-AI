import json
import re
from typing import List, Optional

import verifiers as vf
from datasets import Dataset
from pathlib import Path


def _simple_tokenize(text: str) -> List[str]:
    """Simple word-based tokenization."""
    text = re.sub(r"```[^`]*```", "", text)
    text = re.sub(r"[^\w\s]", " ", text)
    return [t.lower() for t in text.split() if t.strip()]


def _bleu_score(reference: str, hypothesis: str) -> float:
    """Compute simple BLEU-like score (1-gram precision)."""
    ref_tokens = _simple_tokenize(reference)
    hyp_tokens = _simple_tokenize(hypothesis)

    if not hyp_tokens:
        return 0.0
    if not ref_tokens:
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


def load_environment() -> vf.SingleTurnEnv:
    """Load the PortKit Mod Conversion environment.

    Uses existing MMSD validated pairs for training on Minecraft
    Java (Forge) to Bedrock (Add-on) mod conversion.
    """
    dataset_path = (
        Path(__file__).parent.parent.parent.parent
        / "ai_engine/mmsd/data/processed/validated_pairs.jsonl"
    )

    if not dataset_path.exists():
        raise FileNotFoundError(
            f"Dataset not found at {dataset_path}. "
            "Please ensure ai_engine/mmsd/data/processed/validated_pairs.jsonl exists."
        )

    pairs = []
    with open(dataset_path) as f:
        for line in f:
            if line.strip():
                pairs.append(json.loads(line))

    n = len(pairs)
    split = int(n * 0.9)
    train_pairs = pairs[:split]
    eval_pairs = pairs[split:]

    def build_prompt(row: dict) -> List[dict]:
        system = (
            "You are PortKit, an expert at converting Minecraft Java Edition mods (Forge) "
            "to Bedrock Edition Add-ons. Given a mod description and Java source code, "
            "first reason through the platform mapping, then produce the Bedrock Add-on implementation."
        )
        user = (
            f"Mod Description: {row['instruction']}\n\n"
            f"Java Source:\n{row['java_source']}\n\n"
            "Convert this to a Bedrock Add-on. First explain your conversion approach, then provide the files."
        )
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

    train_rows = [
        {
            "prompt": build_prompt(p),
            "answer": p["bedrock_source"],
            "info": {"reasoning_trace": p["reasoning_trace"]},
        }
        for p in train_pairs
    ]

    eval_rows = [
        {
            "prompt": build_prompt(p),
            "answer": p["bedrock_source"],
            "info": {"reasoning_trace": p["reasoning_trace"]},
        }
        for p in eval_pairs
    ]

    train_ds = Dataset.from_list(train_rows)
    eval_ds = Dataset.from_list(eval_rows)

    rubric = vf.Rubric(
        funcs=[
            extract_manifest_reward,
            extract_js_reward,
            json_validity_reward,
            js_syntax_reward,
            bleu_reward,
        ],
        weights=[0.20, 0.20, 0.25, 0.15, 0.20],
    )

    return vf.SingleTurnEnv(
        dataset=train_ds,
        eval_dataset=eval_ds,
        rubric=rubric,
    )


def _extract_manifest(text: str) -> Optional[str]:
    """Extract manifest.json content from completion text."""
    json_blocks = re.findall(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    for block in json_blocks:
        if "format_version" in block or "header" in block:
            return block.strip()

    bedrock_section = re.search(r"## Bedrock Add-on Output(.*?)(?:##|$)", text, re.DOTALL)
    if bedrock_section:
        section = bedrock_section.group(1)
        brace_match = re.search(r'\{[^{}]*"format_version"[^{}]*\}', section, re.DOTALL)
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


async def extract_manifest_reward(completion: List[dict], answer: str, info: dict) -> float:
    """Check if model produces JSON block with manifest keywords."""
    text = completion[-1]["content"] if completion else ""

    has_json_block = bool(re.search(r"```json\s*\{", text, re.DOTALL))
    has_manifest_keywords = bool(re.search(r"format_version|header|modules|dependencies", text))

    score = 0.0
    if has_json_block:
        score += 0.5
    if has_manifest_keywords:
        score += 0.5

    return min(score, 1.0)


async def extract_js_reward(completion: List[dict], answer: str, info: dict) -> float:
    """Check if model produces JavaScript code blocks."""
    text = completion[-1]["content"] if completion else ""

    has_js_block = bool(re.search(r"```(?:javascript|js)\s*", text, re.DOTALL))
    has_js_keywords = bool(re.search(r"\bfunction\b|\bvar\b|\blet\b|\bconst\b|\bexport\b", text))

    score = 0.0
    if has_js_block:
        score += 0.5
    if has_js_keywords:
        score += 0.5

    return min(score, 1.0)


async def json_validity_reward(completion: List[dict], answer: str, info: dict) -> float:
    """Check if extracted manifest is valid JSON with required fields."""
    text = completion[-1]["content"] if completion else ""
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


async def js_syntax_reward(completion: List[dict], answer: str, info: dict) -> float:
    """Check if extracted JS has valid syntax patterns."""
    text = completion[-1]["content"] if completion else ""
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


async def bleu_reward(completion: List[dict], answer: str, info: dict) -> float:
    """Compute BLEU-like score between completion and ground truth answer."""
    text = completion[-1]["content"] if completion else ""
    score = _bleu_score(answer, text)
    return score
