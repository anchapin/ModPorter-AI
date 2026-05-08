# portkit-mod-convert

PortKit Mod Conversion environment for training on Minecraft Java-to-Bedrock mod conversion.

## Overview

This environment uses the MMSD (Modding Multi-Step Dataset) to train models on converting Java Edition Forge mods to Bedrock Edition Add-ons.

### Dataset

- **Source**: `ai_engine/mmsd/data/processed/validated_pairs.jsonl`
- **Size**: 1,400 training pairs (1,260 train / 140 eval)
- **Split**: 90/10 train/eval

### Task Format

Each task provides:
- `instruction`: Brief mod description
- `java_source`: Java Forge 1.21 mod code (Mojmap naming)

Expected output: Bedrock Add-on (manifest.json + scripting .js files)

### Reward Functions

| Reward | Weight | Description |
|--------|--------|-------------|
| `extract_manifest_reward` | 0.25 | Model produces JSON block with manifest keywords |
| `extract_js_reward` | 0.25 | Model produces JavaScript code blocks |
| `json_validity_reward` | 0.30 | Extracted manifest is valid JSON with format_version + header |
| `js_syntax_reward` | 0.20 | Extracted JS has valid syntax patterns |

## Usage

```bash
# Install
prime env install ./environments/portkit-mod-convert

# Run eval
prime eval run portkit-mod-convert -m openai/gpt-4.1-mini -n 20 -r 3
```

## Tags

- code-generation, multi-turn, sandbox