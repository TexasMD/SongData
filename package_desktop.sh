#!/bin/bash
set -e

echo "Installing packaging dependencies..."
python3 -m pip install pyinstaller

echo "Building frontend..."
cd frontend
npm install
npm run build
cd ..

echo "Creating PyInstaller bundle..."
# Note: we need to include both the frontend/dist folder and ensure the api code is available
# --add-data "SOURCE:DEST" format. For PyInstaller on Linux/Mac it's :, on Windows it's ;
# We use : here since we run on Linux. If this script is run on Windows it should use ;
SEPARATOR=":"
if [ "$OS" = "Windows_NT" ]; then
    SEPARATOR=";"
fi

pyinstaller --name MusicDB \
            --windowed \
            --add-data "frontend/dist${SEPARATOR}frontend/dist" \
            --add-data "api${SEPARATOR}api" \
            --add-data "src${SEPARATOR}src" \
            --add-data "scripts${SEPARATOR}scripts" \
            --add-data "apps/musicdb_desktop/backend_manager.py${SEPARATOR}apps/musicdb_desktop" \
            --hidden-import "uvicorn" \
            --hidden-import "fastapi" \
            --hidden-import "pandas" \
            --hidden-import "sqlite3" \
            apps/musicdb_desktop/main.py

echo "Build complete. Check the 'dist' directory."
