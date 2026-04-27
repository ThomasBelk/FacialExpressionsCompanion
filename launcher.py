# At the moment honestly might be better described as a relauncher. After struggling to handle all the edge cases,
# errors, and crashes while trying to spin up and down the VTS tracking thread and the camera+mediapipe thread,
# I've just decided that the best move to launch this feature this century is to just shut down and relaunch the app
# with the new tracking thread. Very annoyed to be here cause it was all working except in the very specific edge case
# when switching back to mediapipe tracking from vts tracking has failed. All was well if you waited for the failed
# connection error. If not, poof, it explodes and dies. I'm done venting now.
import os
import sys
import time
import subprocess
import psutil
import ctypes

LAUNCHER_MUTEX_NAME = "Global\\RealFacialExpressionsLauncher"
APP_NAME = "RealFacialExpressions"
APP_EXE = f"{APP_NAME}.exe"
DEFAULT_APP_DIR = os.path.join(os.getenv("LOCALAPPDATA"), "Programs", APP_NAME)
DEFAULT_APP_PATH = os.path.join(DEFAULT_APP_DIR, APP_EXE)


def is_app_running():
    for p in psutil.process_iter(['name']):
        try:
            if p.info['name'] == APP_NAME:
                return True
        except Exception:
            continue
    return False


def main():
    # prevent multiple launchers
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, LAUNCHER_MUTEX_NAME)
    ERROR_ALREADY_EXISTS = 183
    if ctypes.windll.kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
        print("Launcher already running")
        sys.exit(0)

    if len(sys.argv) == 2:
        app_path = sys.argv[1]
    else:
        app_path = DEFAULT_APP_PATH

    print("Launcher started, waiting for app to close...")

    # wait for app to fully close
    while is_app_running():
        time.sleep(0.2)

    # small buffer to ensure mutex release
    time.sleep(0.2)

    print("Relaunching app...")

    try:
        subprocess.Popen([app_path])
    except Exception as e:
        print(f"Failed to relaunch app: {e}")

    print("Launcher exiting")
    sys.exit(0)


if __name__ == "__main__":
    main()