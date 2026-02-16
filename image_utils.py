# image_utils.py
import cv2
from PySide6.QtGui import QImage
from mediapipe.tasks.python.vision import (
    drawing_utils,
    drawing_styles,
    FaceLandmarksConnections
)

def cv_frame_to_qimage(frame):
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    h, w, ch = rgb.shape
    bytes_per_line = ch * w
    return QImage(
        rgb.data,
        w,
        h,
        bytes_per_line,
        QImage.Format_RGB888
    )

def draw_face_landmarks(frame, landmarks):
    for face_landmarks in landmarks:
        drawing_utils.draw_landmarks(
            image=frame,
            landmark_list=face_landmarks,
            connections=FaceLandmarksConnections.FACE_LANDMARKS_TESSELATION,
            landmark_drawing_spec=None,
            connection_drawing_spec=drawing_styles.get_default_face_mesh_tesselation_style()
        )
        drawing_utils.draw_landmarks(
            image=frame,
            landmark_list=face_landmarks,
            connections=FaceLandmarksConnections.FACE_LANDMARKS_LIPS,
            landmark_drawing_spec=None,
            connection_drawing_spec=lips_style
        )
        drawing_utils.draw_landmarks(
            image=frame,
            landmark_list=face_landmarks,
            connections=FaceLandmarksConnections.FACE_LANDMARKS_LEFT_EYEBROW,
            landmark_drawing_spec=None,
            connection_drawing_spec=left_eyebrow_style
        )
        drawing_utils.draw_landmarks(
            image=frame,
            landmark_list=face_landmarks,
            connections=FaceLandmarksConnections.FACE_LANDMARKS_RIGHT_EYEBROW,
            landmark_drawing_spec=None,
            connection_drawing_spec=right_eyebrow_style
        )
        drawing_utils.draw_landmarks(
            image=frame,
            landmark_list=face_landmarks,
            connections=FaceLandmarksConnections.FACE_LANDMARKS_LEFT_IRIS,
            landmark_drawing_spec=None,
            connection_drawing_spec=left_iris_style
        )
        drawing_utils.draw_landmarks(
            image=frame,
            landmark_list=face_landmarks,
            connections=FaceLandmarksConnections.FACE_LANDMARKS_RIGHT_IRIS,
            landmark_drawing_spec=None,
            connection_drawing_spec=right_iris_style
        )
        drawing_utils.draw_landmarks(
            image=frame,
            landmark_list=face_landmarks,
            connections=FaceLandmarksConnections.FACE_LANDMARKS_FACE_OVAL,
            landmark_drawing_spec=None,
            connection_drawing_spec=face_outline_style
        )

    lm = landmarks[0][468]
    x = lm.x
    y = lm.y
    draw_point(frame, x, y)

def draw_point(frame, x_norm, y_norm, color=(0, 0, 255), radius=3):
    h, w, _ = frame.shape
    x_px = int(x_norm * w)
    y_px = int(y_norm * h)
    cv2.circle(frame, (x_px, y_px), radius, color, -1)



######################
#   Drawing Styles   #
######################

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
