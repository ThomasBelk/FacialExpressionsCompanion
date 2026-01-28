import sys

from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout
from PySide6.QtCore import QSettings


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = QSettings("ThetaBork", "FacialExpressionsCompanion")
        self.containerWidget = QWidget()
        self.initUI()
        self.restoreWindowState()


    def initUI(self):
        self.setWindowTitle("Facial Expressions Companion")

        # Layout Stuff
        vbox = QVBoxLayout()
        self.setCentralWidget(self.containerWidget)
        self.containerWidget.setLayout(vbox)

    def restoreWindowState(self):
        app = QApplication.instance()

        if self.settings.contains("Screen") and self.settings.value("Screen"):
            screen = self.settings.value("Screen").value()
        else:
            screen = app.primaryScreen()
        screenGeo = screen.availableGeometry()

        if self.settings.contains("WindowSize") and self.settings.value("WindowSize"):
            self.resize(self.settings.value("WindowSize"))
        else:
            width = screenGeo.width()
            height = screenGeo.height()
            self.resize(int(width * 0.5), int(height * 0.6))

        # window placement
        if self.settings.contains("WindowPosition") and self.settings.value("WindowPosition"):
            self.move(self.settings.value("WindowPosition"))
        else:
            self.move(screenGeo.center() - self.rect().center())

    def closeEvent(self, event: QCloseEvent):
        self.settings.setValue("WindowSize", self.size())
        self.settings.setValue("Screen", self.screen())
        self.settings.setValue("WindowPosition", self.pos())

        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()


    # make window open in the middle of the screen at a consistent size

    window.show()
    sys.exit(app.exec())



if __name__ == '__main__':
    main()