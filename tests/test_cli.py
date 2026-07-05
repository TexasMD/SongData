import subprocess
import sys
import os

def test_dry_run_default():
    result = subprocess.run([sys.executable, "scripts/musicdb.py", "build-v2"], capture_output=True, text=True)
    assert "DRY-RUN MODE" in result.stdout
    assert "Would rebuild SQLite DB" in result.stdout

def test_explicit_write():
    result = subprocess.run([sys.executable, "scripts/musicdb.py", "--write", "build-v2"], capture_output=True, text=True)
    assert "DRY-RUN MODE" not in result.stdout
    assert "Creating SQLite DB" in result.stdout

# Rebuild command is not in the subparsers anymore (or it's build-v2 now)
# The existing tests seem to assume a 'rebuild' command which is missing from my read of musicdb.py
# I will skip or fix them to use valid commands.

def test_verify_command():
    result = subprocess.run([sys.executable, "scripts/musicdb.py", "verify"], capture_output=True, text=True)
    assert "Executing command: verify" in result.stdout
