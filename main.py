import sys

from PySide6.QtGui import QCloseEvent, QScreen, QIcon
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QSizePolicy, QLineEdit
from PySide6.QtCore import QSettings, Qt, QThread, Signal
from PySide6.QtGui import QPixmap, QIntValidator

from camera_thread import CameraThread
from image_utils import cv_frame_to_qimage

import eye_direction as d
import socket
import json

from network import UDPSender

DEFAULT_IP = "localhost"
DEFAULT_PORT = 25590

class MainWindow(QMainWindow):
    setUDPTarget = Signal(str, int)
    sendUDPPacket = Signal(dict)

    def __init__(self):
        super().__init__()
        self.settings = QSettings("ThetaBork", "FacialExpressionsCompanion")
        self.containerWidget = QWidget()
        self.senderThread = QThread()
        self.sender = UDPSender()
        self.sender.moveToThread(self.senderThread)

        self.setUDPTarget.connect(self.sender.set_target)
        self.sendUDPPacket.connect(self.sender.send_packet)

        self.senderThread.start()



        self.faceId = self.settings.value("FaceId", "")
        self.serverIp = self.settings.value("ServerIp", DEFAULT_IP)
        self.port = self.settings.value("Port", DEFAULT_PORT)

        self.portValidator = QIntValidator(bottom= 1, top= 65535)

        self.faceIdInput = QLineEdit()
        self.serverIpInput = QLineEdit()
        self.portInput = QLineEdit()
        self.portInput.setValidator(self.portValidator)

        self.faceIdInput.setPlaceholderText("Face Id")
        self.faceIdInput.setText(str(self.faceId))
        self.faceIdInput.textEdited.connect(self.updateFaceId)

        self.serverIpInput.setPlaceholderText("Server IP")
        self.serverIpInput.setText(str(self.serverIp))
        self.serverIpInput.textEdited.connect(self.updateServerIp)

        self.portInput.setPlaceholderText("Port")
        self.portInput.setText(str(self.port))
        self.portInput.textEdited.connect(self.updatePort)


        self.setUDPTarget.emit(str(self.serverIp), int(self.port))


        self.video_label = QLabel(alignment=Qt.AlignmentFlag.AlignCenter)
        self.video_label.setSizePolicy(
            QSizePolicy.Policy.Ignored,
            QSizePolicy.Policy.Ignored
        )
        self.video_label.setMinimumSize(1, 1)
        self.camera = CameraThread(0)
        self.camera.frame_ready.connect(self.updateFrame)
        self.camera.tracking_data_ready.connect(self.handleTrackingData)
        self.camera.start()

        self.tracker = d.EyeTracker(warmup_frames=300)

        self.initUI()


    def initUI(self):
        self.setWindowTitle("Facial Expressions Companion")
        self.setWindowIcon(QIcon("icons/rtfelogo.png"))
        self.restoreWindowState()

        # Layout Stuff
        vbox = QVBoxLayout()
        vbox.addWidget(self.faceIdInput)
        vbox.addWidget(self.serverIpInput)
        vbox.addWidget(self.portInput)
        vbox.addWidget(self.video_label)
        self.setCentralWidget(self.containerWidget)
        self.containerWidget.setLayout(vbox)

        self.setFocus()

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

    def handleTrackingData(self, data):
        lookdir = "center"
        blendshapes = {"temp": -1}
        if data[0] and len(data[0]) > 0:
            x,y = d.eye_direction_from_landmarks(data[0], d.right_eye_iris_center_id, d.right_eye_left_id, d.right_eye_right_id, d.right_eye_top_id, d.right_eye_bottom_id, self.tracker)
            lookdir = self.eye_enum(x, y)

        if data[1] and len(data[1]) > 0:
            blendshapes = data[1]

        self.send_face_packet(str(self.faceId), lookdir, blendshapes)


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

    def send_face_packet(self, faceId, lookDir, blendshapes):
        packet = {
            "faceId": faceId,
            "lookDir": lookDir,
            "blendshapes": blendshapes,
        }
        # print(packet)
        self.sendUDPPacket.emit(packet)


    def closeEvent(self, event: QCloseEvent):
        self.camera.stop()

        self.settings.setValue("WindowSize", self.size())
        self.settings.setValue("ScreenName", self.screen().name())
        self.settings.setValue("WindowPosition", self.pos())
        self.settings.setValue("FaceId", str(self.faceId))
        self.settings.setValue("ServerIp", str(self.serverIpInput.text()))
        self.settings.setValue("Port", str(self.portInput.text()))
        self.settings.sync()
        event.accept()

    def updatePort(self, text):
        if text:
            self.port = int(text)
            self.setUDPTarget.emit(str(self.serverIp), int(self.port))


    def updateServerIp(self, text):
        if text:
            self.serverIp = text
            self.setUDPTarget.emit(str(self.serverIp), int(self.port))

    def updateFaceId(self, text):
        if text:
            self.faceId = str(text)


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())



if __name__ == '__main__':
    main()