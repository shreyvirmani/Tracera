from google.cloud import bigquery
import json

client = bigquery.Client(project='tracera-508514')

# Check the payload structure for a few records
query = """
SELECT payload
FROM `httparchive.crawl.pages`
WHERE is_root_page = true
  AND date >= '2025-07-01'
  AND date < '2025-07-02'
  AND client = 'desktop'
LIMIT 3
"""

try:
    result = client.query(query).result()
    for row in result:
        payload = row.payload
        if payload:
            print(json.dumps(payload, indent=2)[:3000])
            print('---')
except Exception as e:
    print('Error:', e)