import json

# Load coverage data
with open('coverage.json', 'r') as f:
    data = json.load(f)

files = data['files']
print('=== SERVICES COVERAGE ===')

# Look for specific services we need to analyze
target_services = []
for k, v in files.items():
    if 'services' in k and ('advanced_visualization' in k or 'version_compatibility' in k):
        coverage_pct = v['summary']['percent_covered']
        num_stmts = v['summary']['num_statements']
        covered_stmts = v['summary']['covered_lines']
        print(f'{k}: {coverage_pct}% ({covered_stmts}/{num_stmts} stmts)')
        target_services.append((k, coverage_pct, num_stmts, covered_stmts))

print('\n=== ANALYSIS ===')
for service, coverage, stmts, covered in target_services:
    missing = stmts - covered
    print(f'{service}:')
    print(f'  Current: {coverage}% ({covered}/{stmts})')
    print(f'  Missing: {missing} statements')
    print(f'  Potential improvement: +{missing:.0f} lines')
