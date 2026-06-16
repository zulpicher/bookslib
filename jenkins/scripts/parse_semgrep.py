import json, sys
try:
    with open('semgrep-report.json') as f:
        data = json.load(f)
    errors = [r for r in data.get('results', []) if r.get('extra', {}).get('severity') == 'ERROR']
    print(len(errors))
except:
    print(0)
