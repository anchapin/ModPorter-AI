# Contributing to Portkit

Thank you for your interest in contributing to Portkit! This document provides guidelines for contributing to the project.

## Code Style

### Naming Conventions

This project enforces consistent naming conventions across both Python and JavaScript/TypeScript codebases.

#### Python (Backend & AI Engine)

- **Variables, Functions, Methods**: `snake_case`
  ```python
  # Good
  def calculate_total_price():
      base_price = 100
      
  # Bad
  def calculateTotalPrice():  # camelCase
      BasePrice = 100          # PascalCase
  ```

- **Classes, Exceptions**: `PascalCase`
  ```python
  # Good
  class ConversionEngine:
      class InvalidInputError(Exception):
          
  # Bad
  class conversion_engine:  # snake_case
  ```

- **Constants**: `UPPER_CASE`
  ```python
  # Good
  MAX_RETRY_ATTEMPTS = 3
  API_BASE_URL = "https://api.example.com"
  
  # Bad
  maxRetryAttempts = 3  # camelCase
  ```

- **Private variables**: Prefix with underscore
  ```python
  # Good
  self._internal_state = None
  
  # Avoid
  self.privateState = None
  ```

#### JavaScript/TypeScript (Frontend)

- **Variables, Functions**: `camelCase`
  ```typescript
  // Good
  function calculateTotalPrice(): number {
      const basePrice = 100;
  }
  
  // Bad
  function calculate_total_price(): number {  // snake_case
      const BasePrice = 100;                   // PascalCase
  }
  ```

- **Classes, Interfaces, Types, Enums**: `PascalCase`
  ```typescript
  // Good
  class ConversionEngine {
      interface ConversionResult {
          success: boolean;
      }
      enum ConversionStatus {
          Pending = "pending",
          Complete = "complete"
      }
  }
  
  // Bad
  class conversion_engine {  // snake_case
  }
  ```

- **Constants**: `UPPER_CASE` or `camelCase` (both accepted)
  ```typescript
  // Good
  const MAX_RETRY_ATTEMPTS = 3;
  const maxRetryAttempts = 3;
  
  // Bad
  const MaxRetryAttempts = 3;  // PascalCase
  ```

- **Component Files**: `PascalCase.tsx`
  ```typescript
  // Good
  src/components/Header.tsx
  src/components/UserProfile.tsx
  
  // Bad
  src/components/header.tsx
  src/components/user-profile.tsx
  ```

- **Private properties**: Prefix with underscore or use TypeScript's `private` keyword
  ```typescript
  // Good
  private _internalState: string;
  private internalState: string;
  
  // Bad
  private InternalState: string;  // PascalCase
  ```

### Import Ordering (Python)

Imports should be organized in the following order using Ruff isort:

1. Standard library imports
2. Third-party imports
3. Local/first-party imports

```python
# Standard library
import os
import sys
from typing import List, Optional

# Third-party
from fastapi import APIRouter, Depends
from sqlalchemy import Column, Integer, String

# Local/first-party
from src.models import User
from src.utils import helper_function
```

### Linting & Formatting

This project uses automated linting tools to enforce code quality:

- **Frontend**: ESLint with TypeScript
  ```bash
  cd frontend
  pnpm run lint
  ```

- **Backend**: Ruff (Python)
  ```bash
  cd backend
  ruff check src/ tests/
  ```

- **Format all code**:
  ```bash
  pnpm run format
  ```

## Getting Started

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes following the naming conventions
4. Run linting/formatting
5. Commit your changes
6. Push to the branch
7. Open a Pull Request

## Questions?

If you have any questions, please feel free to open an issue or reach out to the maintainers.

## Large artifacts (Git LFS / .gitignore)

This repo distinguishes between three classes of binary/large files:

1. **Source assets that must be versioned** (test fixtures, sample images, model
   files used by the app at runtime) → tracked via **Git LFS**. Patterns are
   declared in `.gitattributes` (e.g. `*.png`, `*.pdf`, `*.safetensors` *when*
   they live outside `scripts/*_output*/`, `tests/fixtures/simple_copper_block.jar`).
2. **Generated training/inference outputs** (HF checkpoints, adapter weights,
   tokenizer copies, optimizer state, completion parquets under
   `scripts/phase*_output*/`, `scripts/grpo_output*/`, `scripts/sft_output*/`)
   → **`.gitignore`d**. Re-derive them by re-running the relevant
   `scripts/phase*_*.sh` or training pipelines. **Never `git add` files in
   `scripts/*_output*/`.**
3. **Backups, archives, and other ad-hoc bulk** → store outside the repo, or
   use a release asset.

### First-time setup for Git LFS

The repo requires Git LFS for several patterns declared in `.gitattributes`.
After cloning, run **once** per machine:

```bash
git lfs install          # registers the LFS smudge/clean filters in ~/.gitconfig
git lfs pull             # fetches the actual content for any LFS pointers in HEAD
```

If you skip these, LFS-tracked files will appear in your worktree as 3-line
text pointers (`version https://git-lfs.github.com/spec/v1` …) instead of the
real content, and `git status` may show them as modified.

### "Why is `git status` dirty in a fresh clone?"

If `git status` shows `tokenizer.json` (or any other file) as modified the
moment you clone, it almost always means one of:

- **Git LFS is not installed locally.** Run `git lfs install && git lfs pull`
  and re-check.
- **A file was committed as raw bytes *before* a matching `filter=lfs` rule
  was added to `.gitattributes`.** The clean filter now rewrites the worktree
  content into an LFS pointer when computing the index, which diverges from
  the raw-bytes HEAD blob. The fix is either to migrate the file's history
  (`git lfs migrate import …`, requires force-push) or — for files that
  shouldn't be in git at all — to `.gitignore` them and `git rm --cached`.
- **A generated artifact slipped in.** Confirm the path is covered by
  `.gitignore` (training outputs under `scripts/*_output*/` are ignored), then
  `git rm --cached <path>` and commit.

### Adding a new LFS pattern

Edit `.gitattributes`, e.g.:

```
*.npz filter=lfs diff=lfs merge=lfs -text
```

Then `git add .gitattributes`, `git add path/to/new.npz`, and commit. The
clean filter will replace the file content with an LFS pointer at staging
time; the actual bytes are uploaded on `git push`.
