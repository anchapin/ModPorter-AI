#!/usr/bin/env python3
"""
Simple code quality checker for RAG implementation files
"""
import ast
import os
import sys

def check_syntax(file_path):
    """Check if a Python file has valid syntax"""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        ast.parse(content)
        return True, "Valid syntax"
    except SyntaxError as e:
        return False, f"Syntax error: {e}"
    except Exception as e:
        return False, f"Error reading file: {e}"

def check_imports(file_path):
    """Check for potential import issues"""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        tree = ast.parse(content)
        issues = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith('.'):
                        issues.append(f"Relative import: {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module.startswith('.'):
                    issues.append(f"Relative import: from {node.module}")
        
        return issues
    except Exception as e:
        return [f"Error checking imports: {e}"]

def main():
    rag_files = [
        'src/testing/rag_evaluator.py',
        'src/utils/embedding_generator.py', 
        'src/crew/rag_crew.py',
        'src/utils/vector_db_client.py',
        'tests/unit/test_rag_evaluator.py',
        'tests/unit/test_embedding_generator.py',
        'tests/integration/test_rag_workflow.py',
        'tests/test_rag_crew.py'
    ]
    
    print("Code Quality Check for RAG Implementation")
    print("=" * 50)
    
    all_good = True
    
    for file_path in rag_files:
        if not os.path.exists(file_path):
            print(f"❌ {file_path}: File not found")
            all_good = False
            continue
            
        # Check syntax
        is_valid, msg = check_syntax(file_path)
        if is_valid:
            print(f"✅ {file_path}: {msg}")
        else:
            print(f"❌ {file_path}: {msg}")
            all_good = False
            
        # Check imports
        import_issues = check_imports(file_path)
        if import_issues:
            print(f"⚠️  {file_path}: Import issues: {', '.join(import_issues)}")
    
    if all_good:
        print("\n✅ All files passed syntax checks!")
    else:
        print("\n❌ Some files have issues that need attention")
        sys.exit(1)

if __name__ == "__main__":
    main()
