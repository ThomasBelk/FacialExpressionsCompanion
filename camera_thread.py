# camera_thread.py
import cv2
from PySide6.QtCore import QThread, Signal, Slot
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import (
    FaceLandmarker,
    FaceLandmarkerOptions,
    RunningMode,
)
import image_utils as imu
import blendshapes as b
import file_utils as fu



class CameraThread(QThread):
    frame_ready = Signal(object)
    tracking_data_ready = Signal(object)

    def __init__(self, camera_index=0, parent=None):
        super().__init__(parent)
        self.camera_index = camera_index
        self.show_mesh = True
        self.running = True
        self.timestamp_ms = 0
        self.cap = None

    @Slot(int)
    def switch_camera(self, new_index: int):
        if self.cap is not None and self.cap.isOpened():
            self.cap.release()
        self.camera_index = new_index
        self.cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)

    @Slot(bool)
    def setShowMesh(self, show_mesh: bool):
        self.show_mesh = show_mesh

    def run(self):
        self.cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)

        if not self.cap.isOpened():
            print("❌ Failed to open camera " + str(self.camera_index))
            return

        task_path = fu.resource_path("models/face_landmarker.task")
        options = FaceLandmarkerOptions(
            base_options=BaseOptions(
                model_asset_path=str(task_path)
            ),
            running_mode=RunningMode.VIDEO,
            output_face_blendshapes=True,
            num_faces=1
        )

        landmarker = FaceLandmarker.create_from_options(options)

        while self.running:
            ret, frame = self.cap.read()
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

            # self.frame_ready.emit(frame)
            blendshapes = {"temp" : -1} # temporary cause if I remember correctly server currently drops packets with empty blendshape
            if result.face_blendshapes:
                blendshapes = b.processBlendshapes(result.face_blendshapes[0])

            landmarks = []
            if result.face_landmarks:
                if self.show_mesh:
                    imu.draw_face_landmarks(rgb, result.face_landmarks)
                landmarks = result.face_landmarks[0]

            if result.face_blendshapes or result.face_landmarks:
                self.tracking_data_ready.emit((landmarks, blendshapes))

            frame = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
            self.frame_ready.emit(frame)

        self.cap.release()

    def stop(self):
        self.running = False
        if self.cap is not None and self.cap.isOpened():
            self.cap.release()
        self.wait()
