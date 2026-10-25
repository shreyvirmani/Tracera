import requests
import re

r = requests.get('https://httparchive.org/reports', timeout=30)
print('Status:', r.status_code)

matches = re.findall(r'href=["\']([^"\']+)["\']', r.text)
for m in matches:
    print(m)