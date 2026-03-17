import json

try:
    with open('frontend/dist/bundle-report.json') as f:
        data = json.load(f)
        print(data)
except Exception as e:
    print(e)
