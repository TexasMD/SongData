# MusicDB Desktop App

This is a standalone Windows application wrapper for the MusicDB Pro Console UI.

## Architecture

It uses `PyQt6` and `PyQt6-WebEngine` to create a native window that embeds the React frontend.
It automatically spins up the FastAPI backend (`api.main`) in a background thread.

## Prerequisites

You need the `PyQt6` and `PyQt6-WebEngine` packages installed:

```bash
pip install PyQt6 PyQt6-WebEngine
```

You must also have the frontend running or built. For development, ensure the Vite server is running:

```bash
cd frontend
npm install
npm run dev &
```

## Running

From the repository root:

```bash
PYTHONPATH=. python apps/musicdb_desktop/main.py
```

## Packaging for Windows (Future)

To package this as a standalone `.exe` without requiring Python installed on the target machine, you can use `PyInstaller`.

1. Build the React frontend (`cd frontend && npm run build`).
2. Update `api/main.py` to serve the static frontend files from `frontend/dist` on the root route.
3. Update `apps/musicdb_desktop/main.py` to point the webview to `http://localhost:8000` (the FastAPI server).
4. Run PyInstaller:

```bash
pip install pyinstaller
pyinstaller --name MusicDB --windowed --add-data "frontend/dist:frontend/dist" apps/musicdb_desktop/main.py
```
