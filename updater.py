import sys
import os
import time
import requests
import subprocess
import psutil
import tempfile
import ctypes

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMainWindow, QProgressBar, QLabel, QVBoxLayout, QWidget
from PySide6.QtCore import QTimer, Qt
import file_utils as fu


APP_NAME = "RealFacialExpressions"
APP_EXE = f"{APP_NAME}.exe"
DEFAULT_APP_DIR = os.path.join(os.getenv("LOCALAPPDATA"), "Programs", APP_NAME)
DEFAULT_APP_PATH = os.path.join(DEFAULT_APP_DIR, APP_EXE)

UPDATE_FILE = os.path.join(tempfile.gettempdir(), "real_facial_expressions_update.exe")
UPDATE_MUTEX_NAME = "Global\\RealFacialExpressionsUpdater"

def is_app_running():
    # check if main app is running
    for p in psutil.process_iter(['name']):
        try:
            if p.info['name'] == APP_EXE:
                return True
        except Exception:
            continue
    return False

def get_latest_installer(url:str):
    with requests.get(url, stream=True) as download_r:
        total_size = int(download_r.headers.get("content-length", 0))
        block_size = 1024
        downloaded = 0
        with open(UPDATE_FILE, "wb") as f:
            for data in download_r.iter_content(block_size):
                f.write(data)
                downloaded += len(data)
                yield downloaded, total_size # this is used for progress updates
    return True

# gui
class UpdaterWindow(QMainWindow):
    def __init__(self, url:str, app_path:str = DEFAULT_APP_PATH):
        super().__init__()
        self.url = url
        self.appPath = app_path
        print(app_path)
        print(DEFAULT_APP_PATH)
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.CustomizeWindowHint | Qt.WindowType.WindowTitleHint)
        self.setWindowTitle(f"{APP_NAME} Updater")
        self.setFixedSize(400, 120)

        self.label = QLabel("Checking for updates...")
        self.label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.label.setStyleSheet("font-size: 12pt;")
        self.label.setFixedHeight(25)

        self.progress = QProgressBar()
        self.progress.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.progress.setFixedHeight(25)
        self.progress.setStyleSheet("""
                    QProgressBar {
                        border: 1px solid #999;
                        border-radius: 5px;
                        text-align: center;
                    }
                    QProgressBar::chunk {
                        background-color: #3b99fc;
                        border-radius: 5px;
                    }
                """)

        self.progress.setValue(0)

        layout = QVBoxLayout()
        layout.setSpacing(5)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.addWidget(self.label)
        layout.addWidget(self.progress)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)
        self.setWindowIcon(QIcon(str(fu.resource_path("icons/rfeupdater.ico"))))

        # start update
        QTimer.singleShot(100, self.download_update)

    def download_update(self):
        self.label.setText("Downloading update...")
        try:
            for downloaded, total_size in get_latest_installer(self.url):
                percent = int(downloaded / total_size * 100)
                self.progress.setValue(percent)
                QApplication.processEvents()
            self.progress.setValue(100)
        except Exception as e:
            self.label.setText(f"Download Failed. Check connection or try again later.")
            print(f"Failed to download update: {e}")
            self.enable_close()
            return

        # Wait for main app to exit
        self.label.setText("Please close the Real Facial Expressions App.")
        while is_app_running():
            QApplication.processEvents()
            time.sleep(0.5)

        # Launch installer
        self.label.setText("Installing update...")
        self.progress.setRange(0, 0)  # Indeterminate progress bar

        self.installer_process = subprocess.Popen([UPDATE_FILE, "/VERYSILENT", "/NORESTART"])

        self.timer = QTimer()
        self.timer.timeout.connect(self.check_installer)
        self.timer.start(500)

    def check_installer(self):
        try:
            proc = psutil.Process(self.installer_process.pid)
            if not proc.is_running():
                finished = True
            else:
                finished = False
        except psutil.NoSuchProcess:
            finished = True

        if finished:
            self.timer.stop()
            self.progress.setRange(0, 100)
            self.progress.setValue(100)
            self.label.setText("Installation complete! Starting App..")

            try:
                subprocess.Popen([self.appPath])
                time.sleep(0.3)
                self.close()
            except Exception as e:
                self.label.setText("Failed to start app, try manually starting.")
                print(f"Failed to start app: {e}")
                self.close()

    def enable_close(self):
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowCloseButtonHint)
        self.show()  # have to call to updated window flags.


if __name__ == "__main__":
    # exit immediately if update is already running
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, UPDATE_MUTEX_NAME)
    ERROR_ALREADY_EXISTS = 183
    if ctypes.windll.kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
        print("Updater already running")
        sys.exit(0)

    if len(sys.argv) >= 2:
        installer_url = sys.argv[1]

        app = QApplication(sys.argv)
        if len(sys.argv) == 3:
            window = UpdaterWindow(installer_url, sys.argv[2])
        else:
            window = UpdaterWindow(installer_url)
        window.show()
        sys.exit(app.exec())
    else:
        print("The updater should only be run by the app.")