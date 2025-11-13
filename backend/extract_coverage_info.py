import json

with open('coverage.json', 'r') as f:
    data = json.load(f)
    
file_key = 'src\\services\\conversion_inference.py'
if file_key not in data['files']:
    print("conversion_inference.py not found in coverage data")
    exit(1)

file_data = data['files'][file_key]
functions = file_data.get('functions', {})

print("Sample function data structure:")
first_func = list(functions.keys())[0]
print(f"Function: {first_func}")
print(f"Data keys: {list(functions[first_func].keys())}")
print(f"Full data: {functions[first_func]}")

print("\n=== Functions with 0% Coverage ===")
for func_name, func_data in functions.items():
    summary = func_data.get('summary', {})
    coverage_pct = summary.get('percent_covered', 0)
    if coverage_pct == 0.0:
        print(f'{func_name}: {summary.get("num_statements", 0)} statements at 0% coverage')
