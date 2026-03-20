import re

with open('backend/pyproject.toml', 'r') as f:
    content = f.read()

# Fix the duplicate key
content = content.replace('"src/api/conversions.py" = ["C901"]\n', '')
content = content.replace('"src/services/error_handlers.py" = ["C901"]\n', '')

content = content.replace(
    '"src/api/conversions.py" = ["N805"]',
    '"src/api/conversions.py" = ["N805", "C901"]'
)

content = content.replace(
    '"src/services/error_handlers.py" = ["N818"]',
    '"src/services/error_handlers.py" = ["N818", "C901"]'
)

with open('backend/pyproject.toml', 'w') as f:
    f.write(content)
