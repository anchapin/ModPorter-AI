---
type: markdown
---
# Conversion Audit v4 — Apr 10, 2026 (10:36 AM)

**Pipeline:** `2e2e547f` — includes #1031 (model converter), #1032 (recipe converter), #1033 (BlockEntity classification), #1027 (entity detection)

## v1 → v2 → v3 → v4 Trend

| Metric | v1 (Apr 8) | v2 (Apr 9) | v3 (Apr 10 ~midnight) | v4 (Apr 10 10:36 AM) | Delta |
|--------|-----------|-----------|----------------------|---------------------|-------|
| **Pass rate** | 8/8 | 8/8 | 8/8 | **8/8** | Stable ✅ |
| **Texture coverage** | ~0% | 54.8% | 54.7% | **54.7%** | Stable ✅ |
| **Model coverage** | 0% | 0.2% | 0% | **0%** | ⚠️ No change |
| **Recipe coverage** | 0% | 0% | 0% | **0%** | ⚠️ No change |
| **Entity defs** | 1/mod | 1/mod | 15 total (Create: 9) | **15 total** | Stable ✅ |
| **B2B readiness** | ~5% | ~25% | ~25-30% | **~25-30%** | Stable |

## Why Models & Recipes Are Still 0%

PRs #1031 and #1032 were correctly merged as new standalone agents, but the **E2E integration into `convert_mod()` is still needed**:

- **#1031 (model converter):** New `extract_models_from_jar()`, `parse_blockstate()`, `resolve_parent_model()` functions added to `ai-engine/agents/model_converter.py`. Delegated from `AssetConverterAgent`. **Not yet called** from `modporter/cli/main.py`. The PR itself notes: *"Full E2E integration and Minecraft base model definitions still needed."*

- **#1032 (recipe converter):** Updated `BlockItemGenerator.generate_recipes()` to use `RecipeConverterAgent`. But `BlockItemGenerator` is **not called** from `convert_mod()` — the CLI uses `BedrockBuilderAgent.build_block_addon_mvp()` directly, which doesn't invoke `BlockItemGenerator`.

- **#1033 (BlockEntity classification):** ✅ IS wired in — the fix is in `java_analyzer.py` which IS called. However, results are identical to v3, suggesting iron chests and other BlockEntity mods may still need the downstream block converter to handle tile entity definitions properly.

## What Needs to Happen Next

### For Model Conversion to Show Results
Add to `convert_mod()` in `modporter/cli/main.py`:
```python
from agents.model_converter import extract_models_from_jar
# After block conversion, before packaging:
model_results = extract_models_from_jar(jar_path, bp_path / "models", namespace=mod_id)
```

### For Recipe Conversion to Show Results
Add to `convert_mod()` in `modporter/cli/main.py`:
```python
from agents.block_item_generator import BlockItemGenerator
# After block detection:
generator = BlockItemGenerator()
recipe_output = generator.generate_recipes(recipes_from_jar)
```

## Per-Mod Results (v4)

| Mod | Textures | Models | Entities | Recipes | Status |
|-----|----------|--------|----------|---------|--------|
| Iron Chests | 36/36 (100%) ✅ | 0/28 | 1 | 0/44 | 🟡 |
| Waystones | 23/25 (92%) ✅ | 0/50 | 1 | 0/34 | 🟡 |
| Farmer's Delight | 358/395 (91%) ✅ | 0/342 | 1 | 0/533 | 🟡 |
| Supplementaries | 681/1,103 (62%) 🟡 | 0/1,702 | 1 | 0/459 | 🟡 |
| Create | 633/1,289 (49%) 🟡 | 0/2,684 | **9** 🟢 | 0/2,782 | 🟡 |
| Xaero's Minimap | 12/12 (100%) ✅ | — | 1 | — | ✅ |
| JourneyMap | 22/323 (7%) 🔴 | — | 1 | — | 🟡 |
| JEI | 0/46 (0%) 🔴 | — | 0 | — | 🔴 |

## Verdict

The three P0 fixes are **agent-complete but pipeline-incomplete**. The converter logic is built and tested in isolation — the remaining work is wiring the agents into `convert_mod()`. This is the next priority before v5 can show real gains.

**Estimated impact once wired:** Models + recipes would bring coverage from ~25% to ~55-65%, clearing the 60% B2B target.
