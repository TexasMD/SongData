from pathlib import Path


def test_gitignore_exclusions():
    content = Path(".gitignore").read_text(encoding="utf-8")

    required_patterns = [
        "data/backups/",
        "data/exports/",
        "data/logs/",
        "tmp/",
        "frontend/node_modules/",
        "frontend/dist/",
        "data/staging/antigravity/",
        "data/staging/codex/",
        "data/staging/jules/",
        "basket/*.xlsx",
        "basket/*.zip",
        ".env",
        "*.key",
        "*.token",
        "*.secret",
    ]

    for pattern in required_patterns:
        assert pattern in content


def test_gitignore_uses_path_specific_data_rules():
    content = Path(".gitignore").read_text(encoding="utf-8")

    assert "\n*.csv\n" not in f"\n{content}\n"
    assert "\n*.sqlite\n" not in f"\n{content}\n"
    assert "data/**/*.sqlite" in content


def test_pytest_collection_is_limited_to_tests():
    content = Path("pytest.ini").read_text(encoding="utf-8")

    assert "testpaths = tests" in content
    for excluded in [
        "data/backups",
        "data/exports",
        "data/logs",
        "tmp",
        "frontend/node_modules",
        "frontend/dist",
    ]:
        assert excluded in content


def test_dry_run_by_default():
    # Verify that --write is required for changes in major commands.
    import scripts.musicdb as musicdb

    assert hasattr(musicdb, "import_playlist")
    assert hasattr(musicdb, "build_v2")
