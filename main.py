import sys

from PySide6.QtGui import QCloseEvent, QScreen
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QSizePolicy
from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QPixmap

from camera_thread import CameraThread
from eye_direction import AxisCalibrator
from image_utils import cv_frame_to_qimage

import eye_direction as d
import socket
import json

SERVER_IP = "127.0.0.1"   # or server address
SERVER_PORT = 25590
FACE_ID = "fd32dab3-8276-4f96-8595-99c1199d1eae"

def send_face_packet(sock, faceId, lookDir):
    packet = {
        "faceId": faceId,
        "lookDir": lookDir,
        "blendshapes": {
            "hi": 2
        },
    }

    data = json.dumps(packet).encode("utf-8")
    sock.sendto(data, (SERVER_IP, SERVER_PORT))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = QSettings("ThetaBork", "FacialExpressionsCompanion")
        self.containerWidget = QWidget()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


        self.video_label = QLabel(alignment=Qt.AlignmentFlag.AlignCenter)
        self.video_label.setSizePolicy(
            QSizePolicy.Policy.Ignored,
            QSizePolicy.Policy.Ignored
        )
        self.video_label.setMinimumSize(1, 1)
        self.camera = CameraThread(0)
        self.camera.frame_ready.connect(self.updateFrame)
        self.camera.face_data_ready.connect(self.updateFaceData)
        self.camera.iris_data_ready.connect(self.updateEyeData)
        self.camera.start()

        self.x_cal = AxisCalibrator(adapt_rate=0.05) # x_cal can move faster cause the default range is wider
        self.y_cal = AxisCalibrator(adapt_rate=0.01) # want smaller changes. Will take slightly longer to calibrate

        self.tracker = d.EyeTracker(warmup_frames=300)

        self.initUI()


    def initUI(self):
        self.setWindowTitle("Facial Expressions Companion")
        self.restoreWindowState()

        # Layout Stuff
        vbox = QVBoxLayout()
        vbox.addWidget(self.video_label)
        self.setCentralWidget(self.containerWidget)
        self.containerWidget.setLayout(vbox)

    def restoreWindowState(self):
        app = QApplication.instance()
        screens = app.screens()

        screen_name = self.settings.value("ScreenName", "")
        screen = None
        for s in screens:
            if s.name() == screen_name:
                screen = s
                break

        resetFlag = screen is None
        if resetFlag:
            screen = app.primaryScreen()


        screenGeo = screen.availableGeometry()
        self.setMainWindowGeometry(screenGeo, resetFlag)

    def setMainWindowGeometry(self, screenGeometry : QScreen, reset = False):
        if not reset and self.settings.contains("WindowSize") and self.settings.value("WindowSize"):
            self.resize(self.settings.value("WindowSize"))
        else:
            width = screenGeometry.width()
            height = screenGeometry.height()
            self.resize(int(width * 0.5), int(height * 0.6))

        # window placement
        if not reset and self.settings.contains("WindowPosition") and self.settings.value("WindowPosition"):
            self.move(self.settings.value("WindowPosition"))
        else:
            self.move(screenGeometry.center() - self.rect().center())


    def updateFrame(self, frame):
        image = cv_frame_to_qimage(frame)
        pixmap = QPixmap.fromImage(image)
        self.video_label.setPixmap(
            pixmap.scaled(
                self.video_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
        )

    def updateFaceData(self, blendshapes):
        # print(self.gaze_from_blendshapes(blendshapes))
        # print([
        #     (c.category_name, round(c.score, 2))
        #     for c in blendshapes[:5]
        # ])
        pass

    def updateEyeData(self, landmarks):
        x,y = d.eye_direction_from_landmarks(landmarks, d.right_eye_iris_center_id, d.right_eye_left_id, d.right_eye_right_id, d.right_eye_top_id, d.right_eye_bottom_id, self.tracker)
        lookdir = self.eye_enum(x, y)
        print(lookdir)
        send_face_packet(self.sock, FACE_ID, lookdir)


    def eye_enum(self, x, y, deadzone=0.25):
        vert = None
        horiz = None
        if y > self.tracker.y_center + deadzone:
            vert = "up"
        elif y < self.tracker.y_center - deadzone:
            vert = "down"

        if x < -deadzone:
            horiz = "right"
        elif x > deadzone:
            horiz = "left"

        if vert and horiz:
            return f"{vert}{horiz}"
        elif vert:
            return vert
        elif horiz:
            return horiz

        return "center"


        # if abs(x) < deadzone and abs(y) < deadzone:
        #     return "CENTER" + str(y)
        #
        # vertical = ""
        # horizontal = ""
        #
        # if y < -deadzone:
        #     vertical = "UP" +str(y)
        # elif y > 0.1:
        #     vertical = "DOWN" + str(y)
        #
        # if x < -deadzone:
        #     horizontal = "RIGHT"
        # elif x > deadzone:
        #     horizontal = "LEFT"
        #
        # if vertical and horizontal:
        #     return f"{vertical}_{horizontal}"
        # elif vertical:
        #     return vertical
        # elif horizontal:
        #     return horizontal
        #
        # return "CENTER"

    def classify_gaze(self, x, y):
        CENTER_DEADZONE = 0.25
        DIAGONAL_RATIO = 0.6
        if abs(x) < CENTER_DEADZONE and abs(y) < CENTER_DEADZONE:
            return "center"

        horiz = "left" if x < 0 else "right"
        vert = "down" if y < 0 else "up"

        # Diagonal if both components are strong
        if abs(x) > DIAGONAL_RATIO and abs(y) > DIAGONAL_RATIO:
            return vert + horiz

        # Otherwise cardinal
        if abs(x) > abs(y):
            return horiz
        else:
            return vert

    def gaze_from_blendshapes(self, blendshapes):
        bs = {c.category_name: c.score for c in blendshapes}
        x = (
                    (bs.get("eyeLookOutLeft", 0) - bs.get("eyeLookInLeft", 0)) +
                    (bs.get("eyeLookOutRight", 0) - bs.get("eyeLookInRight", 0))
            ) * 0.5

        print("X = " + str(x))

        y = (
                    (bs.get("eyeLookUpLeft", 0) - bs.get("eyeLookDownLeft", 0)) +
                    (bs.get("eyeLookUpRight", 0) - bs.get("eyeLookDownRight", 0))
            ) * 0.5

        return self.classify_gaze(x, y)


    def closeEvent(self, event: QCloseEvent):
        self.camera.stop()

        self.settings.setValue("WindowSize", self.size())
        self.settings.setValue("ScreenName", self.screen().name())
        self.settings.setValue("WindowPosition", self.pos())
        self.settings.sync()
        event.accept()


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())



if __name__ == '__main__':
    main()