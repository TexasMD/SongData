"""Launch the local MusicDB UI backed by the FastAPI app."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
import webbrowser
from pathlib import Path
from urllib.request import urlopen


PROJECT_DIR = Path(__file__).resolve().parents[1]


def _wait_for_health(url: str, timeout_seconds: int = 30) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            with urlopen(url, timeout=2) as response:
                return response.status == 200
        except Exception:
            time.sleep(0.5)
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Launch the local MusicDB app.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()

    frontend_dist = PROJECT_DIR / "frontend" / "dist"
    if not frontend_dist.exists():
        print("frontend/dist not found. Build the UI first:")
        print("  cd frontend")
        print("  npm run build")
        return 2

    env = os.environ.copy()
    env.setdefault("MUSICDB_ROOT", str(PROJECT_DIR))
    command = [
        sys.executable,
        "-m",
        "uvicorn",
        "api.main:app",
        "--host",
        args.host,
        "--port",
        str(args.port),
    ]
    if args.reload:
        command.append("--reload")

    print("Starting MusicDB API/UI...")
    process = subprocess.Popen(command, cwd=PROJECT_DIR, env=env)
    health_url = f"http://{args.host}:{args.port}/"
    app_url = f"http://{args.host}:{args.port}/app"
    try:
        if not _wait_for_health(health_url):
            print(f"API did not become healthy at {health_url}")
            return 1
        print(f"MusicDB app: {app_url}")
        if not args.no_browser:
            webbrowser.open(app_url)
        return process.wait()
    except KeyboardInterrupt:
        print("Stopping MusicDB app...")
        return 0
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()


if __name__ == "__main__":
    raise SystemExit(main())
