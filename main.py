import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.containerWidget = QWidget()
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Facial Expressions Companion")

        # Layout Stuff
        vbox = QVBoxLayout()
        self.setCentralWidget(self.containerWidget)
        self.containerWidget.setLayout(vbox)




def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()

    # make window open in the middle of the screen at a consistent size
    screen = app.primaryScreen()
    screenGeo = screen.availableGeometry()
    width = screenGeo.width()
    height = screenGeo.height()
    window.resize(int(width * 0.5), int(height * 0.6)) # TODO: Should probably be able to change this in settings
    window.move(screenGeo.center() - window.rect().center())

    window.show()
    sys.exit(app.exec())



if __name__ == '__main__':
    main()