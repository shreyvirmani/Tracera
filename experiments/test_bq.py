from google.cloud import bigquery

client = bigquery.Client(project='tracera-508514')

# Test a simple query first
query = """
SELECT page, url, status_code
FROM `httparchive.summary_pages.2025_07_01_desktop`
WHERE status_code = 200
LIMIT 5
"""

try:
    result = client.query(query).result()
    df = result.to_dataframe()
    print('Simple query works!')
    print(df.head())
except Exception as e:
    print('Error:', e)