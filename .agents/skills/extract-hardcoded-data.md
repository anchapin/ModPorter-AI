---
name: extract-hardcoded-data
description: Extract inline Python dicts/lists to JSON data files (issue #1191 pattern)
---

# Extract Hardcoded Data to JSON

Use this skill whenever you see an inline dict or list with more than ~10 entries.
PortKit issues #1191 and #1100 track the full backlog of these extractions.

## Step 1 — Find the dict in the source
```bash
grep -n "^[A-Z_]* = {" /workspace/ai-engine/converters/<file>.py | head -20
```

## Step 2 — Create the JSON data file
```bash
mkdir -p /workspace/ai-engine/data
```

Extract the dict values to JSON. The JSON file name should match the variable name:
- `FORGE_TAG_MAPPINGS` → `ai-engine/data/forge_tag_mappings.json`
- `ITEM_ID_MAP` → `ai-engine/data/item_id_map.json`

```python
# Quick extraction helper — run once to generate the JSON
import json

ORIGINAL_DICT = {
    "key1": "value1",
    # ... all entries
}

with open("ai-engine/data/<name>.json", "w") as f:
    json.dump(ORIGINAL_DICT, f, indent=2, sort_keys=True)
```

## Step 3 — Replace inline dict with loader function
```python
# Before
FORGE_TAG_MAPPINGS = {
    "forge:ingots/iron": "minecraft:iron_ingot",
    # ... 69 more entries
}

# After
import json
from pathlib import Path

def _load_forge_tag_mappings() -> dict[str, str]:
    """Load forge tag to Bedrock item mappings from data file."""
    data_dir = Path(__file__).parent.parent / "data"
    with open(data_dir / "forge_tag_mappings.json") as f:
        return json.load(f)

FORGE_TAG_MAPPINGS: dict[str, str] = _load_forge_tag_mappings()
```

## Step 4 — Verify nothing broke
```bash
cd /workspace/ai-engine && python -c "from converters.<module> import <CLASS_OR_FUNCTION>; print('OK')"
cd /workspace/ai-engine && python -m pytest tests/ -k "<module>" -v
```

## Notes
- Keep the `_load_*()` pattern (private function returning the dict) for consistency
- Add type hints to the loader return type
- JSON files use snake_case names
- Never put secrets or credentials in data files — only static mappings
