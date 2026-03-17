import re

with open('.github/workflows/ci.yml', 'r') as f:
    content = f.read()

content = content.replace("frontend/pnpm-lock.yaml", "pnpm-lock.yaml")
content = content.replace("cd frontend\n        pnpm install --frozen-lockfile", "pnpm install --frozen-lockfile")

# Also need to replace the multi-line "cd frontend ... pnpm install" in the frontend-tests job
old_install_block = """    - name: Install dependencies (optimized)
      run: |
        echo "⚡ Installing frontend dependencies with pnpm..."
        cd frontend

        # Use pnpm install with frozen lockfile
        pnpm install --frozen-lockfile

        echo "✅ Dependencies installed successfully\""""

new_install_block = """    - name: Install dependencies (optimized)
      run: |
        echo "⚡ Installing frontend dependencies with pnpm..."

        # Use pnpm install with frozen lockfile
        pnpm install --frozen-lockfile

        echo "✅ Dependencies installed successfully\""""

content = content.replace(old_install_block, new_install_block)

# Fix cache key path hashFiles('**/pnpm-lock.yaml') -> hashFiles('pnpm-lock.yaml')
content = content.replace("hashFiles('**/pnpm-lock.yaml')", "hashFiles('pnpm-lock.yaml')")

with open('.github/workflows/ci.yml', 'w') as f:
    f.write(content)
