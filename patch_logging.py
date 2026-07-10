import glob

def patch_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()

    if 'import logging' not in content:
        content = 'import logging\n' + content

    content = content.replace('print(', 'logging.info(')
    content = content.replace('logging.info(f"dry-run', 'logging.info(f"{__name__.split(\'.\')[-1]}: dry-run')

    with open(filepath, 'w') as f:
        f.write(content)

for filepath in glob.glob('src/commands/*.py'):
    if '__init__' not in filepath:
        patch_file(filepath)

# Also patch scripts/musicdb.py
with open('scripts/musicdb.py', 'r') as f:
    content = f.read()

if 'import logging' not in content:
    content = 'import logging\n' + content

if 'logging.basicConfig(level=logging.INFO, format="%(message)s")' not in content:
    content = content.replace('def main():', 'def main():\n    logging.basicConfig(level=logging.INFO, format="%(message)s")')

with open('scripts/musicdb.py', 'w') as f:
    f.write(content)
