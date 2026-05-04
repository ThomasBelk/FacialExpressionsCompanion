import ctypes
import sys

from PySide6.QtGui import QCloseEvent, QScreen, QIcon
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QSizePolicy, \
    QFormLayout, QHBoxLayout, QStackedWidget, QDialog
from PySide6.QtCore import QSettings, Qt, QThread, Signal, QTimer, QProcess
from PySide6.QtGui import QPixmap, QIntValidator

import update_checker
from blendshapes import VTS_EYE_PARAMETERS
from camera_thread import CameraThread
from eye_direction import vts_eye_enum
from image_utils import cv_frame_to_qimage

import eye_direction as d
import file_utils as fu

from network import UDPSender
from ui import FormField, ToggleButton, CameraSelector, VTubeStudioSettingWidget, SimpleDialog, PacketsPerSecondLabel
from update_checker import cleanup_temp_update, get_update_info
from vtube_studio_plugin import VTubeStudioDataHandler, VTubeStudioSettingsData, VTubeStudioPluginAuthWindow

DEFAULT_IP = "localhost"
DEFAULT_PORT = 25590
MUTEX_NAME = "Global\\RealFacialExpressions"
LAUNCHER_EXE = "RealFacialExpressionsLauncher.exe"

class MainWindow(QMainWindow):
    setUDPTarget = Signal(str, int)
    sendUDPPacket = Signal(dict)
    setShowMesh = Signal(bool)
    setCamera = Signal(int)
    setVTSPort = Signal(int)

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
        self.use_vtube_studio_tracking = self.settings.value(
            "VTubeStudioTracking",
            False,
            type=bool
        )
        self.vTubeStudioSettingsData = VTubeStudioSettingsData(self.settings)
        self.acceptAuthWindow = None
        self.cameraErrorWindow = None
        self.vtsErrorWindow = None
        self.switchTrackingModesWindow = None


        self.faceId = self.settings.value("FaceId", "")
        self.serverIp = self.settings.value("ServerIp", DEFAULT_IP)
        self.port = self.settings.value("Port", DEFAULT_PORT)
        self.selectedCameraName = self.settings.value("Camera", None)
        self.vtsPort = self.settings.value("VTSPort", 8001)

        self.portValidator = QIntValidator(bottom= 1, top= 65535)

        self.faceIdInput = FormField("Face Id", "Face Id")
        self.serverIpInput = FormField("Server IP", "Server IP")
        self.portInput = FormField("Port", "Port")
        self.portInput.setValidator(self.portValidator)

        if self.use_vtube_studio_tracking:
            self.vtsPortInput = FormField("VTube Studio API Port", "Default is 8001")
            self.vtsPortInput.setText(str(self.vtsPort))
            self.vtsPortInput.setValidator(self.portValidator)
            self.vtsPortInput.connectEditEvent(self.updateVTSPort)

        self.faceIdInput.setText(str(self.faceId))
        self.faceIdInput.connectEditEvent(self.updateFaceId)

        self.serverIpInput.setText(str(self.serverIp))
        self.serverIpInput.connectEditEvent(self.updateServerIp)

        self.portInput.setText(str(self.port))
        self.portInput.connectEditEvent(self.updatePort)


        self.setUDPTarget.emit(str(self.serverIp), int(self.port))
        self.cameraSelector = CameraSelector()
        self.camera = None

        if not self.use_vtube_studio_tracking:
            self.vtubeStudioThread = None
            self.startCameraThread()
        else:
            self.vTubeStudioSettingsWidget = None
            self.startVTubeStudioThread()

        self.packetsPerSecondLabel = PacketsPerSecondLabel()
        self.initUI()


    def initUI(self):
        window_title = ("Facial Expressions Companion - "
                        + ("Pre-Release Version " if update_checker.INCLUDE_PRE_RELEASE else "Version ")
                        + str(update_checker.CURRENT_VERSION))
        self.setWindowTitle(window_title)
        icon_path = fu.resource_path("icons/rtfelogo.png")
        self.setWindowIcon(QIcon(str(icon_path)))
        self.restoreWindowState()

        self.video_label = QLabel(alignment=Qt.AlignmentFlag.AlignCenter)
        self.video_label.setSizePolicy(
            QSizePolicy.Policy.Ignored,
            QSizePolicy.Policy.Ignored
        )
        self.video_label.setMinimumSize(1, 1)

        # Layout Stuff
        form = QFormLayout()
        form.addRow(self.faceIdInput)
        form.addRow(self.serverIpInput)
        form.addRow(self.portInput)
        if self.use_vtube_studio_tracking:
            form.addRow(self.vtsPortInput)
        form.setSpacing(8)

        formConatiner = QWidget()
        formConatiner.setLayout(form)

        self.showCameraButton = ToggleButton("Show Camera", "Hide Camera", self.show_video,120,110)
        self.showCameraButton.toggledState.connect(self.setVideo)
        self.showFaceMeshButton = ToggleButton("Show Face Mesh", "Hide Face Mesh", self.show_mesh, 120, 110)
        self.showFaceMeshButton.toggledState.connect(self.updateShowMesh)

        t = "This will auto restart the app."
        self.useVTubeStudioButton = ToggleButton("Use VTube Studio Tracking", "Use Webcam Tracking", self.use_vtube_studio_tracking, 180, 170, "Click to receive tracking from VTube Studio. " + t, "Click to use webcam tracking. " + t)
        self.useVTubeStudioButton.toggledState.connect(self.showSwitchTrackingModesWindow)

        hbox = QHBoxLayout()
        if not self.use_vtube_studio_tracking:
            hbox.addWidget(self.cameraSelector)
            hbox.addWidget(self.showCameraButton)
            hbox.addWidget(self.showFaceMeshButton)

        hbox.addWidget(self.useVTubeStudioButton)
        hbox.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hboxWidget = QWidget()
        hboxWidget.setLayout(hbox)

        # for time being self.uiStack is pretty redundant, but I plan to add more pages.
        # Possibly a general settings page, and definitely a page to edit and create custom expressions toggle keybinds
        self.uiStack = QStackedWidget()
        if not self.use_vtube_studio_tracking:
            self.uiStack.addWidget(self.video_label)
        else:
            self.vTubeStudioSettingsWidget = VTubeStudioSettingWidget(self.vTubeStudioSettingsData)
            self.uiStack.addWidget(self.vTubeStudioSettingsWidget)

        self.sender.packetsPerSecond.connect(self.packetsPerSecondLabel.setPacketsPerSecond)

        vbox = QVBoxLayout()
        vbox.setSpacing(0)
        vbox.addWidget(formConatiner)
        vbox.addWidget(hboxWidget, 0)
        vbox.addWidget(self.packetsPerSecondLabel)
        vbox.addWidget(self.uiStack, 1)
        self.setCentralWidget(self.containerWidget)
        self.containerWidget.setLayout(vbox)

        if self.use_vtube_studio_tracking:
            if self.vtubeStudioThread:
                self.vtubeStudioThread.parameter_list_ready.connect(self.vTubeStudioSettingsWidget.updateVTubeStudioParamOptions)

        self.uiStack.setCurrentIndex(0)
        self.setFocus()

    def startCameraThread(self):
        if self.camera:
            return
        initialCameraIndex = self.cameraSelector.findIndexFromName(self.selectedCameraName)
        self.cameraSelector.setCurrentIndex(initialCameraIndex)
        self.camera = CameraThread(initialCameraIndex)
        self.camera.frame_ready.connect(self.updateFrame)
        self.camera.tracking_data_ready.connect(self.handleTrackingData)
        self.camera.camera_error.connect(self.handleCameraError)
        self.setShowMesh.connect(self.camera.setShowMesh)
        self.setCamera.connect(self.camera.switch_camera)
        self.cameraSelector.cameraChanged.connect(self.updateCamera)
        self.camera.start()
        self.tracker = d.EyeTracker(warmup_frames=300)

    def stopCameraThread(self):
        if self.camera:
            try:
                self.camera.frame_ready.disconnect()
                self.camera.tracking_data_ready.disconnect()
                # self.camera.camera_error.disconnect()
                self.camera.stop()
                self.camera.wait()
            except RuntimeError:
                pass # already deleted
            self.camera = None

    def startVTubeStudioThread(self):
        self.vtubeStudioThread = VTubeStudioDataHandler(self.vTubeStudioSettingsData, port=self.vtsPort)
        if self.vTubeStudioSettingsWidget:
            self.vtubeStudioThread.parameter_list_ready.connect(self.vTubeStudioSettingsWidget.updateVTubeStudioParamOptions)
        self.vtubeStudioThread.vts_error.connect(self.handleVTSError)
        self.vtubeStudioThread.accept_auth_notification.connect(self.handleAcceptAuthWindow)
        self.vtubeStudioThread.studio_tracking_ready.connect(self.handleVTSTrackingData)
        self.setVTSPort.connect(self.vtubeStudioThread.updatePort)
        self.vtubeStudioThread.start()

    def stopVTubeStudioThread(self):
        if self.vtubeStudioThread:
            self.vtubeStudioThread.stop()
            self.vtubeStudioThread = None

    def handleVTSError(self, message, flag):
        if not flag and self.vtsErrorWindow is not None:
            self.vtsErrorWindow.setVisible(False)
        # make sure that the error does not block switching tracking modes.
        elif self.vtsErrorWindow is not None and self.switchTrackingModesWindow is not None and self.switchTrackingModesWindow.isVisible():
            self.vtsErrorWindow.setVisible(False)
        elif not flag and self.vtsErrorWindow is None:
            return
        elif self.vtsErrorWindow and self.vtsErrorWindow.isVisible() and message is not self.vtsErrorWindow.getBodyText():
            self.vtsErrorWindow.setBodyText(message + " Attempting to restart the VTS connection.")
            self.vtsErrorWindow.startCountdown(5, "Retrying")
        else:
            self.vtsErrorWindow = SimpleDialog("ERROR", message + " Attempting to restart the VTS connection.", useTimer=True, height=180, rightButtonText="Close")
            self.vtsErrorWindow.startCountdown(5, "Retrying")
            self.vtsErrorWindow.exec()

    def handleCameraError(self, message, flag):
        if not flag and self.cameraErrorWindow is not None:
            self.cameraErrorWindow.setVisible(False)
        # make sure that the error does not block switching tracking modes.
        elif self.cameraErrorWindow is not None and self.switchTrackingModesWindow is not None and self.switchTrackingModesWindow.isVisible():
            self.cameraErrorWindow.setVisible(False)
        elif not flag and self.cameraErrorWindow is None:
            # the flag being false means I want the error window not to open, so if there is no camera window i don't
            # want to do anything.
            return
        elif self.cameraErrorWindow and self.cameraErrorWindow.isVisible() and message is not self.cameraErrorWindow.getBodyText():
            self.cameraErrorWindow.setBodyText(message)
            self.cameraErrorWindow.startCountdown(5, "Retrying")
        else:
            dialog_selector = CameraSelector()
            index = dialog_selector.findIndexFromName(self.selectedCameraName)
            dialog_selector.setCurrentIndex(index)
            dialog_selector.cameraChanged.connect(self.updateCamera)

            self.cameraErrorWindow = SimpleDialog("Camera/Tracking Error", message, rightButtonText="Close", useTimer=True, height=180, selector=dialog_selector)
            self.cameraErrorWindow.startCountdown(5, "Retrying")
            self.cameraErrorWindow.exec()

    def handleAcceptAuthWindow(self, flag):
        if flag and self.acceptAuthWindow is None:
            self.acceptAuthWindow = VTubeStudioPluginAuthWindow()
            self.acceptAuthWindow.exec()
        elif not flag and self.acceptAuthWindow is not None:
            self.acceptAuthWindow.close()
            self.acceptAuthWindow = None

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


    def handleVTSTrackingData(self, data):
        lookdir = "center"

        if all(i in data for i in VTS_EYE_PARAMETERS):
            # x = (data["leftEyeX"] + data["rightEyeX"]) / 2
            # y = (data["leftEyeY"] + data["rightEyeY"]) / 2
            # relying on a single eye for eye direction is just a bit more consistent for the time being. Will have to
            # spend more time finding a better solution than average. Or maybe just allow the user to pick an eye to use.
            # To some extent that is already the case.
            x = data["rightEyeX"]
            y = data["rightEyeY"]
            lookdir = vts_eye_enum(x, y)
        blendshapes = {"temp": -1}
        if len(data) > 0:
            blendshapes = data

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

    def save(self):
        self.settings.setValue("WindowSize", self.size())
        self.settings.setValue("ScreenName", self.screen().name())
        self.settings.setValue("WindowPosition", self.pos())
        self.settings.setValue("FaceId", str(self.faceId))
        self.settings.setValue("ServerIp", str(self.serverIp))
        self.settings.setValue("Port", str(self.port))
        self.settings.setValue("Camera", self.selectedCameraName)
        self.settings.setValue("VTubeStudioTracking", self.use_vtube_studio_tracking)
        self.settings.setValue("VTSPort", str(self.vtsPort))
        self.vTubeStudioSettingsData.saveMappings()
        self.settings.sync()
        print("Saved Successfully")


    def closeEvent(self, event: QCloseEvent):
        if self.camera:
            self.stopCameraThread()
        if self.vtubeStudioThread:
            self.stopVTubeStudioThread()
        if self.senderThread:
            try:
                self.setUDPTarget.disconnect()
                self.sendUDPPacket.disconnect()
            except:
                pass
            self.senderThread.quit()
            self.senderThread.wait()

        self.save()

        event.accept()

    def updatePort(self, text):
        if text:
            self.port = int(text)
            self.setUDPTarget.emit(str(self.serverIp), int(self.port))


    def updateServerIp(self, text):
        if text:
            self.serverIp = text
            self.setUDPTarget.emit(str(self.serverIp), int(self.port))

    def updateVTSPort(self, text):
        if text:
            self.vtsPort = int(text)
            self.setVTSPort.emit(self.vtsPort)

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
        if self.cameraSelector.currentCameraName() != self.selectedCameraName:
            index = self.cameraSelector.findIndexFromName(self.selectedCameraName)
            if index != -1:
                self.cameraSelector.setCameraIndex(index)

    def showSwitchTrackingModesWindow(self, checked: bool):
        if self.switchTrackingModesWindow:
            self.switchTrackingModesWindow.setVisible(True)
        else:
            bodyText = "This action will auto restart the app with the new tracking mode. If for some reason it doesn't restart within a few seconds, just restart the app manually."
            if self.use_vtube_studio_tracking:
                bodyText = "Press confirm to switch to webcam tracking. " + bodyText
            else:
                bodyText = "Press confirm to switch to VTube Studio tracking. " + bodyText

            closeEvent = lambda: self.useVTubeStudioButton.mySetChecked(not checked)

            self.switchTrackingModesWindow = SimpleDialog("Switch Tracking Modes", bodyText, rightButtonText="Cancel", useLeftButton=True, leftButtonText="Confirm", leftButtonAction=self.switchTrackingModes, rightButtonAction=closeEvent, closeEventAction=closeEvent)
            self.switchTrackingModesWindow.exec()

    def switchTrackingModes(self):
        self.use_vtube_studio_tracking = not self.use_vtube_studio_tracking
        if self.switchTrackingModesWindow and self.switchTrackingModesWindow.isVisible():
            self.switchTrackingModesWindow.setVisible(False)
        self.save()
        # the self.close() is just used for testing, since the launcher will launch the current version install not ie not the same a pycharm run
        #self.close()
        # comment back in self.restartApp() and comment out close
        self.restartApp()

    def restartApp(self):
        fu.run_temp_launcher(sys.executable)
        QApplication.quit()


def main():
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, MUTEX_NAME)
    ERROR_ALREADY_EXISTS = 183
    if ctypes.windll.kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
        print("App already running")
        sys.exit(0)

    cleanup_temp_update()
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()

    url = get_update_info()
    if url:
        dialog = update_checker.UpdateDialog(url)
        dialog.exec()
    exit_code = app.exec()

    sys.exit(exit_code)


if __name__ == '__main__':
    main()