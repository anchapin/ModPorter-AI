import re

filepath = 'backend/pyproject.toml'
with open(filepath, 'r') as f:
    content = f.read()

# Instead of auto mode with no loop scope, let's use strict mode and configure scope explicitly
content = content.replace('asyncio_mode = "auto"', 'asyncio_mode = "strict"')
if 'asyncio_default_fixture_loop_scope = "function"' not in content:
    content = content.replace('asyncio_mode = "strict"', 'asyncio_mode = "strict"\nasyncio_default_fixture_loop_scope = "function"')

with open(filepath, 'w') as f:
    f.write(content)

print("Restored backend/pyproject.toml.")
