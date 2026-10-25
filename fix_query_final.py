import re

with open(r'C:\Tracera\ml\data\http_archive\extract.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the query template
start = content.find('HTTP_ARCHIVE_QUERY = """')
end = content.find('"""', start + 20)
if end == -1:
    end = content.find('\n"""', start + 20)

if start < 0 or end < 0:
    print('Could not find query template')
    exit(1)

old_query = content[start:end+3]
print('Found query template, length:', len(old_query))

# Read new query from file
with open(r'C:\Tracera\new_query_final.txt', 'r', encoding='utf-8') as f:
    new_query = f.read()

# Replace
new_content = content[:start] + new_query + content[end+3:]

with open(r'C:\Tracera\ml\data\http_archive\extract.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

print('Query updated successfully!')