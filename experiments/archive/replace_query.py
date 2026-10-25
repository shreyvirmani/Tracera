with open(r'C:\Tracera\ml\data\http_archive\extract.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the query template
start = content.find('HTTP_ARCHIVE_QUERY = """')
if start < 0:
    print('Query template not found!')
    exit(1)

end = content.find('"""', start + 20)
if end == -1:
    end = content.find('\n"""', start + 20)

if end < 0:
    print('Could not find end of query template')
    exit(1)

print('Found query template, length:', end - start)

# Read new query from file
with open(r'C:\Tracera\new_query.txt', 'r', encoding='utf-8') as f:
    new_query = f.read()

# Replace
new_content = content[:start] + new_query + content[end+3:]

with open(r'C:\Tracera\ml\data\http_archive\extract.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

print('Query updated successfully!')