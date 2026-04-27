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
import time



class CameraThread(QThread):
    frame_ready = Signal(object)
    tracking_data_ready = Signal(object)
    camera_error = Signal(str, bool)

    def __init__(self, camera_index=0, parent=None):
        super().__init__(parent)
        self.camera_index = camera_index
        self.show_mesh = True
        self.running = True
        self.start_time = 0
        self.cap = None
        self.processing = False

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
        try:
            self.start_time = time.time()
            # self.cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)

            task_path = fu.resource_path("models/face_landmarker.task")
            options = FaceLandmarkerOptions(
                base_options=BaseOptions(
                    model_asset_path=str(task_path)
                ),
                running_mode=RunningMode.VIDEO,
                output_face_blendshapes=True,
                num_faces=1
            )

            with FaceLandmarker.create_from_options(options) as landmarker:
                while self.running:
                    if self.cap is None or not self.cap.isOpened():
                        self.cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
                        if not self.cap.isOpened():
                            m = "Failed to open selected camera. Check to make sure your camera is not being used by another app or try another camera. If you need to use a camera feed in multiple apps look into virtual cameras."
                            print("Failed to open camera " + str(self.camera_index))
                            self.camera_error.emit(m, True)
                            for _ in range(50):
                                if not self.running:
                                    return
                                self.msleep(100)
                            continue
                        else:
                            self.camera_error.emit("", False)


                    ret, frame = self.cap.read()
                    # this is to prevent a camera that is not producing frames from trying to be used by the landmarker
                    if not ret or frame is None:
                        self.camera_error.emit("Camera not producing frames. Recommend switching cameras. If this is a virtual camera I recommend restarting it.", True)
                        for _ in range(50):
                            if not self.running:
                                return
                            self.msleep(100)
                        continue
                    else:
                        self.camera_error.emit("", False)

                    timestamp_ms = int((time.time() - self.start_time) * 1000)

                    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                    mp_image = mp.Image(
                        image_format=mp.ImageFormat.SRGB,
                        data=rgb
                    )
                    # this is an attempt to stop crash where i think landmarker is trying to access freed memory
                    self.processing = True
                    try:
                        result = landmarker.detect_for_video(
                            mp_image,
                            timestamp_ms
                        )
                    finally:
                        self.processing = False

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
                if self.cap:
                    self.cap.release()
        except Exception as e:
            print(e)

    def stop(self):
        self.running = False

        while self.processing:
            self.msleep(5)

        if self.cap is not None and self.cap.isOpened():
            self.cap.release()
            self.cap = None

        self.quit()
        self.wait()
