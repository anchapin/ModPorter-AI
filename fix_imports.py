#!/usr/bin/env python3
import os
import re
from pathlib import Path

def fix_imports_in_file(file_path):
    """Fix imports in a Python file by replacing 'backend.src.' with relative imports."""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Replace 'from backend.src.' with 'from '
    modified_content = re.sub(r'from\s+backend\.src\.', 'from ', content)
    
    # Replace 'import backend.src.' with 'import '
    modified_content = re.sub(r'import\s+backend\.src\.', 'import ', modified_content)
    
    if content != modified_content:
        with open(file_path, 'w') as f:
            f.write(modified_content)
        print(f"Fixed imports in {file_path}")

def find_and_fix_python_files(directory):
    """Find all Python files in the directory and fix imports."""
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                fix_imports_in_file(file_path)

if __name__ == "__main__":
    # Fix imports in backend/src/tests
    find_and_fix_python_files('backend/src/tests')
    
    # Fix imports in backend/src/db
    fix_imports_in_file('backend/src/db/base.py')
    
    print("Import fixing completed!")
