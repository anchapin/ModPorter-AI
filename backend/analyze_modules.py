#!/usr/bin/env python3
"""
Analyze modules for test coverage improvement potential
"""
import os
import ast
import json

def count_statements(file_path):
    """Count the number of executable statements in a Python file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        tree = ast.parse(content)
        return len(tree.body)
    except Exception as e:
        print(f"Error parsing {file_path}: {e}")
        return 0

def main():
    # Get coverage data if available
    coverage_data = {}
    try:
        with open('coverage.json', 'r') as f:
            coverage_data = json.load(f)
    except:
        pass

    print('HIGH-IMPACT MODULES FOR COVERAGE IMPROVEMENT')
    print('='*60)

    # Collect all modules with substantial code
    all_modules = []

    # API modules
    api_dir = 'src/api'
    for root, dirs, files in os.walk(api_dir):
        for file in files:
            if file.endswith('.py') and file != '__init__.py':
                file_path = os.path.join(root, file)
                stmt_count = count_statements(file_path)
                if stmt_count >= 10:
                    rel_path = file_path.replace(os.path.sep, '/').replace('src/', '')
                    coverage = 'N/A'
                    if coverage_data and 'files' in coverage_data:
                        key = file_path.replace(os.path.sep, '/').replace('backend/', '')
                        if key in coverage_data['files']:
                            coverage = f"{coverage_data['files'][key]['summary']['percent_covered_display']}%"
                    all_modules.append((rel_path, stmt_count, 'API', coverage))

    # Service modules
    service_dir = 'src/services'
    for root, dirs, files in os.walk(service_dir):
        for file in files:
            if file.endswith('.py') and file != '__init__.py':
                file_path = os.path.join(root, file)
                stmt_count = count_statements(file_path)
                if stmt_count >= 10:
                    rel_path = file_path.replace(os.path.sep, '/').replace('src/', '')
                    coverage = 'N/A'
                    if coverage_data and 'files' in coverage_data:
                        key = file_path.replace(os.path.sep, '/').replace('backend/', '')
                        if key in coverage_data['files']:
                            coverage = f"{coverage_data['files'][key]['summary']['percent_covered_display']}%"
                    all_modules.append((rel_path, stmt_count, 'Service', coverage))

    # Sort by statement count (highest impact first)
    all_modules.sort(key=lambda x: x[1], reverse=True)

    print('Top modules by statement count (impact potential):')
    print('-' * 60)
    for rel_path, stmt_count, module_type, coverage in all_modules[:25]:
        print(f'{rel_path:<45} {stmt_count:>4} stmt  {module_type:<8} {coverage}')
    
    print('\n' + '='*60)
    print('PRIORITY MODULES (0% coverage, high statement count):')
    print('-' * 60)
    
    priority_modules = []
    for rel_path, stmt_count, module_type, coverage in all_modules:
        if coverage == '0%' or coverage == 'N/A':
            if stmt_count >= 50:  # Focus on substantial modules
                priority_modules.append((rel_path, stmt_count, module_type, coverage))
    
    # Sort priority modules by statement count
    priority_modules.sort(key=lambda x: x[1], reverse=True)
    
    for rel_path, stmt_count, module_type, coverage in priority_modules[:15]:
        print(f'{rel_path:<45} {stmt_count:>4} stmt  {module_type:<8} {coverage}')
    
    print(f'\nTotal priority modules: {len(priority_modules)}')
    print(f'Total statement count in priority modules: {sum(m[1] for m in priority_modules)}')

if __name__ == '__main__':
    main()
