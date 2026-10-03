import requests
import re

url = 'https://httparchive.org/'
r = requests.get(url, timeout=30)
text = r.text
links = re.findall(r'href="([^"]+)"', r.text)
for link in links:
    print(link)