with open('tests/test_config_and_commands.py', 'r') as f:
    content = f.read()

content = content.replace(
    'from src.commands import build_v2, quality_report',
    'from src.commands.build import build_v2\nfrom src.commands.quality import generate_quality_report as quality_report'
)

with open('tests/test_config_and_commands.py', 'w') as f:
    f.write(content)
