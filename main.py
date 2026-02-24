import sys

from PySide6.QtGui import QCloseEvent, QScreen, QIcon
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QSizePolicy, QLineEdit, \
    QFormLayout, QHBoxLayout
from PySide6.QtCore import QSettings, Qt, QThread, Signal
from PySide6.QtGui import QPixmap, QIntValidator

from camera_thread import CameraThread
from image_utils import cv_frame_to_qimage

import eye_direction as d
import file_utils as fu

from network import UDPSender
from ui import FormField, ToggleButton, CameraSelector

DEFAULT_IP = "localhost"
DEFAULT_PORT = 25590

class MainWindow(QMainWindow):
    setUDPTarget = Signal(str, int)
    sendUDPPacket = Signal(dict)
    setShowMesh = Signal(bool)
    setCamera = Signal(int)

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

        self.show_video = False
        self.show_mesh = True


        self.faceId = self.settings.value("FaceId", "")
        self.serverIp = self.settings.value("ServerIp", DEFAULT_IP)
        self.port = self.settings.value("Port", DEFAULT_PORT)
        self.selectedCameraName = self.settings.value("Camera", None)

        self.portValidator = QIntValidator(bottom= 1, top= 65535)

        self.faceIdInput = FormField("Face Id", "Face Id")
        self.serverIpInput = FormField("Server IP", "Server IP")
        self.portInput = FormField("Port", "Port")
        self.portInput.setValidator(self.portValidator)

        self.faceIdInput.setText(str(self.faceId))
        self.faceIdInput.connectEditEvent(self.updateFaceId)

        self.serverIpInput.setText(str(self.serverIp))
        self.serverIpInput.connectEditEvent(self.updateServerIp)

        self.portInput.setText(str(self.port))
        self.portInput.connectEditEvent(self.updatePort)


        self.setUDPTarget.emit(str(self.serverIp), int(self.port))

        self.cameraSelector = CameraSelector()

        self.video_label = QLabel(alignment=Qt.AlignmentFlag.AlignCenter)
        self.video_label.setSizePolicy(
            QSizePolicy.Policy.Ignored,
            QSizePolicy.Policy.Ignored
        )
        self.video_label.setMinimumSize(1, 1)
        initialCameraIndex = self.cameraSelector.findIndexFromName(self.selectedCameraName)

        self.cameraSelector.setCurrentIndex(initialCameraIndex)
        self.camera = CameraThread(initialCameraIndex)
        self.camera.frame_ready.connect(self.updateFrame)
        self.camera.tracking_data_ready.connect(self.handleTrackingData)
        self.setShowMesh.connect(self.camera.setShowMesh)
        self.setCamera.connect(self.camera.switch_camera)
        self.cameraSelector.cameraChanged.connect(self.updateCamera)
        self.camera.start()

        self.tracker = d.EyeTracker(warmup_frames=300)

        self.initUI()


    def initUI(self):
        self.setWindowTitle("Facial Expressions Companion")
        icon_path = fu.resource_path("icons/rtfelogo.png")
        self.setWindowIcon(QIcon(str(icon_path)))
        self.restoreWindowState()

        # Layout Stuff
        form = QFormLayout()
        form.addRow(self.faceIdInput)
        form.addRow(self.serverIpInput)
        form.addRow(self.portInput)
        form.setSpacing(8)

        formConatiner = QWidget()
        formConatiner.setLayout(form)

        showCameraButton = ToggleButton("Show Camera", "Hide Camera", self.show_video,120,110)
        showCameraButton.toggledState.connect(self.setVideo)
        showFaceMeshButton = ToggleButton("Show Face Mesh", "Hide Face Mesh", self.show_mesh, 120, 110)
        showFaceMeshButton.toggledState.connect(self.updateShowMesh)

        hbox = QHBoxLayout()
        hbox.addWidget(self.cameraSelector)
        hbox.addWidget(showCameraButton)
        hbox.addWidget(showFaceMeshButton)
        hbox.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hboxWidget = QWidget()
        hboxWidget.setLayout(hbox)

        vbox = QVBoxLayout()
        vbox.setSpacing(0)
        vbox.addWidget(formConatiner)
        vbox.addWidget(hboxWidget, 0)
        vbox.addWidget(self.video_label, 1)
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
        if not self.show_video:
            return
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
        self.settings.setValue("ServerIp", str(self.serverIp))
        self.settings.setValue("Port", str(self.port))
        self.settings.setValue("Camera", self.selectedCameraName)
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

    def setVideo(self, checked: bool):
        self.show_video = checked
        if not self.show_video:
            self.video_label.clear()

    def updateShowMesh(self, checked: bool):
        self.show_mesh = checked
        self.setShowMesh.emit(checked)

    def updateCamera(self, checked: int, s):
        self.setCamera.emit(checked)
        self.selectedCameraName = s


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())



if __name__ == '__main__':
    main()