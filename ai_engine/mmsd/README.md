# MMSD (Modding Multi-Step Dataset)

This directory contains the MMSD dataset and tooling for training AI models on Java-to-Bedrock Minecraft mod conversion.

## Mapping Standard

**All Java source code in training pairs MUST use Mojmap naming conventions.**

### Background

Forge JAR files use obfuscated class/method names. Over Forge's history, three mappings have been used:

| Mapping | Used In | Example |
|---------|---------|---------|
| **SRG** (Searge/MCP) | Forge 1.12–1.16 | `func_123456`, `field_789012` |
| **MCP** | Forge 1.12–1.20 | `registerBlock` (community-maintained) |
| **Mojmap** | Forge 1.21+ | `registerBlock` (official Mojang mappings) |

Training on mixed-mapping data causes the model to output inconsistent or hallucinated method names.

### Valid Patterns (Mojmap)

```java
// Method names
public void registerBlock() {}
public BlockState getDefaultState() {}
protected void onPlayerInteract() {}

// Package names
import net.minecraft.world.level.block.Block;
import net.minecraft.world.entity.Entity;

// Class names follow standard Java conventions
public class SpellcastingStation extends Block {}
```

### Invalid Patterns (SRG/MCP)

```java
// SRG method patterns
public void func_123456_a() {}
public int field_789012;

// SRG package patterns
import net_minecraft.world.entity.Entity;

// SRG inner class patterns
private class class_345678 {}
```

### Why This Matters

The model cannot reliably learn the Java→Bedrock mapping if it sees five different names for `Block.registerBlock()`. Normalizing to Mojmap once, before any training run, permanently improves model output quality without any inference-time cost.

## Validation

The `validators/mojmap_validator.py` module provides:

- `MojmapMappingValidator.validate(java_source)` - Checks a single source for SRG patterns
- `MojmapMappingValidator.filter_pairs(pairs)` - Separates valid/invalid pairs

The `run_validation.py` script runs full validation including Mojmap checks before producing the validated training set.

## Dataset Structure

```
ai_engine/mmsd/
├── synthesis_pairs.jsonl     # Raw generated pairs (1400 pairs)
├── data/
│   └── processed/
│       ├── synthesis_pairs.jsonl   # Pre-processed input
│       └── validated_pairs.jsonl   # Output with Mojmap validation
├── validators/
│   ├── code_validator.py     # Java/Bedrock syntax validation
│   └── mojmap_validator.py   # SRG/Mojmap pattern detection
├── run_validation.py         # Full validation pipeline
└── README.md                 # This file
```

## Adding New Pairs

When generating new synthesis pairs:

1. Ensure source Java uses Mojmap naming (official Forge 1.21+ mappings)
2. Run `run_validation.py` to validate and filter
3. Add validated pairs to the training set

## References

- [Fabric Loom](https://github.com/FabricMC/fabric-loom) - Tool for remapping JARs
- [Enigma](https://github.com/FabricMC/Enigma) - Reverse-engineering tool with mapping support
- [Mojang Mapping](https://minecraft.wiki.ffabila.com/wiki/Mojang_Mappings) - Official mapping documentation