---
name: add-converter
description: Add a new Java-to-Bedrock converter to PortKit's ai-engine
---

# Add a New PortKit Converter

## Step 1 — Read context
```bash
cat /workspace/CLAUDE.md
cat /workspace/ai-engine/SKELETON-converters.md
```
Understand which converters already exist and the file structure before writing anything.

## Step 2 — Determine placement
- Simple single-file converters → `ai-engine/converters/<name>_converter.py`
- Complex converters (>300 LOC anticipated) → `ai-engine/converters/<name>/` subpackage with:
  - `__init__.py` (re-exports the primary tool)
  - `<name>_converter.py` (main logic)
  - `models.py` (dataclasses / Pydantic models if needed)
  - `utils.py` (helpers)

## Step 3 — Write the converter using the @tool decorator
```python
from crewai.tools import tool
from typing import Optional
import logging

logger = logging.getLogger(__name__)

@tool("<name>_converter")
def convert_<name>(java_code: str, context: Optional[str] = None) -> str:
    """
    One-sentence description of what this converter does.
    Used by the PortKit conversion crew for <specific Java feature>.

    Args:
        java_code: Raw Java source code containing the feature to convert
        context: Optional context from prior conversion steps

    Returns:
        Bedrock addon JSON/MCFUNCTION/MCMETA representation
    """
    try:
        # 1. Parse Java structure
        # 2. Map to Bedrock equivalent
        # 3. Return serialized output
        pass
    except Exception as e:
        logger.error(f"<name> conversion failed: {e}")
        raise
```

## Step 4 — Add data files for large mappings
If the converter needs mappings with more than 10 entries, write them to JSON:
```bash
# Create data file
cat > /workspace/ai-engine/data/<name>_mappings.json << 'EOF'
{ "java_key": "bedrock_equivalent" }
EOF
```
Load in the converter:
```python
import json
from pathlib import Path

def _load_<name>_mappings() -> dict:
    data_dir = Path(__file__).parent.parent / "data"
    with open(data_dir / "<name>_mappings.json") as f:
        return json.load(f)

_MAPPINGS = _load_<name>_mappings()
```

## Step 5 — Register in __init__.py
Open `ai-engine/converters/__init__.py` (or the subpackage `__init__.py`) and add:
```python
from .name_converter import convert_<name>

__all__ = [..., "convert_<name>"]
```

## Step 6 — Write a pytest test
```python
# ai-engine/tests/converters/test_<name>_converter.py
import pytest
from converters.<name>_converter import convert_<name>

SAMPLE_JAVA = """
// minimal valid Java snippet for this feature
"""

def test_basic_conversion():
    result = convert_<name>(SAMPLE_JAVA)
    assert result is not None
    assert isinstance(result, str)

def test_empty_input_raises():
    with pytest.raises(Exception):
        convert_<name>("")

def test_known_mapping():
    result = convert_<name>(SAMPLE_JAVA)
    assert "expected_bedrock_key" in result
```

## Step 7 — Run tests to verify
```bash
cd /workspace/ai-engine && python -m pytest tests/converters/test_<name>_converter.py -v
```

## Checklist before finishing
- [ ] Converter file created in correct location
- [ ] @tool decorator used with descriptive name and docstring
- [ ] Large dicts extracted to ai-engine/data/*.json
- [ ] Registered in __init__.py
- [ ] Test file created with at least 3 test cases
- [ ] Tests pass
