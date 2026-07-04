import subprocess
import sys
import os

def test_dry_run_default():
    result = subprocess.run([sys.executable, "scripts/musicdb.py", "build-v2"], capture_output=True, text=True)
    assert "dry-run=True" in result.stdout
    assert "Executing write operations" not in result.stdout

def test_explicit_write():
    result = subprocess.run([sys.executable, "scripts/musicdb.py", "--write", "build-v2"], capture_output=True, text=True)
    assert "dry-run=False" in result.stdout
    assert "Executing write operations" in result.stdout
