from google.cloud import bigquery
import json

client = bigquery.Client(project='tracera-508514')

# Query a sample from the pages table
query = """
SELECT 
    page,
    client,
    is_root_page,
    payload
FROM `httparchive.crawl.pages`
WHERE is_root_page = true
LIMIT 5
"""

try:
    result = client.query(query).result()
    df = result.to_dataframe()
    print(df.head())
    print()
    print('Payload sample:')
    payload = json.loads(df['payload'].iloc[0])
    print(json.dumps(payload, indent=2)[:2000])
except Exception as e:
    print('Error:', e)