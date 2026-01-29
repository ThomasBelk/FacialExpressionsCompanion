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
    drawing_utils,
    drawing_styles,
    FaceLandmarksConnections
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

        lips_style = drawing_utils.DrawingSpec(
            color=(255, 0, 0),
            thickness=1
        )

        left_eyebrow_style = drawing_utils.DrawingSpec(
            color=(0, 255, 255),
            thickness=1
        )

        right_eyebrow_style = drawing_utils.DrawingSpec(
            color=(255, 255, 0),
            thickness=1
        )

        left_iris_style = drawing_utils.DrawingSpec(
            color=(0, 0, 255),
            thickness=1
        )

        right_iris_style = drawing_utils.DrawingSpec(
            color=(0, 255, 0),
            thickness=1
        )

        face_outline_style = drawing_utils.DrawingSpec(
            color=(128, 0, 128),
            thickness=1
        )

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

            # self.frame_ready.emit(frame)
            if result.face_blendshapes:
                self.face_data_ready.emit(result.face_blendshapes[0])

            if result.face_landmarks:
                for face_landmarks in result.face_landmarks:
                    drawing_utils.draw_landmarks(
                        image=rgb,
                        landmark_list=face_landmarks,
                        connections=FaceLandmarksConnections.FACE_LANDMARKS_TESSELATION,
                        landmark_drawing_spec=None,
                        connection_drawing_spec=drawing_styles.get_default_face_mesh_tesselation_style()
                    )
                    drawing_utils.draw_landmarks(
                        image=rgb,
                        landmark_list=face_landmarks,
                        connections=FaceLandmarksConnections.FACE_LANDMARKS_LIPS,
                        landmark_drawing_spec=None,
                        connection_drawing_spec=lips_style
                    )
                    drawing_utils.draw_landmarks(
                        image=rgb,
                        landmark_list=face_landmarks,
                        connections=FaceLandmarksConnections.FACE_LANDMARKS_LEFT_EYEBROW,
                        landmark_drawing_spec=None,
                        connection_drawing_spec=left_eyebrow_style
                    )
                    drawing_utils.draw_landmarks(
                        image=rgb,
                        landmark_list=face_landmarks,
                        connections=FaceLandmarksConnections.FACE_LANDMARKS_RIGHT_EYEBROW,
                        landmark_drawing_spec=None,
                        connection_drawing_spec=right_eyebrow_style
                    )
                    drawing_utils.draw_landmarks(
                        image=rgb,
                        landmark_list=face_landmarks,
                        connections=FaceLandmarksConnections.FACE_LANDMARKS_LEFT_IRIS,
                        landmark_drawing_spec=None,
                        connection_drawing_spec=left_iris_style
                    )
                    drawing_utils.draw_landmarks(
                        image=rgb,
                        landmark_list=face_landmarks,
                        connections=FaceLandmarksConnections.FACE_LANDMARKS_RIGHT_IRIS,
                        landmark_drawing_spec=None,
                        connection_drawing_spec=right_iris_style
                    )
                    drawing_utils.draw_landmarks(
                        image=rgb,
                        landmark_list=face_landmarks,
                        connections=FaceLandmarksConnections.FACE_LANDMARKS_FACE_OVAL,
                        landmark_drawing_spec=None,
                        connection_drawing_spec=face_outline_style
                    )
            frame = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
            self.frame_ready.emit(frame)

        cap.release()

    def draw_face_landmarks(self, frame, landmarks):
        h, w, _ = frame.shape

        for lm in landmarks:
            x = int(lm.x * w)
            y = int(lm.y * h)
            cv2.circle(frame, (x, y), 1, (0, 255, 0), -1)

    def stop(self):
        self.running = False
        self.wait()
