# MusicDB Desktop App

This is a standalone Windows application wrapper for the MusicDB Pro Console UI.

## Architecture & Technology Choice

The desktop wrapper uses **PyQt6** and **PyQt6-WebEngine** to create a native window that embeds the existing React frontend.

**Why PyQt6 instead of Electron?**
- **Simplicity:** Since the MusicDB backend is already written in Python (FastAPI), sticking with a Python-based wrapper avoids introducing a completely separate Node.js/Electron ecosystem just for a window shell.
- **Process Management:** Managing the lifecycle of the Python subprocess (uvicorn) is significantly easier and more robust when orchestrated from Python itself. We use `psutil` to guarantee clean process tree termination, preventing orphaned uvicorn workers.

## Features
- Displays the React frontend in a native window.
- Automatically spins up the FastAPI backend (`api.main`) in a background thread upon launch.
- Provides a toolbar to manually stop/start the backend, as well as reload the UI.
- Displays real-time backend status in the status bar.

## Prerequisites

You need the `PyQt6`, `PyQt6-WebEngine`, and `psutil` packages installed:

```bash
pip install PyQt6 PyQt6-WebEngine psutil
```

You must also have the frontend running or built. For development, ensure the Vite server is running:

```bash
cd frontend
npm install
npm run dev &
```

*(Note: In a fully packaged production app, the FastAPI backend would serve static files compiled from the frontend).*

## Running

From the repository root:

```bash
PYTHONPATH=. python apps/musicdb_desktop/main.py
```

## Packaging for Windows (Future)

To package this as a standalone `.exe` without requiring Python installed on the target machine, use `PyInstaller`.

1. Build the React frontend (`cd frontend && npm run build`).
2. Update `api/main.py` to serve the static frontend files from `frontend/dist` on the root route.
3. Update `apps/musicdb_desktop/main.py` to point the webview to `http://localhost:8000` (the FastAPI server).
4. Run PyInstaller:

```bash
pip install pyinstaller
pyinstaller --name MusicDB --windowed --add-data "frontend/dist:frontend/dist" apps/musicdb_desktop/main.py
```
