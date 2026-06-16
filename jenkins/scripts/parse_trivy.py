import json, sys

service = sys.argv[1] if len(sys.argv) > 1 else "unknown"
try:
    with open(f'trivy-{service}.json') as f:
        data = json.load(f)
    count = 0
    for result in data.get('Results', []):
        for vuln in result.get('Vulnerabilities', []):
            if vuln.get('Severity') == 'CRITICAL':
                count += 1
    print(count)
except:
    print(0)
