# camera_thread.py
import cv2
from PySide6.QtCore import QThread, Signal


class CameraThread(QThread):
    frame_ready = Signal(object)

    def __init__(self, camera_index=0, parent=None):
        super().__init__(parent)
        self.camera_index = camera_index
        self.running = True

    def run(self):
        cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)

        if not cap.isOpened():
            print("❌ Failed to open camera")
            return

        while self.running:
            ret, frame = cap.read()
            if not ret:
                continue

            self.frame_ready.emit(frame)

        cap.release()

    def stop(self):
        self.running = False
        self.wait()
