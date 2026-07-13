import re
path = r'C:\Users\crist\.local\share\kilo\tool-output\tool_f3b1f1535001f4nNN9StOUWNbA'
with open(path, 'r', encoding='utf-8') as f:
    text = f.read()
pattern = r'href="([^"]+(?:zip|db_|txt|xlsx)[^"]*)"'
links = re.findall(pattern, text)
print('Links encontrados:', len(links))
for l in sorted(set(links))[:50]:
    print(l)
