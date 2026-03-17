import re

with open('.github/workflows/ci.yml', 'r') as f:
    content = f.read()

content = content.replace("cd frontend && pnpm run lint:duplicates", "pnpm run lint:duplicates")

with open('.github/workflows/ci.yml', 'w') as f:
    f.write(content)
