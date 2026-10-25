import requests
import re

r = requests.get('https://httparchive.org/', timeout=30)
print('Status:', r.status_code)

matches = re.findall(r'href=["\']([^"\']*api[^"\']*)["\']', r.text, re.IGNORECASE)
for m in matches[:10]:
    print(m)

matches = re.findall(r'href=["\']([^"\']*download[^"\']*)["\']', r.text, re.IGNORECASE)
for m in matches[:10]:
    print(m)

matches = re.findall(r'href=["\']([^"\']*data[^"\']*)["\']', r.text, re.IGNORECASE)
for m in matches[:10]:
    print(m)