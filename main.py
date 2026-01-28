import sys

from PySide6.QtGui import QCloseEvent, QScreen
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QSizePolicy
from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QPixmap

from camera_thread import CameraThread
from image_utils import cv_frame_to_qimage

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = QSettings("ThetaBork", "FacialExpressionsCompanion")
        self.containerWidget = QWidget()


        self.video_label = QLabel(alignment=Qt.AlignmentFlag.AlignCenter)
        self.video_label.setSizePolicy(
            QSizePolicy.Policy.Ignored,
            QSizePolicy.Policy.Ignored
        )
        self.video_label.setMinimumSize(1, 1)
        self.camera = CameraThread(0)
        self.camera.frame_ready.connect(self.updateFrame)
        self.camera.start()

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