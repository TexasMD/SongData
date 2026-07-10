import sys

def replace_in_file(filepath, old, new):
    with open(filepath, 'r') as f:
        content = f.read()
    content = content.replace(old, new)
    with open(filepath, 'w') as f:
        f.write(content)

# Patch sqlite_poc.py
replace_in_file('src/sqlite_poc.py',
                'DB_PATH = "data/staging/jules/MusicDB.sqlite"',
                'from src.config import paths\nDB_PATH = str(paths().sqlite_poc_path)')

replace_in_file('src/sqlite_poc.py',
                'insert_v2_records(records, db_path="data/staging/jules/poc.db")',
                'insert_v2_records(records, db_path=str(paths().sqlite_poc_path))')


# Patch scripts/musicdb.py
with open('scripts/musicdb.py', 'r') as f:
    content = f.read()

content = content.replace('INPUT_MOCK_FILE = "data/staging/recordings_mock.csv"',
                          'from src.config import paths\nINPUT_FILE = str(paths().recordings_csv)')
content = content.replace('INPUT_MOCK_FILE', 'INPUT_FILE')
content = content.replace('ensure_mock_file()', '# Mock file no longer needed, using actual path via config')
content = content.replace('def build_v2(input_csv=INPUT_FILE, write_enabled=False, sqlite_path=DB_PATH):',
                          'def build_v2(input_csv=None, write_enabled=False, sqlite_path=None):\n    input_csv = input_csv or INPUT_FILE\n    sqlite_path = sqlite_path or DB_PATH')
content = content.replace('def generate_quality_report(\n    input_csv=INPUT_FILE, write_enabled=False, export_dir=None\n):',
                          'def generate_quality_report(\n    input_csv=None, write_enabled=False, export_dir=None\n):\n    input_csv = input_csv or INPUT_FILE')

# Fix ensure_mock_file references inside functions
import re
content = re.sub(r'\s*# Mock file no longer needed, using actual path via config\s*', '\n    ', content)
content = re.sub(r'def ensure_mock_file\(\):.*?def build_v2', 'def build_v2', content, flags=re.DOTALL)

with open('scripts/musicdb.py', 'w') as f:
    f.write(content)
