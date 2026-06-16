import json, sys
try:
    with open('frontend/npm-audit-report.json') as f:
        data = json.load(f)
    meta = data.get('metadata', {}).get('vulnerabilities', {})
    print(meta.get('high', 0) + meta.get('critical', 0))
except:
    print(0)
