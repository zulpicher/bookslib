import json, sys
try:
    with open('reviews-service/pip-audit-report.json') as f:
        data = json.load(f)
    vulns = [d for d in data.get('dependencies', []) if d.get('vulns')]
    print(len(vulns))
except:
    print(0)
