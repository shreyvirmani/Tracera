from google.cloud import bigquery

client = bigquery.Client(project='tracera-508514')

# Test a simple query first
query = """
SELECT page as url, client, date as crawl_date, is_root_page, payload
FROM `httparchive.crawl.pages`
WHERE is_root_page = true
  AND date >= '2025-07-01'
  AND date < '2025-07-02'
  AND client = 'desktop'
LIMIT 5
"""

try:
    result = client.query(query).result()
    df = result.to_dataframe()
    print('Success!')
    print(df.head())
    print()
    print('Payload sample:')
    import json
    payload = json.loads(df['payload'].iloc[0])
    print(json.dumps(payload, indent=2)[:2000])
except Exception as e:
    print('Error:', e)