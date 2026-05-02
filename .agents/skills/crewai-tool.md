---
name: crewai-tool
description: Write a new CrewAI @tool for PortKit's agent pipeline
---

# Write a New CrewAI Tool

PortKit's ai-engine uses CrewAI for its multi-agent conversion pipeline.
This skill covers writing a new `@tool` that agents can call.

## Step 1 — Read existing tools for patterns
```bash
cat /workspace/ai-engine/SKELETON-agents.md
grep -r "@tool" /workspace/ai-engine/converters/ | head -20
```

## Step 2 — Write the tool
```python
from crewai.tools import tool
from typing import Optional
import logging

logger = logging.getLogger(__name__)

@tool("<descriptive_tool_name>")
def <tool_function_name>(
    primary_input: str,
    optional_context: Optional[str] = None,
) -> str:
    """
    One sentence: what this tool does and when an agent should use it.

    Use this tool when you need to <specific situation>.
    Do NOT use this tool for <what it doesn't cover>.

    Args:
        primary_input: Description — be specific about expected format (e.g., "Raw Java source code")
        optional_context: Description of optional param

    Returns:
        Description of return format (e.g., "Bedrock addon JSON string")
    """
    try:
        result = _do_the_work(primary_input, optional_context)
        logger.info(f"<tool_function_name> completed successfully")
        return result
    except ValueError as e:
        logger.warning(f"<tool_function_name> invalid input: {e}")
        return f"Error: invalid input - {e}"
    except Exception as e:
        logger.error(f"<tool_function_name> failed: {e}")
        raise


def _do_the_work(primary_input: str, context: Optional[str]) -> str:
    """Internal implementation — keep tool wrapper thin."""
    # Implementation here
    pass
```

## Step 3 — Register the tool with the relevant agent
Find the agent that should have access to this tool:
```bash
grep -r "tools=" /workspace/ai-engine/agents/ | head -20
```

Add the tool to the agent's tools list:
```python
# ai-engine/agents/<agent_file>.py
from converters.<module> import <tool_function_name>

<agent_name> = Agent(
    role="...",
    goal="...",
    tools=[
        existing_tool,
        <tool_function_name>,  # Add here
    ],
)
```

## Step 4 — Write a unit test
```python
# ai-engine/tests/converters/test_<tool_function_name>.py
from converters.<module> import <tool_function_name>

def test_tool_happy_path():
    result = <tool_function_name>("valid input")
    assert result is not None
    assert "expected_content" in result

def test_tool_error_returns_string_not_raise():
    # Tools should return error strings, not raise — agents need to handle gracefully
    result = <tool_function_name>("")
    assert result.startswith("Error:")
```

## Key rules for CrewAI tools
- **Docstring is the agent's instruction** — write it as if you're telling a non-technical person when to use this
- Tools should return strings (not dicts/objects) — agents process text
- On bad input: return `"Error: ..."` string, don't raise (agents need to handle gracefully)
- On unexpected failure: raise (let CrewAI retry logic handle it)
- Keep the `@tool` wrapper thin; put real logic in a private `_do_*` function
