import re

with open('scripts/musicdb.py', 'r') as f:
    content = f.read()

# Fix the syntax error from my last patch script attempt
content = re.sub(r'def\s*:\s*if not os\.path\.exists\(INPUT_FILE\):.*?def build_v2', 'def build_v2', content, flags=re.DOTALL)

with open('scripts/musicdb.py', 'w') as f:
    f.write(content)
