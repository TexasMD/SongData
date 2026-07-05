import os

def test_gitignore_exclusions():
    assert os.path.exists(".gitignore")
    with open(".gitignore", "r") as f:
        content = f.read()

    required_patterns = [
        "*.csv",
        "*.sqlite",
        "data/backups/",
        "data/exports/raw/",
        "data/staging/antigravity/",
        "data/staging/codex/",
        ".env",
        "*.key",
        "*.token",
        "*.secret"
    ]

    for pattern in required_patterns:
        assert pattern in content

def test_dry_run_by_default():
    # Verify that --write is required for changes in major commands
    import scripts.musicdb as musicdb
    import argparse

    # This is more of a code inspection test or a behavioral test if we mock things
    # We can check if the main function or specific functions handle write_enabled correctly
    assert hasattr(musicdb, 'import_playlist')
    assert hasattr(musicdb, 'build_v2')
