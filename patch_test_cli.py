with open('tests/test_cli.py', 'r') as f:
    content = f.read()

content = content.replace(
    'assert "data/staging/jules/MusicDB.sqlite" in captured.out',
    'assert "jules/poc.sqlite" in captured.out'
)

with open('tests/test_cli.py', 'w') as f:
    f.write(content)
