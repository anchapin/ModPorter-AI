import re

with open('.github/workflows/ci.yml', 'r') as f:
    content = f.read()

# Replace multiple instances where pnpm commands are missing "cd frontend" for package execution
content = content.replace("            pnpm install --frozen-lockfile\n            # Run linting\n            pnpm run lint", "            cd frontend\n            pnpm install --frozen-lockfile\n            # Run linting\n            pnpm run lint")
content = content.replace("            # Run tests with coverage in CI mode\n            pnpm run test:ci", "            # Run tests with coverage in CI mode\n            cd frontend\n            pnpm run test:ci")
content = content.replace("            # Build with production optimizations\n            NODE_ENV=production pnpm run build", "            # Build with production optimizations\n            cd frontend\n            NODE_ENV=production pnpm run build")

with open('.github/workflows/ci.yml', 'w') as f:
    f.write(content)
