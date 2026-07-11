import sys
import os
import threading
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QMessageBox
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import QUrl, QTimer

root_dir = Path(__file__).resolve().parents[2]
if str(root_dir) not in sys.path:
    sys.path.append(str(root_dir))

# Try to import uvicorn and FastAPI backend
try:
    import uvicorn
    from api.main import app as fastapi_app
    HAS_BACKEND = True
except ImportError:
    HAS_BACKEND = False

class MusicDBDesktop(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MusicDB Pro Console")
        self.setGeometry(100, 100, 1280, 800)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.browser = QWebEngineView()
        self.layout.addWidget(self.browser)

        # Determine URL
        # For this prototype, we'll assume the frontend is running on localhost:5173
        # (Vite default) if in dev, or we'd serve static files.
        # Since we just need to run the UI, we'll connect to the Vite dev server for now.
        # In a real packaged app, you'd serve the built React files via FastAPI
        # and load the local FastAPI server URL.
        self.frontend_url = "http://localhost:5173"

        self.backend_thread = None
        if HAS_BACKEND:
            self.start_backend()
            # Give backend a moment to start
            QTimer.singleShot(1000, self.load_ui)
        else:
            QMessageBox.warning(self, "Warning", "Backend dependencies not found. UI may not function fully.")
            self.load_ui()

    def start_backend(self):
        def run_server():
            # In production, use standard port like 8000
            uvicorn.run(fastapi_app, host="127.0.0.1", port=8000, log_level="warning")

        self.backend_thread = threading.Thread(target=run_server, daemon=True)
        self.backend_thread.start()

    def load_ui(self):
        self.browser.setUrl(QUrl(self.frontend_url))

    def closeEvent(self, event):
        # Backend thread is daemon so it will die with the app
        super().closeEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Optional: Set app style to dark to match
    app.setStyle("Fusion")

    window = MusicDBDesktop()
    window.show()
    sys.exit(app.exec())
