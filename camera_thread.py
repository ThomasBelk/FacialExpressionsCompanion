# camera_thread.py
import cv2
from PySide6.QtCore import QThread, Signal
import numpy as np
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import (
    FaceLandmarker,
    FaceLandmarkerOptions,
    RunningMode,

)


class CameraThread(QThread):
    frame_ready = Signal(object)
    face_data_ready = Signal(object)

    def __init__(self, camera_index=0, parent=None):
        super().__init__(parent)
        self.camera_index = camera_index
        self.running = True
        self.timestamp_ms = 0
      #  self.face_mesh = FaceMeshProcessor()

    def run(self):
        cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)

        if not cap.isOpened():
            print("❌ Failed to open camera")
            return

        options = FaceLandmarkerOptions(
            base_options=BaseOptions(
                model_asset_path="models/face_landmarker.task"
            ),
            running_mode=RunningMode.VIDEO,
            output_face_blendshapes=True,
            num_faces=1
        )

        landmarker = FaceLandmarker.create_from_options(options)

        while self.running:
            ret, frame = cap.read()
            if not ret:
                continue

            self.timestamp_ms += 33

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            mp_image = mp.Image(
                image_format=mp.ImageFormat.SRGB,
                data=rgb
            )

            result = landmarker.detect_for_video(
                mp_image,
                self.timestamp_ms
            )

            self.frame_ready.emit(frame)
            if result.face_blendshapes:
                self.face_data_ready.emit(result.face_blendshapes[0])

        cap.release()

    def stop(self):
        self.running = False
        self.wait()
