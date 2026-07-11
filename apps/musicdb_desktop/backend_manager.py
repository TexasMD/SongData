import multiprocessing
import sys
import psutil
from pathlib import Path

# Important: This target function must be importable by the multiprocessing module.
def _run_uvicorn(port: int):
    import uvicorn
    from api.main import app
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")

class BackendManager:
    def __init__(self, port: int = 8000):
        self.port = port
        self.process = None

    def start(self):
        if self.is_running():
            return False

        self.process = multiprocessing.Process(
            target=_run_uvicorn,
            args=(self.port,),
            daemon=True
        )
        self.process.start()
        return True

    def stop(self):
        if not self.is_running():
            return False

        try:
            # Cleanly terminate the multiprocessing tree
            parent = psutil.Process(self.process.pid)
            for child in parent.children(recursive=True):
                child.terminate()
            parent.terminate()

            gone, alive = psutil.wait_procs(parent.children(recursive=True) + [parent], timeout=3)
            for p in alive:
                p.kill()
        except psutil.NoSuchProcess:
            pass

        if self.process:
            self.process.join(timeout=1)
            # If it's still somehow alive, brute force it (though it shouldn't be after psutil)
            if self.process.is_alive():
                self.process.terminate()
                self.process.join()

        self.process = None
        return True

    def is_running(self):
        if self.process is None:
            return False
        if not self.process.is_alive():
            self.process = None
            return False
        return True
