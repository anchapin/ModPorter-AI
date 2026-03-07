# Contributing to ModPorter AI

Thank you for your interest in contributing to ModPorter AI! This document provides guidelines for contributing to the project.

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
