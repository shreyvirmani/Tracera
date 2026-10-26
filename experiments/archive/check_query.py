import re

with open(r'C:\Tracera\ml\data\http_archive\query.sql', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the query template
start = content.find('HTTP_ARCHIVE_QUERY = """')
end = content.find('"""', start + 20)
if end == -1:
    end = content.find('\n"""', start + 20)

if start >= 0 and end >= 0:
    old_query = content[start:end+3]
    placeholders = set(re.findall(r'\{(\w+)\}', old_query))
    print('Placeholders in query:', sorted(placeholders))
else:
    print('Could not find query template')