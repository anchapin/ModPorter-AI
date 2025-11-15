import json

data = json.load(open('coverage.json'))
print("All files by statement count (with coverage):")
print("=" * 80)

files_by_stmts = sorted(
    data['files'].items(), 
    key=lambda x: x[1]['summary']['num_statements'], 
    reverse=True
)

for file, info in files_by_stmts[:25]:
    summary = info['summary']
    stmts = summary['num_statements']
    coverage = summary['percent_covered_display']
    missing = summary['missing_lines']
    covered = summary['covered_lines']
    print(f"{file:60s} {stmts:4d} stmts, {coverage:>5}% ({covered}/{covered+missing})")

print("\n" + "=" * 80)
total_stmts = data['totals']['num_statements']
total_covered = data['totals']['covered_lines']
total_coverage = data['totals']['percent_covered']
print(f"Overall: {total_stmts} total statements, {total_covered} covered, {total_coverage:.1f}% coverage")
