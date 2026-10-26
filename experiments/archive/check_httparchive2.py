import requests
import re

r = requests.get('https://httparchive.org/', timeout=30)
print('Status:', r.status_code)
print('Content length:', len(r.text))

# Find links
matches = re.findall(r'href=["\']([^"\']+)["\']', r.text)
for m in matches:
    if any(k in m.lower() for k in ['api', 'download', 'data', 'bigquery', 'sql']):
        print(m)