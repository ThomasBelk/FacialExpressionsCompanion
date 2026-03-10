import requests
import threading
import subprocess
import tempfile
import os
from packaging.version import Version

OWNER = "ThomasBelk"
REPO = "FacialExpressionsCompanion"

CURRENT_VERSION = Version("0.1.2")

UPDATE_FILE = os.path.join(tempfile.gettempdir(), "real_facial_expressions_update.exe")

update_downloaded = False

INCLUDE_PRE_RELEASE = True  # toggle this to allow/disallow prereleases

def get_update_info():
    try:
        url = f"https://api.github.com/repos/{OWNER}/{REPO}/releases"
        r = requests.get(url, timeout=5)
        r.raise_for_status()
        releases = r.json()

        for release in releases:
            # Skip prereleases if include_pre_release is False
            if release["prerelease"] and not INCLUDE_PRE_RELEASE:
                continue

            latest_version = Version(release["tag_name"].lstrip("v"))

            if latest_version <= CURRENT_VERSION:
                continue  # Not newer

            # Find the .exe asset
            for asset in release["assets"]:
                if asset["name"].endswith(".exe"):
                    return asset["browser_download_url"]

        print("No updates found.")
        return None

    except Exception as e:
        print("Update check failed:", e)
        return None


def download_update(url):
    global update_downloaded

    try:
        r = requests.get(url, stream=True)

        with open(UPDATE_FILE, "wb") as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)

        update_downloaded = True
        print("Update downloaded.")

    except Exception as e:
        print("Download failed:", e)


def start_update_download(url):
    thread = threading.Thread(target=download_update, args=(url,))
    thread.daemon = True
    thread.start()


def check_for_updates():
    url = get_update_info()

    if url:
        print("New version found. Downloading in background...")
        start_update_download(url)


def install_update_if_ready():
    if os.path.exists(UPDATE_FILE):
        print("Launching installer...")
        subprocess.Popen([UPDATE_FILE, "/VERYSILENT", "/NORESTART"])