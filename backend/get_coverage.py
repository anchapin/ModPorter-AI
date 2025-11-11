import json
with open('coverage.json') as f:
    data = json.load(f)
total = data['totals']['percent_covered']
print(f"Overall Coverage: {total:.1f}%")

# Get files with lowest coverage
files = []
for filename, file_data in data['files'].items():
    if file_data['summary']['num_statements'] > 0:
        coverage_pct = file_data['summary']['percent_covered']
        files.append((filename, coverage_pct, file_data['summary']['num_statements']))

# Sort by coverage (lowest first) and by statement count (highest first)
files.sort(key=lambda x: (x[1], -x[2]))

print("\nFiles needing coverage (lowest % with most statements):")
for i, (filename, coverage, statements) in enumerate(files[:15], 1):
    print(f"{i:2d}. {filename:<60} {coverage:5.1f}% ({statements} stmts)")

print(f"\nTarget: 80.0%")
print(f"Current: {total:.1f}%")
print(f"Need: {80.0 - total:.1f}% more")
