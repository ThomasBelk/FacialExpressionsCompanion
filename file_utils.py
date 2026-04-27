import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

def resource_path(relative_path: str) -> Path:
    if getattr(sys, 'frozen', False):
        base = Path(sys._MEIPASS)  # points to _internal
    else:
        base = Path(__file__).parent
    return base / relative_path

def get_updater_file() -> Path:
    if getattr(sys, 'frozen', False):
        base = Path(sys.executable).parent
    else:
        base = Path(__file__).parent / "dist"
    return base / "RealFacialExpressionsUpdater.exe"

def get_launcher_file() -> Path:
    if getattr(sys, 'frozen', False):
        base = Path(sys.executable).parent
    else:
        base = Path(__file__).parent / "dist"
    return base / "RealFacialExpressionsLauncher.exe"

def run_temp_updater(url):
    src = get_updater_file()
    temp_updater = Path(tempfile.gettempdir()) / "RealFacialExpressionsUpdater.exe"

    shutil.copy2(src, temp_updater)
    if "python.exe" in os.path.abspath(sys.executable):
        subprocess.Popen([temp_updater, url])
        print("Dev Update Started")
    else:
        # in case the app is in a nonstandard dir we pass the path to the app so it can be restarted after update.
        subprocess.Popen([temp_updater, url, os.path.abspath(sys.executable)])
        print("Regular Update Started for app at path")

def run_temp_launcher(app_path):
    src = get_launcher_file()
    temp_launcher = Path(tempfile.gettempdir()) / "RealFacialExpressionsLauncher.exe"

    shutil.copy2(src, temp_launcher)
    if "python.exe" in os.path.abspath(sys.executable):
        subprocess.Popen([temp_launcher])
        print("Dev Update Started")
    else:
        # in case the app is in a nonstandard dir we pass the path to the app so it can be restarted after update.
        subprocess.Popen([temp_launcher, os.path.abspath(sys.executable)])
        print("Regular Update Started for app at path")