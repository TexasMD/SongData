import subprocess
import sys
from pathlib import Path
import os
import psutil

class BackendManager:
    def __init__(self, port: int = 8000):
        self.port = port
        self.process = None
        self.project_root = str(Path(__file__).resolve().parents[2])

    def start(self):
        if self.is_running():
            return False

        env = os.environ.copy()
        env["PYTHONPATH"] = self.project_root

        # Use sys.executable to ensure we use the same Python environment
        cmd = [sys.executable, "-m", "uvicorn", "api.main:app", "--host", "127.0.0.1", "--port", str(self.port)]

        self.process = subprocess.Popen(
            cmd,
            cwd=self.project_root,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return True

    def stop(self):
        if not self.is_running():
            return False

        try:
            # On Windows, terminating the parent might not terminate the children (like uvicorn workers).
            # We use psutil to kill the process tree to be safe and avoid orphans.
            parent = psutil.Process(self.process.pid)
            for child in parent.children(recursive=True):
                child.terminate()
            parent.terminate()

            # Wait for them to actually die
            gone, alive = psutil.wait_procs(parent.children(recursive=True) + [parent], timeout=3)
            for p in alive:
                p.kill()

        except psutil.NoSuchProcess:
            pass

        self.process = None
        return True

    def is_running(self):
        if self.process is None:
            return False
        if self.process.poll() is not None:
            self.process = None
            return False
        return True
