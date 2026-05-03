#!/usr/bin/env python3
"""
Script to sanitize error messages in API endpoints.
Removes str(e) from HTTPException details and adds proper logging.
"""

import re
import os
from pathlib import Path


def sanitize_file(file_path):
    """Sanitize a single file."""
    with open(file_path, "r") as f:
        content = f.read()

    original_content = content

    # Pattern 1: raise HTTPException(..., detail=f"...{str(e)}")
    # Replace with generic message + add logger.error before
    pattern1 = (
        r'(\s+)raise HTTPException\(status_code=(\d+), detail=f"([^"]*)\{str\(e\)\}([^"]*)"\)'
    )
    matches1 = list(re.finditer(pattern1, content))

    for match in reversed(matches1):  # Reverse to maintain positions
        indent = match.group(1)
        status_code = match.group(2)
        msg_before = match.group(3)
        msg_after = match.group(4)

        # Create generic message based on status code
        if status_code.startswith("4"):
            generic_msg = f"{msg_before}".strip() if msg_before else "Invalid request"
            if not generic_msg or generic_msg.endswith(":"):
                generic_msg += " Invalid request. Please check your input."
            else:
                generic_msg += ". Please check your input."
        else:
            generic_msg = f"{msg_before}".strip() if msg_before else "An error occurred"
            if not generic_msg or generic_msg.endswith(":"):
                generic_msg += " Please try again."
            else:
                generic_msg += ". Please try again."

        # Find the exception variable name (usually 'e')
        exc_var = "e"

        # Create the replacement with logger call
        replacement = f'''{indent}logger.error(f"{msg_before}{{str({exc_var})}}{msg_after}", exc_info=True)
{indent}raise HTTPException(status_code={status_code}, detail="{generic_msg}")'''

        content = content[: match.start()] + replacement + content[match.end() :]

    # Pattern 2: raise HTTPException(..., detail=str(e))
    pattern2 = r"(\s+)raise HTTPException\(status_code=(\d+), detail=str\(e\)\)"
    matches2 = list(re.finditer(pattern2, content))

    for match in reversed(matches2):
        indent = match.group(1)
        status_code = match.group(2)

        if status_code.startswith("4"):
            generic_msg = "Invalid request. Please check your input."
        else:
            generic_msg = "An error occurred. Please try again."

        replacement = f'''{indent}logger.error(f"Request error: {{str(e)}}", exc_info=True)
{indent}raise HTTPException(status_code={status_code}, detail="{generic_msg}")'''

        content = content[: match.start()] + replacement + content[match.end() :]

    if content != original_content:
        with open(file_path, "w") as f:
            f.write(content)
        return True
    return False


# Process all files
api_dir = Path("/home/alex/Projects/portkit/backend/src/api")
files_to_process = [
    "analytics.py",
    "behavioral_testing.py",
    "behavior_export.py",
    "behavior_files.py",
    "behavior_templates.py",
    "build_performance.py",
    "comparison.py",
    "feedback.py",
    "mod_imports.py",
    "query_monitoring.py",
    "task_queue.py",
]

for filename in files_to_process:
    file_path = api_dir / filename
    if file_path.exists():
        if sanitize_file(file_path):
            print(f"✓ Sanitized {filename}")
        else:
            print(f"- No changes needed in {filename}")
    else:
        print(f"✗ File not found: {filename}")

print("\nDone!")
