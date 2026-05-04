import sys
import requests
import tempfile
import os
from PySide6.QtGui import QIcon, Qt
from PySide6.QtWidgets import QDialog, QLabel, QPushButton, QVBoxLayout, QHBoxLayout
from packaging.version import Version
import file_utils as fu

OWNER = "ThomasBelk"
REPO = "FacialExpressionsCompanion"

CURRENT_VERSION = Version("0.2.1")

UPDATE_FILE = os.path.join(tempfile.gettempdir(), "real_facial_expressions_update.exe")

update_downloaded = False

INCLUDE_PRE_RELEASE = False

def cleanup_temp_update():
    if os.path.exists(UPDATE_FILE):
        try:
            os.remove(UPDATE_FILE)
            print(f"Removed temp update file: {UPDATE_FILE}")
        except Exception as e:
            print(f"Failed to remove temp update file: {e}")

def get_update_info():
    try:
        url = f"https://api.github.com/repos/{OWNER}/{REPO}/releases"
        r = requests.get(url, timeout=5)
        r.raise_for_status()
        releases = r.json()

        for release in releases:
            if release["prerelease"] and not INCLUDE_PRE_RELEASE:
                continue

            latest_version = Version(release["tag_name"].lstrip("v"))

            if latest_version <= CURRENT_VERSION:
                continue

            # find .exe asset
            for asset in release["assets"]:
                if asset["name"].endswith(".exe"):
                    return asset["browser_download_url"]

        print("No updates found.")
        return None

    except Exception as e:
        print("Update check failed:", e)
        return None

class UpdateDialog(QDialog):
    def __init__(self, url:str):
        super().__init__()
        self.url = url

        self.setWindowTitle("New Update")
        self.setFixedSize(300, 120)
        icon_path = fu.resource_path("icons/rtfelogo.png")
        self.setWindowIcon(QIcon(str(icon_path)))

        label = QLabel("A new update is available for the Real Facial Expressions Companion App.")
        label.setWordWrap(True)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        update_button = QPushButton("Update")
        remind_button = QPushButton("Remind Me Later")
        update_button.clicked.connect(self.handleUpdateButton)
        remind_button.clicked.connect(self.handleRemindMeButton)

        layout = QVBoxLayout()
        horizontal_layout = QHBoxLayout()
        layout.addWidget(label)
        horizontal_layout.addWidget(update_button)
        horizontal_layout.addWidget(remind_button)
        layout.addLayout(horizontal_layout)

        self.setLayout(layout)

    def handleRemindMeButton(self):
        self.accept()

    def handleUpdateButton(self):
        try:
            fu.run_temp_updater(self.url)
            sys.exit(0)
        except Exception as e:
            print(e)
            self.close()