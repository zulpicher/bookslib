import json, sys
name = sys.argv[1]
try:
    with open(f'trivy-{name}.json') as f:
        data = json.load(f)
    total = sum(
        1 for r in data.get('Results', [])
        for v in r.get('Vulnerabilities', [])
        if v.get('Severity') == 'CRITICAL'
    )
    print(total)
except:
    print(0)
