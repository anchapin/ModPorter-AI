import json

data = json.load(open('coverage.json'))
print(f'Overall coverage: {data["totals"]["percent_covered"]:.1f}%')
