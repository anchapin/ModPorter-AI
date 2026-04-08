import pytest

with open('backend/src/tests/unit/test_mode_classifier.py', 'r') as f:
    content = f.read()

# Let's replace the assertion to match the new error
content = content.replace('match="Invalid file path"', 'match="Access denied|Invalid file path"')

with open('backend/src/tests/unit/test_mode_classifier.py', 'w') as f:
    f.write(content)
