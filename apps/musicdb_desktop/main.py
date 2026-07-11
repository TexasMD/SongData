import sys
import threading
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget,
    QToolBar, QLabel, QStatusBar
)
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import QUrl, QTimer

root_dir = Path(__file__).resolve().parents[2]
if str(root_dir) not in sys.path:
    sys.path.append(str(root_dir))

from apps.musicdb_desktop.backend_manager import BackendManager

class MusicDBDesktop(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MusicDB Pro Console")
        self.setGeometry(100, 100, 1280, 800)

        self.backend = BackendManager(port=8000)
        # Using the standard dev server port for now
        self.frontend_url = "http://localhost:5173"

        self.init_ui()

        # Start backend automatically by default
        self.toggle_backend()

    def init_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # Create toolbar
        toolbar = QToolBar("Controls")
        self.addToolBar(toolbar)

        self.start_stop_action = QAction("Start Backend", self)
        self.start_stop_action.triggered.connect(self.toggle_backend)
        toolbar.addAction(self.start_stop_action)

        reload_action = QAction("Reload UI", self)
        reload_action.triggered.connect(self.load_ui)
        toolbar.addAction(reload_action)

        # Create web view
        self.browser = QWebEngineView()
        self.layout.addWidget(self.browser)

        # Status bar
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status_label = QLabel("Backend: Stopped")
        self.status.addPermanentWidget(self.status_label)

        # Timer to poll backend status in case it dies
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self.update_status)
        self.status_timer.start(2000)

    def load_ui(self):
        self.browser.setUrl(QUrl(self.frontend_url))

    def toggle_backend(self):
        if self.backend.is_running():
            self.status.showMessage("Stopping backend...", 2000)
            self.backend.stop()
            self.update_status()
        else:
            self.status.showMessage("Starting backend...", 2000)
            success = self.backend.start()
            if success:
                # Wait briefly then load UI
                QTimer.singleShot(1000, self.load_ui)
            self.update_status()

    def update_status(self):
        running = self.backend.is_running()
        if running:
            self.status_label.setText("Backend: Running (Port 8000)")
            self.status_label.setStyleSheet("color: green;")
            self.start_stop_action.setText("Stop Backend")
        else:
            self.status_label.setText("Backend: Stopped")
            self.status_label.setStyleSheet("color: red;")
            self.start_stop_action.setText("Start Backend")

    def closeEvent(self, event):
        if self.backend.is_running():
            self.backend.stop()
        super().closeEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MusicDBDesktop()
    window.show()
    sys.exit(app.exec())
