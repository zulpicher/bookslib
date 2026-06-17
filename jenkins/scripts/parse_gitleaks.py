import json
try:
    data = json.load(open('gitleaks-report.json'))
    print(len(data) if isinstance(data, list) else 0)
except:
    print(0)
