import requests
import re

r = requests.get('https://httparchive.org/faq', timeout=30)
print('Status:', r.status_code)

matches = re.findall(r'href=["\']([^"\']+)["\']', r.text)
for m in matches:
    if any(k in m.lower() for k in ['api', 'download', 'data', 'bigquery', 'sql', 'query', 'access']):
        print(m)